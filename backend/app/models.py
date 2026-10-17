import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, JSON, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship, validates

from .db import Base
from .security import get_password_hash


class RoleEnum(enum.Enum):
    COORDENADOR = "COORDENADOR"
    PROFESSOR = "PROFESSOR"
    MARKETING = "MARKETING"


class PhotoStatusEnum(enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED_FOR_MARKETING = "APPROVED_FOR_MARKETING"
    PRIVATE_SCHOOL_ONLY = "PRIVATE_SCHOOL_ONLY"

class ProcessStatusEnum(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class StudentStatusEnum(enum.Enum):
    ATIVO = "ATIVO"
    INATIVO = "INATIVO"


user_class_link = Table(
    "user_class_link", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("class_id", Integer, ForeignKey("classes.id"), primary_key=True),
)
photo_student_link = Table(
    "photo_student_link", Base.metadata,
    Column("photo_id", Integer, ForeignKey("photos.id"), primary_key=True),
    Column("student_id", Integer, ForeignKey("students.id"), primary_key=True),
)
photo_tag_link = Table(
    "photo_tag_link", Base.metadata,
    Column("photo_id", Integer, ForeignKey("photos.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)
post_photo_link = Table(
    "post_photo_link", Base.metadata,
    Column("post_id", String, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("photo_id", Integer, ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True),
)
project_photo_link = Table(
    "project_photo_link", Base.metadata,
    Column("project_id", String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("photo_id", Integer, ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True),
)
student_child_link = Table(
    "student_child_link", Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
    Column("child_id", String, ForeignKey("children.id", ondelete="CASCADE"), primary_key=True, unique=True),
)
parent_child_link = Table(
    "parent_child_link", Base.metadata,
    Column("parent_id", String, ForeignKey("parents.id", ondelete="CASCADE"), primary_key=True),
    Column("child_id", String, ForeignKey("children.id", ondelete="CASCADE"), primary_key=True),
)
post_child_link = Table(
    "post_child_link", Base.metadata,
    Column("post_id", String, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("child_id", String, ForeignKey("children.id", ondelete="CASCADE"), primary_key=True),
)


class School(Base):
    __tablename__ = "schools"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    plan_name = Column(String, nullable=False, default="Básico")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    users = relationship("User", back_populates="school")
    classes = relationship("Class", back_populates="school")
    students = relationship("Student", back_populates="school")
    photos = relationship("Photo", back_populates="school")


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    photos = relationship("Photo", secondary=photo_tag_link, back_populates="tags")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.PROFESSOR, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    school = relationship("School", back_populates="users")
    classes = relationship("Class", secondary=user_class_link, back_populates="teachers")
    uploaded_photos = relationship("Photo", back_populates="uploader")

    @validates("hashed_password")
    def validate_hashed_password(self, _key, password):
        if password and (password.startswith("$2b$") or password.startswith("$2a$")):
            return password
        return get_password_hash(password)


class Class(Base):
    __tablename__ = "classes"
    __table_args__ = (UniqueConstraint("school_id", "name", "year", name="uq_class_school_name_year"),)
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    school = relationship("School", back_populates="classes")
    teachers = relationship("User", secondary=user_class_link, back_populates="classes")
    students = relationship("Student", back_populates="school_class")
    photos = relationship("Photo", back_populates="school_class")


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    status = Column(SQLEnum(StudentStatusEnum), default=StudentStatusEnum.ATIVO, nullable=False)
    marketing_allowed = Column(Boolean, default=False, nullable=False)
    school = relationship("School", back_populates="students")
    school_class = relationship("Class", back_populates="students")
    photos = relationship("Photo", secondary=photo_student_link, back_populates="students")
    child_profile = relationship("Child", secondary=student_child_link, back_populates="student_profile", uselist=False)


class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    file_path = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True, index=True)
    status = Column(SQLEnum(PhotoStatusEnum), default=PhotoStatusEnum.PENDING_REVIEW, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    school = relationship("School", back_populates="photos")
    process_status = Column(SQLEnum(ProcessStatusEnum), default=ProcessStatusEnum.PENDING, nullable=False)
    process_attempts = Column(Integer, default=0, nullable=False)
    process_error = Column(Text, nullable=True)
    uploader = relationship("User", back_populates="uploaded_photos")
    school_class = relationship("Class", back_populates="photos")
    students = relationship("Student", secondary=photo_student_link, back_populates="photos")
    tags = relationship("Tag", secondary=photo_tag_link, back_populates="photos")
    posts = relationship("Post", secondary=post_photo_link, back_populates="photos")
    projects = relationship("Project", secondary=project_photo_link, back_populates="photos")
    detected_faces = relationship("DetectedFace", back_populates="photo", cascade="all, delete-orphan")


class Parent(Base):
    __tablename__ = "parents"
    id = Column(String, primary_key=True, index=True)
    # Nullable somente para contas antigas sem escola identificável.
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    google_id = Column(String, unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    children = relationship("Child", secondary=parent_child_link, back_populates="parents")


class Child(Base):
    __tablename__ = "children"
    id = Column(String, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    avatar_path = Column(String, nullable=True)
    classroom = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    school = relationship("School")
    parents = relationship("Parent", secondary=parent_child_link, back_populates="children")
    posts = relationship("Post", secondary=post_child_link, back_populates="children")
    projects = relationship("Project", back_populates="child")
    student_profile = relationship("Student", secondary=student_child_link, back_populates="child_profile", uselist=False)


class Post(Base):
    __tablename__ = "posts"
    id = Column(String, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    classroom_name = Column(String, nullable=False)
    teacher_name = Column(String, nullable=False)
    teacher_avatar_url = Column(String, nullable=True)
    image_path = Column(String, nullable=False)
    caption = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    school = relationship("School")
    children = relationship("Child", secondary=post_child_link, back_populates="posts")
    photos = relationship("Photo", secondary=post_photo_link, back_populates="posts")


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    child_id = Column(String, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    image_path = Column(String, nullable=False)
    completion_date = Column(DateTime, nullable=False)
    description = Column(String, nullable=False)
    pedagogical_objectives = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    school = relationship("School")
    child = relationship("Child", back_populates="projects")
    photos = relationship("Photo", secondary=project_photo_link, back_populates="projects")

class FaceCluster(Base):
    __tablename__ = 'face_clusters'

    id = Column(String, primary_key=True, index=True)  # UUID
    # Nullable apenas para grupos antigos cuja escola não pode ser identificada.
    school_id = Column(Integer, ForeignKey('schools.id'), nullable=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id', ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", backref="face_clusters")
    faces = relationship("DetectedFace", back_populates="cluster", cascade="all, delete-orphan")

class DetectedFace(Base):
    __tablename__ = 'detected_faces'

    id = Column(String, primary_key=True, index=True)  # UUID
    photo_id = Column(Integer, ForeignKey('photos.id', ondelete="CASCADE"), nullable=False)
    cluster_id = Column(String, ForeignKey('face_clusters.id', ondelete="SET NULL"), nullable=True)
    bounding_box = Column(JSON, nullable=False)  # [x1, y1, x2, y2]
    embedding = Column(JSON, nullable=True)  # List[float] (512-dim embedding)
    face_crop_path = Column(String, nullable=True)
    detection_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    photo = relationship("Photo", back_populates="detected_faces")
    cluster = relationship("FaceCluster", back_populates="faces")
