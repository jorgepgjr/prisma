from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from .models import RoleEnum, PhotoStatusEnum

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[RoleEnum] = None

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: RoleEnum = RoleEnum.PROFESSOR

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Adicionais para futuras iterações (Turmas, Alunos, etc) ---
class ClassBase(BaseModel):
    name: str
    year: int

class ClassCreate(ClassBase):
    pass

class ClassResponse(ClassBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Tag Schemas ---
class TagBase(BaseModel):
    name: str

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Photo Schemas ---
class PhotoResponse(BaseModel):
    id: int
    file_path: str
    title: Optional[str] = None
    uploaded_by_user_id: int
    class_id: Optional[int] = None
    status: str
    created_at: datetime
    student_ids: List[int] = []
    tags: List[TagResponse] = []

    class Config:
        from_attributes = True

# --- Student Schemas ---
class StudentBase(BaseModel):
    name: str
    class_id: int
    marketing_allowed: bool = False

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    id: int
    status: str

    class Config:
        from_attributes = True

class PhotoStatusUpdate(BaseModel):
    status: PhotoStatusEnum

class PhotoTagStudents(BaseModel):
    student_ids: List[int]

# --- TinhaKids API Schemas (Parents View) ---

class ChildResponse(BaseModel):
    id: str
    name: str
    avatar_path: str
    classroom: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ParentResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    children: List[ChildResponse] = []
    
    class Config:
        from_attributes = True

class PostResponse(BaseModel):
    id: str
    classroom_name: str
    teacher_name: str
    teacher_avatar_url: str
    image_url: str # This will be the presigned URL
    caption: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProjectResponse(BaseModel):
    id: str
    child_id: str
    title: str
    image_url: str # Presigned URL
    completion_date: datetime
    description: str
    pedagogical_objectives: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
