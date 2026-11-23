from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import auth_service
import schemas
import services
from database import obter_sessao
from models import UsuarioDB
from security import exigir_administrador, obter_usuario_atual

router = APIRouter()

autenticado = [Depends(obter_usuario_atual)]
somente_administrador = [Depends(exigir_administrador)]


@router.post("/usuarios", response_model=schemas.Usuario, status_code=status.HTTP_201_CREATED, tags=["Autenticação"])
def cadastrar_usuario(dados: schemas.UsuarioEntrada, db: Session = Depends(obter_sessao)):
    return auth_service.cadastrar_usuario(db, dados)


@router.post("/auth/login", response_model=schemas.Token, tags=["Autenticação"])
def login(dados: schemas.LoginEntrada, db: Session = Depends(obter_sessao)):
    return auth_service.autenticar(db, dados)


@router.get("/auth/me", response_model=schemas.Usuario, tags=["Autenticação"])
def usuario_autenticado(usuario: UsuarioDB = Depends(obter_usuario_atual)):
    return usuario


@router.post(
    "/eventos",
    response_model=schemas.Evento,
    status_code=status.HTTP_201_CREATED,
    tags=["Eventos"],
    dependencies=somente_administrador,
)
def cadastrar_evento(dados: schemas.EventoEntrada, db: Session = Depends(obter_sessao)):
    return services.cadastrar_evento(db, dados)


@router.get("/eventos", response_model=list[schemas.Evento], tags=["Eventos"], dependencies=autenticado)
def listar_eventos(db: Session = Depends(obter_sessao)):
    return services.listar_eventos(db)


@router.get("/eventos/{evento_id}", response_model=schemas.Evento, tags=["Eventos"], dependencies=autenticado)
def consultar_evento(evento_id: int, db: Session = Depends(obter_sessao)):
    return services.buscar_evento(db, evento_id)


@router.put("/eventos/{evento_id}", response_model=schemas.Evento, tags=["Eventos"], dependencies=somente_administrador)
def atualizar_evento(evento_id: int, dados: schemas.EventoEntrada, db: Session = Depends(obter_sessao)):
    return services.atualizar_evento(db, evento_id, dados)


@router.delete(
    "/eventos/{evento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Eventos"],
    dependencies=somente_administrador,
)
def excluir_evento(evento_id: int, db: Session = Depends(obter_sessao)):
    services.remover_evento(db, evento_id)


@router.post(
    "/eventos/{evento_id}/inscricoes/{participante_id}",
    response_model=schemas.Inscricao,
    status_code=status.HTTP_201_CREATED,
    tags=["Inscrições"],
    dependencies=autenticado,
)
def inscrever(evento_id: int, participante_id: int, db: Session = Depends(obter_sessao)):
    return services.inscrever_participante(db, evento_id, participante_id)


@router.get(
    "/eventos/{evento_id}/inscricoes",
    response_model=list[schemas.Participante],
    tags=["Inscrições"],
    dependencies=autenticado,
)
def listar_inscritos(evento_id: int, db: Session = Depends(obter_sessao)):
    return services.listar_inscritos(db, evento_id)


@router.post(
    "/participantes",
    response_model=schemas.Participante,
    status_code=status.HTTP_201_CREATED,
    tags=["Participantes"],
    dependencies=autenticado,
)
def cadastrar_participante(dados: schemas.ParticipanteEntrada, db: Session = Depends(obter_sessao)):
    return services.cadastrar_participante(db, dados)


@router.get("/participantes", response_model=list[schemas.Participante], tags=["Participantes"], dependencies=autenticado)
def listar_participantes(db: Session = Depends(obter_sessao)):
    return services.listar_participantes(db)


@router.get(
    "/participantes/{participante_id}",
    response_model=schemas.Participante,
    tags=["Participantes"],
    dependencies=autenticado,
)
def consultar_participante(participante_id: int, db: Session = Depends(obter_sessao)):
    return services.buscar_participante(db, participante_id)


@router.put(
    "/participantes/{participante_id}",
    response_model=schemas.Participante,
    tags=["Participantes"],
    dependencies=somente_administrador,
)
def atualizar_participante(participante_id: int, dados: schemas.ParticipanteEntrada, db: Session = Depends(obter_sessao)):
    return services.atualizar_participante(db, participante_id, dados)


@router.delete(
    "/participantes/{participante_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Participantes"],
    dependencies=somente_administrador,
)
def excluir_participante(participante_id: int, db: Session = Depends(obter_sessao)):
    services.remover_participante(db, participante_id)


@router.get(
    "/relatorios/eventos/ocupacao",
    response_model=list[schemas.RelatorioOcupacaoEvento],
    tags=["Relatórios"],
    dependencies=somente_administrador,
)
def relatorio_ocupacao(db: Session = Depends(obter_sessao)):
    return services.relatorio_ocupacao(db)


@router.get(
    "/relatorios/eventos/categorias",
    response_model=list[schemas.RelatorioCategoria],
    tags=["Relatórios"],
    dependencies=somente_administrador,
)
def relatorio_categorias(db: Session = Depends(obter_sessao)):
    return services.relatorio_categorias(db)


@router.get(
    "/relatorios/participantes/cursos",
    response_model=list[schemas.RelatorioCurso],
    tags=["Relatórios"],
    dependencies=somente_administrador,
)
def relatorio_cursos(db: Session = Depends(obter_sessao)):
    return services.relatorio_cursos(db)
