# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. O projeto já possuía alguma separação de camadas (`models/`, `routes/`, `services/`, `utils/`); a skill **preservou essa organização e completou o MVC** (relatório em [`../reports/audit-project-3.md`](../reports/audit-project-3.md)).

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # opcional (carregado via python-dotenv)
python seed.py
python app.py
```

A aplicação sobe em `http://localhost:5000`. O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**.

## Estrutura

```
app.py                  # create_app(): composition root + entry point
config.py               # Config via env vars + constantes de domínio
database.py             # instância do SQLAlchemy
models/                 # Task, User, Category (sem senha no to_dict, hash scrypt, is_overdue)
controllers/            # NOVO — task, user, report, category (regra de negócio)
routes/                 # views HTTP finas (Blueprints) — categorias em category_routes.py
services/               # NotificationService com config injetada
middlewares/            # NOVO — error_handler (JSON central), auth (token assinado)
utils/                  # helpers puros + validators centralizados
```

## Mudanças de contrato (por segurança)

- `password` não é mais retornado em nenhuma resposta.
- `token` do `/login` agora é assinado (itsdangerous) em vez de `fake-jwt-token-<id>`.
- Com `AUTH_REQUIRED=true`, todas as rotas exceto `/`, `/health`, `/login` e `POST /users` exigem `Authorization: Bearer <token>`, e só admins podem atribuir roles `admin`/`manager`. Padrão: `false` (contrato original).
- Erros de validação de tipo (ex.: `priority: "alta"`) retornam 400 em vez de 500; 404/405/500 retornam JSON `{"error": ...}`.
- Deletar categoria desvincula as tasks (`category_id = null`).
