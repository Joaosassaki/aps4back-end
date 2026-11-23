from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import EventoDB, ParticipanteDB, InscricaoDB
from schemas import EventoEntrada, ParticipanteEntrada


def cadastrar_evento(db: Session, dados: EventoEntrada) -> EventoDB:
    evento = EventoDB(**dados.model_dump())
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


def listar_eventos(db: Session) -> list[EventoDB]:
    return db.query(EventoDB).order_by(EventoDB.id).all()


def buscar_evento(db: Session, evento_id: int) -> EventoDB:
    evento = db.get(EventoDB, evento_id)
    if evento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    return evento


def atualizar_evento(db: Session, evento_id: int, dados: EventoEntrada) -> EventoDB:
    evento = buscar_evento(db, evento_id)
    for campo, valor in dados.model_dump().items():
        setattr(evento, campo, valor)
    db.commit()
    db.refresh(evento)
    return evento


def remover_evento(db: Session, evento_id: int) -> None:
    evento = buscar_evento(db, evento_id)
    db.delete(evento)
    db.commit()


def cadastrar_participante(db: Session, dados: ParticipanteEntrada) -> ParticipanteDB:
    participante = ParticipanteDB(**dados.model_dump())
    db.add(participante)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um participante cadastrado com este e-mail.")
    db.refresh(participante)
    return participante


def listar_participantes(db: Session) -> list[ParticipanteDB]:
    return db.query(ParticipanteDB).order_by(ParticipanteDB.id).all()


def buscar_participante(db: Session, participante_id: int) -> ParticipanteDB:
    participante = db.get(ParticipanteDB, participante_id)
    if participante is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participante não encontrado.")
    return participante


def atualizar_participante(db: Session, participante_id: int, dados: ParticipanteEntrada) -> ParticipanteDB:
    participante = buscar_participante(db, participante_id)
    for campo, valor in dados.model_dump().items():
        setattr(participante, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um participante cadastrado com este e-mail.")
    db.refresh(participante)
    return participante


def remover_participante(db: Session, participante_id: int) -> None:
    participante = buscar_participante(db, participante_id)
    db.delete(participante)
    db.commit()


def inscrever_participante(db: Session, evento_id: int, participante_id: int) -> InscricaoDB:
    evento = buscar_evento(db, evento_id)
    buscar_participante(db, participante_id)

    ja_inscrito = (
        db.query(InscricaoDB)
        .filter(InscricaoDB.evento_id == evento_id, InscricaoDB.participante_id == participante_id)
        .first()
    )
    if ja_inscrito is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Participante já está inscrito neste evento.")

    total_inscritos = db.query(InscricaoDB).filter(InscricaoDB.evento_id == evento_id).count()
    if total_inscritos >= evento.capacidade:
        raise HTTPException(status.HTTP_409_CONFLICT, "Não existem vagas disponíveis para este evento.")

    inscricao = InscricaoDB(evento_id=evento_id, participante_id=participante_id)
    db.add(inscricao)
    db.commit()
    db.refresh(inscricao)
    return inscricao


def listar_inscritos(db: Session, evento_id: int) -> list[ParticipanteDB]:
    buscar_evento(db, evento_id)
    return (
        db.query(ParticipanteDB)
        .join(InscricaoDB, InscricaoDB.participante_id == ParticipanteDB.id)
        .filter(InscricaoDB.evento_id == evento_id)
        .order_by(ParticipanteDB.id)
        .all()
    )


def relatorio_ocupacao(db: Session) -> list[dict]:
    linhas = (
        db.query(
            EventoDB.id,
            EventoDB.titulo,
            EventoDB.capacidade,
            func.count(InscricaoDB.id).label("total_inscritos"),
        )
        .outerjoin(InscricaoDB, InscricaoDB.evento_id == EventoDB.id)
        .group_by(EventoDB.id)
        .order_by(EventoDB.id)
        .all()
    )

    resultado = []
    for evento_id, titulo, capacidade, total_inscritos in linhas:
        percentual = (total_inscritos / capacidade * 100) if capacidade > 0 else 0.0
        resultado.append(
            {
                "evento_id": evento_id,
                "titulo": titulo,
                "capacidade": capacidade,
                "total_inscritos": total_inscritos,
                "vagas_disponiveis": capacidade - total_inscritos,
                "percentual_ocupacao": round(percentual, 2),
            }
        )
    return resultado


def relatorio_categorias(db: Session) -> list[dict]:
    inscritos_por_evento = (
        db.query(InscricaoDB.evento_id.label("evento_id"), func.count(InscricaoDB.id).label("total"))
        .group_by(InscricaoDB.evento_id)
        .subquery()
    )
    linhas = (
        db.query(
            EventoDB.categoria,
            func.count(EventoDB.id).label("total_eventos"),
            func.sum(EventoDB.capacidade).label("capacidade_total"),
            func.coalesce(func.sum(inscritos_por_evento.c.total), 0).label("total_inscricoes"),
        )
        .outerjoin(inscritos_por_evento, inscritos_por_evento.c.evento_id == EventoDB.id)
        .group_by(EventoDB.categoria)
        .order_by(EventoDB.categoria)
        .all()
    )

    return [
        {
            "categoria": categoria,
            "total_eventos": total_eventos,
            "capacidade_total": int(capacidade_total or 0),
            "total_inscricoes": total_inscricoes,
        }
        for categoria, total_eventos, capacidade_total, total_inscricoes in linhas
    ]


def relatorio_cursos(db: Session) -> list[dict]:
    linhas = (
        db.query(
            ParticipanteDB.curso,
            func.count(func.distinct(ParticipanteDB.id)).label("total_participantes"),
            func.count(InscricaoDB.id).label("total_inscricoes"),
        )
        .outerjoin(InscricaoDB, InscricaoDB.participante_id == ParticipanteDB.id)
        .group_by(ParticipanteDB.curso)
        .order_by(ParticipanteDB.curso)
        .all()
    )

    return [
        {
            "curso": curso,
            "total_participantes": total_participantes,
            "total_inscricoes": total_inscricoes,
        }
        for curso, total_participantes, total_inscricoes in linhas
    ]
