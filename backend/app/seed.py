import random
import os
import time
import base64
from sqlalchemy.orm import Session
from faker import Faker
from .db import SessionLocal
from .models import (
    User, 
    Class, 
    Student, 
    Photo, 
    RoleEnum, 
    PhotoStatusEnum, 
    StudentStatusEnum, 
    user_class_link, 
    photo_student_link
)

# Inicializa Faker em Português do Brasil para nomes realistas
fake = Faker('pt_BR')

def clean_name(name: str) -> str:
    prefixes = ["Dr. ", "Dra. ", "Sr. ", "Sra. ", "Srta. ", "Dr(a). "]
    for p in prefixes:
        if name.startswith(p):
            name = name[len(p):]
    return name

def clean_database(session: Session):
    print("Limpando registros antigos do banco de dados...")
    # Deleta associações N:N
    session.execute(photo_student_link.delete())
    session.execute(user_class_link.delete())
    # Deleta tabelas principais
    session.query(Photo).delete()
    session.query(Student).delete()
    session.query(Class).delete()
    session.query(User).delete()
    session.commit()
    print("Banco de dados limpo com sucesso!")

def seed_data():
    session = SessionLocal()
    try:
        clean_database(session)

        print("\nIniciando carga de dados de teste...")

        # 1. Criação de usuários administrativos padrão (a senha será criptografada pelo @validates do model)
        admin = User(
            name="Administrador do Sistema",
            email="admin@school.com",
            hashed_password="mypassword",
            role=RoleEnum.ADMIN
        )
        diretor = User(
            name="Diretora Regina",
            email="diretor@school.com",
            hashed_password="mypassword",
            role=RoleEnum.DIRETOR
        )
        coordenador = User(
            name="Coordenadora Paula",
            email="coordenador@school.com",
            hashed_password="mypassword",
            role=RoleEnum.COORDENADOR
        )
        marketing = User(
            name="Aline Marketing",
            email="marketing@school.com",
            hashed_password="mypassword",
            role=RoleEnum.MARKETING
        )
        session.add_all([admin, diretor, coordenador, marketing])
        session.commit()
        print("Usuários administrativos criados (admin@, diretor@, coordenador@, marketing@ | Senha: mypassword)")

        # 2. Criação de Professores
        professores = []
        
        # Cria a professora específica Marília Sena
        prof_marilia = User(
            name="Marília Sena",
            email="marilia@school.com",
            hashed_password="mypassword",
            role=RoleEnum.PROFESSOR
        )
        session.add(prof_marilia)
        professores.append(prof_marilia)
        
        # Cria mais 5 professores aleatórios
        for i in range(5):
            prof = User(
                name=f"Prof. {clean_name(fake.name())}",
                email=f"professor{i+1}@school.com",
                hashed_password="mypassword",
                role=RoleEnum.PROFESSOR
            )
            session.add(prof)
            professores.append(prof)
        session.commit()
        print("Professores criados (incluindo Marília Sena | marilia@school.com)")

        # 3. Criação de Turmas (Classes)
        turmas_nomes = ["Grupo 1", "Grupo 2", "Grupo 3"]
        turmas = []
        for nome in turmas_nomes:
            turma = Class(
                name=nome,
                year=2026
            )
            session.add(turma)
            turmas.append(turma)
        session.commit()
        print(f"{len(turmas)} turmas criadas (Grupo 1, 2 e 3) para o ano de 2026.")

        # 4. Vincula Professores às Turmas (Muitos para Muitos)
        for prof in professores:
            if prof.email == "marilia@school.com":
                # Marília Sena leciona APENAS no Grupo 2
                grupo2 = next(t for t in turmas if t.name == "Grupo 2")
                prof.classes.append(grupo2)
            else:
                # Vincula professor1 -> Grupo 1, professor2 -> Grupo 2, professor3 -> Grupo 3, etc.
                try:
                    num_str = prof.email.replace("professor", "").replace("@school.com", "")
                    num = int(num_str)
                    # Mapeia de forma cíclica conforme o número do professor
                    grupo_idx = (num - 1) % len(turmas)
                    prof.classes.append(turmas[grupo_idx])
                except ValueError:
                    prof.classes.append(random.choice(turmas))
                
        session.commit()
        print("Professores vinculados às suas respectivas turmas com sucesso (professor1 -> Grupo 1, professor2 -> Grupo 2, etc).")

        # 5. Criação de Alunos (Students)
        # 5 a 10 alunos por turma, com 70% de chance de autorização LGPD para marketing
        alunos_totais = 0
        for turma in turmas:
            num_alunos = random.randint(5, 10)
            for _ in range(num_alunos):
                aluno = Student(
                    name=clean_name(fake.name()),
                    class_id=turma.id,
                    marketing_allowed=random.random() < 0.70, # 70% de chance de ter autorização
                    status=StudentStatusEnum.ATIVO
                )
                session.add(aluno)
                alunos_totais += 1
        session.commit()
        print(f"{alunos_totais} alunos criados e distribuídos pelas turmas.")

        # 6. Escanear e renomear arquivos físicos de uploads para o padrão timestamp
        upload_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "uploads")
        )
        os.makedirs(upload_dir, exist_ok=True)
        
        # Filtra os arquivos de imagem permitidos
        files = os.listdir(upload_dir)
        renamed_files = []
        
        # Ignora arquivos ocultos e do sistema
        image_files = [f for f in files if not f.startswith('.') and os.path.splitext(f.lower())[1] in {'.jpg', '.jpeg', '.png', '.avif'}]
        
        for idx, file_name in enumerate(sorted(image_files)):
            name_no_ext, ext = os.path.splitext(file_name.lower())
            
            if name_no_ext.isdigit():
                # Já segue o padrão de timestamp, mantém o nome
                renamed_files.append(file_name)
            else:
                # Renomeia seguindo padrão de timestamp baseado no tempo atual mais offset
                new_name = f"{int(time.time() * 1000) + idx}{ext}"
                old_path = os.path.join(upload_dir, file_name)
                new_path = os.path.join(upload_dir, new_name)
                os.rename(old_path, new_path)
                print(f"Renomeado físico: {file_name} -> {new_name}")
                renamed_files.append(new_name)

        # Se a pasta estiver vazia ou com poucas fotos, criamos fallbacks (pixel transparente) para ter fotos suficientes
        if len(renamed_files) < 3:
            print("Poucas ou nenhuma foto encontrada em uploads/. Gerando fotos fallback transparentes...")
            pixel_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            pixel_binary = base64.b64decode(pixel_base64)
            for k in range(3):
                new_name = f"{int(time.time() * 1000) + len(renamed_files) + k}.png"
                file_path = os.path.join(upload_dir, new_name)
                with open(file_path, "wb") as f:
                    f.write(pixel_binary)
                print(f"Criado arquivo mock físico: {new_name}")
                renamed_files.append(new_name)

        # 7. Criação dos registros de Photo vinculados aos arquivos físicos
        fotos_totais = 0
        todos_alunos = session.query(Student).all()
        
        print(f"Cadastrando {len(renamed_files)} fotos físicas como registros lógicos no banco...")
        for idx, file_name in enumerate(renamed_files):
            # Associa de forma cíclica às turmas (Grupo 1, 2 ou 3)
            turma = turmas[idx % len(turmas)]
            alunos_da_turma = [a for a in todos_alunos if a.class_id == turma.id]
            
            professores_da_turma = [p for p in professores if turma in p.classes]
            uploader_id = professores_da_turma[0].id if professores_da_turma else diretor.id
            
            foto = Photo(
                file_id=file_name,
                title=f"Atividade {turma.name} - Imagem {idx + 1}",
                description=fake.sentence(),
                uploaded_by_user_id=uploader_id,
                class_id=turma.id,
                status=random.choice(list(PhotoStatusEnum))
            )
            
            # Sorteia de 1 a 3 alunos da própria turma para marcar na foto
            if alunos_da_turma:
                alunos_marcados = random.sample(alunos_da_turma, k=min(random.randint(1, 3), len(alunos_da_turma)))
                foto.students.extend(alunos_marcados)
                
            session.add(foto)
            fotos_totais += 1
            
        session.commit()
        print(f"{fotos_totais} fotos de teste registradas logicamente no banco de dados.")
        
        print("\nCarga inicial de dados finalizada com SUCESSO!")

    except Exception as e:
        session.rollback()
        print(f"Erro durante a carga de dados: {str(e)}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    seed_data()
