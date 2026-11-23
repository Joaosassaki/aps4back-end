import os

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import UsuarioDB, PERFIL_ADMINISTRADOR, PERFIL_USUARIO
from schemas import UsuarioEntrada, LoginEntrada
from security import HASH_FALSO, criar_token, gerar_hash, verificar_senha

MENSAGEM_EMAIL_DUPLICADO = "Já existe um usuário cadastrado com este e-mail."


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def cadastrar_usuario(db: Session, dados: UsuarioEntrada, perfil: str = PERFIL_USUARIO) -> UsuarioDB:
    email = normalizar_email(dados.email)
    if db.query(UsuarioDB).filter(UsuarioDB.email == email).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, MENSAGEM_EMAIL_DUPLICADO)

    usuario = UsuarioDB(nome=dados.nome, email=email, senha_hash=gerar_hash(dados.senha), perfil=perfil)
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, MENSAGEM_EMAIL_DUPLICADO)
    db.refresh(usuario)
    return usuario


def autenticar(db: Session, dados: LoginEntrada) -> dict:
    usuario = db.query(UsuarioDB).filter(UsuarioDB.email == normalizar_email(dados.email)).first()
    senha_confere = verificar_senha(dados.senha, usuario.senha_hash if usuario else HASH_FALSO)
    if usuario is None or not senha_confere:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": criar_token(usuario.id), "token_type": "bearer"}


def criar_administrador_inicial(db: Session) -> None:
    email = os.getenv("ADMIN_EMAIL")
    senha = os.getenv("ADMIN_SENHA")
    if not email or not senha:
        return
    if db.query(UsuarioDB).filter(UsuarioDB.email == normalizar_email(email)).first() is not None:
        return
    dados = UsuarioEntrada(nome=os.getenv("ADMIN_NOME", "Administrador"), email=email, senha=senha)
    cadastrar_usuario(db, dados, perfil=PERFIL_ADMINISTRADOR)
