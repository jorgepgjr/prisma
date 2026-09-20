import os
import unittest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi import HTTPException

from app import models, schemas, security
from app.db import SessionLocal, engine
from app.publishing import create_school_post
from app.school_portfolio import create_school_portfolio
from app.families import create_family_profile


class PublicationFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        models.Base.metadata.create_all(bind=engine)

    @classmethod
    def tearDownClass(cls):
        models.Base.metadata.drop_all(bind=engine)

    def setUp(self):
        self.session = SessionLocal()
        school_class = models.Class(name="Grupo 2", year=2026)
        teacher = models.User(name="Marília", email="marilia@school.com", hashed_password="mypassword", role=models.RoleEnum.PROFESSOR)
        teacher.classes.append(school_class)
        student = models.Student(name="Pedro", school_class=school_class)
        child = models.Child(id="pedro", name="Pedro", avatar_path="avatar.png", classroom="Grupo 2")
        student.child_profile = child
        parent = models.Parent(id="responsavel", name="Responsável", email="familia@example.com", hashed_password="123456", is_active=True)
        parent.children.append(child)
        photo = models.Photo(file_path="foto.jpg", title="Atividade", uploader=teacher, school_class=school_class)
        photo_two = models.Photo(file_path="foto-2.jpg", title="Atividade 2", uploader=teacher, school_class=school_class)
        self.session.add_all([school_class, teacher, student, child, parent, photo, photo_two])
        self.session.commit()
        self.teacher_id = teacher.id
        self.student_id = student.id
        self.photo_id = photo.id
        self.photo_two_id = photo_two.id
        self.parent_id = parent.id

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
        student = models.Student(name="Helena", class_id=teacher.classes[0].id)
        self.session.add(student)
        self.session.commit()
        result = create_family_profile(
            student.id,
            schemas.FamilyAccountCreate(
                parent_name="Maria",
                parent_email="maria@example.com",
                initial_password="123456",
            ),
            teacher,
            self.session,
        )
        self.assertEqual(result.name, "Helena")
        self.assertEqual(result.linked_student_id, student.id)
        self.assertEqual(result.parent_emails, ["maria@example.com"])


if __name__ == "__main__":
    unittest.main()
