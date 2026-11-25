# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. O projeto já tinha alguma separação de camadas (`models/`, `routes/`, `services/`, `utils/`). A skill **preservou essa organização e completou o MVC**. Relatórios: [`../reports/audit-project-3.md`](../reports/audit-project-3.md) (auditoria original) e [`../reports/reaudit-project-3.md`](../reports/reaudit-project-3.md) (re-auditoria do código refatorado, cujos findings foram corrigidos).

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # opcional (carregado via python-dotenv)
SEED_PASSWORD=minha-senha python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. Rode o `seed.py` **antes do primeiro boot**. Ele popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo:
- Os usuários são joao (admin), maria (user) e pedro (manager).
- A senha de todos vem de `SEED_PASSWORD`. Sem a variável, ela é gerada e exibida ao final.
- O seed apaga os dados existentes e se recusa a rodar com `APP_ENV=production`.

A autenticação vem **ligada por padrão** (`AUTH_REQUIRED=true`):
1. Faça `POST /login` e envie `Authorization: Bearer <token>` nas demais rotas.
2. Para usar o contrato legado sem autenticação (apenas em desenvolvimento), defina `AUTH_REQUIRED=false`.

## Estrutura

```
app.py                  # create_app(): composition root (serviços em app.extensions) + entry point
config.py               # Config via env vars + constantes de domínio
errors.py               # erros de domínio (camada neutra)
database.py             # instância do SQLAlchemy
models/                 # Task, User, Category (back_populates, sem senha no to_dict, hash scrypt, is_overdue)
controllers/            # task, user, report, category (regra de negócio; recebem o Actor e serviços injetados)
routes/                 # views HTTP finas (Blueprints)
services/               # auth_service (tokens + rate limit de login), authorization_service (regras de acesso),
                        # notification_service (SMTP em background, desligado por padrão)
middlewares/            # error_handler (JSON central), auth (identifica o usuário do token)
utils/                  # helpers puros + validators centralizados
```

## Autorização (com `AUTH_REQUIRED=true`)

| Ação | Quem pode |
|---|---|
| Leitura (`GET /tasks`, `/users`, `/categories`...) | qualquer usuário autenticado |
| Criar/editar/deletar task | dono da task, `admin` ou `manager` (usuário comum só atribui tasks a si mesmo) |
| `PUT /users/<id>` | o próprio usuário ou `admin`; alterar `role`/`active` só `admin` |
| `DELETE /users/<id>` | `admin` |
| `GET /reports/summary` | `admin` ou `manager` |
| `GET /reports/user/<id>` | o próprio usuário, `admin` ou `manager` |
| `POST/PUT/DELETE /categories` | `admin` ou `manager` |
| `POST /users` (cadastro público) | qualquer um; criar `admin`/`manager` só um `admin` autenticado |

## Mudanças de contrato (por segurança)

- `password` não é mais retornado em nenhuma resposta.
- O `token` do `/login` agora é assinado (itsdangerous), em vez de `fake-jwt-token-<id>`.
- Autenticação ligada por padrão, com autorização por recurso conforme a tabela acima. Rotas protegidas respondem 401 sem token e 403 quando falta permissão. Com `AUTH_REQUIRED=false`, todas as rotas respondem como no contrato original.
- Login:
  - bloqueado com 429 após 5 falhas seguidas do mesmo IP+email em 15 minutos;
  - `email`/`password` que não são texto retornam 400.
- Senha mínima de 8 caracteres para novos usuários e trocas de senha.
- Tipos inválidos retornam 400 em vez de 500. Exemplos: `priority: "alta"`, `tags`/`description` como objeto, `name` da categoria como lista.
- 404/405/500 retornam JSON `{"error": ...}`.
- Deletar categoria desvincula as tasks (`category_id = null`).
- `GET /tasks/search?q=` trata `%` e `_` como texto literal.
- `GET /tasks` aceita paginação opcional (`?page=1&per_page=20`). Sem `page`, retorna a lista completa, como antes.
- Em produção (`APP_ENV=production`), `SECRET_KEY` é obrigatório.
- Defaults seguros:
  - `HOST` passa a ser `127.0.0.1`.
  - CORS fica desabilitado até `CORS_ORIGINS` ser definido.
