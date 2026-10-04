from sqlalchemy import inspect, text

from .db import engine


def ensure_parent_school_column() -> None:
    """Preserva os dados existentes e permite familiares sem alunos vinculados."""
    inspector = inspect(engine)
    if not inspector.has_table("parents"):
        return
    existing = {column["name"] for column in inspector.get_columns("parents")}
    with engine.begin() as connection:
        if "school_id" not in existing:
            connection.execute(text("ALTER TABLE parents ADD COLUMN school_id INTEGER REFERENCES schools(id)"))
            connection.execute(text("CREATE INDEX ix_parents_school_id ON parents (school_id)"))
        connection.execute(text("""
            UPDATE parents SET school_id = (
                SELECT MIN(children.school_id) FROM parent_child_link
                JOIN children ON children.id = parent_child_link.child_id
                WHERE parent_child_link.parent_id = parents.id
            ) WHERE school_id IS NULL AND (
                SELECT COUNT(DISTINCT children.school_id) FROM parent_child_link
                JOIN children ON children.id = parent_child_link.child_id
                WHERE parent_child_link.parent_id = parents.id
            ) = 1
        """))


def ensure_photo_processing_columns() -> None:
    """Add the face-queue columns to databases created before face processing."""
    inspector = inspect(engine)
    if not inspector.has_table("photos"):
        return

    existing = {column["name"] for column in inspector.get_columns("photos")}
    missing = {"process_status", "process_attempts", "process_error"} - existing
    if not missing:
        return

    if engine.dialect.name == "postgresql":
        status_type = "processstatusenum"
    else:
        status_type = "VARCHAR(16)"

    column_definitions = {
        "process_status": f"{status_type} NOT NULL DEFAULT 'PENDING'",
        "process_attempts": "INTEGER NOT NULL DEFAULT 0",
        "process_error": "TEXT",
    }

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql" and "process_status" in missing:
            connection.execute(text("""
                DO $$
                BEGIN
                    CREATE TYPE processstatusenum AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                END $$;
            """))

        for column_name in sorted(missing):
            connection.execute(text(
                f"ALTER TABLE photos ADD COLUMN {column_name} {column_definitions[column_name]}"
            ))
