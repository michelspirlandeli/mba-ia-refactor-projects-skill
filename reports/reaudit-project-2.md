================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js v20.20.1 local) + Express ^4.18.2 (SQLite via sqlite3 ^5.1.6, in-memory)
Files:   21 analyzed | ~563 lines of code
Date:    2026-11-25

> Contexto: esta é uma **re-auditoria** do código já reestruturado em MVC (commit `bb88f34`).
> Os findings abaixo são problemas remanescentes; vários foram confirmados executando a aplicação.

## Summary
CRITICAL: 0 | HIGH: 3 | MEDIUM: 3 | LOW: 2

## Findings

### #1 [HIGH] Endpoint administrativo sem autenticação por padrão (AP-03)
File: src/middlewares/requireAdmin.js:12-16
File: src/config/index.js:6
File: src/routes/adminRoutes.js:7, 11
Description: `requireAdmin` é *fail-open*: com `ADMIN_TOKEN` vazio (default `''` em config) faz apenas `logger.warn(...)` e `next()`. `GET /api/admin/financial-report` e `DELETE /api/users/:id` ficam públicos. Confirmado: `DELETE /api/users/1` sem header → 200. Severidade rebaixada de CRITICAL porque existe o mecanismo de token, mas ele é opcional.
Impact: Qualquer cliente lê faturamento/nomes de alunos e apaga usuários (com matrículas e pagamentos) se o deploy esquecer a variável.
Recommendation: Fail-closed — negar (403) quando `ADMIN_TOKEN` não estiver configurado, exceto com opt-in explícito de dev (ex.: `ALLOW_INSECURE_ADMIN=true`) (Playbook P-03).

### #2 [HIGH] Autenticação falsa no checkout de usuário existente (AP-09)
File: src/controllers/checkoutController.js:26-39
File: src/services/passwordService.js:15-20
Description: Quando `eml` já existe, o `pwd` enviado é ignorado e a matrícula/pagamento é vinculada à conta (`existingUser ? existingUser.id : ...`). `passwordService.verify` existe mas nunca é chamado. Confirmado: checkout com `eml: leonan@fullcycle.com.br`, `pwd: "errada"` → 200 `enrollment_id: 4`.
Impact: Qualquer pessoa que conheça um e-mail cria matrículas e cobranças em nome de outro usuário.
Recommendation: Para usuário existente exigir `pwd` e validar com `passwordService.verify` contra o hash salvo (model expõe método específico que retorna o hash apenas para verificação); falha → 401 (Playbook P-09).

### #3 [HIGH] Integridade de dados: pagamento antes de validar, duplicidades sem restrição (AP-10)
File: src/controllers/checkoutController.js:26, 33-36, 39-41
File: src/database/connection.js:4, 6
Description: (a) `paymentService.authorize` roda antes de `passwordService.hash`; com `pwd: 123` (número) o log registra `Pagamento PAID` e em seguida ocorre 500 — cobrança sem matrícula. (b) `users.email` não tem `UNIQUE` e a checagem `findByEmail` ocorre fora da transação → requisições concorrentes com o mesmo e-mail novo criam usuários duplicados. (c) Não há verificação nem `UNIQUE(user_id, course_id)` em `enrollments`: o mesmo usuário foi matriculado e cobrado duas vezes no curso 2 (`enrollment_id` 4 e 5).
Impact: Cobrança indevida/dupla e dados inconsistentes (usuários e matrículas duplicados).
Recommendation: Validar e preparar tudo (hash) antes de autorizar o pagamento; adicionar `UNIQUE` em `users.email` e `enrollments(user_id, course_id)`; recusar matrícula repetida com 409 (Playbook P-10).

### #4 [MEDIUM] Validação de tipos de entrada ausente (AP-12)
File: src/controllers/checkoutController.js:12-17
Description: `validate` só checa presença e aplica `String(...)` antes das regex, então tipos errados passam: `usr: {"a":1}` foi gravado como `"[object Object]"` (visível no relatório financeiro); `eml: ["a3@x.com"]` aceito; `pwd: 123` → TypeError do `crypto.scrypt` → 500. Sem tamanho mínimo de senha.
Impact: Dados corrompidos persistidos e erros 500 para input inválido do cliente.
Recommendation: Exigir `typeof === 'string'` para `usr`, `eml`, `pwd`, `card`; limites de tamanho; responder 400 (Playbook P-12).

### #5 [MEDIUM] Error handler não trata erros HTTP do body-parser (AP-13)
File: src/middlewares/errorHandler.js:15-20
Description: Apenas `err.type === 'entity.parse.failed'` vira 400; os demais erros do `express.json()` que carregam `err.status` (415 charset não suportado, 413 payload > 100kb) caem no ramo genérico. Confirmado: `Content-Type: application/json; charset=latin9` → `500 Erro interno` e stack trace completo logado como erro.
Impact: Erros de cliente reportados como falha do servidor; ruído em log/alertas.
Recommendation: Respeitar `err.status`/`err.statusCode` 4xx de erros `expose`d (body-parser/http-errors) e só tratar o restante como 500 (Playbook P-13).

### #6 [MEDIUM] Credencial fixa no seed executado em qualquer ambiente (AP-02)
File: src/database/connection.js:71-81
Description: O seed cria o usuário `leonan@fullcycle.com.br` com senha `'123'` (`passwordService.hash('123')`) sempre que a tabela `courses` está vazia — inclusive com `DB_PATH` apontando para arquivo em produção. Rebaixado de CRITICAL: a senha é armazenada com hash e o default é banco em memória.
Impact: Conta conhecida com senha trivial em ambientes reais.
Recommendation: Seed apenas em dev (flag `SEED_DB`/`NODE_ENV`), senha vinda do ambiente ou gerada aleatoriamente (Playbook P-02).

### #7 [LOW] Código morto / cache sem leitura (AP-20)
File: src/services/cacheService.js:3-11
File: src/controllers/checkoutController.js:46
File: src/services/paymentService.js:8
File: src/database/connection.js:60-62
Description: `cacheService.set('last_checkout_<id>', ...)` é escrito a cada checkout, mas `get` nunca é chamado (Map cresce sem limite e não serve a nada). `PaymentService.gatewayKey` é armazenado e nunca usado; `Database.close()` não é usado (sem graceful shutdown).
Impact: Memória crescente sem benefício; código que sugere funcionalidade inexistente.
Recommendation: Remover o cache (ou dar-lhe um consumidor e limite); usar `close()` em shutdown (SIGTERM/SIGINT) (Playbook P-15).

### #8 [LOW] Magic numbers/strings no seed (AP-17)
File: src/database/connection.js:79-80
Description: IDs fixos `[1, 1]` e `[1, 997.0, 'PAID']` assumem os autoincrementos e duplicam o preço e o status em vez de usar `lastID` e `PAYMENT_STATUS.PAID`.
Impact: Seed quebra silenciosamente se a ordem de inserts mudar.
Recommendation: Usar os `lastID` retornados e as constantes de `config` (Playbook P-15).

## Deprecated APIs
| File:Line | Deprecated | Modern replacement |
|---|---|---|
| — | Nenhuma API deprecated detectada para Node.js 20 / Express 4.18 / sqlite3 5 (callbacks já encapsulados em Promises; sem `var`, `new Buffer`, `body-parser`, `req.param`) | — |

## Architecture Overview (current → target)
- Current: MVC / camadas adequado — config isolada, models com SQL parametrizado, controllers com regra, rotas finas, error handler central e composition root com DI. Restam falhas de segurança/integridade no fluxo de checkout e no middleware admin.
- Target:  MVC — mantém a estrutura; correções pontuais em middlewares/requireAdmin, controllers/checkoutController, middlewares/errorHandler, database/connection (schema + seed) e remoção de código morto.

================================
Total: 8 findings
================================
