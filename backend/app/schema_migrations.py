import uuid

from sqlalchemy import inspect, text

from .db import engine


def ensure_tag_school_columns() -> None:
    """Preserve legacy tags while partitioning their photo links by school."""
    inspector = inspect(engine)
    if not inspector.has_table("tags"):
        return
    columns = {column["name"] for column in inspector.get_columns("tags")}
    if "school_id" in columns:
        return
    if engine.dialect.name != "postgresql":
        raise RuntimeError("A migração de tags existentes requer PostgreSQL.")
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE tags ADD COLUMN school_id INTEGER REFERENCES schools(id)"))
        connection.execute(text("DROP INDEX IF EXISTS ix_tags_name"))
        connection.execute(text("ALTER TABLE tags DROP CONSTRAINT IF EXISTS tags_name_key"))
        legacy = connection.execute(text("SELECT id, name FROM tags")).mappings().all()
        schools = connection.execute(text("SELECT id FROM schools ORDER BY id")).scalars().all()
        for tag in legacy:
            if not schools:
                connection.execute(text("DELETE FROM tags WHERE id = :id"), {"id": tag["id"]})
                continue
            connection.execute(text("UPDATE tags SET school_id = :school WHERE id = :id"),
                               {"school": schools[0], "id": tag["id"]})
            for school in schools[1:]:
                new_id = connection.execute(text("INSERT INTO tags (name, school_id, created_at) VALUES (:name, :school, CURRENT_TIMESTAMP) RETURNING id"),
                                            {"name": tag["name"], "school": school}).scalar_one()
                connection.execute(text("""
                    UPDATE photo_tag_link SET tag_id = :new_id WHERE tag_id = :old_id
                    AND photo_id IN (SELECT id FROM photos WHERE school_id = :school)
                """), {"new_id": new_id, "old_id": tag["id"], "school": school})
        connection.execute(text("ALTER TABLE tags ALTER COLUMN school_id SET NOT NULL"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_tag_school_name ON tags (school_id, name)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_tags_school_id ON tags (school_id)"))


def ensure_photo_upload_id_column() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("photos"):
        return
    if "client_upload_id" in {column["name"] for column in inspector.get_columns("photos")}:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE photos ADD COLUMN client_upload_id VARCHAR(64)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_photo_school_client_upload ON photos (school_id, client_upload_id)"))


def ensure_parent_account_fields() -> None:
    """Restaura os campos originais sem remover ou substituir contas."""
    inspector = inspect(engine)
    if not inspector.has_table("parents"):
        return
    columns = {column["name"] for column in inspector.get_columns("parents")}
    unique_google = any(index["unique"] and index["column_names"] == ["google_id"]
                        for index in inspector.get_indexes("parents")) or any(
        constraint["column_names"] == ["google_id"]
        for constraint in inspector.get_unique_constraints("parents")
    )
    with engine.begin() as connection:
        duplicates = connection.execute(text("""
            SELECT google_id FROM parents WHERE google_id IS NOT NULL
            GROUP BY google_id HAVING COUNT(*) > 1
        """)).first()
        if duplicates:
            raise RuntimeError("Identificação Google duplicada. Nenhuma conta foi apagada; revise os vínculos antes de aplicar a restrição.")
        if "updated_at" not in columns:
            connection.execute(text("ALTER TABLE parents ADD COLUMN updated_at TIMESTAMP"))
            connection.execute(text("UPDATE parents SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP)"))
        if not unique_google:
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_parents_google_id ON parents (google_id)"))


def ensure_face_cluster_school_column() -> None:
    """Identifica a escola dos grupos e separa grupos legados misturados, preservando faces."""
    inspector = inspect(engine)
    if not inspector.has_table("face_clusters"):
        return
    columns = {column["name"] for column in inspector.get_columns("face_clusters")}
    with engine.begin() as connection:
        if "school_id" not in columns:
            connection.execute(text("ALTER TABLE face_clusters ADD COLUMN school_id INTEGER REFERENCES schools(id)"))
            connection.execute(text("CREATE INDEX ix_face_clusters_school_id ON face_clusters (school_id)"))
        clusters = connection.execute(text("SELECT id, student_id, created_at FROM face_clusters WHERE school_id IS NULL")).mappings().all()
        for cluster in clusters:
            school_ids = set(connection.execute(text("""
                SELECT DISTINCT photos.school_id FROM detected_faces
                JOIN photos ON photos.id = detected_faces.photo_id
                WHERE detected_faces.cluster_id = :cluster_id
            """), {"cluster_id": cluster["id"]}).scalars())
            student_school = connection.execute(text("SELECT school_id FROM students WHERE id = :student_id"),
                                                {"student_id": cluster["student_id"]}).scalar()
            if student_school is not None:
                school_ids.add(student_school)
            if not school_ids:
                continue  # Não adivinha a escola de um grupo órfão.
            owner = student_school if student_school is not None else min(school_ids)
            connection.execute(text("UPDATE face_clusters SET school_id = :school_id WHERE id = :cluster_id"),
                               {"school_id": owner, "cluster_id": cluster["id"]})
            for school_id in sorted(school_ids - {owner}):
                new_id = uuid.uuid4().hex
                connection.execute(text("""
                    INSERT INTO face_clusters (id, school_id, student_id, name, created_at)
                    VALUES (:id, :school_id, NULL, :name, :created_at)
                """), {"id": new_id, "school_id": school_id, "name": f"Pessoa #{new_id[:6]}",
                        "created_at": cluster["created_at"]})
                connection.execute(text("""
                    UPDATE detected_faces SET cluster_id = :new_id
                    WHERE cluster_id = :old_id AND photo_id IN (
                        SELECT id FROM photos WHERE school_id = :school_id
                    )
                """), {"new_id": new_id, "old_id": cluster["id"], "school_id": school_id})


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
