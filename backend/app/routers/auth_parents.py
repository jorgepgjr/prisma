from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta
import uuid

from .. import db, models, security
from ..schemas import ParentResponse, Token

# Utilizando google.oauth2.id_token
from google.oauth2 import id_token
from google.auth.transport import requests

router = APIRouter()

# --- Request Schemas específicos deste router ---
class RequestActivation(BaseModel):
    email: EmailStr

class ActivateAccount(BaseModel):
    token: str
    password: str
    phone: str

class LoginRequest(BaseModel):
    identifier: str # aceita email ou celular
    password: str

class GoogleLogin(BaseModel):
    id_token: str

GOOGLE_CLIENT_ID = "seu-google-client-id-aqui.apps.googleusercontent.com" # Em prod viria do .env

@router.post("/request-activation")
def request_activation(req: RequestActivation, session: Session = Depends(db.get_db)):
    parent = session.query(models.Parent).filter(models.Parent.email == req.email).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Email não pré-cadastrado na escola.")
    
    # Na prática isso salvaria no banco um token com expiração
    activation_token = str(uuid.uuid4()) 
    
    print(f"=== SIMULAÇÃO DE E-MAIL ===")
    print(f"Para: {req.email}")
    print(f"Assunto: Ative sua conta TinhaKids")
    print(f"Link: https://tinhakids.app/activate?token={activation_token}")
    print(f"===========================")
    
    return {"message": "Email de ativação enviado com sucesso."}

@router.post("/activate", response_model=ParentResponse)
def activate_account(req: ActivateAccount, session: Session = Depends(db.get_db)):
    # Simulação: Como não salvamos o token real no banco neste boilerplate,
    # vamos apenas aprovar quem não tem senha ainda como demonstração.
    # Numa aplicação real, buscaríamos pelo token.
    parent = session.query(models.Parent).filter(models.Parent.is_active == False).first()
    
    if not parent:
        raise HTTPException(status_code=400, detail="Nenhuma conta aguardando ativação ou token inválido.")
        
    parent.hashed_password = security.get_password_hash(req.password)
    parent.phone = req.phone
    parent.is_active = True
    
    session.commit()
    session.refresh(parent)
    return parent

@router.post("/login", response_model=Token)
def login(req: LoginRequest, session: Session = Depends(db.get_db)):
    parent = session.query(models.Parent).filter(
        (models.Parent.email == req.identifier) | (models.Parent.phone == req.identifier)
    ).first()
    
    if not parent or not parent.is_active:
        raise HTTPException(status_code=401, detail="Credenciais inválidas ou conta inativa.")
        
    if not parent.hashed_password or not security.verify_password(req.password, parent.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")
        
    access_token = security.create_access_token(data={"sub": parent.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/google", response_model=Token)
def google_login(req: GoogleLogin, session: Session = Depends(db.get_db)):
    try:
        idinfo = id_token.verify_oauth2_token(req.id_token, requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo['email']
        google_id = idinfo['sub']
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    parent = session.query(models.Parent).filter(models.Parent.email == email).first()
    
    if not parent:
        raise HTTPException(status_code=403, detail="Email não pré-cadastrado na escola.")
        
    # Vincula o google_id e ativa se ainda não estava
    parent.google_id = google_id
    parent.is_active = True
    session.commit()
    
    access_token = security.create_access_token(data={"sub": parent.id})
    return {"access_token": access_token, "token_type": "bearer"}
