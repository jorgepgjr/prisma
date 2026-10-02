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


class MultiSchoolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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


if __name__ == "__main__":
    unittest.main()
