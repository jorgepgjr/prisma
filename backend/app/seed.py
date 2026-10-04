import json
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw
from sqlalchemy import text

from .db import SessionLocal, engine
from .models import (
    Base, Child, Class, Parent, Photo, PhotoStatusEnum, Post, ProcessStatusEnum,
    Project, RoleEnum, School, Student, User,
)
from .security import get_password_hash

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"


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
        Student(school_id=school.id, class_id=school_class.id,
                name="FILHO TESTE" if slug == "girassol" else "Pedro", marketing_allowed=True),
        Student(school_id=school.id, class_id=school_class.id, name="Sofia", marketing_allowed=True),
    ]
    session.add_all(students)
    # Cada responsável recebe somente um aluno, com conteúdo distinto para
    # validar o isolamento familiar tanto na mesma escola quanto entre escolas.
    for index, student in enumerate(students):
        child = Child(id=str(uuid.uuid4()), school_id=school.id, name=student.name,
                      classroom=school_class.name, avatar_path="")
        student.child_profile = child
        parent = Parent(
            id=str(uuid.uuid4()), school_id=school.id,
            name="PAI TESTE" if index == 0 else "MÃE SOFIA",
            email=f"{'pai.teste' if index == 0 else 'mae.sofia'}@{slug}.com",
            hashed_password=get_password_hash("mypassword"), is_active=True,
        )
        parent.children.append(child)
        relative_path = Path(str(school.id)) / f"exemplo-{uuid.uuid4()}.png"
        destination = UPLOAD_DIR / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (640, 420), "#dbeafe" if index == 0 else "#fce7f3")
        drawing = ImageDraw.Draw(image)
        drawing.text((40, 160), f"FOTO DE TESTE - {student.name}", fill="#1e293b")
        drawing.text((40, 190), name, fill="#1e293b")
        image.save(destination)
        photo = Photo(
            school_id=school.id, file_path=relative_path.as_posix(),
            title=f"Foto de teste - {student.name}", uploaded_by_user_id=teacher.id,
            class_id=school_class.id, status=PhotoStatusEnum.APPROVED_FOR_MARKETING,
            process_status=ProcessStatusEnum.COMPLETED,
        )
        photo.students.append(student)
        post = Post(
            id=str(uuid.uuid4()), school_id=school.id, classroom_name=school_class.name,
            teacher_name=teacher.name, teacher_avatar_url="", image_path=photo.file_path,
            caption=f"Publicação de teste de {student.name}",
        )
        post.children.append(child)
        post.photos.append(photo)
        project = Project(
            id=str(uuid.uuid4()), school_id=school.id, child=child,
            title=f"Portfólio de teste de {student.name}", image_path=photo.file_path,
            completion_date=datetime.utcnow(), description="Atividade de demonstração.",
            pedagogical_objectives=json.dumps(["Explorar cores"]),
        )
        project.photos.append(photo)
        session.add_all([parent, child, photo, post, project])


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
