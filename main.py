from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

import auth_service
from database import SessionLocal, criar_tabelas
from routers import router
from security import obter_chave_secreta


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    obter_chave_secreta()
    criar_tabelas()
    with SessionLocal() as db:
        auth_service.criar_administrador_inicial(db)
    yield


app = FastAPI(title="API de Eventos Acadêmicos", version="4.0.0", lifespan=ciclo_de_vida)


@app.exception_handler(SQLAlchemyError)
async def tratar_erro_de_banco(request: Request, erro: SQLAlchemyError):
    return JSONResponse(status_code=500, content={"detail": "Erro ao processar a operação no banco de dados."})


app.include_router(router)


@app.get("/")
def raiz():
    return {"mensagem": "API de Eventos Acadêmicos no ar. Acesse /docs para o Swagger."}
