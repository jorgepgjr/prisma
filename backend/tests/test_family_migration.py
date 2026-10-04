import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.schema_migrations import (ensure_parent_school_column, ensure_parent_account_fields,
                                   ensure_face_cluster_school_column)


class FamilyMigrationTest(unittest.TestCase):
    def test_additive_migration_preserves_accounts_and_identifies_school(self):
        legacy_engine = create_engine("sqlite:///:memory:")
        try:
            with legacy_engine.begin() as connection:
                for definition in ["schools (id INTEGER PRIMARY KEY)",
                                   "parents (id TEXT PRIMARY KEY, name TEXT)",
                                   "children (id TEXT PRIMARY KEY, school_id INTEGER)",
                                   "parent_child_link (parent_id TEXT, child_id TEXT)"]:
                    connection.execute(text(f"CREATE TABLE {definition}"))
                connection.execute(text("INSERT INTO schools VALUES (1), (2)"))
                connection.execute(text("INSERT INTO parents VALUES ('one', 'Uma escola'), ('shared', 'Duas escolas'), ('unlinked', 'Sem vínculo')"))
                connection.execute(text("INSERT INTO children VALUES ('a', 1), ('b', 2)"))
                connection.execute(text("INSERT INTO parent_child_link VALUES ('one', 'a'), ('shared', 'a'), ('shared', 'b')"))
            with patch("app.schema_migrations.engine", legacy_engine):
                ensure_parent_school_column()
                ensure_parent_school_column()  # Pode rodar novamente sem perder dados.
            self.assertIn("school_id", {column["name"] for column in inspect(legacy_engine).get_columns("parents")})
            with legacy_engine.connect() as connection:
                rows = dict(connection.execute(text("SELECT id, school_id FROM parents")).all())
                self.assertEqual(rows, {"one": 1, "shared": None, "unlinked": None})
        finally:
            legacy_engine.dispose()

    def test_restored_fields_preserve_accounts_and_reject_duplicate_google_id(self):
        legacy_engine = create_engine("sqlite:///:memory:")
        try:
            with legacy_engine.begin() as connection:
                connection.execute(text("CREATE TABLE parents (id TEXT PRIMARY KEY, google_id TEXT, created_at TIMESTAMP)"))
                connection.execute(text("INSERT INTO parents VALUES ('one', 'google-one', '2026-01-01'), ('two', NULL, '2026-02-01'), ('three', NULL, '2026-03-01')"))
            with patch("app.schema_migrations.engine", legacy_engine):
                ensure_parent_account_fields()
                ensure_parent_account_fields()
            with legacy_engine.connect() as connection:
                self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM parents")).scalar(), 3)
                self.assertEqual(connection.execute(text("SELECT updated_at FROM parents WHERE id='one'")).scalar(), "2026-01-01")
            from sqlalchemy.exc import IntegrityError
            with self.assertRaises(IntegrityError), legacy_engine.begin() as connection:
                connection.execute(text("UPDATE parents SET google_id='google-one' WHERE id='two'"))
        finally:
            legacy_engine.dispose()

    def test_google_migration_does_not_delete_conflicting_accounts(self):
        legacy_engine = create_engine("sqlite:///:memory:")
        try:
            with legacy_engine.begin() as connection:
                connection.execute(text("CREATE TABLE parents (id TEXT PRIMARY KEY, google_id TEXT, created_at TIMESTAMP)"))
                connection.execute(text("INSERT INTO parents VALUES ('one', 'duplicate', NULL), ('two', 'duplicate', NULL)"))
            with patch("app.schema_migrations.engine", legacy_engine), self.assertRaises(RuntimeError):
                ensure_parent_account_fields()
            with legacy_engine.connect() as connection:
                self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM parents")).scalar(), 2)
            self.assertNotIn("updated_at", {column["name"] for column in inspect(legacy_engine).get_columns("parents")})
        finally:
            legacy_engine.dispose()

    def test_face_migration_separates_legacy_schools_without_deleting_faces(self):
        legacy_engine = create_engine("sqlite:///:memory:")
        try:
            with legacy_engine.begin() as connection:
                for definition in ["schools (id INTEGER PRIMARY KEY)",
                                   "students (id INTEGER PRIMARY KEY, school_id INTEGER)",
                                   "photos (id INTEGER PRIMARY KEY, school_id INTEGER)",
                                   "face_clusters (id TEXT PRIMARY KEY, student_id INTEGER, name TEXT, created_at TIMESTAMP)",
                                   "detected_faces (id TEXT PRIMARY KEY, photo_id INTEGER, cluster_id TEXT)"]:
                    connection.execute(text(f"CREATE TABLE {definition}"))
                connection.execute(text("INSERT INTO schools VALUES (1), (2)"))
                connection.execute(text("INSERT INTO students VALUES (10, 1)"))
                connection.execute(text("INSERT INTO photos VALUES (100, 1), (200, 2)"))
                connection.execute(text("INSERT INTO face_clusters VALUES ('mixed', 10, 'Aluno da escola 1', '2026-01-01'), ('only', NULL, 'Pessoa', '2026-01-01'), ('orphan', NULL, 'Antigo', '2026-01-01')"))
                connection.execute(text("INSERT INTO detected_faces VALUES ('a', 100, 'mixed'), ('b', 200, 'mixed'), ('c', 100, 'only')"))
            with patch("app.schema_migrations.engine", legacy_engine):
                ensure_face_cluster_school_column()
                ensure_face_cluster_school_column()
            with legacy_engine.connect() as connection:
                self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM face_clusters")).scalar(), 4)
                self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM detected_faces")).scalar(), 3)
                self.assertEqual(connection.execute(text("SELECT student_id FROM face_clusters WHERE id='mixed'")).scalar(), 10)
                self.assertIsNone(connection.execute(text("SELECT school_id FROM face_clusters WHERE id='orphan'")).scalar())
                self.assertEqual(dict(connection.execute(text("SELECT detected_faces.id, face_clusters.school_id FROM detected_faces JOIN face_clusters ON face_clusters.id=detected_faces.cluster_id")).all()), {"a": 1, "b": 2, "c": 1})
                self.assertNotEqual(connection.execute(text("SELECT cluster_id FROM detected_faces WHERE id='b'")).scalar(), 'mixed')
        finally:
            legacy_engine.dispose()
