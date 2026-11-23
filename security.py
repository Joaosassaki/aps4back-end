import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from database import obter_sessao
from models import UsuarioDB, PERFIL_ADMINISTRADOR

load_dotenv()

ALGORITMO = "HS256"

hasher = PasswordHash.recommended()
HASH_FALSO = hasher.hash("senha-usada-apenas-para-igualar-o-tempo-de-resposta")
esquema_bearer = HTTPBearer(auto_error=False)


def gerar_hash(senha: str) -> str:
    return hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return hasher.verify(senha, senha_hash)


def obter_chave_secreta() -> str:
    chave = os.getenv("SECRET_KEY")
    if not chave:
        raise RuntimeError("A variável de ambiente SECRET_KEY não foi definida. Veja o README.")
    return chave


def obter_validade() -> timedelta:
    return timedelta(minutes=int(os.getenv("TOKEN_EXPIRA_MINUTOS", "30")))


def criar_token(usuario_id: int, validade: timedelta | None = None) -> str:
    agora = datetime.now(timezone.utc)
    dados = {
        "sub": str(usuario_id),
        "iat": agora,
        "exp": agora + (validade if validade is not None else obter_validade()),
    }
    return jwt.encode(dados, obter_chave_secreta(), algorithm=ALGORITMO)


def erro_de_credenciais() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def identificar_usuario_do_token(token: str) -> int:
    try:
        dados = jwt.decode(
            token,
            obter_chave_secreta(),
            algorithms=[ALGORITMO],
            options={"require": ["exp", "sub"]},
        )
        return int(dados["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise erro_de_credenciais()


def obter_usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(obter_sessao),
) -> UsuarioDB:
    if credenciais is None:
        raise erro_de_credenciais()
    usuario = db.get(UsuarioDB, identificar_usuario_do_token(credenciais.credentials))
    if usuario is None:
        raise erro_de_credenciais()
    return usuario


def exigir_administrador(usuario: UsuarioDB = Depends(obter_usuario_atual)) -> UsuarioDB:
    if usuario.perfil != PERFIL_ADMINISTRADOR:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não possui permissão para executar esta operação.")
    return usuario
