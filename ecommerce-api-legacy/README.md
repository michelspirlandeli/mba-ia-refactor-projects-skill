# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`. Foi **refatorada para MVC** pela skill. Relatórios: [`../reports/audit-project-2.md`](../reports/audit-project-2.md) (auditoria original) e [`../reports/reaudit-project-2.md`](../reports/reaudit-project-2.md) (re-auditoria do código refatorado, cujos findings foram corrigidos).

## Como rodar

```bash
npm install
npm start          # node src/server.js
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória por padrão (`DB_PATH`).

Fora de produção (`NODE_ENV` diferente de `production`), o boot cria cursos e o usuário de demonstração `leonan@fullcycle.com.br`. A senha dele vem de `SEED_USER_PASSWORD`. Se a variável estiver vazia, a senha é gerada e exibida uma vez no log.

Exemplos de requisições estão em `api.http`. Variáveis de ambiente em [`.env.example`](.env.example).

## Estrutura

```
src/
├── server.js                 # entry point (listen + encerramento limpo em SIGTERM/SIGINT)
├── app.js                    # composition root: cria db, models, services, controllers e rotas
├── config/index.js           # env vars + constantes de domínio
├── database/connection.js    # wrapper Promise do sqlite3, schema, índices únicos, seed de dev, transaction()
├── models/                   # user, course, enrollment, payment, auditLog
├── services/                 # payment, password (scrypt), logger
├── controllers/              # checkout, report, user
├── routes/                   # checkoutRoutes, adminRoutes (views HTTP)
├── middlewares/              # errorHandler (central), requireAdmin
└── errors/AppError.js        # erros de domínio
```

## Mudanças de contrato (por segurança/integridade)

- `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem `ADMIN_TOKEN` configurado e o header `X-Admin-Token`. Sem eles, respondem 403 (fail-closed).
- Checkout de usuário **existente** exige o `pwd` correto. Sem ele ou com senha errada, responde 401. Antes, bastava saber o email para matricular e cobrar em nome de outra pessoa.
- Checkout de **novo** usuário sem `pwd` retorna 400 (antes criava a conta com a senha fixa `123456`). A senha precisa ter no mínimo 6 caracteres.
- Matrícula repetida no mesmo curso retorna 409 e não gera nova cobrança. Isso vale também para checkouts concorrentes do mesmo email, garantido pelos índices `UNIQUE`.
- Validação, verificação de senha e hash acontecem **antes** de autorizar o pagamento.
- Checkout recusado não cria mais o usuário.
- Tipos inválidos (`usr` objeto, `eml` lista, `pwd` numérico) retornam 400 em vez de gravar `[object Object]` ou responder 500.
- Erros 4xx do parser de JSON (413 payload grande, 415 charset inválido) são devolvidos com o status correto em vez de 500.
- `DELETE /api/users/:id` remove também matrículas e pagamentos (transação) e retorna 404 para usuário inexistente.
