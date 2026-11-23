import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

CAMINHO_BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eventos.db")
URL_BANCO = f"sqlite:///{CAMINHO_BANCO}"

engine = create_engine(URL_BANCO, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def obter_sessao():
    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()


def criar_tabelas():
    import models  # noqa: F401 garante que as tabelas sejam registradas em Base
    Base.metadata.create_all(bind=engine)
