from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from .models import PhotoStatusEnum, RoleEnum

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class SchoolResponse(BaseModel):
    id: int
    name: str
    plan_name: str
    is_active: bool
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    school_id: int
    name: str
    email: EmailStr
    role: RoleEnum
    is_active: bool
    created_at: datetime
    class_ids: List[int] = []
    class Config:
        from_attributes = True


class CurrentUserResponse(UserResponse):
    school: SchoolResponse


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: RoleEnum
    password: str = Field(min_length=6, max_length=128)
    class_ids: List[int] = []


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    role: Optional[RoleEnum] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    class_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None


class ClassBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    year: int = Field(ge=2000, le=2200)


class ClassCreate(ClassBase):
    teacher_ids: List[int] = []


class ClassUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    year: Optional[int] = Field(default=None, ge=2000, le=2200)
    teacher_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None


class ClassResponse(ClassBase):
    id: int
    school_id: int
    is_active: bool
    created_at: datetime
    teacher_ids: List[int] = []
    class Config:
        from_attributes = True


class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    pass


class TagResponse(TagBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


class PhotoResponse(BaseModel):
    id: int
    file_path: str
    media_url: str
    title: Optional[str] = None
    description: Optional[str] = None
    uploaded_by_user_id: int
    uploader_name: Optional[str] = None
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    status: str
    process_status: Optional[str] = "PENDING"
    process_attempts: int = 0
    process_error: Optional[str] = None
    detected_faces_count: int = 0
    created_at: datetime
    student_ids: List[int] = []
    tags: List[TagResponse] = []
    class Config:
        from_attributes = True


class StudentBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    class_id: int
    marketing_allowed: bool = False


class StudentCreate(StudentBase):
    parent_ids: List[str] = []


class StudentUpdate(BaseModel):
    parent_ids: Optional[List[str]] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    class_id: Optional[int] = None
    marketing_allowed: Optional[bool] = None
    is_active: Optional[bool] = None


class StudentResponse(StudentBase):
    parent_ids: List[str] = []
    id: int
    school_id: int
    status: str
    child_id: Optional[str] = None
    class Config:
        from_attributes = True


class AdminSummaryResponse(BaseModel):
    school: SchoolResponse
    active_professionals: int
    active_classes: int
    active_students: int
    photo_count: int
    storage_bytes: int
    missing_files: int


class PhotoStatusUpdate(BaseModel):
    status: PhotoStatusEnum


class PhotoTagStudents(BaseModel):
    student_ids: List[int]


class StudentFamilyLink(BaseModel):
    child_id: Optional[str] = None


class FamilyChildResponse(BaseModel):
    id: str
    name: str
    classroom: str
    avatar_url: str
    parent_names: List[str] = []
    parent_emails: List[str] = []
    linked_student_id: Optional[int] = None


class FamilyAccountCreate(BaseModel):
    parent_name: str
    parent_email: EmailStr
    parent_phone: Optional[str] = None
    initial_password: Optional[str] = None


class FamilyParentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(min_length=6)
    student_ids: List[int] = []


class FamilyParentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6)
    is_active: Optional[bool] = None
    student_ids: Optional[List[int]] = None


class FamilyParentResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    is_active: bool
    student_ids: List[int] = []


class ChildResponse(BaseModel):
    id: str
    name: str
    avatar_url: str
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
    image_url: str
    image_urls: List[str] = []
    caption: str
    created_at: datetime
    class Config:
        from_attributes = True


class PostCreate(BaseModel):
    photo_ids: List[int]
    caption: str
    student_ids: List[int]


class ManagedPostResponse(PostResponse):
    photo_id: Optional[int] = None
    child_names: List[str] = []


class ProjectResponse(BaseModel):
    id: str
    child_id: str
    title: str
    image_url: str
    image_urls: List[str] = []
    completion_date: datetime
    description: str
    pedagogical_objectives: List[str]
    created_at: datetime
    class Config:
        from_attributes = True


class PortfolioCreate(BaseModel):
    photo_ids: List[int]
    student_ids: List[int]
    title: str
    description: str
    pedagogical_objectives: List[str] = []

# --- Face Recognition & Clustering Schemas ---

class DetectedFaceResponse(BaseModel):
    id: str
    photo_id: int
    cluster_id: Optional[str] = None
    bounding_box: List[float] = []
    face_crop_url: Optional[str] = None
    detection_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

class FaceClusterResponse(BaseModel):
    id: str
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    student_class_name: Optional[str] = None
    name: Optional[str] = None
    face_count: int = 0
    photo_count: int = 0
    sample_face_crops: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True

class FaceClusterAssignRequest(BaseModel):
    student_id: int

class SystemProcessingStatusResponse(BaseModel):
    pending: int
    processing: int
    completed: int
    failed: int
    total: int

class DetectedFaceDetail(BaseModel):
    id: str
    bounding_box: List[float] = []
    face_crop_url: Optional[str] = None
    detection_score: Optional[float] = None
    cluster_id: Optional[str] = None
    cluster_name: Optional[str] = None
    student_id: Optional[int] = None
    student_name: Optional[str] = None

class ProcessingPhotoDetail(BaseModel):
    id: int
    file_path: str
    image_url: str
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    process_status: str
    process_attempts: int
    process_error: Optional[str] = None
    created_at: datetime
    detected_faces: List[DetectedFaceDetail] = []

class IngestTestFolderResponse(BaseModel):
    imported_count: int
    skipped_count: int
    total_found: int
    message: str

class ProcessNowResponse(BaseModel):
    processed_count: int
    message: str
