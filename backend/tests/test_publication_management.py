import os
import unittest
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi import HTTPException
from sqlalchemy import create_engine, event, text
from app import models, schemas
from app.db import SessionLocal, engine
from app.publishing import create_school_post, update_school_post, delete_school_post, get_school_post, list_school_posts
from app.routers.posts import get_posts
from app.photos import get_photos_by_class, serialize_photo
from app.schema_migrations import ensure_publication_management_columns


class PublicationManagementTest(unittest.TestCase):
    def setUp(self):
        if engine.dialect.name != "sqlite" or engine.url.database != ":memory:":
            raise RuntimeError("Testes permitidos somente no SQLite em memória.")
        models.Base.metadata.create_all(engine)
        self.db = SessionLocal()
        self.school = models.School(name="Escola")
        self.other_school = models.School(name="Outra")
        self.db.add_all([self.school, self.other_school]); self.db.flush()
        self.group = models.Class(name="Grupo", year=2026, school_id=self.school.id)
        self.second_group = models.Class(name="Grupo", year=2025, school_id=self.school.id)
        self.foreign_group = models.Class(name="Grupo", year=2026, school_id=self.other_school.id)
        self.teacher = self.user("teacher", models.RoleEnum.PROFESSOR)
        self.colleague = self.user("colleague", models.RoleEnum.PROFESSOR)
        self.coordinator = self.user("coordinator", models.RoleEnum.COORDENADOR)
        self.marketing = self.user("marketing", models.RoleEnum.MARKETING)
        self.foreign_teacher = self.user("foreign", models.RoleEnum.PROFESSOR, self.other_school)
        self.teacher.classes.append(self.group)
        self.colleague.classes.append(self.group)
        self.foreign_teacher.classes.append(self.foreign_group)
        self.children = [models.Child(id=f"child-{i}", name=f"Aluno {i}", classroom="Grupo", school_id=self.school.id) for i in range(2)]
        self.students = [models.Student(name=child.name, school_id=self.school.id, school_class=self.group, child_profile=child) for child in self.children]
        self.photos = [models.Photo(file_path=f"photo-{i}.jpg", school_id=self.school.id, school_class=self.group, uploader=self.teacher) for i in range(3)]
        self.foreign_photo = models.Photo(file_path="foreign.jpg", school_id=self.other_school.id, school_class=self.foreign_group, uploader=self.foreign_teacher)
        self.db.add_all([self.group, self.second_group, self.foreign_group, self.teacher, self.colleague,
                         self.coordinator, self.marketing, self.foreign_teacher, *self.students, *self.photos, self.foreign_photo])
        self.db.commit()

    def user(self, name, role, school=None):
        return models.User(name=name, email=f"{name}@test.com", school_id=(school or self.school).id, hashed_password="test", role=role)

    def tearDown(self):
        self.db.close()
        models.Base.metadata.drop_all(engine)

    def payload(self, photos=None, students=None, caption="Legenda"):
        return schemas.PostCreate(photo_ids=photos if photos is not None else [self.photos[0].id, self.photos[1].id],
            student_ids=students if students is not None else [self.students[0].id], caption=caption)

    def create(self):
        return create_school_post(self.payload(), self.teacher, self.db)

    def count(self, photo):
        self.db.expire(photo)
        return serialize_photo(photo).publication_count

    def denied(self, code, fn, *args):
        with self.assertRaises(HTTPException) as error:
            fn(*args)
        self.assertEqual(error.exception.status_code, code)

    def test_author_and_class_are_recorded_and_class_rename_does_not_hide_posts(self):
        post = self.create()
        self.assertEqual(post.created_by_user_id, self.teacher.id)
        self.assertEqual(post.class_id, self.group.id)
        self.assertTrue(post.can_manage)
        self.group.name = "Novo nome"; self.db.commit()
        self.assertEqual([p.id for p in list_school_posts(self.group.id, self.teacher, self.db)], [post.id])
        self.assertEqual(len(list_school_posts(None, self.colleague, self.db)), 1)
        self.assertFalse(get_school_post(post.id, self.colleague, self.db).can_manage)

    def test_only_author_or_coordinator_can_change_or_delete(self):
        post = self.create()
        self.denied(403, update_school_post, post.id, self.payload(caption="Mudou"), self.colleague, self.db)
        self.denied(403, delete_school_post, post.id, self.colleague, self.db)
        updated = update_school_post(post.id, self.payload(caption="Coordenação"), self.coordinator, self.db)
        self.assertEqual(updated.caption, "Coordenação")
        self.assertEqual(updated.created_by_user_id, self.teacher.id)
        self.assertEqual(updated.created_at, post.created_at)
        delete_school_post(post.id, self.coordinator, self.db)
        self.assertEqual(self.db.query(models.Photo).count(), 4)

    def test_legacy_posts_are_read_only_for_teachers_and_manageable_by_coordination(self):
        post = models.Post(id="legacy", school_id=self.school.id, class_id=self.group.id, teacher_name=self.teacher.name,
            classroom_name="Grupo", image_path=self.photos[0].file_path, caption="Antiga", photos=[self.photos[0]], children=[self.children[0]])
        self.db.add(post); self.db.commit()
        self.assertFalse(get_school_post(post.id, self.teacher, self.db).can_manage)
        self.denied(403, update_school_post, post.id, self.payload(), self.teacher, self.db)
        self.assertTrue(get_school_post(post.id, self.coordinator, self.db).can_manage)
        delete_school_post(post.id, self.coordinator, self.db)

    def test_other_school_unassigned_class_and_marketing_are_denied(self):
        post = self.create()
        for action in [get_school_post, delete_school_post]:
            self.denied(404, action, post.id, self.foreign_teacher, self.db)
            self.denied(403, action, post.id, self.marketing, self.db)
        self.denied(403, create_school_post, self.payload(), self.marketing, self.db)
        self.denied(403, list_school_posts, None, self.marketing, self.db)
        self.teacher.classes = []; self.db.commit()
        self.denied(404, update_school_post, post.id, self.payload(), self.teacher, self.db)
        self.assertEqual(list_school_posts(None, self.teacher, self.db), [])

    def test_invalid_content_is_atomic_and_class_cannot_be_changed(self):
        post = self.create()
        other_photo = models.Photo(file_path="second.jpg", school_id=self.school.id, school_class=self.second_group, uploader=self.teacher)
        self.teacher.classes.append(self.second_group)
        self.db.add(other_photo); self.db.commit()
        for code, payload in [
            (422, self.payload(caption="  ")), (422, self.payload(photos=[])), (422, self.payload(students=[])),
            (404, self.payload(photos=[self.foreign_photo.id])), (404, self.payload(students=[999999])),
            (422, self.payload(photos=[other_photo.id])),
            (422, self.payload(photos=[self.photos[0].id, other_photo.id])),
        ]:
            self.denied(code, update_school_post, post.id, payload, self.teacher, self.db)
            self.assertEqual(get_school_post(post.id, self.teacher, self.db).caption, "Legenda")
            self.assertEqual(get_school_post(post.id, self.teacher, self.db).photo_ids, post.photo_ids)

    def test_edit_retargets_family_feed_and_preserves_author_date_photo_order_and_identification(self):
        post = self.create()
        self.assertEqual(len(get_posts(self.children[0], self.db)), 1)
        updated = update_school_post(post.id, self.payload(photos=[self.photos[2].id, self.photos[0].id],
            students=[self.students[1].id], caption="Nova"), self.teacher, self.db)
        self.db.expire_all()
        self.assertEqual(get_posts(self.children[0], self.db), [])
        feed = get_posts(self.children[1], self.db)
        self.assertEqual([p["caption"] for p in feed], ["Nova"])
        self.assertEqual(updated.photo_ids, [self.photos[2].id, self.photos[0].id])
        self.assertIn("photo-2.jpg", feed[0]["image_url"])
        self.assertEqual(updated.created_at, post.created_at)
        self.assertEqual(updated.created_by_user_id, self.teacher.id)
        self.assertIn(self.students[0], self.photos[0].students)
        self.assertEqual(self.count(self.photos[1]), 0)
        self.assertEqual(self.count(self.photos[2]), 1)

    def test_usage_counts_follow_multiple_posts_and_deletion_preserves_portfolios(self):
        post = self.create()
        second = create_school_post(self.payload(photos=[self.photos[0].id]), self.teacher, self.db)
        project = models.Project(id="project", school_id=self.school.id, child=self.children[0], title="Projeto",
            description="Texto", pedagogical_objectives="[]", image_path=self.photos[0].file_path,
            completion_date=post.created_at, photos=[self.photos[0]])
        self.db.add(project); self.db.commit()
        self.assertEqual(self.count(self.photos[0]), 2)
        delete_school_post(post.id, self.teacher, self.db)
        self.assertEqual(self.count(self.photos[0]), 1)
        self.assertEqual(self.count(self.photos[1]), 0)
        delete_school_post(second.id, self.teacher, self.db)
        self.assertEqual(self.count(self.photos[0]), 0)
        self.assertEqual(self.db.query(models.Project).count(), 1)
        self.db.expire_all()
        self.assertEqual(get_posts(self.children[0], self.db), [])
        self.assertEqual(self.photos[0].projects[0].id, "project")

    def test_student_without_family_and_inactive_student_cannot_be_published(self):
        student = models.Student(name="Sem vínculo", school_id=self.school.id, school_class=self.group)
        self.db.add(student); self.db.commit()
        self.denied(422, create_school_post, self.payload(students=[student.id]), self.teacher, self.db)
        self.students[0].status = models.StudentStatusEnum.INATIVO; self.db.commit()
        self.denied(422, create_school_post, self.payload(), self.teacher, self.db)

    def test_counts_are_loaded_in_the_photo_query_and_ignore_other_school_links(self):
        self.create()
        foreign_post = models.Post(id="wrong-link", school_id=self.other_school.id, class_id=self.foreign_group.id,
            teacher_name="Outra escola", classroom_name="Grupo", image_path=self.photos[0].file_path,
            caption="Dado legado inválido", photos=[self.photos[0]])
        self.db.add(foreign_post); self.db.commit(); self.db.expire_all()
        queries = []
        def record(connection, cursor, statement, parameters, context, many):
            queries.append(statement)
        event.listen(engine, "before_cursor_execute", record)
        try:
            photos = self.db.query(models.Photo).all()
            query_count = len(queries)
            counts = {photo.id: photo.publication_count for photo in photos}
            self.assertEqual(len(queries), query_count)
            self.assertEqual(query_count, 1)
            self.assertEqual(counts[self.photos[0].id], 1)
        finally:
            event.remove(engine, "before_cursor_execute", record)
        self.assertEqual(get_school_post(foreign_post.id, self.foreign_teacher, self.db).image_urls, [])

    def test_coordination_can_edit_existing_posts_in_inactive_classes(self):
        post = self.create()
        self.group.is_active = False; self.db.commit()
        self.denied(404, get_school_post, post.id, self.teacher, self.db)
        result = update_school_post(post.id, self.payload(caption="Corrigida"), self.coordinator, self.db)
        self.assertEqual(result.caption, "Corrigida")


class PublicationMigrationTest(unittest.TestCase):
    def test_legacy_migration_is_additive_repeatable_and_never_guesses_author(self):
        legacy = create_engine("sqlite:///:memory:")
        try:
            with legacy.begin() as connection:
                for table in ["schools (id INTEGER PRIMARY KEY)", "users (id INTEGER PRIMARY KEY)",
                              "classes (id INTEGER PRIMARY KEY, school_id INTEGER, name TEXT)",
                              "photos (id INTEGER PRIMARY KEY, school_id INTEGER, class_id INTEGER, file_path TEXT)",
                              "posts (id TEXT PRIMARY KEY, school_id INTEGER, classroom_name TEXT, teacher_name TEXT, image_path TEXT)",
                              "post_photo_link (post_id TEXT, photo_id INTEGER, PRIMARY KEY (post_id, photo_id))"]:
                    connection.execute(text(f"CREATE TABLE {table}"))
                connection.execute(text("INSERT INTO schools VALUES (1), (2)"))
                connection.execute(text("INSERT INTO users VALUES (1)"))
                connection.execute(text("INSERT INTO classes VALUES (1, 1, 'Grupo'), (2, 1, 'Grupo'), (3, 2, 'Grupo'), (4, 1, 'Única')"))
                connection.execute(text("INSERT INTO photos VALUES (1, 1, 1, 'one.jpg'), (2, 2, 3, 'other.jpg')"))
                connection.execute(text("INSERT INTO posts VALUES ('path', 1, 'Grupo', 'Nome', 'one.jpg'), ('ambiguous', 1, 'Grupo', 'Nome', 'missing'), ('unique', 1, 'Única', 'Nome', 'missing'), ('foreign', 1, 'Única', 'Nome', 'other.jpg')"))
                connection.execute(text("INSERT INTO post_photo_link VALUES ('foreign', 2)"))
            with patch("app.schema_migrations.engine", legacy):
                ensure_publication_management_columns()
                ensure_publication_management_columns()
            with legacy.connect() as connection:
                rows = {row["id"]: row for row in connection.execute(text("SELECT * FROM posts")).mappings()}
                self.assertEqual(len(rows), 4)
                self.assertEqual(rows["path"]["class_id"], 1)
                self.assertEqual(rows["unique"]["class_id"], 4)
                self.assertIsNone(rows["ambiguous"]["class_id"])
                self.assertIsNone(rows["foreign"]["class_id"])
                self.assertTrue(all(row["created_by_user_id"] is None for row in rows.values()))
                self.assertTrue(all(row["teacher_name"] == "Nome" for row in rows.values()))
                self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM post_photo_link WHERE post_id = 'path'")).scalar(), 1)
        finally:
            legacy.dispose()
