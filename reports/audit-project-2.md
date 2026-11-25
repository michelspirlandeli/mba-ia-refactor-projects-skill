```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js v20.20.1 local)
Framework:     Express ^4.18.2
Dependencies:  express, sqlite3 ^5.1.6
Domain:        LMS com fluxo de checkout (usuários, cursos, matrículas, pagamentos, auditoria)
Architecture:  Monolito "big ball of mud" — classe AppManager concentra banco, schema/seed, rotas,
               pagamento, matrícula, auditoria e relatório; utils.js mistura config com segredos, cache global e "crypto"
Source files:  3 files analyzed (~180 lines)
DB tables:     users, courses, enrollments, payments, audit_logs (SQLite em memória)
Entry point:   src/app.js (npm start, porta 3000)
Endpoints:     3 routes mapped (POST /api/checkout, GET /api/admin/financial-report, DELETE /api/users/:id)
================================
```

================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript + Express 4.18 (SQLite em memória via sqlite3, callbacks)
Files:   3 analyzed | ~180 lines of code
Date:    2026-11-25

## Summary
CRITICAL: 4 | HIGH: 5 | MEDIUM: 5 | LOW: 4

## Findings

### #1 [CRITICAL] Hardcoded Credentials (AP-02)
File: src/utils.js:2-5
Description: Objeto `config` contém `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"` (chave **live** de gateway de pagamento), `dbUser` e `smtpUser` literais.
Impact: Segredos de produção versionados no repositório; qualquer pessoa com acesso ao código pode operar o gateway de pagamento.
Recommendation: `src/config/index.js` lendo `process.env` (sem default para segredos) + `.env.example` (Playbook P-02).

### #2 [CRITICAL] Dados de cartão e segredo em log (AP-05)
File: src/AppManager.js:45
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` grava o número completo do cartão e a chave do gateway no stdout a cada checkout.
Impact: Violação de PCI-DSS; vazamento de PAN e chave live em qualquer agregador de logs.
Recommendation: Nunca logar cartão/segredos; quando necessário, apenas os 4 últimos dígitos mascarados (Playbook P-05, P-16).

### #3 [CRITICAL] God Class (AP-04)
File: src/AppManager.js:4-139
Description: `AppManager` cria a conexão (`new sqlite3.Database`), define o schema, faz seed, registra as 3 rotas, valida entrada, decide aprovação de pagamento, cria usuário, matrícula, pagamento, log de auditoria, cache e monta o relatório financeiro.
Impact: Nenhuma parte é testável isoladamente; qualquer alteração exige mexer na classe inteira.
Recommendation: Decompor em `database/`, `models/` (user, course, enrollment, payment, auditLog), `services/` (payment, password, cache), `controllers/`, `routes/` e composition root em `app.js` (Playbook P-04).

### #4 [CRITICAL] Endpoints administrativos sem autenticação (AP-03)
File: src/AppManager.js:80, 131-137
Description: `GET /api/admin/financial-report` (faturamento e alunos por curso) e `DELETE /api/users/:id` são públicos, sem qualquer verificação de identidade/perfil.
Impact: Exposição de dados financeiros e pessoais; qualquer cliente anônimo pode apagar usuários.
Recommendation: Middleware `requireAdmin` baseado em token administrativo de config (Playbook P-03).

### #5 [HIGH] Hash de senha fraco e senha default (AP-09)
File: src/utils.js:17-23
File: src/AppManager.js:18, 68
Description: `badCrypto` repete os 2 primeiros caracteres do base64 da senha 10.000 vezes e trunca em 10 chars — sem salt, determinístico e trivialmente reversível (senhas com mesmo prefixo colidem). Checkout sem `pwd` cria usuário com senha `"123456"`. Seed grava senha `'123'` em texto puro.
Impact: Senhas de todos os usuários recuperáveis a partir do banco; contas criadas com senha conhecida.
Recommendation: `crypto.scrypt` com salt aleatório; exigir `pwd` ao criar usuário (400 se ausente) (Playbook P-09).

### #6 [HIGH] Regra de negócio no handler HTTP / callback hell (AP-06)
File: src/AppManager.js:28-78
Description: O handler de `/api/checkout` tem 50 linhas e 5 níveis de callbacks aninhados combinando validação, busca de curso, criação de usuário, decisão de pagamento (`cc.startsWith("4")`), matrícula, pagamento, auditoria e cache.
Impact: Fluxo de negócio crítico impossível de testar sem HTTP + banco; tratamento de erro inconsistente em cada nível.
Recommendation: `CheckoutController.checkout()` com async/await, `PaymentService.authorize()` e models injetados (Playbook P-06).

### #7 [HIGH] Estado global mutável (AP-08)
File: src/utils.js:9-15, 25
Description: `let globalCache = {}` e `let totalRevenue = 0` em escopo de módulo, mutados por `logAndCache` e exportados para qualquer consumidor.
Impact: Estado compartilhado entre requests sem controle, vazamento de memória (cache sem limite), comportamento imprevisível em testes.
Recommendation: `CacheService` instanciado no composition root e injetado (Playbook P-08).

### #8 [HIGH] Acoplamento forte sem injeção de dependência (AP-07)
File: src/AppManager.js:7, 37, 40, 50, 54, 57, 69, 83, 92, 104, 106, 133
File: src/app.js:8-10
Description: O banco é instanciado no construtor (`new sqlite3.Database(':memory:')`) e usado diretamente (`this.db`/`self.db`) dentro dos handlers; `app.js` depende da classe concreta para inicializar banco e rotas.
Impact: Impossível substituir o banco/gateway em testes; ciclo de vida do banco preso à classe de rotas.
Recommendation: Composition root cria a conexão e injeta em models → controllers → routers (Playbook P-07).

### #9 [HIGH] Ausência de transação e integridade referencial (AP-10)
File: src/AppManager.js:46-75, 50-61, 131-137
Description: (a) usuário novo é criado (l.69) **antes** da decisão de pagamento — checkout recusado deixa usuário órfão; (b) matrícula, pagamento e audit log são inserts independentes sem transação; (c) `DELETE /api/users/:id` remove o usuário mantendo matrículas e pagamentos (a própria resposta admite: "ficaram sujos no banco"); (d) erros de `audit_logs` e do delete são ignorados.
Impact: Dados inconsistentes (matrícula sem pagamento, pagamentos de usuários inexistentes no relatório como "Unknown").
Recommendation: Decidir pagamento antes de qualquer escrita; `BEGIN/COMMIT/ROLLBACK` no checkout; delete em cascata transacional (Playbook P-10).

### #10 [MEDIUM] Queries N+1 no relatório financeiro (AP-11)
File: src/AppManager.js:83-127
Description: Para cada curso, uma query de matrículas; para cada matrícula, uma query de usuário e outra de pagamento — 1 + C + 2·E queries, coordenadas por contadores manuais (`coursesPending`, `enrPending`).
Impact: Latência cresce linearmente com matrículas; lógica de sincronização frágil.
Recommendation: Uma única query com `LEFT JOIN` entre courses, enrollments, users e payments, agregada em memória (Playbook P-11).

### #11 [MEDIUM] Validação de entrada insuficiente (AP-12)
File: src/AppManager.js:35
Description: Apenas presença de campos é checada; `pwd` é opcional (cai no default), não há validação de formato de email, tipo de `c_id` ou formato do cartão; `:id` do DELETE não é validado.
Impact: Dados inválidos gravados; comportamento inesperado com tipos errados.
Recommendation: Validador de payload de checkout no controller, retornando 400 (Playbook P-12).

### #12 [MEDIUM] Error handling inconsistente / erros ignorados (AP-13)
File: src/AppManager.js:38, 92-93, 104-106, 133-135
Description: `if (err || !course)` transforma erro de banco em 404; no relatório o `err` é ignorado e `enrollments.length` lança `TypeError` derrubando o processo se a query falhar; não há middleware de erro global (404 padrão do Express retorna HTML).
Impact: Falhas mascaradas ou crash do servidor; respostas inconsistentes.
Recommendation: Erros de domínio (`NotFoundError`, `ValidationError`) + middleware `(err, req, res, next)` central (Playbook P-13).

### #13 [MEDIUM] API legada de callbacks do sqlite3 (AP-14)
File: src/AppManager.js:37-77, 83-128
Description: Uso do estilo de callbacks aninhados do driver `sqlite3` (padrão Node pré-async/await) em vez de Promises; `function(err) { this.lastID }` depende de `this` dinâmico, forçando o hack `const self = this` (l.26).
Impact: Pyramid of doom, erros não propagados, código difícil de ler.
Recommendation: Wrapper `run/get/all` promisificado na camada de database e `async/await` (Playbook P-14).

### #14 [MEDIUM] Configuração acoplada ao código (AP-15)
File: src/AppManager.js:7
File: src/utils.js:6
Description: Banco `':memory:'` e porta `3000` fixos no código, sem leitura de variáveis de ambiente.
Impact: Impossível configurar por ambiente (persistência, porta).
Recommendation: `PORT` e `DB_PATH` via `process.env` com defaults de dev (Playbook P-02).

### #15 [LOW] Nomes pouco descritivos (AP-18)
File: src/AppManager.js:26, 29-33
File: src/utils.js:12, 17
Description: Variáveis `u`, `e`, `p`, `cid`, `cc`, `self`; nomes enganosos `badCrypto`, `logAndCache` (faz duas coisas), `AppManager` (genérico).
Impact: Leitura difícil e intenção obscura. (Os campos do contrato `usr`, `eml`, `pwd`, `c_id`, `card` devem ser mantidos.)
Recommendation: Desestruturar o body para nomes claros (`name`, `email`, `password`, `courseId`, `card`) (Playbook P-15).

### #16 [LOW] Magic numbers e strings (AP-17)
File: src/AppManager.js:46, 48, 108
File: src/utils.js:19, 22
Description: Prefixo de cartão aprovado `"4"`, status `"PAID"`/`"DENIED"` repetidos como string, `10000` iterações e `10` caracteres no hash.
Impact: Regras implícitas espalhadas.
Recommendation: Constantes `PAYMENT_STATUS`, `APPROVED_CARD_PREFIX` (Playbook P-15).

### #17 [LOW] Código morto / exports não usados (AP-20)
File: src/AppManager.js:2
File: src/utils.js:10, 25
Description: `totalRevenue` é declarado, exportado e importado mas nunca usado; `globalCache` é exportado sem consumidor.
Impact: Ruído e falsa impressão de funcionalidade.
Recommendation: Remover (Playbook P-15).

### #18 [LOW] console.log como mecanismo de log (AP-19)
File: src/AppManager.js:45
File: src/utils.js:13
File: src/app.js:13
Description: Logs ad-hoc sem nível nem contexto.
Impact: Observabilidade pobre.
Recommendation: Logger simples centralizado com níveis (Playbook P-16).

## Deprecated APIs
| File:Line | Deprecated | Modern replacement |
|---|---|---|
| src/AppManager.js:37-77, 83-128 | API de callbacks aninhados do `sqlite3` (estilo legado) | Wrapper com Promises + `async/await` |
| src/AppManager.js:29-33, 81, 86, 90, 93 | `let` em variáveis nunca reatribuídas | `const` |

## Architecture Overview (current → target)
- Current: uma God Class (`AppManager`) + `utils.js` com config/segredos/estado global.
- Target:  MVC — src/config / src/database / src/models / src/services / src/controllers / src/routes / src/middlewares / app.js (composition root) + server.js

================================
Total: 18 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
