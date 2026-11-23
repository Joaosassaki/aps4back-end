# API de Eventos Acadêmicos — APS 4

API RESTful em FastAPI para gerenciar eventos acadêmicos, participantes e inscrições, com persistência em SQLite (SQLAlchemy) e relatórios consolidados.

Nesta versão foram adicionados **cadastro de usuários, senhas com hash, login com token JWT, proteção de rotas e controle de acesso por perfil** (administrador e usuário).

## Tecnologias

Python, FastAPI, SQLite, SQLAlchemy ORM, Pydantic, Uvicorn, PyJWT (tokens), pwdlib com Argon2 (hash de senhas) e python-dotenv (leitura do `.env`).

## Instalação e execução

1. Crie e ative o ambiente virtual e instale as dependências:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

No Linux ou macOS, ative com `source venv/bin/activate`.

2. Configure a chave secreta (próxima seção).

3. Suba a API:

```
uvicorn main:app --reload
```

A API fica em `http://127.0.0.1:8000` e o Swagger em `http://127.0.0.1:8000/docs`.

## Configuração da chave secreta

A chave que assina os tokens **não está no código**. Ela é lida da variável de ambiente `SECRET_KEY`, que pode ficar em um arquivo `.env` na pasta do projeto. O `.env` está no `.gitignore` e não vai para o repositório. Se a variável não existir, a API se recusa a iniciar.

1. Copie o arquivo de exemplo:

```
copy .env.example .env
```

No Linux ou macOS: `cp .env.example .env`.

2. Gere uma chave aleatória e cole no `.env`, no lugar do valor de `SECRET_KEY`:

```
python -c "import secrets; print(secrets.token_hex(32))"
```

3. Variáveis aceitas no `.env`:

| Variável | Para que serve |
|---|---|
| `SECRET_KEY` | Chave que assina e valida os tokens (obrigatória) |
| `TOKEN_EXPIRA_MINUTOS` | Validade do token em minutos (padrão: 30) |
| `ADMIN_EMAIL`, `ADMIN_SENHA`, `ADMIN_NOME` | Criam o administrador inicial (opcionais) |

O `.env.example` só tem valores de exemplo. Troque a chave e a senha do administrador antes de usar.

## Criação do administrador inicial

Ninguém se torna administrador pelo cadastro público: `POST /usuarios` sempre cria um usuário com perfil `usuario`, e enviar o campo `perfil` no corpo é recusado com `422`.

O primeiro administrador é criado de forma controlada: ao iniciar, a API lê `ADMIN_EMAIL` e `ADMIN_SENHA` do `.env` e, se esse e-mail ainda não existir, cria o administrador. Se as variáveis não estiverem definidas, nenhum administrador é criado.

## Estrutura do projeto

```
api-eventos-aps4/
├── main.py            cria a aplicação, valida a chave secreta e cria o administrador inicial
├── database.py        conexão com o SQLite, sessões e criação das tabelas
├── models.py          tabelas e relacionamentos (SQLAlchemy), incluindo usuários
├── schemas.py         validação de entrada e formato das respostas (Pydantic)
├── security.py        hash de senha, geração e validação do JWT, identificação do usuário e perfil exigido
├── auth_service.py    cadastro de usuários, verificação de credenciais e administrador inicial
├── services.py        regras de negócio de eventos, participantes, inscrições e relatórios
├── routers.py         rotas HTTP (Controller)
├── requirements.txt
├── .env.example
└── tests/test_api.py
```

A validação do token e a checagem de perfil ficam em `security.py` e entram nas rotas por dependências do FastAPI (`Depends`), sem repetir a lógica em cada rota.

## Como funciona a segurança

- **Hash de senha:** a senha é transformada em hash com **Argon2** (biblioteca `pwdlib`) antes de ser salva. Só o campo `senha_hash` vai para o banco. A senha original e o hash nunca aparecem nas respostas.
- **Login:** `POST /auth/login` confere a senha com o hash. Se o e-mail não existir ou a senha estiver errada, a resposta é a mesma: `401` com "E-mail ou senha inválidos."
- **Token JWT:** assinado com HS256 e a chave secreta. Leva o id do usuário (`sub`), a data de emissão (`iat`) e a expiração (`exp`, 30 minutos por padrão). Tokens inválidos, adulterados, de outra chave ou expirados são recusados com `401`.
- **Autorização:** o perfil é lido do banco a cada requisição, a partir do usuário identificado pelo token. A API não confia em nada que o cliente envie sobre o próprio perfil. Sem permissão, a resposta é `403`.

## Perfis e permissões

| Rota | Acesso |
|---|---|
| `GET /`, `POST /usuarios`, `POST /auth/login`, `/docs` | Pública |
| `GET /auth/me` | Qualquer usuário autenticado |
| `GET /eventos`, `GET /eventos/{id}` | Qualquer usuário autenticado |
| `POST /eventos`, `PUT /eventos/{id}`, `DELETE /eventos/{id}` | Somente administrador |
| `POST /participantes`, `GET /participantes`, `GET /participantes/{id}` | Qualquer usuário autenticado |
| `PUT /participantes/{id}`, `DELETE /participantes/{id}` | Somente administrador |
| `POST /eventos/{evento_id}/inscricoes/{participante_id}` | Qualquer usuário autenticado |
| `GET /eventos/{evento_id}/inscricoes` | Qualquer usuário autenticado |
| `GET /relatorios/...` (os três relatórios) | Somente administrador |

Regras adicionais escolhidas pela equipe: o usuário comum pode cadastrar um participante (para poder se inscrever), mas só o administrador altera ou exclui participantes e consulta os relatórios.

## Principais rotas

**Autenticação**

| Método | Rota | Descrição |
|---|---|---|
| POST | /usuarios | Cadastra usuário (sempre com perfil `usuario`) |
| POST | /auth/login | Autentica e devolve o token JWT |
| GET | /auth/me | Dados do usuário autenticado |

**Eventos, participantes, inscrições e relatórios** seguem as rotas da APS 3 (`/eventos`, `/participantes`, `/eventos/{id}/inscricoes/{participante_id}`, `/relatorios/eventos/ocupacao`, `/relatorios/eventos/categorias`, `/relatorios/participantes/cursos`), agora com as proteções da tabela acima.

## Cadastrar usuário e obter token

Cadastro (`POST /usuarios`):

```json
{ "nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "senha": "senha_segura" }
```

Resposta (`201`), sem senha nem hash:

```json
{ "id": 1, "nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "perfil": "usuario" }
```

A senha precisa ter de 8 a 128 caracteres.

Login (`POST /auth/login`):

```json
{ "email": "aluno@exemplo.com", "senha": "senha_segura" }
```

Resposta (`200`):

```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

Para usar o token em uma rota protegida, envie o cabeçalho:

```
Authorization: Bearer eyJhbGciOi...
```

No Swagger, clique em **Authorize**, cole só o token (sem a palavra `Bearer`) e confirme. Depois disso, as rotas protegidas passam a enviar o token sozinhas.

## Erros

| Situação | Código | Mensagem |
|---|---|---|
| Credenciais inválidas no login | 401 | E-mail ou senha inválidos. |
| Token ausente, inválido ou expirado | 401 | Não foi possível validar as credenciais. |
| Usuário sem permissão | 403 | Você não possui permissão para executar esta operação. |
| E-mail de usuário já cadastrado | 409 | Já existe um usuário cadastrado com este e-mail. |
| Dados inválidos (e-mail, senha curta, campo `perfil`) | 422 | Detalhes do campo inválido |
| Evento ou participante inexistente | 404 | Evento não encontrado. / Participante não encontrado. |
| Inscrição duplicada, sem vagas ou e-mail de participante repetido | 409 | Mensagens da APS 3 |

## Como reproduzir os testes

Pelo Swagger (`/docs`), com a API rodando e o administrador inicial configurado no `.env`:

1. **Cadastro:** `POST /usuarios` com um usuário novo (resposta `201`, sem senha nem hash).
2. **Senha em hash:** com a API parada ou rodando, execute na pasta do projeto:
   `python -c "import sqlite3; print(sqlite3.connect('eventos.db').execute('select email, senha_hash, perfil from usuarios').fetchall())"`
   A coluna `senha_hash` mostra um valor começando com `$argon2id`, não a senha.
3. **E-mail duplicado:** repita o `POST /usuarios` com o mesmo e-mail (`409`).
4. **Login válido:** `POST /auth/login` com o e-mail e a senha (`200` e o token).
5. **Login inválido:** `POST /auth/login` com senha errada e depois com e-mail inexistente (`401`, mesma mensagem).
6. **Sem token:** chame `GET /eventos` sem clicar em Authorize (`401`).
7. **Token válido:** clique em Authorize, cole o token e chame `GET /eventos` (`200`).
8. **Token inválido ou expirado:** em Authorize, troque o token por um texto qualquer e chame `GET /eventos` (`401`). Para o expirado, defina `TOKEN_EXPIRA_MINUTOS=1` no `.env`, reinicie, faça login e espere 1 minuto.
9. **Usuário comum em rota de administrador:** com o token de um usuário comum, chame `POST /eventos` ou `GET /relatorios/eventos/ocupacao` (`403`).
10. **Administrador:** faça login com o administrador inicial, use o token e chame `POST /eventos` (`201`).
11. **Dados do usuário:** com qualquer token, chame `GET /auth/me`.
12. **APS 3 funcionando:** com o token do administrador, consulte os relatórios, e com um usuário comum faça uma inscrição, tentando repeti-la (`409`) e inscrever em evento inexistente (`404`).

Testes automatizados (usam banco temporário, não alteram o `eventos.db`):

```
pip install pytest httpx
python -m pytest tests -q
```

## Repositório

Link do repositório no GitHub: _adicionar aqui_
