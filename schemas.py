from datetime import date, time, datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, ConfigDict, StringConstraints


NomeUsuario = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class UsuarioEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: NomeUsuario
    email: EmailStr
    senha: str = Field(..., min_length=8, max_length=128)


class Usuario(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    email: EmailStr
    perfil: str


class LoginEntrada(BaseModel):
    email: str = Field(..., min_length=1)
    senha: str = Field(..., min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EventoEntrada(BaseModel):
    titulo: str = Field(..., min_length=1)
    descricao: str = Field(..., min_length=1)
    data: date
    horario: time
    local: str = Field(..., min_length=1)
    capacidade: int = Field(..., gt=0)
    categoria: str = Field(..., min_length=1)


class Evento(EventoEntrada):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ParticipanteEntrada(BaseModel):
    nome: str = Field(..., min_length=1)
    email: EmailStr
    curso: str = Field(..., min_length=1)


class Participante(ParticipanteEntrada):
    model_config = ConfigDict(from_attributes=True)
    id: int


class Inscricao(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    evento_id: int
    participante_id: int
    data_inscricao: datetime


class RelatorioOcupacaoEvento(BaseModel):
    evento_id: int
    titulo: str
    capacidade: int
    total_inscritos: int
    vagas_disponiveis: int
    percentual_ocupacao: float


class RelatorioCategoria(BaseModel):
    categoria: str
    total_eventos: int
    capacidade_total: int
    total_inscricoes: int


class RelatorioCurso(BaseModel):
    curso: str
    total_participantes: int
    total_inscricoes: int
