from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum, DateTime, Table
from sqlalchemy.orm import relationship, validates
from datetime import datetime
import enum
from .db import Base
from .security import get_password_hash

class RoleEnum(enum.Enum):
    ADMIN = "ADMIN"
    DIRETOR = "DIRETOR"
    COORDENADOR = "COORDENADOR"
    PROFESSOR = "PROFESSOR"
    MARKETING = "MARKETING"

class PhotoStatusEnum(enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED_FOR_MARKETING = "APPROVED_FOR_MARKETING"
    PRIVATE_SCHOOL_ONLY = "PRIVATE_SCHOOL_ONLY"

class StudentStatusEnum(enum.Enum):
    ATIVO = "ATIVO"
    INATIVO = "INATIVO"

# Relacionamento N:N entre Usuários (Professores) e Turmas
user_class_link = Table(
    'user_class_link',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('class_id', Integer, ForeignKey('classes.id'), primary_key=True)
)

# Relacionamento N:N entre Fotos e Alunos
photo_student_link = Table(
    'photo_student_link',
    Base.metadata,
    Column('photo_id', Integer, ForeignKey('photos.id'), primary_key=True),
    Column('student_id', Integer, ForeignKey('students.id'), primary_key=True)
)

# Relacionamento N:N entre Fotos e Tags
photo_tag_link = Table(
    'photo_tag_link',
    Base.metadata,
    Column('photo_id', Integer, ForeignKey('photos.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    photos = relationship("Photo", secondary=photo_tag_link, back_populates="tags")

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.PROFESSOR, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relação com Turmas (Para Professores)
    classes = relationship("Class", secondary=user_class_link, back_populates="teachers")
    # Relação com Fotos que ele fez upload
    uploaded_photos = relationship("Photo", back_populates="uploader")

    @validates('hashed_password')
    def validate_hashed_password(self, key, password):
        if password and (password.startswith("$2b$") or password.startswith("$2a$")):
            return password
        return get_password_hash(password)


class Class(Base):
    __tablename__ = 'classes'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    teachers = relationship("User", secondary=user_class_link, back_populates="classes")
    students = relationship("Student", back_populates="school_class")
    photos = relationship("Photo", back_populates="school_class")


class Student(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    status = Column(SQLEnum(StudentStatusEnum), default=StudentStatusEnum.ATIVO, nullable=False)
    marketing_allowed = Column(Boolean, default=False, nullable=False)

    school_class = relationship("Class", back_populates="students")
    photos = relationship("Photo", secondary=photo_student_link, back_populates="students")


class Photo(Base):
    __tablename__ = 'photos'

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    uploaded_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=True)
    status = Column(SQLEnum(PhotoStatusEnum), default=PhotoStatusEnum.PENDING_REVIEW, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    uploader = relationship("User", back_populates="uploaded_photos")
    school_class = relationship("Class", back_populates="photos")
    students = relationship("Student", secondary=photo_student_link, back_populates="photos")
    tags = relationship("Tag", secondary=photo_tag_link, back_populates="photos")

# Tabela Associativa N:N Parent -> Child
parent_child_link = Table(
    'parent_child_link',
    Base.metadata,
    Column('parent_id', String, ForeignKey('parents.id', ondelete="CASCADE"), primary_key=True),
    Column('child_id', String, ForeignKey('children.id', ondelete="CASCADE"), primary_key=True)
)

# Tabela Associativa N:N Child -> Post
post_child_link = Table(
    'post_child_link',
    Base.metadata,
    Column('post_id', String, ForeignKey('posts.id', ondelete="CASCADE"), primary_key=True),
    Column('child_id', String, ForeignKey('children.id', ondelete="CASCADE"), primary_key=True)
)

class Parent(Base):
    __tablename__ = 'parents'
    id = Column(String, primary_key=True, index=True) # UUID
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    google_id = Column(String, unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    children = relationship("Child", secondary=parent_child_link, back_populates="parents")

class Child(Base):
    __tablename__ = 'children'
    id = Column(String, primary_key=True, index=True) # UUID
    name = Column(String, nullable=False)
    avatar_path = Column(String, nullable=False)
    classroom = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    parents = relationship("Parent", secondary=parent_child_link, back_populates="children")
    posts = relationship("Post", secondary=post_child_link, back_populates="children")
    projects = relationship("Project", back_populates="child")

class Post(Base):
    __tablename__ = 'posts'
    id = Column(String, primary_key=True, index=True) # UUID
    classroom_name = Column(String, nullable=False)
    teacher_name = Column(String, nullable=False)
    teacher_avatar_url = Column(String, nullable=False)
    image_path = Column(String, nullable=False)
    caption = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    children = relationship("Child", secondary=post_child_link, back_populates="posts")

class Project(Base):
    __tablename__ = 'projects'
    id = Column(String, primary_key=True, index=True) # UUID
    child_id = Column(String, ForeignKey('children.id', ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    image_path = Column(String, nullable=False)
    completion_date = Column(DateTime, nullable=False)
    description = Column(String, nullable=False)
    pedagogical_objectives = Column(String, nullable=False) # JSON encoded string
    created_at = Column(DateTime, default=datetime.utcnow)
    
    child = relationship("Child", back_populates="projects")
