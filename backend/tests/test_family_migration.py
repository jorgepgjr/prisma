import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.schema_migrations import ensure_parent_school_column


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
