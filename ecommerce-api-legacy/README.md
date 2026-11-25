# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch` — **refatorada para MVC** pela skill (relatório em [`../reports/audit-project-2.md`](../reports/audit-project-2.md)).

## Como rodar

```bash
npm install
npm start          # node src/server.js
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória por padrão (`DB_PATH`) e já carrega seeds automaticamente no boot.

Exemplos de requisições estão em `api.http`. Variáveis de ambiente em [`.env.example`](.env.example).

## Estrutura

```
src/
├── server.js                 # entry point (listen)
├── app.js                    # composition root: cria db, models, services, controllers e rotas
├── config/index.js           # env vars + constantes de domínio
├── database/connection.js    # wrapper Promise do sqlite3, schema, seed, transaction()
├── models/                   # user, course, enrollment, payment, auditLog
├── services/                 # payment, password (scrypt), cache, logger
├── controllers/              # checkout, report, user
├── routes/                   # checkoutRoutes, adminRoutes (views HTTP)
├── middlewares/              # errorHandler (central), requireAdmin
└── errors/AppError.js        # erros de domínio
```

## Mudanças de contrato (por segurança/integridade)

- Se `ADMIN_TOKEN` estiver definido, `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem o header `X-Admin-Token`.
- Checkout de **novo** usuário sem `pwd` retorna 400 (antes criava a conta com a senha fixa `123456`).
- Checkout recusado não cria mais o usuário.
- `DELETE /api/users/:id` remove também matrículas e pagamentos (transação) e retorna 404 para usuário inexistente.
