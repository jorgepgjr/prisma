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

fake = Faker('pt_BR')

def clean_name(name: str) -> str:
    prefixes = ["Dr. ", "Dra. ", "Sr. ", "Sra. ", "Srta. ", "Dr(a). "]
    for p in prefixes:
        if name.startswith(p):
            name = name[len(p):]
    return name

def clean_database(session: Session):
    print("Limpando registros antigos do banco de dados (DROP TABLE)...")
    from .db import engine
    from .models import Base
    # Deleta e recria todas as tabelas para sincronizar schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Banco de dados limpo e recriado com sucesso!")

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
                file_path=file_name,
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
        
        # 8. Criação de Dados TinhaKids (Pais, Crianças, Posts, Portfólio)
        from .models import Parent, Child, Post, Project
        from .security import get_password_hash
        import json
        from datetime import datetime, timedelta
        
        print("\nSemeando dados TinhaKids...")
        
        parent = Parent(
            id="parent_teste",
            name="João Teste",
            email="teste@teste.com",
            phone="11999999999",
            hashed_password=get_password_hash("123456"),
            is_active=True
        )
        session.add(parent)
        
        child_pedro = Child(
            id="pedro",
            name="Pedro",
            avatar_path="https://images.unsplash.com/photo-1503919545889-aef636e10ad4?auto=format&fit=crop&q=80&w=300",
            classroom="Maternal II - Profª Ana"
        )
        child_sofia = Child(
            id="sofia",
            name="Sofia",
            avatar_path="https://images.unsplash.com/photo-1516627145497-ae6968895b74?auto=format&fit=crop&q=80&w=300",
            classroom="Maternal II - Profª Ana"
        )
        
        parent.children.extend([child_pedro, child_sofia])
        session.add_all([child_pedro, child_sofia])
        
        # Posts
        now = datetime.utcnow()
        posts_data = [
            ("post_1", [child_pedro, child_sofia], "https://images.unsplash.com/photo-1513364776144-60967b0f800f?auto=format&fit=crop&q=80&w=800", "Hoje aprendemos sobre as cores usando tinta guache! 🎨 As crianças misturaram as cores primárias para ver novas cores surgindo. Foi uma festa de criatividade e descobertas!", now - timedelta(hours=2)),
            ("post_2", [child_pedro], "https://images.unsplash.com/photo-1515488042361-404e9250afef?auto=format&fit=crop&q=80&w=800", "O Pedro ficou super concentrado montando a maior torre de blocos hoje! 🧱 Ele trabalhou muito bem o equilíbrio e a noção de espaço.", now - timedelta(hours=4)),
            ("post_3", [child_sofia], "https://images.unsplash.com/photo-1530606901857-6c97337def3c?auto=format&fit=crop&q=80&w=800", "A Sofia ajudando a regar a nossa horta da escola. Ela adorou ver como as sementinhas de feijão que plantamos estão crescendo fortes! 🌱💧", now - timedelta(hours=6)),
            ("post_4", [child_pedro, child_sofia], "https://images.unsplash.com/photo-1577896851231-70ef18881754?auto=format&fit=crop&q=80&w=800", "Momento de contação de histórias! 🦁📚 Hoje mergulhamos na aventura do leãozinho corajoso. Todos participaram ativamente imitando os animais da selva.", now - timedelta(days=1)),
            ("post_5", [child_sofia], "https://images.unsplash.com/photo-1596464716127-f2a82984de30?auto=format&fit=crop&q=80&w=800", "Sofia explorando diferentes texturas com massinha de modelar caseira! 👩‍🎨 Ela criou flores e bichinhos fantásticos, exercitando muito a imaginação.", now - timedelta(days=2)),
            ("post_6", [child_pedro], "https://images.unsplash.com/photo-1587654780291-39c9404d746b?auto=format&fit=crop&q=80&w=800", "Pedro se divertindo demais no caça ao tesouro do parquinho! 🏃‍♂️ Ele correu, achou pistas e trabalhou super bem em equipe para encontrar o baú de adesivos.", now - timedelta(days=3))
        ]
        
        for p_id, p_children, p_img, p_caption, p_time in posts_data:
            post = Post(
                id=p_id,
                classroom_name="Maternal II",
                teacher_name="Profª Ana Souza",
                teacher_avatar_url="https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=300",
                image_path=p_img,
                caption=p_caption,
                created_at=p_time
            )
            post.children.extend(p_children)
            session.add(post)
            
        # Projects
        projects_data = [
            ("p_p1", child_pedro, "Autorretrato com Colagem", "https://images.unsplash.com/photo-1513364776144-60967b0f800f?auto=format&fit=crop&q=80&w=800", datetime(2026, 6, 15), ["Desenvolvimento da coordenação motora fina ao recortar e colar papéis.", "Exploração do autoreconhecimento das características e partes do rosto.", "Expressão de sentimentos e identidade pessoal através da arte livre."], "Atividade de identificação das partes do rosto usando materiais reciclados, recortes de revistas e lã para os cabelos. Pedro escolheu tons vibrantes e focou bastante no cabelo e olhos."),
            ("p_p2", child_pedro, "Mestre da Construção", "https://images.unsplash.com/photo-1515488042361-404e9250afef?auto=format&fit=crop&q=80&w=800", datetime(2026, 6, 2), ["Noções de tridimensionalidade, gravidade, peso e equilíbrio das formas.", "Trabalho colaborativo e divisão de tarefas para alcançar objetivos coletivos.", "Resolução de problemas estruturais simples ao equilibrar blocos gigantes."], "Criação de estruturas tridimensionais usando blocos de madeira e plástico. Pedro liderou a construção de \"castelo fortificado\" com seus colegas de mesa."),
            ("p_p3", child_pedro, "Germinação do Feijão", "https://images.unsplash.com/photo-1530606901857-6c97337def3c?auto=format&fit=crop&q=80&w=800", datetime(2026, 5, 18), ["Observação prática e anotação visual do crescimento dos vegetais.", "Compreensão do ciclo de vida básico das plantas e importância da água/sol.", "Estimulação de rotinas diárias de cuidado, responsabilidade e afeto."], "Acompanhamento do plantio de sementes em copinhos com algodão e terra. Pedro regou seu brotinho todos os dias e mediu a altura com ajuda da régua colorida."),
            ("p_p4", child_pedro, "Sopros de Guache", "https://images.unsplash.com/photo-1596464716127-f2a82984de30?auto=format&fit=crop&q=80&w=800", datetime(2026, 4, 27), ["Estimulação da capacidade respiratória e sopro direcional.", "Exploração de misturas de tintas e formação espontânea de cores secundárias.", "Percepção de causa e efeito ao mover a tinta líquida no papel com canudinho."], "Atividade de artes soprando pingos de tinta com um canudo para criar padrões psicodélicos. Pedro achou a atividade muito divertida e a chamou de \"explosão espacial\"."),
            ("p_p5", child_pedro, "Pintura Corporal e Sensorial", "https://images.unsplash.com/photo-1503919545889-aef636e10ad4?auto=format&fit=crop&q=80&w=800", datetime(2026, 3, 9), ["Exploração tátil e sensorial com tintas espessas de diferentes texturas.", "Expressão de movimentos amplos utilizando braços, mãos e pés no papel.", "Redução da aversão tátil a texturas molhadas ou pastosas."], "Pintura gigante no chão da sala de artes, utilizando as mãos e pés para carimbar formas. Estimulou a socialização e desinibição tátil das crianças."),
            
            ("s_p1", child_sofia, "Jardim das Borboletas", "https://images.unsplash.com/photo-1513364776144-60967b0f800f?auto=format&fit=crop&q=80&w=800", datetime(2026, 6, 18), ["Exploração de simetria por meio da dobra do papel pintado.", "Coordenação óculo-manual de alta precisão ao colar lantejoulas e fitas.", "Introdução aos insetos polinizadores e seu papel na natureza."], "Confecção de borboletas tridimensionais com papel dobrado e tinta. Dobrando o papel ao meio, Sofia aprendeu sobre cópias simétricas e decorou as asas com brilho."),
            ("s_p2", child_sofia, "Horta Escolar Coletiva", "https://images.unsplash.com/photo-1530606901857-6c97337def3c?auto=format&fit=crop&q=80&w=800", datetime(2026, 6, 5), ["Educação alimentar através do contato direto com alimentos naturais.", "Desenvolvimento da paciência e respeito pelos tempos da natureza.", "Estímulo tátil ao manusear terra adubada, sementes e mudas."], "Plantio coletivo de alface e tomatinhos na horta do Maternal. Sofia ajudou a fazer os buraquinhos na terra e a colocar as pequenas mudas com todo carinho."),
            ("s_p3", child_sofia, "Modelagem em Argila Natural", "https://images.unsplash.com/photo-1596464716127-f2a82984de30?auto=format&fit=crop&q=80&w=800", datetime(2026, 5, 22), ["Fortalecimento muscular das mãos e articulações finas.", "Experimentação de transformações físicas de sólido a maleável.", "Apreciação estética e autoria no desenvolvimento de esculturas."], "Sofia modelou pequenos pratinhos e bolinhas de argila natural, que depois de secos foram pintados com tinta metálica. Ela declarou que fez \"comidinhas de dinossauro\"."),
            ("s_p4", child_sofia, "Sons e Chocalhos Caseiros", "https://images.unsplash.com/photo-1577896851231-70ef18881754?auto=format&fit=crop&q=80&w=800", datetime(2026, 4, 12), ["Construção de instrumentos percussivos com sucata e grãos.", "Desenvolvimento de percepção de compasso, ritmo e som/silêncio.", "Trabalho de foco auditivo e discriminação de barulhos finos e grossos."], "Garrafinhas PET decoradas com grãos de feijão, arroz e lentilha. Sofia criou seu próprio chocalho rítmico e acompanhou a cantoria da Profª Ana."),
            ("s_p5", child_sofia, "Explorando Cores Quentes", "https://images.unsplash.com/photo-1516627145497-ae6968895b74?auto=format&fit=crop&q=80&w=800", datetime(2026, 3, 15), ["Classificação de tonalidades em quentes (vermelho, amarelo, laranja).", "Desenho guiado expressivo baseado em música calma.", "Habilidades de preenchimento de espaço no papel sulfite gigante."], "Atividade de colorir inspirada em sons da natureza, usando gizes de cera pastel de cores quentes. Sofia desenhou grandes círculos simulando o sol e flores.")
        ]
        
        for proj_id, p_child, p_title, p_img, p_date, p_obj, p_desc in projects_data:
            proj = Project(
                id=proj_id,
                child_id=p_child.id,
                title=p_title,
                image_path=p_img,
                completion_date=p_date,
                description=p_desc,
                pedagogical_objectives=json.dumps(p_obj)
            )
            session.add(proj)
            
        session.commit()
        print("Dados do TinhaKids registrados com sucesso!")
        
        print("\nCarga inicial de dados finalizada com SUCESSO!")

    except Exception as e:
        session.rollback()
        print(f"Erro durante a carga de dados: {str(e)}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    seed_data()
