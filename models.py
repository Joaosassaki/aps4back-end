from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Date, Time, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


PERFIL_ADMINISTRADOR = "administrador"
PERFIL_USUARIO = "usuario"


class UsuarioDB(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    senha_hash = Column(String, nullable=False)
    perfil = Column(String, nullable=False, default=PERFIL_USUARIO)


class EventoDB(Base):
    __tablename__ = "eventos"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    data = Column(Date, nullable=False)
    horario = Column(Time, nullable=False)
    local = Column(String, nullable=False)
    capacidade = Column(Integer, nullable=False)
    categoria = Column(String, nullable=False)

    inscricoes = relationship(
        "InscricaoDB", back_populates="evento", cascade="all, delete-orphan"
    )


class ParticipanteDB(Base):
    __tablename__ = "participantes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    curso = Column(String, nullable=False)

    inscricoes = relationship(
        "InscricaoDB", back_populates="participante", cascade="all, delete-orphan"
    )


class InscricaoDB(Base):
    __tablename__ = "inscricoes"
    __table_args__ = (UniqueConstraint("evento_id", "participante_id", name="uq_evento_participante"),)

    id = Column(Integer, primary_key=True, index=True)
    evento_id = Column(Integer, ForeignKey("eventos.id"), nullable=False)
    participante_id = Column(Integer, ForeignKey("participantes.id"), nullable=False)
    data_inscricao = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    evento = relationship("EventoDB", back_populates="inscricoes")
    participante = relationship("ParticipanteDB", back_populates="inscricoes")
