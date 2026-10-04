import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi import FastAPI
from PIL import Image

from app import db, models, security
from app.face_service import run_clustering_routine, recluster_all_faces, sync_cluster_student_links
from app.routers import faces, system, media


class FaceSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if db.engine.dialect.name != "sqlite" or db.engine.url.database != ":memory:":
            raise RuntimeError("Testes permitidos somente no SQLite em memória.")
        models.Base.metadata.create_all(bind=db.engine)
        cls.password_hash = security.get_password_hash("secret1")

    @classmethod
    def tearDownClass(cls):
        models.Base.metadata.drop_all(bind=db.engine)

    def setUp(self):
        self.session = db.SessionLocal()
        schools = [models.School(name="Uma escola"), models.School(name="Outra escola")]
        self.session.add_all(schools)
        self.session.flush()
        self.users = []
        self.photos = []
        self.students = []
        self.classes = []
        for index, school in enumerate(schools):
            user = models.User(school_id=school.id, name="Coordenação", email=f"coord{index}@test.com",
                               hashed_password=self.password_hash, role=models.RoleEnum.COORDENADOR)
            classroom = models.Class(school_id=school.id, name="Grupo 2", year=2026)
            self.session.add_all([user, classroom])
            self.session.flush()
            student = models.Student(school_id=school.id, class_id=classroom.id, name=f"Aluno {index}")
            photo = models.Photo(school_id=school.id, class_id=classroom.id, uploaded_by_user_id=user.id,
                                 file_path=f"{school.id}/foto.png", process_status=models.ProcessStatusEnum.PENDING)
            cluster = models.FaceCluster(id=f"cluster-{index}", school_id=school.id, name=f"Pessoa {index}")
            face = models.DetectedFace(id=f"face-{index}", photo=photo, cluster=cluster,
                                       bounding_box=[0, 0, 1, 1], embedding=[1.0, 0.0], face_crop_path=f"crop-{index}.png")
            self.session.add_all([student, photo, cluster, face])
            self.users.append(user)
            self.classes.append(classroom)
            self.photos.append(photo)
            self.students.append(student)
        for role in [models.RoleEnum.PROFESSOR, models.RoleEnum.MARKETING]:
            self.session.add(models.User(school_id=schools[0].id, name=role.value,
                email=f"{role.value.lower()}@test.com", hashed_password=self.password_hash, role=role))
        self.session.commit()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "faces").mkdir()
        for index, photo in enumerate(self.photos):
            destination = self.root / photo.file_path
            destination.parent.mkdir()
            Image.new("RGB", (80, 80)).save(destination)
            Image.new("RGB", (16, 16)).save(self.root / "faces" / f"crop-{index}.png")
        self.patches = [patch("app.routers.faces.UPLOADS_DIR", self.root),
                        patch("app.routers.media.UPLOAD_DIR", self.root),
                        patch("app.face_service.UPLOADS_DIR", str(self.root))]
        for item in self.patches:
            item.start()
        self.app = FastAPI()
        self.app.include_router(faces.router, prefix="/api/faces")
        self.app.include_router(system.router, prefix="/api/system")
        self.app.include_router(media.router, prefix="/api/v1/media")
        self.app.dependency_overrides[db.get_db] = lambda: self.session

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.session.close()
        self.temp.cleanup()
        models.Base.metadata.drop_all(bind=db.engine)
        models.Base.metadata.create_all(bind=db.engine)

    def request(self, path, method="GET", email="coord0@test.com", body=None):
        """Executa a API real em memória, sem serviços externos ou dependências adicionais."""
        parsed = urlsplit(path)
        headers = [(b"content-type", b"application/json")]
        if email:
            token = security.create_access_token({"sub": email})
            headers.append((b"authorization", f"Bearer {token}".encode()))
        scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
                 "http_version": "1.1", "method": method, "scheme": "http", "path": parsed.path,
                 "raw_path": parsed.path.encode(), "query_string": parsed.query.encode(),
                 "root_path": "", "headers": headers, "server": ("test", 80), "client": ("test", 123)}
        sent = []
        async def receive():
            return {"type": "http.request", "body": json.dumps(body or {}).encode(), "more_body": False}
        async def send(message):
            sent.append(message)
        asyncio.run(self.app(scope, receive, send))
        start = next(message for message in sent if message["type"] == "http.response.start")
        content = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
        content_type = dict(start["headers"]).get(b"content-type", b"")
        if start["status"] in (307, 308):
            return self.request(dict(start["headers"])[b"location"].decode(), method, email, body)
        return start["status"], json.loads(content) if b"json" in content_type else content

    def test_all_routes_require_coordinator_authentication(self):
        endpoints = [("GET", "/api/faces/clusters"), ("GET", "/api/faces/clusters/cluster-0"),
                     ("GET", "/api/faces/clusters/cluster-0/photos"), ("GET", "/api/faces/crop/face-0"),
                     ("POST", "/api/faces/clusters/cluster-0/assign"), ("DELETE", "/api/faces/clusters/cluster-0/assign"),
                     ("GET", "/api/system/processing-status"), ("GET", "/api/system/processing-photos"),
                     ("POST", "/api/system/process-now"), ("POST", "/api/system/ingest-test-folder"),
                     ("POST", "/api/system/reprocess-failed"), ("POST", "/api/system/reprocess-all"),
                     ("POST", "/api/system/recluster-all")]
        for email, expected in [(None, 401), ("professor@test.com", 403), ("marketing@test.com", 403), ("family-id", 401)]:
            for method, path in endpoints:
                with self.subTest(email=email, path=path):
                    self.assertEqual(self.request(path, method, email, {"student_id": self.students[0].id})[0], expected)

    def test_school_lists_counts_and_signed_crops_are_isolated(self):
        code, data = self.request("/api/system/processing-status")
        self.assertEqual((code, data["total"], data["pending"]), (200, 1, 1))
        code, data = self.request("/api/system/processing-photos")
        self.assertEqual([item["id"] for item in data], [self.photos[0].id])
        self.assertEqual(self.request(data[0]["detected_faces"][0]["face_crop_url"], email=None)[0], 200)
        code, clusters = self.request("/api/faces/clusters")
        self.assertEqual([item["id"] for item in clusters], ["cluster-0"])
        self.assertEqual(clusters[0]["photo_count"], 1)
        self.assertIn("signature=", clusters[0]["sample_face_crops"][0])
        self.assertEqual(self.request(clusters[0]["sample_face_crops"][0] + "invalid", email=None)[0], 403)
        self.assertEqual(self.request("/api/faces/crop/face-0")[0], 200)

    def test_foreign_ids_and_assignments_are_not_found(self):
        for method, path in [("GET", "/api/faces/clusters/cluster-1"), ("GET", "/api/faces/clusters/cluster-1/photos"),
                             ("GET", "/api/faces/crop/face-1"), ("GET", f"/api/faces/clusters?class_id={self.classes[1].id}"),
                             ("GET", "/api/system/processing-photos?cluster_id=cluster-1"),
                             ("POST", "/api/faces/clusters/cluster-1/assign"), ("DELETE", "/api/faces/clusters/cluster-1/assign")]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path, method, body={"student_id": self.students[0].id})[0], 404)
        self.assertEqual(self.request("/api/faces/clusters/cluster-0/assign", "POST", body={"student_id": self.students[1].id})[0], 404)
        self.assertEqual(self.request("/api/faces/clusters/cluster-0/assign", "POST", body={"student_id": self.students[0].id})[0], 200)
        self.assertEqual(self.photos[0].students, [self.students[0]])
        self.assertEqual(self.photos[1].students, [])

    def test_requeue_only_changes_the_current_school(self):
        for photo in self.photos:
            photo.process_status = models.ProcessStatusEnum.FAILED
            photo.process_attempts = 4
            photo.process_error = "Teste"
        self.session.commit()
        self.assertEqual(self.request("/api/system/reprocess-failed", "POST")[0], 200)
        self.assertEqual(self.photos[0].process_status, models.ProcessStatusEnum.PENDING)
        self.assertEqual(self.photos[1].process_status, models.ProcessStatusEnum.FAILED)
        self.assertEqual(self.request("/api/system/reprocess-all", "POST")[0], 200)
        self.assertEqual(self.photos[0].process_attempts, 0)
        self.assertEqual(self.photos[1].process_attempts, 4)
        self.assertEqual(self.photos[1].process_error, "Teste")

    def test_process_now_does_not_claim_other_school_photos(self):
        detector = Mock()
        detector.detect_and_extract.return_value = [{"bbox": [0, 0, 1, 1], "embedding": [1.0, 0.0],
                                                    "crop_filename": "crop-0.png", "score": 1.0}]
        with patch("app.face_service.FaceAnalysisEngine.get_instance", return_value=detector):
            code, result = self.request("/api/system/process-now", "POST")
        self.assertEqual((code, result["processed_count"]), (200, 1))
        self.assertEqual(self.photos[1].process_status, models.ProcessStatusEnum.PENDING)
        self.assertEqual(self.session.get(models.DetectedFace, "face-1").cluster_id, "cluster-1")

    def test_identical_embeddings_never_merge_schools(self):
        for face in self.session.query(models.DetectedFace):
            face.cluster_id = None
        self.session.commit()
        run_clustering_routine(self.session)
        first = self.session.get(models.DetectedFace, "face-0")
        second = self.session.get(models.DetectedFace, "face-1")
        self.assertNotEqual(first.cluster_id, second.cluster_id)
        self.assertEqual(first.cluster.school_id, self.users[0].school_id)
        self.assertEqual(second.cluster.school_id, self.users[1].school_id)

    def test_reclustering_preserves_other_school_and_all_face_rows(self):
        other_cluster = self.session.get(models.FaceCluster, "cluster-1")
        other_cluster.student_id = self.students[1].id
        self.session.commit()
        code, result = self.request("/api/system/recluster-all", "POST")
        self.assertEqual((code, result["result"]["total_faces"]), (200, 1))
        self.assertEqual(self.session.query(models.DetectedFace).count(), 2)
        self.assertEqual(self.session.query(models.Photo).count(), 2)
        self.assertEqual(self.session.get(models.DetectedFace, "face-1").cluster_id, "cluster-1")
        self.assertEqual(self.session.get(models.FaceCluster, "cluster-1").student_id, self.students[1].id)

    def test_sync_rejects_inconsistent_legacy_school_links(self):
        cluster = self.session.get(models.FaceCluster, "cluster-0")
        cluster.student_id = self.students[1].id
        self.session.commit()
        sync_cluster_student_links(self.session)
        self.assertEqual(self.photos[0].students, [])
        self.assertIsNone(self.request("/api/faces/clusters/cluster-0")[1]["student_name"])

    def test_inconsistent_mixed_cluster_is_hidden_and_cannot_change_other_school(self):
        foreign_face = self.session.get(models.DetectedFace, "face-1")
        foreign_face.cluster_id = "cluster-0"
        self.session.commit()
        self.assertEqual(self.request("/api/faces/clusters/cluster-0")[0], 404)
        self.assertEqual(self.request("/api/faces/clusters")[1], [])
        recluster_all_faces(self.session, school_id=self.users[0].school_id)
        self.assertEqual(foreign_face.cluster_id, "cluster-0")
        self.assertIsNotNone(self.session.get(models.FaceCluster, "cluster-0"))

    def test_parent_timestamp_and_google_uniqueness(self):
        from sqlalchemy.exc import IntegrityError
        parent = models.Parent(id="parent", school_id=self.users[0].school_id, name="Pai", email="pai@test.com", google_id="google-one")
        self.session.add(parent)
        self.session.commit()
        created = parent.updated_at
        parent.name = "Pai editado"
        self.session.commit()
        self.assertGreaterEqual(parent.updated_at, created)
        self.session.add(models.Parent(id="another", name="Outro", email="outro@test.com", google_id="google-one"))
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()


if __name__ == "__main__":
    unittest.main()
