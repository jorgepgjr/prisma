import os
import uuid
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.db import SessionLocal, engine
from app import models

def run_seed():
    models.Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    # 1. Criar o Pai
    parent_email = "pais@escola.com"
    parent = session.query(models.Parent).filter(models.Parent.email == parent_email).first()
    if not parent:
        parent = models.Parent(
            id=str(uuid.uuid4()),
            name="João da Silva",
            email=parent_email,
            phone="11999999999",
            is_active=False
        )
        session.add(parent)
        session.commit()
        session.refresh(parent)
        print("Pai criado.")

    # 2. Criar Crianças (Pedro e Sofia)
    child1 = session.query(models.Child).filter(models.Child.name == "Pedro").first()
    if not child1:
        child1 = models.Child(
            id=str(uuid.uuid4()),
            name="Pedro",
            avatar_path="avatars/pedro.jpg",
            classroom="Maternal II - Profª Ana Souza"
        )
        child1.parents.append(parent)
        session.add(child1)
        
    child2 = session.query(models.Child).filter(models.Child.name == "Sofia").first()
    if not child2:
        child2 = models.Child(
            id=str(uuid.uuid4()),
            name="Sofia",
            avatar_path="avatars/sofia.jpg",
            classroom="Maternal II - Profª Ana Souza"
        )
        child2.parents.append(parent)
        session.add(child2)
        
    session.commit()
    print("Crianças criadas.")

    # 3. Criar Post da "Profª Ana Souza"
    post = session.query(models.Post).filter(models.Post.caption == "Dia de pintura no pátio!").first()
    if not post:
        post = models.Post(
            id=str(uuid.uuid4()),
            classroom_name="Maternal II",
            teacher_name="Profª Ana Souza",
            teacher_avatar_url="avatars/prof_ana.jpg",
            image_path="posts/pintura.jpg",
            caption="Dia de pintura no pátio!"
        )
        # Marcando Pedro e Sofia no Post
        post.children.append(child1)
        post.children.append(child2)
        session.add(post)
        session.commit()
        print("Post criado.")

    # 4. Criar Projetos
    project1 = session.query(models.Project).filter(models.Project.title == "Meu primeiro boneco de argila").first()
    if not project1:
        project1 = models.Project(
            id=str(uuid.uuid4()),
            child_id=child1.id,
            title="Meu primeiro boneco de argila",
            image_path="projects/argila.jpg",
            completion_date=datetime.utcnow(),
            description="Pedro fez um boneco de argila muito criativo.",
            pedagogical_objectives=json.dumps(["Coordenação Motora", "Criatividade"])
        )
        session.add(project1)
        session.commit()
        print("Projeto de portfólio criado.")

    print("Seed finalizado com sucesso!")
    session.close()

if __name__ == "__main__":
    run_seed()
