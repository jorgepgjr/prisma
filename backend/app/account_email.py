"""Um único endereço por conta, sem juntar os cadastros profissionais e familiares."""
from fastapi import HTTPException
from sqlalchemy import func, text

from . import models


def normalize_email(value):
    return str(value).strip().lower()


def email_accounts(session, email):
    email = normalize_email(email)
    return (session.query(models.User).filter(func.lower(func.trim(models.User.email)) == email).all(),
            session.query(models.Parent).filter(func.lower(func.trim(models.Parent.email)) == email).all())


def ensure_available_email(session, value, *, user_id=None, parent_id=None):
    email = normalize_email(value)
    # Serializa criações/edições simultâneas entre as duas tabelas no PostgreSQL.
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:email))"), {"email": email})
    users, parents = email_accounts(session, email)
    if any(user.id != user_id for user in users) or any(parent.id != parent_id for parent in parents):
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado. Use um e-mail diferente para cada perfil.")
    return email
