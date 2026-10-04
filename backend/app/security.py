import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt

# Configurações do JWT
SECRET_KEY = os.getenv("SECRET_KEY", "uma-chave-secreta-muito-segura-para-desenvolvimento")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Dependências para TinhaKids API ---
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Presumimos que get_db está em app.db
from .db import get_db
from . import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def parent_school_is_active(parent: models.Parent, session: Session) -> bool:
    if parent.school_id is None:
        return True  # Compatibilidade com contas familiares legadas.
    school = session.get(models.School, parent.school_id)
    return school is not None and school.is_active


def can_parent_access_child(parent: models.Parent, child: models.Child) -> bool:
    if child not in parent.children:
        return False
    if parent.school_id is not None and parent.school_id != child.school_id:
        return False
    if not child.school or not child.school.is_active:
        return False
    student = child.student_profile
    return student is None or (
        student.school_id == child.school_id and student.status == models.StudentStatusEnum.ATIVO
    )


def get_current_parent(token: str = Depends(oauth2_scheme), session: Session = Depends(get_db)) -> models.Parent:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        parent_id: str = payload.get("sub")
        if parent_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    parent = session.query(models.Parent).filter(models.Parent.id == parent_id).first()
    if parent is None or not parent.is_active or not parent_school_is_active(parent, session):
        raise credentials_exception
    return parent

def verifyChildAccess(child_id: str, current_parent: models.Parent = Depends(get_current_parent), session: Session = Depends(get_db)):
    """
    Middleware/Dependency to check if the current parent has access to the specified child.
    """
    child = session.query(models.Child).filter(models.Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
        
    if not can_parent_access_child(current_parent, child):
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this child's data")
        
    return child

def generatePresignedUrl(image_path: str) -> str:
    """
    Simulates a presigned URL by generating a short-lived JWT token containing the path,
    which will be verified by the /api/v1/media endpoint.
    Returns the path directly if it is an external URL (http/https).
    """
    if not image_path:
        return ""
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return image_path
        
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {"path": image_path, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return f"/api/v1/media?path={image_path}&signature={encoded_jwt}"
