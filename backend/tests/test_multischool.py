import os
import unittest
from datetime import datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi import HTTPException
from jose import jwt

from app import models, schemas
from app.admin_api import create_user, list_users, summary, update_user
from app.classes import get_classes, update_class
from app.db import SessionLocal, engine
from app.photos import list_school_photos, marketing_photos
from app.routers.media import get_media
from app.security import ALGORITHM, SECRET_KEY
from app.students import create_student, update_student, get_student_photos
from app.families import create_parent, deactivate_parent, update_parent, list_school_parents
from app import security


class MultiSchoolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if engine.dialect.name != "sqlite" or engine.url.database != ":memory:":
            raise RuntimeError("Testes destrutivos permitidos somente no SQLite em memória.")
        models.Base.metadata.create_all(bind=engine)

    @classmethod
    def tearDownClass(cls):
        models.Base.metadata.drop_all(bind=engine)

    def setUp(self):
        self.session = SessionLocal()
        first = models.School(name="Escola Um")
        second = models.School(name="Escola Dois")
        self.session.add_all([first, second])
        self.session.flush()
        self.coordinator = models.User(school_id=first.id, name="Coord Um", email="coord1@test.com", hashed_password="secret1", role=models.RoleEnum.COORDENADOR)
        self.other_coordinator = models.User(school_id=second.id, name="Coord Dois", email="coord2@test.com", hashed_password="secret1", role=models.RoleEnum.COORDENADOR)
        self.teacher = models.User(school_id=first.id, name="Prof Um", email="prof1@test.com", hashed_password="secret1", role=models.RoleEnum.PROFESSOR)
        self.marketing = models.User(school_id=first.id, name="Mkt Um", email="mkt1@test.com", hashed_password="secret1", role=models.RoleEnum.MARKETING)
        first_class = models.Class(school_id=first.id, name="Turma A", year=2026)
        second_class = models.Class(school_id=second.id, name="Turma B", year=2026)
        self.teacher.classes.append(first_class)
        self.session.add_all([self.coordinator, self.other_coordinator, self.teacher, self.marketing, first_class, second_class])
        self.session.flush()
        self.session.add_all([
            models.Student(school_id=first.id, class_id=first_class.id, name="Ana"),
            models.Student(school_id=second.id, class_id=second_class.id, name="Bia"),
            models.Photo(school_id=first.id, class_id=first_class.id, uploaded_by_user_id=self.teacher.id, file_path="1/ok.jpg", status=models.PhotoStatusEnum.APPROVED_FOR_MARKETING),
            models.Photo(school_id=first.id, class_id=first_class.id, uploaded_by_user_id=self.teacher.id, file_path="1/private.jpg", status=models.PhotoStatusEnum.PRIVATE_SCHOOL_ONLY),
            models.Photo(school_id=second.id, class_id=second_class.id, uploaded_by_user_id=self.other_coordinator.id, file_path="2/other.jpg", status=models.PhotoStatusEnum.APPROVED_FOR_MARKETING),
        ])
        self.session.commit()
        self.first_class_id = first_class.id
        self.second_class_id = second_class.id

    def tearDown(self):
        self.session.close()
        models.Base.metadata.drop_all(bind=engine)
        models.Base.metadata.create_all(bind=engine)

    def test_teacher_and_coordinator_only_list_own_school_classes(self):
        teacher_classes = get_classes(False, self.teacher, self.session)
        coordinator_classes = get_classes(False, self.coordinator, self.session)
        self.assertEqual([item.id for item in teacher_classes], [self.first_class_id])
        self.assertEqual([item.id for item in coordinator_classes], [self.first_class_id])

    def test_cross_school_ids_are_not_found(self):
        with self.assertRaises(HTTPException) as denied:
            update_class(self.second_class_id, schemas.ClassUpdate(name="Invadida"), self.coordinator, self.session)
        self.assertEqual(denied.exception.status_code, 404)
        with self.assertRaises(HTTPException) as denied_user:
            update_user(self.other_coordinator.id, schemas.UserUpdate(name="Invadido"), self.coordinator, self.session)
        self.assertEqual(denied_user.exception.status_code, 404)

    def test_coordinator_cannot_create_another_coordinator(self):
        payload = schemas.UserCreate(name="Novo Coord", email="novo@test.com", role=models.RoleEnum.COORDENADOR, password="secret1")
        with self.assertRaises(HTTPException) as denied:
            create_user(payload, self.coordinator, self.session)
        self.assertEqual(denied.exception.status_code, 422)

    def test_marketing_only_receives_approved_photos_from_own_school(self):
        photos = marketing_photos(self.marketing, self.session)
        self.assertEqual(len(photos), 1)
        self.assertEqual(photos[0].file_path, "1/ok.jpg")

    def test_coordinator_lists_all_photos_from_own_school(self):
        photos = list_school_photos(None, self.coordinator, self.session)
        self.assertEqual({item.file_path for item in photos}, {"1/ok.jpg", "1/private.jpg"})

    def test_admin_lists_managed_roles_and_summary_is_scoped(self):
        users = list_users(True, self.coordinator, self.session)
        self.assertEqual({item.email for item in users}, {"prof1@test.com", "mkt1@test.com"})
        data = summary(self.coordinator, self.session)
        self.assertEqual(data.active_classes, 1)
        self.assertEqual(data.active_students, 1)
        self.assertEqual(data.photo_count, 2)
        self.assertEqual(data.missing_files, 2)

    def test_expired_media_signature_is_rejected(self):
        signature = jwt.encode(
            {"path": "1/ok.jpg", "exp": datetime.utcnow() - timedelta(minutes=1)},
            SECRET_KEY, algorithm=ALGORITHM,
        )
        with self.assertRaises(HTTPException) as denied:
            get_media("1/ok.jpg", signature)
        self.assertEqual(denied.exception.status_code, 403)

    def test_student_can_have_zero_one_or_multiple_parents(self):
        parents = [models.Parent(id="mother", name="Mãe", email="mae@example.com"),
                   models.Parent(id="father", name="Pai", email="pai@example.com")]
        existing_child = models.Child(id="sibling", school_id=self.coordinator.school_id,
                                      name="Irmão", classroom="Turma A", avatar_path="")
        existing_child.parents = parents
        self.session.add(existing_child)
        self.session.commit()
        result = create_student(schemas.StudentCreate(name="Novo aluno", class_id=self.first_class_id), self.coordinator, self.session)
        self.assertEqual(result.parent_ids, [])
        self.assertIsNone(result.child_id)
        result = update_student(result.id, schemas.StudentUpdate(parent_ids=["mother"]), self.coordinator, self.session)
        self.assertEqual(result.parent_ids, ["mother"])
        result = update_student(result.id, schemas.StudentUpdate(parent_ids=["mother", "father"]), self.coordinator, self.session)
        self.assertEqual(set(result.parent_ids), {"mother", "father"})
        self.assertEqual(len(list_school_parents(self.coordinator, self.session, True)), 2)
        self.assertEqual(list_school_parents(self.other_coordinator, self.session), [])
        result = update_student(result.id, schemas.StudentUpdate(parent_ids=[]), self.coordinator, self.session)
        self.assertEqual(result.parent_ids, [])

    def test_create_student_links_two_parents_atomically_and_rejects_other_school(self):
        mother = models.Parent(id="mother", name="Mãe", email="mae@example.com")
        father = models.Parent(id="father", name="Pai", email="pai@example.com")
        child = models.Child(id="existing", school_id=self.coordinator.school_id, name="Existente", classroom="A", avatar_path="")
        child.parents = [mother, father]
        outsider = models.Parent(id="outsider", name="Outro", email="outro@example.com")
        other_child = models.Child(id="other", school_id=self.other_coordinator.school_id, name="Outra escola", classroom="B", avatar_path="")
        other_child.parents = [outsider]
        self.session.add_all([child, other_child])
        self.session.commit()
        result = create_student(schemas.StudentCreate(name="Aluno", class_id=self.first_class_id, parent_ids=["mother", "father"]), self.coordinator, self.session)
        self.assertEqual(set(result.parent_ids), {"mother", "father"})
        self.assertIsNotNone(result.child_id)
        count = self.session.query(models.Student).count()
        with self.assertRaises(HTTPException) as denied:
            create_student(schemas.StudentCreate(name="Inválido", class_id=self.first_class_id, parent_ids=["outsider"]), self.coordinator, self.session)
        self.assertEqual(denied.exception.status_code, 404)
        self.assertEqual(self.session.query(models.Student).count(), count)

    def test_family_crud_without_students_and_soft_deactivation(self):
        result = create_parent(schemas.FamilyParentCreate(name="Mãe Ana", email="mae@test.com", password="secret1"), self.coordinator, self.session)
        self.assertEqual(result.student_ids, [])
        self.assertEqual([item.id for item in list_school_parents(self.coordinator, self.session)], [result.id])
        self.assertEqual(list_school_parents(self.other_coordinator, self.session), [])
        result = update_parent(result.id, schemas.FamilyParentUpdate(name="Mãe editada", phone="12345", password="newsecret"), self.coordinator, self.session)
        self.assertEqual(result.name, "Mãe editada")
        self.assertTrue(security.verify_password("newsecret", self.session.get(models.Parent, result.id).hashed_password))
        deactivate_parent(result.id, self.coordinator, self.session)
        self.assertEqual(list_school_parents(self.coordinator, self.session), [])
        self.assertEqual(len(list_school_parents(self.coordinator, self.session, True)), 1)
        token = security.create_access_token({"sub": result.id})
        with self.assertRaises(HTTPException) as denied:
            security.get_current_parent(token, self.session)
        self.assertEqual(denied.exception.status_code, 401)
        update_parent(result.id, schemas.FamilyParentUpdate(is_active=True), self.coordinator, self.session)
        self.assertTrue(security.get_current_parent(token, self.session).is_active)

    def test_family_linking_preserves_other_parent_and_history(self):
        student = self.session.query(models.Student).filter_by(school_id=self.coordinator.school_id).first()
        one = create_parent(schemas.FamilyParentCreate(name="Mãe", email="mae@test.com", password="secret1", student_ids=[student.id]), self.coordinator, self.session)
        two = create_parent(schemas.FamilyParentCreate(name="Pai", email="pai@test.com", password="secret1", student_ids=[student.id]), self.coordinator, self.session)
        self.assertEqual({p.id for p in student.child_profile.parents}, {one.id, two.id})
        child_id = student.child_profile.id
        deactivate_parent(one.id, self.coordinator, self.session)
        self.assertEqual(student.child_profile.id, child_id)
        self.assertEqual(len(student.child_profile.parents), 2)
        update_parent(one.id, schemas.FamilyParentUpdate(student_ids=[]), self.coordinator, self.session)
        self.assertEqual([p.id for p in student.child_profile.parents], [two.id])
        self.assertEqual(student.child_profile.id, child_id)
        # Continua administrável mesmo sem alunos e sem apagar o perfil histórico.
        self.assertIn(one.id, [p.id for p in list_school_parents(self.coordinator, self.session, True)])

    def test_family_crud_rejects_cross_school_and_duplicate_email(self):
        other_student = self.session.query(models.Student).filter_by(school_id=self.other_coordinator.school_id).first()
        before = self.session.query(models.Parent).count()
        with self.assertRaises(HTTPException) as denied:
            create_parent(schemas.FamilyParentCreate(name="Mãe", email="mae@test.com", password="secret1", student_ids=[other_student.id]), self.coordinator, self.session)
        self.assertEqual(denied.exception.status_code, 404)
        self.assertEqual(self.session.query(models.Parent).count(), before)
        parent = create_parent(schemas.FamilyParentCreate(name="Mãe", email="mae@test.com", password="secret1"), self.coordinator, self.session)
        for action in [lambda: update_parent(parent.id, schemas.FamilyParentUpdate(name="Invadida"), self.other_coordinator, self.session),
                       lambda: deactivate_parent(parent.id, self.other_coordinator, self.session),
                       lambda: update_parent(parent.id, schemas.FamilyParentUpdate(student_ids=[other_student.id]), self.coordinator, self.session)]:
            with self.assertRaises(HTTPException) as denied:
                action()
            self.assertEqual(denied.exception.status_code, 404)
        with self.assertRaises(HTTPException) as duplicate:
            create_parent(schemas.FamilyParentCreate(name="Outra mãe", email="mae@test.com", password="secret1"), self.other_coordinator, self.session)
        self.assertEqual(duplicate.exception.status_code, 409)

    def test_owned_parent_without_students_can_link_on_student_registration(self):
        parent = create_parent(schemas.FamilyParentCreate(name="Mãe", email="mae@test.com", password="secret1"), self.coordinator, self.session)
        student = create_student(schemas.StudentCreate(name="Aluno", class_id=self.first_class_id, parent_ids=[parent.id]), self.coordinator, self.session)
        self.assertEqual(student.parent_ids, [parent.id])
        self.assertEqual(list_school_parents(self.coordinator, self.session)[0].student_ids, [student.id])

    def test_family_routes_reject_professor_and_marketing(self):
        import inspect
        # Exercita a dependência real de autorização de cada endpoint.
        endpoints = [list_school_parents, create_parent, update_parent, deactivate_parent]
        for user in [self.teacher, self.marketing]:
            for endpoint in endpoints:
                authorize = inspect.signature(endpoint).parameters["current_user"].default.dependency
                with self.assertRaises(HTTPException) as denied:
                    authorize(user)
                self.assertEqual(denied.exception.status_code, 403)

    def test_student_photo_gallery_is_scoped_and_includes_face_clusters(self):
        student = self.session.query(models.Student).filter_by(school_id=self.coordinator.school_id).first()
        photos = self.session.query(models.Photo).filter_by(school_id=self.coordinator.school_id).all()
        student.photos.append(photos[0])
        cluster = models.FaceCluster(id="cluster-1", student_id=student.id)
        self.session.add(cluster)
        self.session.flush()
        self.session.add(models.DetectedFace(id="face-1", photo_id=photos[1].id, cluster_id=cluster.id, embedding=[], bounding_box=[0, 0, 10, 10]))
        self.session.commit()
        self.assertEqual({p.id for p in get_student_photos(student.id, self.coordinator, self.session)}, {p.id for p in photos})
        with self.assertRaises(HTTPException) as denied:
            get_student_photos(student.id, self.other_coordinator, self.session)
        self.assertEqual(denied.exception.status_code, 404)

    def test_shared_legacy_family_cannot_be_changed_by_one_school(self):
        parent = models.Parent(id="shared", name="Compartilhado", email="shared@test.com", is_active=True)
        parent.children = [models.Child(id="legacy-one", school_id=self.coordinator.school_id, name="Um", classroom="A"),
                           models.Child(id="legacy-two", school_id=self.other_coordinator.school_id, name="Dois", classroom="B")]
        self.session.add(parent)
        self.session.commit()
        for coordinator in [self.coordinator, self.other_coordinator]:
            with self.assertRaises(HTTPException) as denied:
                deactivate_parent(parent.id, coordinator, self.session)
            self.assertEqual(denied.exception.status_code, 409)
        self.assertTrue(parent.is_active)

    def test_disabled_family_cannot_reactivate_through_google_or_demo_activation(self):
        from unittest.mock import patch
        from app.routers.auth_parents import google_login, GoogleLogin, activate_account, ActivateAccount
        parent = create_parent(schemas.FamilyParentCreate(name="Mãe", email="mae@test.com", password="secret1"), self.coordinator, self.session)
        deactivate_parent(parent.id, self.coordinator, self.session)
        with patch("app.routers.auth_parents.id_token.verify_oauth2_token", return_value={"email": "mae@test.com", "sub": "google-id"}):
            with self.assertRaises(HTTPException) as denied:
                google_login(GoogleLogin(id_token="test-token"), self.session)
            self.assertEqual(denied.exception.status_code, 403)
        with self.assertRaises(HTTPException) as denied:
            activate_account(ActivateAccount(token="anything", password="secret2", phone="123"), self.session)
        self.assertEqual(denied.exception.status_code, 400)
        self.assertFalse(self.session.get(models.Parent, parent.id).is_active)


if __name__ == "__main__":
    unittest.main()
