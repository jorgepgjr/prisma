from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .db import engine
from .auth import router as auth_router
from .photos import router as photos_router
from .classes import router as classes_router
from .students import router as students_router
from .tags import router as tags_router
from .routers.auth_parents import router as auth_parents_router
from .routers.children import router as children_router
from .routers.posts import router as posts_router
from .routers.portfolio import router as portfolio_router
from .routers.media import router as media_router
from .admin import setup_admin

# Cria as tabelas do banco de dados (útil para desenvolvimento, 
# em produção recomenda-se usar Alembic)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Portal Web para Galeria Escolar",
    description="API para gerenciar fotos, turmas e permissões de usuários (RBAC).",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    from .db import SessionLocal
    db = SessionLocal()
    try:
        # Create default tags if they don't exist
        default_tags = ["restricao-lgpd", "marketing"]
        for tag_name in default_tags:
            tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
            if not tag:
                new_tag = models.Tag(name=tag_name)
                db.add(new_tag)
        db.commit()
    finally:
        db.close()


# Inicializa o SQLAdmin
setup_admin(app)

# Configuração de CORS para permitir que o frontend (Next.js) acesse a API
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui o roteador de autenticação
app.include_router(auth_router, prefix="/api/auth", tags=["Autenticação"])
app.include_router(photos_router, prefix="/api/photos", tags=["Fotos"])
app.include_router(classes_router, prefix="/api/classes", tags=["Turmas"])
app.include_router(students_router, prefix="/api/students", tags=["Alunos"])
app.include_router(tags_router, prefix="/api/tags", tags=["Tags"])

# TinhaKids API v1 (Visão dos Pais)
app.include_router(auth_parents_router, prefix="/api/v1/auth", tags=["TinhaKids - Auth"])
app.include_router(children_router, prefix="/api/v1/children", tags=["TinhaKids - Crianças"])
app.include_router(posts_router, prefix="/api/v1/posts", tags=["TinhaKids - Posts"])
app.include_router(portfolio_router, prefix="/api/v1/portfolio", tags=["TinhaKids - Portfólio"])
app.include_router(media_router, prefix="/api/v1/media", tags=["TinhaKids - Mídia Segura"])

@app.get("/")
def read_root():
    return {"message": "API do Portal Web da Galeria Escolar está online!"}
