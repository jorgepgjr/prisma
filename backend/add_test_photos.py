"""Carga incremental de quatro imagens fictícias; nunca recria a base.

Execute no backend: python add_test_photos.py
Os arquivos gerados devem existir previamente em uploads/<escola>/.
"""
from pathlib import Path

from app.db import SessionLocal
from app.models import Parent, Photo, PhotoStatusEnum, Post, ProcessStatusEnum, User


def main():
    with SessionLocal() as session:
        teacher = session.query(User).filter_by(email="professora@girassol.com").one()
        parent = session.query(Parent).filter_by(email="pai.teste@girassol.com").one()
        child = next(c for c in parent.children if c.school_id == teacher.school_id and c.student_profile)
        student = child.student_profile
        classroom = student.school_class
        assert classroom in teacher.classes and classroom.is_active
        assets = [
            ("professora-artes", "Artes", False),
            ("professora-leitura", "Leitura", False),
            ("familia-blocos", "Brincando com blocos", True),
            ("familia-jardim", "Cuidando do jardim", True),
        ]
        for slug, title, publish in assets:
            path = f"{teacher.school_id}/test-{slug}-20261020.png"
            assert (Path(__file__).parent / "uploads" / path).is_file(), path
            photo = session.query(Photo).filter_by(file_path=path).one_or_none()
            if photo is None:
                photo = Photo(
                    school_id=teacher.school_id, file_path=path,
                    title=f"Teste fictício — {title}",
                    description="Imagem gerada por IA exclusivamente para testes.",
                    uploaded_by_user_id=teacher.id, class_id=classroom.id,
                    status=PhotoStatusEnum.PRIVATE_SCHOOL_ONLY,
                    process_status=ProcessStatusEnum.COMPLETED,
                )
                session.add(photo)
            if publish:
                if student not in photo.students:
                    photo.students.append(student)
                post_id = f"test-20261020-{slug}"
                existing_post = session.get(Post, post_id)
                if existing_post is not None:
                    existing_post.teacher_avatar_url = existing_post.teacher_avatar_url or ""
                else:
                    session.add(Post(
                        id=post_id, school_id=teacher.school_id,
                        classroom_name=classroom.name, teacher_name=teacher.name, teacher_avatar_url="",
                        image_path=path,
                        caption=f"Teste com imagem fictícia: {title}.",
                        children=[child], photos=[photo],
                    ))
        session.commit()
        print("4 fotos prontas: 2 só na galeria escolar e 2 publicadas para FILHO TESTE.")


if __name__ == "__main__":
    main()
