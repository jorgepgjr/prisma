import os
import unittest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi import HTTPException

from app import models, schemas, security
from app.db import SessionLocal, engine
from app.publishing import create_school_post
from app.school_portfolio import create_school_portfolio
from app.families import create_family_profile, create_parent, deactivate_parent, update_parent
from app.students import create_student, update_student
from app.routers.auth_parents import LoginRequest, login
from app.routers.children import get_children
from app.routers.posts import get_posts
from app.routers.portfolio import get_portfolio


class PublicationFlowTest(unittest.TestCase):
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
        school = models.School(name="Escola Teste")
        self.session.add(school)
        self.session.flush()
        school_class = models.Class(school_id=school.id, name="Grupo 2", year=2026)
        teacher = models.User(school_id=school.id, name="Marília", email="marilia@school.com", hashed_password="mypassword", role=models.RoleEnum.PROFESSOR)
        coordinator = models.User(school_id=school.id, name="Coordenação", email="coord@school.com", hashed_password="mypassword", role=models.RoleEnum.COORDENADOR)
        teacher.classes.append(school_class)
        student = models.Student(school_id=school.id, name="Pedro", school_class=school_class)
        child = models.Child(id="pedro", school_id=school.id, name="Pedro", avatar_path="avatar.png", classroom="Grupo 2")
        student.child_profile = child
        parent = models.Parent(id="responsavel", name="Responsável", email="familia@example.com", hashed_password="123456", is_active=True)
        parent.children.append(child)
        photo = models.Photo(school_id=school.id, file_path="foto.jpg", title="Atividade", uploader=teacher, school_class=school_class)
        photo_two = models.Photo(school_id=school.id, file_path="foto-2.jpg", title="Atividade 2", uploader=teacher, school_class=school_class)
        self.session.add_all([school_class, teacher, coordinator, student, child, parent, photo, photo_two])
        self.session.commit()
        self.teacher_id = teacher.id
        self.coordinator_id = coordinator.id
        self.student_id = student.id
        self.photo_id = photo.id
        self.photo_two_id = photo_two.id
        self.parent_id = parent.id
        self.school_id = school.id

    def tearDown(self):
        self.session.close()
        models.Base.metadata.drop_all(bind=engine)
        models.Base.metadata.create_all(bind=engine)

    def test_publication_reaches_only_linked_family_profile(self):
        teacher = self.session.get(models.User, self.teacher_id)
        post = create_school_post(
            schemas.PostCreate(photo_ids=[self.photo_id, self.photo_two_id], caption="Dia de pintura", student_ids=[self.student_id]),
            teacher,
            self.session,
        )
        self.assertEqual(post.child_names, ["Pedro"])
        self.assertEqual(len(post.image_urls), 2)

        parent = self.session.get(models.Parent, self.parent_id)
        child = security.verifyChildAccess("pedro", parent, self.session)
        self.assertEqual([item.caption for item in child.posts], ["Dia de pintura"])

        other_parent = models.Parent(id="outro", name="Outro", email="outro@example.com", hashed_password="123456", is_active=True)
        self.session.add(other_parent)
        self.session.commit()
        with self.assertRaises(HTTPException) as denied:
            security.verifyChildAccess("pedro", other_parent, self.session)
        self.assertEqual(denied.exception.status_code, 403)

    def test_portfolio_supports_multiple_photos(self):
        teacher = self.session.get(models.User, self.teacher_id)
        projects = create_school_portfolio(
            schemas.PortfolioCreate(
                photo_ids=[self.photo_id, self.photo_two_id],
                student_ids=[self.student_id],
                title="Cores",
                description="Experiência com cores.",
                pedagogical_objectives=["Coordenação motora"],
            ),
            teacher,
            self.session,
        )
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].child_id, "pedro")
        self.assertEqual(len(projects[0].image_urls), 2)

    def test_school_can_create_and_link_a_family(self):
        teacher = self.session.get(models.User, self.teacher_id)
        coordinator = self.session.get(models.User, self.coordinator_id)
        student = models.Student(school_id=self.school_id, name="Helena", class_id=teacher.classes[0].id)
        self.session.add(student)
        self.session.commit()
        result = create_family_profile(
            student.id,
            schemas.FamilyAccountCreate(
                parent_name="Maria",
                parent_email="maria@example.com",
                initial_password="123456",
            ),
            coordinator,
            self.session,
        )
        self.assertEqual(result.name, "Helena")
        self.assertEqual(result.linked_student_id, student.id)
        self.assertEqual(result.parent_emails, ["maria@example.com"])

    def test_prisma_family_login_only_receives_linked_students_content(self):
        coordinator = self.session.get(models.User, self.coordinator_id)
        teacher = self.session.get(models.User, self.teacher_id)
        family = create_parent(schemas.FamilyParentCreate(
            name="PAI TESTE", email="pai.teste@example.com", password="secret1",
        ), coordinator, self.session)
        student = create_student(schemas.StudentCreate(
            name="FILHO TESTE", class_id=teacher.classes[0].id, parent_ids=[family.id],
        ), coordinator, self.session)
        other_family = create_parent(schemas.FamilyParentCreate(
            name="Outra Família", email="outra@example.com", password="secret1",
            student_ids=[self.student_id],
        ), coordinator, self.session)
        create_school_post(schemas.PostCreate(photo_ids=[self.photo_id],
            caption="Somente FILHO TESTE", student_ids=[student.id]), teacher, self.session)
        create_school_post(schemas.PostCreate(photo_ids=[self.photo_two_id],
            caption="Somente Pedro", student_ids=[self.student_id]), teacher, self.session)
        create_school_portfolio(schemas.PortfolioCreate(photo_ids=[self.photo_id],
            student_ids=[student.id], title="Projeto FILHO TESTE", description="Teste",
            pedagogical_objectives=[]), teacher, self.session)

        token = login(LoginRequest(identifier=" PAI.TESTE@example.com ", password="secret1"), self.session)["access_token"]
        parent = security.get_current_parent(token, self.session)
        children = get_children(parent)
        self.assertEqual([item["name"] for item in children], ["FILHO TESTE"])
        child_id = children[0]["id"]
        child = security.verifyChildAccess(child_id, parent, self.session)
        posts = get_posts(child, self.session)
        self.assertEqual([item["caption"] for item in posts], ["Somente FILHO TESTE"])
        self.assertEqual(len(posts[0]["image_urls"]), 1)
        self.assertIn("path=foto.jpg", posts[0]["image_url"])
        self.assertEqual([item["title"] for item in get_portfolio(child, self.session)], ["Projeto FILHO TESTE"])
        with self.assertRaises(HTTPException):
            security.verifyChildAccess("pedro", parent, self.session)
        with self.assertRaises(HTTPException):
            security.verifyChildAccess(child_id, self.session.get(models.Parent, other_family.id), self.session)

        # Alterar o vínculo no Prisma afeta inclusive uma sessão já autenticada.
        update_parent(family.id, schemas.FamilyParentUpdate(student_ids=[]), coordinator, self.session)
        parent = security.get_current_parent(token, self.session)
        self.assertEqual(get_children(parent), [])
        with self.assertRaises(HTTPException):
            security.verifyChildAccess(child_id, parent, self.session)
        update_parent(family.id, schemas.FamilyParentUpdate(student_ids=[student.id]), coordinator, self.session)
        parent = security.get_current_parent(token, self.session)
        self.assertEqual(get_children(parent)[0]["id"], child_id)
        self.assertEqual(len(get_posts(security.verifyChildAccess(child_id, parent, self.session), self.session)), 1)

    def test_inactive_family_school_or_student_cannot_receive_content(self):
        coordinator = self.session.get(models.User, self.coordinator_id)
        family = create_parent(schemas.FamilyParentCreate(name="PAI TESTE",
            email="pai@example.com", password="secret1", student_ids=[self.student_id]), coordinator, self.session)
        token = login(LoginRequest(identifier=family.email, password="secret1"), self.session)["access_token"]
        parent = security.get_current_parent(token, self.session)
        update_student(self.student_id, schemas.StudentUpdate(is_active=False), coordinator, self.session)
        self.assertEqual(get_children(parent), [])
        with self.assertRaises(HTTPException):
            security.verifyChildAccess("pedro", parent, self.session)
        update_student(self.student_id, schemas.StudentUpdate(is_active=True), coordinator, self.session)
        school = self.session.get(models.School, self.school_id)
        school.is_active = False
        self.session.commit()
        for operation in (lambda: login(LoginRequest(identifier=family.email, password="secret1"), self.session),
                          lambda: security.get_current_parent(token, self.session)):
            with self.assertRaises(HTTPException) as denied:
                operation()
            self.assertEqual(denied.exception.status_code, 401)
        school.is_active = True
        self.session.commit()
        deactivate_parent(family.id, coordinator, self.session)
        with self.assertRaises(HTTPException):
            security.get_current_parent(token, self.session)


if __name__ == "__main__":
    unittest.main()
