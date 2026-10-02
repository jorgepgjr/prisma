import base64
from pathlib import Path

from sqlalchemy import text

from .db import SessionLocal, engine
from .models import (
    Base, Class, Photo, PhotoStatusEnum, RoleEnum, School, Student, User,
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
PIXEL = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def create_school(session, name: str, slug: str):
    school = School(name=name, plan_name="Básico")
    session.add(school)
    session.flush()
    coordinator = User(
        school_id=school.id, name=f"Coordenação {name}", email=f"coordenacao@{slug}.com",
        hashed_password="mypassword", role=RoleEnum.COORDENADOR,
    )
    teacher = User(
        school_id=school.id, name=f"Professora {name}", email=f"professora@{slug}.com",
        hashed_password="mypassword", role=RoleEnum.PROFESSOR,
    )
    marketing = User(
        school_id=school.id, name=f"Marketing {name}", email=f"marketing@{slug}.com",
        hashed_password="mypassword", role=RoleEnum.MARKETING,
    )
    school_class = Class(school_id=school.id, name="Grupo 2", year=2026)
    teacher.classes.append(school_class)
    session.add_all([coordinator, teacher, marketing, school_class])
    session.flush()
    students = [
        Student(school_id=school.id, class_id=school_class.id, name="Pedro", marketing_allowed=True),
        Student(school_id=school.id, class_id=school_class.id, name="Sofia", marketing_allowed=True),
    ]
    session.add_all(students)
    relative_path = Path(str(school.id)) / "foto-exemplo.png"
    destination = UPLOAD_DIR / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(PIXEL)
    session.add(Photo(
        school_id=school.id, file_path=relative_path.as_posix(), title="Foto de exemplo",
        uploaded_by_user_id=teacher.id, class_id=school_class.id,
        status=PhotoStatusEnum.APPROVED_FOR_MARKETING,
    ))


def seed_data():
    if engine.dialect.name == "postgresql":
        # O banco local de desenvolvimento pode conter tabelas de protótipos
        # anteriores que não fazem parte deste metadata, mas referenciam schools.
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    else:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        create_school(session, "Escola Girassol", "girassol")
        create_school(session, "Escola Horizonte", "horizonte")
        session.commit()
        print("Base recriada com duas escolas. Senha das contas de teste: mypassword")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_data()
