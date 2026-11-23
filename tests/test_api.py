import os
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SECRET_KEY"] = "chave-de-teste-com-mais-de-trinta-e-dois-caracteres"
os.environ.pop("ADMIN_EMAIL", None)
os.environ.pop("ADMIN_SENHA", None)

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import auth_service
import security
from database import Base, obter_sessao
from main import app
from models import UsuarioDB, PERFIL_ADMINISTRADOR
from schemas import UsuarioEntrada

SENHA = "senha_segura_123"
MSG_TOKEN = "Não foi possível validar as credenciais."
MSG_PERMISSAO = "Você não possui permissão para executar esta operação."

EVENTO = {
    "titulo": "Semana de Tecnologia",
    "descricao": "Evento sobre inovação",
    "data": "2026-11-10",
    "horario": "19:00:00",
    "local": "Auditório 1",
    "capacidade": 2,
    "categoria": "Palestra",
}


@pytest.fixture
def amb(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'teste.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Sessao = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def sessao_de_teste():
        sessao = Sessao()
        try:
            yield sessao
        finally:
            sessao.close()

    app.dependency_overrides[obter_sessao] = sessao_de_teste
    yield SimpleNamespace(c=TestClient(app), Sessao=Sessao)
    app.dependency_overrides.clear()
    engine.dispose()


def criar_admin(amb, email="admin@exemplo.com"):
    with amb.Sessao() as db:
        auth_service.cadastrar_usuario(
            db, UsuarioEntrada(nome="Admin", email=email, senha=SENHA), perfil=PERFIL_ADMINISTRADOR
        )


def registrar(amb, email="aluno@exemplo.com", nome="Aluno Exemplo"):
    resposta = amb.c.post("/usuarios", json={"nome": nome, "email": email, "senha": SENHA})
    assert resposta.status_code == 201
    return resposta.json()


def cabecalho(amb, email, senha=SENHA):
    resposta = amb.c.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


@pytest.fixture
def admin(amb):
    criar_admin(amb)
    return cabecalho(amb, "admin@exemplo.com")


@pytest.fixture
def comum(amb):
    registrar(amb)
    return cabecalho(amb, "aluno@exemplo.com")


def test_cadastro_de_usuario(amb):
    resposta = amb.c.post("/usuarios", json={"nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "senha": SENHA})
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo == {"id": 1, "nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "perfil": "usuario"}
    assert "senha" not in corpo and "senha_hash" not in corpo
    assert SENHA not in resposta.text


def test_senha_e_armazenada_como_hash(amb):
    registrar(amb)
    with amb.Sessao() as db:
        usuario = db.query(UsuarioDB).one()
        assert usuario.senha_hash != SENHA
        assert SENHA not in usuario.senha_hash
        assert usuario.senha_hash.startswith("$argon2")
        assert security.verificar_senha(SENHA, usuario.senha_hash)
        assert not security.verificar_senha("outra_senha", usuario.senha_hash)


def test_mesma_senha_gera_hashes_diferentes(amb):
    registrar(amb, "a@exemplo.com")
    registrar(amb, "b@exemplo.com")
    with amb.Sessao() as db:
        hashes = [u.senha_hash for u in db.query(UsuarioDB).all()]
    assert hashes[0] != hashes[1]


def test_email_duplicado(amb):
    registrar(amb)
    for email in ("aluno@exemplo.com", "ALUNO@Exemplo.com"):
        resposta = amb.c.post("/usuarios", json={"nome": "Outro", "email": email, "senha": SENHA})
        assert resposta.status_code == 409
        assert resposta.json()["detail"] == "Já existe um usuário cadastrado com este e-mail."


@pytest.mark.parametrize("corpo", [
    {"nome": "", "email": "a@exemplo.com", "senha": SENHA},
    {"nome": "   ", "email": "a@exemplo.com", "senha": SENHA},
    {"email": "a@exemplo.com", "senha": SENHA},
    {"nome": "Ana", "email": "", "senha": SENHA},
    {"nome": "Ana", "senha": SENHA},
    {"nome": "Ana", "email": "sem-arroba", "senha": SENHA},
    {"nome": "Ana", "email": "a@exemplo.com", "senha": ""},
    {"nome": "Ana", "email": "a@exemplo.com", "senha": "curta"},
    {"nome": "Ana", "email": "a@exemplo.com"},
])
def test_validacoes_do_cadastro(amb, corpo):
    assert amb.c.post("/usuarios", json=corpo).status_code == 422


def test_nao_e_possivel_se_declarar_administrador(amb):
    resposta = amb.c.post(
        "/usuarios",
        json={"nome": "Espertinho", "email": "e@exemplo.com", "senha": SENHA, "perfil": "administrador"},
    )
    assert resposta.status_code == 422
    with amb.Sessao() as db:
        assert db.query(UsuarioDB).count() == 0


def test_todo_cadastro_publico_vira_usuario_comum(amb):
    assert registrar(amb)["perfil"] == "usuario"


def test_login_valido(amb):
    usuario = registrar(amb)
    resposta = amb.c.post("/auth/login", json={"email": "aluno@exemplo.com", "senha": SENHA})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "bearer"
    dados = jwt.decode(corpo["access_token"], os.environ["SECRET_KEY"], algorithms=["HS256"])
    assert dados["sub"] == str(usuario["id"])
    assert dados["exp"] > dados["iat"]


def test_login_aceita_email_com_caixa_diferente(amb):
    registrar(amb)
    assert amb.c.post("/auth/login", json={"email": "ALUNO@exemplo.com", "senha": SENHA}).status_code == 200


def test_login_invalido_nao_revela_o_motivo(amb):
    registrar(amb)
    senha_errada = amb.c.post("/auth/login", json={"email": "aluno@exemplo.com", "senha": "errada"})
    email_inexistente = amb.c.post("/auth/login", json={"email": "naoexiste@exemplo.com", "senha": SENHA})
    assert senha_errada.status_code == email_inexistente.status_code == 401
    assert senha_errada.json() == email_inexistente.json() == {"detail": "E-mail ou senha inválidos."}


def test_rota_protegida_sem_token(amb):
    resposta = amb.c.get("/eventos")
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == MSG_TOKEN
    assert amb.c.get("/eventos", headers={"Authorization": "Basic abc123"}).status_code == 401


def test_token_invalido(amb):
    registrar(amb)
    valido = security.criar_token(1)
    assinatura_trocada = valido[:-3] + ("AAA" if not valido.endswith("AAA") else "BBB")
    outra_chave = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "uma-outra-chave-secreta-com-mais-de-trinta-e-dois-bytes",
        algorithm="HS256",
    )
    sem_assinatura = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, key="", algorithm="none"
    )
    sem_exp = jwt.encode({"sub": "1"}, os.environ["SECRET_KEY"], algorithm="HS256")
    sem_sub = jwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, os.environ["SECRET_KEY"], algorithm="HS256"
    )
    for token in ("abc.def.ghi", "lixo", assinatura_trocada, outra_chave, sem_assinatura, sem_exp, sem_sub):
        resposta = amb.c.get("/eventos", headers={"Authorization": f"Bearer {token}"})
        assert resposta.status_code == 401, token
        assert resposta.json()["detail"] == MSG_TOKEN


def test_token_expirado(amb):
    usuario = registrar(amb)
    expirado = security.criar_token(usuario["id"], validade=timedelta(seconds=-10))
    resposta = amb.c.get("/eventos", headers={"Authorization": f"Bearer {expirado}"})
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == MSG_TOKEN


def test_token_valido_acessa_rota_protegida(amb, comum):
    resposta = amb.c.get("/eventos", headers=comum)
    assert resposta.status_code == 200 and resposta.json() == []


def test_token_de_usuario_removido_e_recusado(amb, comum):
    with amb.Sessao() as db:
        db.query(UsuarioDB).delete()
        db.commit()
    assert amb.c.get("/eventos", headers=comum).status_code == 401


def test_prazo_de_validade_configuravel(monkeypatch):
    padrao = jwt.decode(security.criar_token(1), os.environ["SECRET_KEY"], algorithms=["HS256"])
    assert padrao["exp"] - padrao["iat"] == 30 * 60
    monkeypatch.setenv("TOKEN_EXPIRA_MINUTOS", "5")
    curto = jwt.decode(security.criar_token(1), os.environ["SECRET_KEY"], algorithms=["HS256"])
    assert curto["exp"] - curto["iat"] == 5 * 60


def test_sem_chave_secreta_a_aplicacao_nao_funciona(monkeypatch):
    monkeypatch.delenv("SECRET_KEY")
    with pytest.raises(RuntimeError):
        security.obter_chave_secreta()


def test_usuario_comum_nao_executa_operacoes_de_administrador(amb, comum, admin):
    evento = amb.c.post("/eventos", json=EVENTO, headers=admin).json()
    participante = amb.c.post(
        "/participantes", json={"nome": "Ana", "email": "ana@exemplo.com", "curso": "ADS"}, headers=comum
    ).json()
    proibidas = [
        ("post", "/eventos", EVENTO),
        ("put", f"/eventos/{evento['id']}", EVENTO),
        ("delete", f"/eventos/{evento['id']}", None),
        ("put", f"/participantes/{participante['id']}", {"nome": "Ana", "email": "ana@exemplo.com", "curso": "ADS"}),
        ("delete", f"/participantes/{participante['id']}", None),
        ("get", "/relatorios/eventos/ocupacao", None),
        ("get", "/relatorios/eventos/categorias", None),
        ("get", "/relatorios/participantes/cursos", None),
    ]
    for metodo, rota, corpo in proibidas:
        resposta = getattr(amb.c, metodo)(rota, headers=comum, **({"json": corpo} if corpo else {}))
        assert resposta.status_code == 403, (metodo, rota)
        assert resposta.json()["detail"] == MSG_PERMISSAO
    assert amb.c.get(f"/eventos/{evento['id']}", headers=comum).status_code == 200


def test_cliente_nao_consegue_forcar_perfil_por_cabecalho_ou_corpo(amb, comum):
    cabecalhos = {**comum, "X-Perfil": "administrador", "perfil": "administrador"}
    assert amb.c.post("/eventos", json={**EVENTO, "perfil": "administrador"}, headers=cabecalhos).status_code == 403


def test_administrador_executa_operacoes_administrativas(amb, admin):
    criado = amb.c.post("/eventos", json=EVENTO, headers=admin)
    assert criado.status_code == 201
    evento_id = criado.json()["id"]
    assert amb.c.put(f"/eventos/{evento_id}", json={**EVENTO, "local": "Sala 2"}, headers=admin).json()["local"] == "Sala 2"
    assert amb.c.get("/relatorios/eventos/ocupacao", headers=admin).status_code == 200
    assert amb.c.delete(f"/eventos/{evento_id}", headers=admin).status_code == 204


def test_auth_me(amb, comum, admin):
    eu = amb.c.get("/auth/me", headers=comum)
    assert eu.status_code == 200
    assert eu.json() == {"id": 1, "nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "perfil": "usuario"}
    assert "senha_hash" not in eu.text and "argon2" not in eu.text
    assert amb.c.get("/auth/me", headers=admin).json()["perfil"] == "administrador"
    assert amb.c.get("/auth/me").status_code == 401
    assert amb.c.get("/auth/me?id=2", headers=comum).json()["id"] == 1


def test_nenhuma_resposta_expoe_senha_ou_hash(amb, comum, admin):
    respostas = [
        amb.c.get("/auth/me", headers=admin),
        amb.c.get("/eventos", headers=admin),
        amb.c.post("/usuarios", json={"nome": "Z", "email": "z@exemplo.com", "senha": SENHA}),
        amb.c.post("/auth/login", json={"email": "z@exemplo.com", "senha": SENHA}),
    ]
    for resposta in respostas:
        assert "argon2" not in resposta.text and "senha_hash" not in resposta.text and SENHA not in resposta.text


def test_rotas_publicas(amb):
    assert amb.c.get("/").status_code == 200
    assert amb.c.get("/docs").status_code == 200
    assert amb.c.post("/usuarios", json={"nome": "A", "email": "a@exemplo.com", "senha": SENHA}).status_code == 201
    assert amb.c.post("/auth/login", json={"email": "a@exemplo.com", "senha": SENHA}).status_code == 200


def test_funcionalidades_da_aps3_continuam_funcionando(amb, comum, admin):
    c = amb.c
    e1 = c.post("/eventos", json={**EVENTO, "titulo": "IA", "capacidade": 1, "categoria": "Palestra"}, headers=admin).json()
    e2 = c.post("/eventos", json={**EVENTO, "titulo": "Python", "capacidade": 5, "categoria": "Workshop"}, headers=admin).json()
    ana = c.post("/participantes", json={"nome": "Ana", "email": "ana@exemplo.com", "curso": "ADS"}, headers=comum).json()
    bia = c.post("/participantes", json={"nome": "Bia", "email": "bia@exemplo.com", "curso": "ADS"}, headers=comum).json()

    repetido = c.post("/participantes", json={"nome": "X", "email": "ana@exemplo.com", "curso": "ADS"}, headers=comum)
    assert repetido.status_code == 409
    assert repetido.json()["detail"] == "Já existe um participante cadastrado com este e-mail."

    assert c.post(f"/eventos/{e1['id']}/inscricoes/{ana['id']}", headers=comum).status_code == 201
    assert c.post(f"/eventos/{e1['id']}/inscricoes/{ana['id']}", headers=comum).status_code == 409
    assert c.post(f"/eventos/{e1['id']}/inscricoes/{bia['id']}", headers=comum).status_code == 409
    assert c.post(f"/eventos/999/inscricoes/{ana['id']}", headers=comum).status_code == 404
    assert c.post(f"/eventos/{e2['id']}/inscricoes/{ana['id']}", headers=comum).status_code == 201
    assert c.post(f"/eventos/{e2['id']}/inscricoes/{bia['id']}", headers=comum).status_code == 201
    assert [p["nome"] for p in c.get(f"/eventos/{e2['id']}/inscricoes", headers=comum).json()] == ["Ana", "Bia"]
    assert c.post(f"/eventos/{e1['id']}/inscricoes/{ana['id']}").status_code == 401

    ocupacao = {r["titulo"]: r for r in c.get("/relatorios/eventos/ocupacao", headers=admin).json()}
    assert ocupacao["IA"]["percentual_ocupacao"] == 100.0 and ocupacao["IA"]["vagas_disponiveis"] == 0
    assert ocupacao["Python"]["total_inscritos"] == 2 and ocupacao["Python"]["vagas_disponiveis"] == 3
    categorias = {r["categoria"]: r for r in c.get("/relatorios/eventos/categorias", headers=admin).json()}
    assert categorias["Workshop"] == {"categoria": "Workshop", "total_eventos": 1, "capacidade_total": 5, "total_inscricoes": 2}
    cursos = c.get("/relatorios/participantes/cursos", headers=admin).json()
    assert cursos == [{"curso": "ADS", "total_participantes": 2, "total_inscricoes": 3}]

    c.delete(f"/participantes/{ana['id']}", headers=admin)
    cursos = c.get("/relatorios/participantes/cursos", headers=admin).json()
    assert cursos == [{"curso": "ADS", "total_participantes": 1, "total_inscricoes": 1}]


def test_administrador_inicial_vem_de_variaveis_de_ambiente(amb, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "chefe@exemplo.com")
    monkeypatch.setenv("ADMIN_SENHA", "senha_do_chefe_123")
    monkeypatch.setenv("ADMIN_NOME", "Chefe")
    with amb.Sessao() as db:
        auth_service.criar_administrador_inicial(db)
        auth_service.criar_administrador_inicial(db)
        assert db.query(UsuarioDB).count() == 1
        assert db.query(UsuarioDB).one().perfil == "administrador"
    token = amb.c.post("/auth/login", json={"email": "chefe@exemplo.com", "senha": "senha_do_chefe_123"}).json()
    resposta = amb.c.post("/eventos", json=EVENTO, headers={"Authorization": f"Bearer {token['access_token']}"})
    assert resposta.status_code == 201


def test_sem_variaveis_de_admin_nenhum_administrador_e_criado(amb, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_SENHA", raising=False)
    with amb.Sessao() as db:
        auth_service.criar_administrador_inicial(db)
        assert db.query(UsuarioDB).count() == 0


def test_dados_e_usuarios_persistem_apos_reiniciar(tmp_path):
    caminho = tmp_path / "persistente.db"

    def abrir():
        engine = create_engine(f"sqlite:///{caminho}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        Sessao = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def sessao_de_teste():
            with Sessao() as sessao:
                yield sessao

        app.dependency_overrides[obter_sessao] = sessao_de_teste
        return TestClient(app), engine

    c1, e1 = abrir()
    c1.post("/usuarios", json={"nome": "Aluno", "email": "aluno@exemplo.com", "senha": SENHA})
    token = c1.post("/auth/login", json={"email": "aluno@exemplo.com", "senha": SENHA}).json()["access_token"]
    e1.dispose()

    c2, e2 = abrir()
    assert c2.post("/auth/login", json={"email": "aluno@exemplo.com", "senha": SENHA}).status_code == 200
    assert c2.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    app.dependency_overrides.clear()
    e2.dispose()
