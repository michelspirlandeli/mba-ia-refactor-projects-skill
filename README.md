# Skill `refactor-arch` — Refatoração Arquitetural Automatizada

Entrega do desafio **Criação de Skills — Refatoração Arquitetural Automatizada** (MBA em Engenharia de Software com IA).
Repositório base: [devfullcycle/mba-ia-refactor-projects-skill](https://github.com/devfullcycle/mba-ia-refactor-projects-skill).

A skill `refactor-arch` (Claude Code) analisa uma codebase backend, audita anti-patterns com severidade e `arquivo:linha`, gera um relatório, **pede confirmação** e refatora o projeto para MVC validando boot + endpoints. Ela foi executada nos 3 projetos legados deste repositório:

| Projeto | Stack | Domínio | Relatório |
|---|---|---|---|
| `code-smells-project/` | Python 3.12 + Flask 3.1.1 + sqlite3 | E-commerce | [reports/audit-project-1.md](reports/audit-project-1.md) |
| `ecommerce-api-legacy/` | Node.js 20 + Express 4.18 + sqlite3 | LMS com checkout | [reports/audit-project-2.md](reports/audit-project-2.md) |
| `task-manager-api/` | Python 3.12 + Flask 3.0 + Flask-SQLAlchemy | Task Manager | [reports/audit-project-3.md](reports/audit-project-3.md) |

```
.
├── README.md
├── reports/audit-project-{1,2,3}.md          # saída da Fase 2 de cada projeto
├── scripts/smoke_project{1,2,3}.*            # smoke tests usados na validação
├── code-smells-project/.claude/skills/refactor-arch/   # skill (original)
├── ecommerce-api-legacy/.claude/skills/refactor-arch/  # cópia idêntica
└── task-manager-api/.claude/skills/refactor-arch/      # cópia idêntica
```

---

## A) Análise Manual

Antes de escrever a skill, li integralmente o código dos 3 projetos e subi cada aplicação original para confirmar os problemas na prática (ex.: o bypass de login por SQL Injection do projeto 1 e o vazamento do hash MD5 no `/login` do projeto 3 foram reproduzidos com `curl`). Abaixo, os principais achados manuais; os relatórios completos gerados pela skill estão em `reports/`.

### Projeto 1 — code-smells-project (Python/Flask, E-commerce)

| # | Severidade | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **SQL Injection** — todas as queries montadas por concatenação | `models.py:28, 47-50, 109-111, 289-297…` | Login com `' OR '1'='1' --` autentica como Admin (reproduzido). Permite ler/apagar qualquer tabela. |
| 2 | CRITICAL | **Endpoint que executa SQL arbitrário** sem auth (`POST /admin/query`) e reset do banco sem auth | `app.py:47-78` | Um único request anônimo destrói ou exfiltra o banco. |
| 3 | CRITICAL | **Credenciais hardcoded e vazadas** — `SECRET_KEY` literal e devolvida no `/health` junto com `db_path` e `debug` | `app.py:7`, `controllers.py:285-289` | Segredo exposto no repositório *e* para qualquer cliente HTTP. |
| 4 | CRITICAL | **God File / falso MVC** — `models.py` tem SQL + regra de negócio + formatação de 4 domínios; controllers acessam o banco direto | `models.py:1-314`, `controllers.py:3, 264-277` | Nada é testável isoladamente; qualquer mudança afeta tudo. |
| 5 | HIGH | **Senhas em texto puro**, comparadas no `WHERE` e retornadas em `GET /usuarios` | `models.py:83, 99, 105-131`, `database.py:75-79` | Qualquer vazamento expõe as senhas reais dos clientes. |
| 6 | HIGH | **Estado global mutável** — conexão SQLite singleton com `check_same_thread=False` | `database.py:4-11` | Transações de requests diferentes se misturam; impossível injetar banco de teste. |
| 7 | MEDIUM | **Queries N+1** na listagem de pedidos (1 + N + N×M queries) | `models.py:171-233` | Degrada linearmente com o volume. |
| 8 | MEDIUM | **Validação duplicada/ausente** — create/update de produto copiados; `dados.get` em body `None` → 500 | `controllers.py:24-96, 167-170` | Entradas inválidas geram 500 e regras divergem entre cópias. |
| 9 | LOW | **Magic numbers** — faixas de desconto `10000/5000/1000` e taxas `0.1/0.05/0.02`, limites de nome, listas de status/categorias | `models.py:257-262`, `controllers.py:47-52, 242` | Regra comercial escondida em literais. |
| 10 | LOW | **`print` como log**, incluindo email do usuário em login | `controllers.py:8, 179, 182, 208-210` | Sem níveis; PII em stdout. |

### Projeto 2 — ecommerce-api-legacy (Node.js/Express, LMS com checkout)

| # | Severidade | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **Segredos hardcoded** — `dbPass` e chave **live** do gateway (`pk_live_…`) em `config` | `src/utils.js:2-5` | Permite operar o gateway de pagamento a partir do código-fonte. |
| 2 | CRITICAL | **Número do cartão e chave do gateway no log** | `src/AppManager.js:45` | Violação PCI-DSS; PAN completo em stdout. |
| 3 | CRITICAL | **God Class `AppManager`** — banco, schema, seed, rotas, pagamento, matrícula, auditoria e relatório em uma classe | `src/AppManager.js:4-139` | Zero separação de responsabilidades. |
| 4 | HIGH | **"Hash" de senha caseiro** (`badCrypto`: base64 truncado, sem salt) + senha default `123456` | `src/utils.js:17-23`, `src/AppManager.js:68` | Senhas trivialmente reversíveis; contas criadas com senha conhecida. |
| 5 | HIGH | **Callback hell com regra de negócio no handler** (5 níveis) e **sem transação**: usuário criado mesmo com pagamento recusado; matrícula/pagamento/auditoria não atômicos | `src/AppManager.js:28-78` | Dados inconsistentes e fluxo impossível de testar. |
| 6 | HIGH | **Estado global mutável** (`globalCache`, `totalRevenue` exportados) | `src/utils.js:9-15, 25` | Estado compartilhado sem controle e cache sem limite. |
| 7 | MEDIUM | **N+1 no relatório financeiro** (1 + C + 2·E queries com contadores manuais) | `src/AppManager.js:83-127` | Latência cresce com matrículas; sincronização frágil. |
| 8 | MEDIUM | **Delete deixa órfãos** e **erros de callback ignorados** (`enrollments.length` com `err` derruba o processo) | `src/AppManager.js:92-93, 131-137` | Relatório passa a exibir alunos "Unknown"; risco de crash. |
| 9 | LOW | **Nomes ruins** — `u`, `e`, `p`, `cid`, `cc`, `self`, `badCrypto` | `src/AppManager.js:26-33` | Intenção obscura. |
| 10 | LOW | **Magic strings/números** — prefixo de cartão `"4"`, `"PAID"`/`"DENIED"`, `10000` iterações | `src/AppManager.js:46, 108`, `src/utils.js:19-22` | Regras implícitas espalhadas. |

### Projeto 3 — task-manager-api (Python/Flask, Task Manager)

| # | Severidade | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **Hash da senha exposto** — `User.to_dict()` inclui `password`, devolvido em `/login`, `/users/<id>`, `POST/PUT /users` | `models/user.py:16-25` | Com MD5 sem salt, a senha real sai por rainbow table (`81dc9bdb…` = `1234`). |
| 2 | CRITICAL | **Autenticação inexistente** — token previsível `fake-jwt-token-<id>`, nenhuma rota protegida, qualquer um cria usuário `admin` | `routes/user_routes.py:52, 71, 210` | Escalada de privilégio trivial. |
| 3 | CRITICAL | **Credenciais hardcoded** — `SECRET_KEY` e senha SMTP | `app.py:13`, `services/notification_service.py:7-10` | Segredos versionados. |
| 4 | HIGH | **MD5 para senhas** | `models/user.py:27-32` | Algoritmo quebrado. |
| 5 | HIGH | **Rotas "gordas" sem camada de controller** — validação, regra, query e serialização juntas; `services/` não usado | `routes/*.py` | Mesmo "organizado", o projeto não tem MVC de fato. |
| 6 | MEDIUM | **N+1** — `User.query.get`/`Category.query.get` por task; `count()` por categoria/usuário | `routes/task_routes.py:41-57`, `routes/report_routes.py:53-68, 159-164` | Queries crescem com os dados. |
| 7 | MEDIUM | **APIs deprecated** — `Query.get()` (legado no SQLAlchemy 2.x), `datetime.utcnow()` (deprecated no Python 3.12) | 16 + 22 ocorrências | O próprio seed emite `DeprecationWarning`. |
| 8 | MEDIUM | **`except:` nu** e sem error handler global; `priority: "alta"` → 500 com debugger HTML | `routes/task_routes.py:62, 113, 137…` | Bugs mascarados; stack trace exposto. |
| 9 | LOW | **Imports não usados / código morto** — `os, sys, json, time`, helpers e constantes nunca usados | `app.py:7`, `routes/task_routes.py:7`, `utils/helpers.py` | Ruído e falsa sensação de validação existente. |
| 10 | LOW | **Lógica de atraso duplicada 6×** e magic numbers (`3`, `200`, `4`, `7` dias, `priority <= 2`) embora `Task.is_overdue()` e constantes existam | `routes/*.py`, `utils/helpers.py:110-116` | Cópias já divergem entre si. |

---

## B) Construção da Skill

### Decisões de design

```
.claude/skills/refactor-arch/
├── SKILL.md                              # o "prompt": fluxo das 3 fases e regras
└── references/
    ├── project-analysis.md               # Fase 1: heurísticas de stack, banco, domínio, arquitetura, rotas
    ├── anti-patterns-catalog.md          # Fase 2: 20 anti-patterns com sinais de detecção e severidade
    ├── report-template.md                # Fase 2: formato obrigatório do relatório
    ├── mvc-guidelines.md                 # Fase 3: camadas, responsabilidades, estrutura alvo por stack
    └── refactoring-playbook.md           # Fase 3: 16 transformações com código antes/depois
```

- **`SKILL.md` é orquestração, não conhecimento.** Ele define a sequência das fases, o que imprimir em cada uma (blocos `PHASE 1`, relatório, `PHASE 3`) e as regras invioláveis: ler *todos* os arquivos, não inventar findings, **parar com `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`** e só declarar sucesso com evidência de validação.
- **Referências carregadas sob demanda (progressive disclosure).** Cada fase manda ler apenas os arquivos de que precisa, mantendo o contexto enxuto. As 5 áreas de conhecimento exigidas viraram 5 arquivos com nomes autoexplicativos.
- **IDs cruzados.** Anti-patterns têm IDs (`AP-01…AP-20`) e o playbook tem padrões (`P-01…P-16`) com uma tabela "padrão → APs que resolve". O relatório cita os dois, então a Fase 3 sabe exatamente qual transformação aplicar para cada finding.
- **Contrato HTTP é sagrado.** A Fase 1 mapeia todos os endpoints; a Fase 3 precisa preservar paths, métodos, campos e status. Mudanças só são permitidas por segurança e devem ser listadas no resumo final ("Contract changes").
- **Validação com evidência.** A Fase 3 exige boot em background, chamada a *todos* os endpoints mapeados (incluindo caminhos de erro) e re-execução dos greps do catálogo.

### Anti-patterns do catálogo (20) e por quê

| Severidade | Anti-patterns | Motivação |
|---|---|---|
| CRITICAL | AP-01 SQL Injection · AP-02 Segredos hardcoded · AP-03 Execução arbitrária / admin sem auth · AP-04 God Class · AP-05 Exposição de dados sensíveis | Os riscos de maior impacto encontrados na análise manual (todos os 3 projetos tinham pelo menos 2). |
| HIGH | AP-06 Regra de negócio em rota · AP-07 Acoplamento sem DI · AP-08 Estado global mutável · AP-09 Hash fraco / auth falsa · AP-10 Transações ausentes | Violações MVC/SOLID que impedem testes e geram inconsistência de dados. |
| MEDIUM | AP-11 N+1 · AP-12 Validação ausente/duplicada · AP-13 Error handling inconsistente · **AP-14 APIs deprecated** · AP-15 Config acoplada · AP-16 Side effects síncronos | Performance, padronização e manutenção. AP-14 traz uma tabela por stack (Python 3.12, SQLAlchemy 2.x, Flask, Node, Express, sqlite3) com o equivalente moderno. |
| LOW | AP-17 Magic numbers · AP-18 Nomes ruins · AP-19 `print`/`console.log` como log · AP-20 Código morto | Legibilidade. |

Cada entrada tem **sinais greppáveis** (regex quando possível), **o que não é finding** (ex.: `.like(f'%{q}%')` do SQLAlchemy é parametrizado) e o padrão do playbook que corrige.

### Como garanti que a skill é agnóstica de tecnologia

- **Detecção por evidência**, nunca por suposição: tabelas de sinais para 8 linguagens e ~7 frameworks (manifesto + código), além de padrões de registro de rotas por stack.
- **Sinais de detecção em pares Python/JS** e um procedimento de varredura independente de linguagem (greps objetivos + leitura estrutural).
- **Estrutura alvo por stack** nas guidelines: monolito Flask → `src/` completo; Flask já em camadas → preservar pacotes e adicionar `controllers/` e `middlewares/`; Express → `server.js` + composition root `app.js` com injeção por construtor.
- **Playbook bilíngue** (Python e JavaScript) para os padrões onde a implementação difere (hash de senha, DI, transações, error handler).
- Prova prática: a mesma pasta, copiada sem alterações, funcionou nos 3 projetos (2 Flask com níveis de organização diferentes + 1 Express).

### Desafios encontrados e como resolvi

| Desafio | Solução |
|---|---|
| **Linhas exatas** nos findings | A Fase 2 exige ler todos os arquivos e confirmar cada ocorrência com grep; o template proíbe findings sem linha/evidência e mostra um exemplo "mal escrito". |
| **Relatório inflado** (mesmo problema repetido 20×) | Regra de agrupamento: mesmo AP + mesmo arquivo = um finding com várias linhas. |
| **Projeto 3 já organizado** — risco de "reescrever por reescrever" | `SKILL.md` diferencia monolito × parcialmente organizado; as guidelines têm uma árvore alvo específica que preserva `models/routes/services/utils` e adiciona só o que falta. |
| **Corrigir segurança sem quebrar o contrato** (ex.: endpoints admin públicos) | Na 1ª passada, a proteção era opcional (`ADMIN_TOKEN` / `AUTH_REQUIRED` desligados por padrão). A **re-auditoria feita pela própria skill** apontou isso como CRITICAL (fail-open). Ficou assim: segurança por padrão (fail-closed), contrato legado apenas como opt-out explícito de dev (`AUTH_REQUIRED=false`), e exceções documentadas. `/admin/query` (SQL arbitrário) foi removido por não ter forma segura. A regra "seguro por padrão / autenticação ≠ autorização" foi incorporada ao `SKILL.md` e ao catálogo. |
| **Senhas já gravadas** em texto puro/MD5 | Migração transparente: no login, hash legado é verificado uma vez e regravado com scrypt. |
| **sqlite3 do Node + transações concorrentes** na mesma conexão | Wrapper com Promises e `transaction()` serializado por fila; testado com 6 checkouts paralelos. |
| **Comparar antes/depois de forma objetiva** | Smoke tests (`scripts/`) rodados no código original (baseline) e no refatorado, com `diff` do status e do formato de cada resposta. |

---

## C) Resultados

### Resumo dos relatórios de auditoria

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | APIs deprecated |
|---|---|---|---|---|---|---|
| 1 — code-smells-project | 5 | 5 | 4 | 4 | **18** | nenhuma aplicável (Flask 3.1 / sqlite3) |
| 2 — ecommerce-api-legacy | 4 | 5 | 5 | 4 | **18** | callbacks legados do `sqlite3`, `let` não reatribuído |
| 3 — task-manager-api | 3 | 3 | 7 | 4 | **17** | `Query.get()` (16×), `datetime.utcnow()` (22×), `type(x) ==` (3×) |

Todos os findings da análise manual (seção A) aparecem nos relatórios gerados pela skill.

### Execução completa da skill sobre o código original

A skill foi executada com `claude "/refactor-arch"` em cada projeto, sobre o código original (commit `6d1ce62`, numa cópia separada via `git worktree`). As 3 execuções percorreram as 3 fases: análise, relatório, pausa, confirmação `y` e refatoração com validação. As sessões completas estão em [`logs/run-original-project-{1,2,3}-*.txt`](logs/).

| | P1 — code-smells-project | P2 — ecommerce-api-legacy | P3 — task-manager-api |
|---|---|---|---|
| **Fase 1:** stack | Python 3.12 + Flask 3.1.1 | Node 20 + Express ^4.18.2 | Python 3.12 + Flask 3.0.0 + Flask-SQLAlchemy 3.1.1 |
| Arquitetura detectada | "Fake MVC" (controllers acessam o banco) | "Big ball of mud" (`AppManager`) | Parcialmente em camadas |
| Arquivos / rotas | 4 arquivos (~780 linhas) / 19 rotas | 3 arquivos (~180 linhas) / 3 rotas | 15 arquivos (~1158 linhas) / 22 rotas |
| **Fase 2:** findings | 19 (5 CRITICAL, 5 HIGH, 5 MEDIUM, 4 LOW) | 19 (4 CRITICAL, 5 HIGH, 6 MEDIUM, 4 LOW) | 17 (3 CRITICAL, 4 HIGH, 6 MEDIUM, 4 LOW) |
| Pausa `[y/n]` respeitada | ✅ | ✅ | ✅ |
| **Fase 3:** boot | ✅ | ✅ | ✅ (sem DeprecationWarnings) |
| Endpoints | ✅ 18/18 (+ `/admin/query` removido), 65/65 checks | ✅ 3/3, 28/28 checks | ✅ 22/22 |
| CRITICAL/HIGH restantes | ✅ 0 | ✅ 0 | ✅ 0 |

As contagens variam pouco em relação aos relatórios em `reports/audit-project-*.md` (18/18/17), porque a skill agrupa ocorrências de forma ligeiramente diferente a cada execução. Os anti-patterns detectados são os mesmos.

O código entregue nesta branch é o da refatoração versionada nos commits, validado contra o baseline e corrigido na iteração 2 abaixo. As execuções sobre o código original servem como evidência de que a skill funciona de ponta a ponta nas 3 stacks.

### Iteração 2: re-auditoria do código refatorado

Depois da refatoração, rodei `claude "/refactor-arch"` novamente em cada projeto, já sobre o código refatorado. A skill reconheceu o MVC e não propôs reestruturar. Mesmo assim, encontrou falhas reais que ficaram da 1ª passada e confirmou cada uma com requisições de teste. Os relatórios estão em [`reports/reaudit-project-{1,2,3}.md`](reports/) e os logs da sessão em [`logs/`](logs/).

| Projeto | Re-auditoria | Principais achados | Correção |
|---|---|---|---|
| 1 | 1 CRITICAL, 2 HIGH, 1 MEDIUM, 4 LOW | `/admin/reset-db` aberto sem `ADMIN_TOKEN` (fail-open). Seed com senhas fixas. Email duplicado e pedido para usuário inexistente aceitos. Tipos inválidos geravam 500. | `require_admin` fail-closed. Seed só em dev, com senhas do ambiente. `UNIQUE(email)` + 409. Usuário do pedido validado. Validadores de tipo. Exceções em `src/exceptions.py`. Reset movido para `database/`. Defaults seguros. |
| 2 | 0 CRITICAL, 3 HIGH, 3 MEDIUM, 2 LOW | Rotas admin fail-open. Checkout de usuário existente **ignorava a senha**. Pagamento autorizado antes do hash. Matrícula/cobrança duplicada. 413/415 viravam 500. | `requireAdmin` fail-closed. `passwordService.verify` → 401. Toda validação antes do pagamento. `UNIQUE(email)` e `UNIQUE(user_id, course_id)` → 409. Error handler respeita 4xx. Cache morto removido. Shutdown limpo. |
| 3 | 1 CRITICAL, 0 HIGH, 8 MEDIUM, 3 LOW | Autenticação opcional e **sem autorização**: usuário comum trocava a senha do admin ou o deletava. MD5/senha de 4 caracteres, sem rate limit. Agregações em memória. SMTP síncrono. Deps com CVE. | `AUTH_REQUIRED=true` por padrão + `authorization_service` (dono/role por recurso). Login com 429 após 5 falhas. Senha mínima de 8. Overdue e contagens no banco. SMTP em background. `flask-cors 6.0.1`. `back_populates`. Erros em `errors.py`. |

Validação depois das correções (smoke tests em `scripts/`, rodados contra o servidor real):

- **P1:**
  - 29 dos 30 casos com o mesmo status do baseline original. A exceção intencional é o SQL Injection, que agora recebe 401.
  - Mais 8 casos de segurança e integridade: 409 para email duplicado, 400 para tipos inválidos, 400 para usuário inexistente e 403 para admin sem token. Com o token correto, 200. Em `APP_ENV=producao`, o seed não roda.
- **P2:**
  - 9 de 9 casos do contrato.
  - Mais 9 casos de segurança: 401 para senha errada e para senha ausente, 409 para matrícula repetida, 400 para tipos inválidos, 415 para charset inválido e 403 para admin sem token.
  - Em 6 checkouts concorrentes do mesmo email, 1 recebe 200 e 5 recebem 409.
- **P3:**
  - 36 de 36 casos com `AUTH_REQUIRED=false`, idênticos ao baseline. Os mesmos 36 de 36 com autenticação ligada e token de admin.
  - Mais 20 casos de autorização, validação e rate limit: usuário comum recebe 403 ao alterar ou deletar outro usuário, ao se promover e ao ver o relatório geral. Recebe 200 nos próprios recursos. A 6ª falha de login seguida recebe 429.
  - Os valores de `/reports/*` e `/tasks/stats` são idênticos aos da versão anterior.

### Antes × depois

**Projeto 1 — code-smells-project** (monolito → MVC completo)

```
ANTES                         DEPOIS
app.py         (88)           app.py                       # entry point
controllers.py (292)          src/app.py                   # create_app() — composition root
models.py      (314)          src/config/settings.py       # env vars + constantes
database.py    (86)           src/database/connection.py   # conexão por request (flask.g), schema, seed
                              src/models/{produto,usuario,pedido}_model.py
                              src/controllers/{produto,usuario,pedido,relatorio,sistema}_controller.py
                              src/controllers/validators.py
                              src/services/notification_service.py
                              src/views/{produto,usuario,pedido,sistema}_routes.py   # Blueprints
                              src/middlewares/{error_handler,auth}.py
```

**Projeto 2 — ecommerce-api-legacy** (God Class → MVC com injeção de dependência)

```
ANTES                         DEPOIS
src/app.js        (14)        src/server.js                # entry point (listen)
src/AppManager.js (141)       src/app.js                   # composition root
src/utils.js      (25)        src/config/index.js
                              src/database/connection.js   # wrapper Promise + transaction()
                              src/models/{user,course,enrollment,payment,auditLog}Model.js
                              src/services/{payment,password}Service.js, logger.js
                              src/controllers/{checkout,report,user}Controller.js
                              src/routes/{checkout,admin}Routes.js
                              src/middlewares/{errorHandler,requireAdmin}.js
                              src/errors/AppError.js
```

**Projeto 3 — task-manager-api** (camadas parciais → MVC completo, preservando a organização)

```
ANTES                                  DEPOIS
app.py (config + rotas + create_all)   app.py           # create_app() factory
                                       config.py        # NOVO — env vars (dotenv) + constantes
                                       errors.py        # NOVO — erros de domínio
models/  (to_dict com password, MD5)   models/          # sem password, scrypt, is_overdue único
routes/  (validação+regra+query)       routes/          # views finas; + category_routes, system_routes
—                                      controllers/     # NOVO — task, user, report, category
services/ (não usado, senha SMTP)      services/        # notification (background), auth (token + rate limit),
                                                        # authorization (regras dono/role)
—                                      middlewares/     # NOVO — error_handler, auth (identifica o usuário)
utils/helpers.py (código morto)        utils/           # helpers puros + validators.py
```

### Checklist de validação

| Item | P1 | P2 | P3 |
|---|---|---|---|
| **Fase 1** — Linguagem detectada corretamente | ✅ Python | ✅ JavaScript/Node | ✅ Python |
| Framework detectado corretamente | ✅ Flask 3.1.1 | ✅ Express 4.18 | ✅ Flask 3.0.0 + SQLAlchemy |
| Domínio descrito corretamente | ✅ E-commerce | ✅ LMS com checkout | ✅ Task Manager |
| Nº de arquivos condiz com a realidade | ✅ 4 | ✅ 3 | ✅ 15 |
| **Fase 2** — Relatório segue o template | ✅ | ✅ | ✅ |
| Cada finding tem arquivo e linhas exatos | ✅ | ✅ | ✅ |
| Findings ordenados CRITICAL → LOW | ✅ | ✅ | ✅ |
| Mínimo de 5 findings | ✅ 18 (execução no original: 19) | ✅ 18 (19) | ✅ 17 (17) |
| Detecção de APIs deprecated (se aplicável) | ✅ (nenhuma aplicável) | ✅ | ✅ |
| Pausa e pede confirmação antes da Fase 3 | ✅ | ✅ | ✅ |
| **Fase 3** — Estrutura de diretórios MVC | ✅ | ✅ | ✅ |
| Configuração extraída (sem hardcoded) | ✅ | ✅ | ✅ |
| Models abstraem os dados | ✅ | ✅ | ✅ |
| Views/Routes separadas | ✅ | ✅ | ✅ |
| Controllers concentram o fluxo | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ | ✅ | ✅ |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem corretamente | ✅ 30/30 | ✅ 9/9 | ✅ 36/36 |
| **Iteração 2**: re-auditoria executada e findings corrigidos | ✅ 8 | ✅ 8 | ✅ 12 |

### Logs de execução após a refatoração

**Projeto 1** — `python app.py` + `python scripts/smoke_project1.py` (status / método / rota):

```
 * Serving Flask app 'src.app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
200 GET    /                      200 GET    /usuarios              201 POST   /pedidos
200 GET    /health                200 GET    /usuarios/1            400 POST   /pedidos (produto 999)
200 GET    /produtos              404 GET    /usuarios/999          400 POST   /pedidos (sem itens)
200 GET    /produtos/1            201 POST   /usuarios              200 GET    /pedidos
404 GET    /produtos/999          400 POST   /usuarios (inválido)   200 GET    /pedidos/usuario/2
200 GET    /produtos/busca?...    200 POST   /login                 200 PUT    /pedidos/1/status
201 POST   /produtos              401 POST   /login (senha errada)  400 PUT    /pedidos/1/status (xyz)
400 POST   /produtos (x2)         401 POST   /login (' OR '1'='1)   200 GET    /relatorios/vendas
200 PUT    /produtos/11           404 PUT    /produtos/999          404 GET    /rota-inexistente (JSON)
200 DELETE /produtos/11           404 DELETE /produtos/999
```
Diff contra o baseline original: **mesmos status em 29/30 casos**; o único diferente é o login por SQL Injection (antes 200, agora 401 — correção intencional).

**Projeto 2** — `npm start` + `sh scripts/smoke_project2.sh`:

```
2026-11-25T17:27:05.158Z [INFO] LMS API rodando na porta 3000
POST /api/checkout (sucesso)          200  {"msg":"Sucesso","enrollment_id":2}
POST /api/checkout (cartão recusado)  400  Pagamento recusado
POST /api/checkout (usuário existente)200  {"msg":"Sucesso","enrollment_id":3}
POST /api/checkout (curso inexistente)404  Curso não encontrado
POST /api/checkout (incompleto)       400  Bad Request
GET  /api/admin/financial-report      200  [{"course":"Clean Architecture","revenue":997,...},{"course":"Docker","revenue":994,...}]
DELETE /api/users/1                   200  Usuário deletado com suas matrículas e pagamentos.
GET  /nao-existe                      404  Cannot GET /nao-existe
2026-11-25T17:27:05.684Z [INFO] Pagamento PAID card=****4444 amount=497   <- cartão mascarado
```
Corpos e status são idênticos ao original nos 5 casos de checkout e no relatório. Na iteração 2, as rotas admin exigem `ADMIN_TOKEN`: sem header, 403; com header, 200. O checkout de usuário existente passou a exigir o `pwd` correto, e o smoke test envia essa senha. Veja a seção "Iteração 2" acima.

**Projeto 3** — `python seed.py && python app.py` + `python scripts/smoke_project3.py`:

```
Seed concluído com sucesso!   3 usuários / 4 categorias / 10 tasks   (sem DeprecationWarning)
200 GET /   200 GET /health   200 GET /tasks   200 GET /tasks/1   404 GET /tasks/999
200 GET /tasks/search   200 GET /tasks/stats   201/400/400/404 POST /tasks
200/400/404 PUT /tasks   200/404 DELETE /tasks
200 GET /users   200 GET /users/1   404 GET /users/999   201/409/400 POST /users
200 PUT /users/4   200 GET /users/1/tasks   200/401 POST /login   200 DELETE /users/4
200 GET /reports/summary   200/404 GET /reports/user/<id>
200 GET /categories   201 POST   200 PUT   200/404 DELETE /categories
404 GET /rota-inexistente (JSON)
```
Diff contra o baseline: **mesmos status em 36/36 casos**; diferenças apenas na remoção do campo `password` e no 404 em JSON. Extras:
- `priority: "alta"` → 400 (antes 500).
- Login com hash MD5 legado → 200, e o hash é migrado para `scrypt:`.
- Com autenticação ligada, que é o padrão desde a iteração 2:
  - `GET /tasks` sem token → 401;
  - token forjado `fake-jwt-token-1` → 401;
  - token válido → 200;
  - criar `admin` sem ser admin → 403.

### Comportamento da skill em stacks diferentes

- **Monolito Python (P1)**: a skill aplicou a reestruturação completa em `src/` — é o caso em que o playbook "God Class → camadas" (P-04) domina.
- **Node/Express (P2)**: os mesmos APs foram detectados com sinais JS (template literals, `this.db` em handlers, `let` global exportado). A diferença principal foi a DI por construtor no composition root e a troca da API de callbacks por Promises para viabilizar transações.
- **Flask parcialmente organizado (P3)**: a skill não "achou que estava tudo certo" por haver pastas `models/routes/services`; detectou que as rotas eram controllers disfarçados e criou a camada `controllers/` mantendo os pacotes existentes. Foi também o único projeto com muitas **APIs deprecated** reais (SQLAlchemy 2.x e Python 3.12), cobertas pela tabela do AP-14.
- O formato de erro de cada projeto foi preservado (`{"erro"}` no P1, texto puro no P2, `{"error"}` no P3), conforme a regra "mantenha o formato que o projeto já usava" do playbook.

---

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) instalado e autenticado (`npm install -g @anthropic-ai/claude-code`).
- Python 3.10+ (testado com 3.12) e Node.js 18+ (testado com 20).

### Executar a skill em cada projeto

A skill fica em `.claude/skills/refactor-arch/` dentro de cada projeto, então basta abrir o Claude Code no diretório do projeto:

```bash
# Projeto 1
cd code-smells-project
claude "/refactor-arch"

# Projeto 2
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3
cd ../task-manager-api
claude "/refactor-arch"
```

A skill imprime a Fase 1, gera o relatório da Fase 2 e **para** com `Proceed with refactoring (Phase 3)? [y/n]`. Responda `y` para refatorar.

Rodada sobre o código desta branch, que já está refatorado, ela faz uma **re-auditoria**. Para executá-la sobre o código **original** sem mexer na branch, use uma cópia separada:

```bash
git worktree add ../base 6d1ce62
for p in code-smells-project ecommerce-api-legacy task-manager-api; do
  mkdir -p ../base/$p/.claude/skills && cp -r $p/.claude/skills/refactor-arch ../base/$p/.claude/skills/
done
cd ../base/code-smells-project && claude "/refactor-arch"   # idem para os outros dois
```

### Validar que a refatoração funcionou

```bash
# Projeto 1
cd code-smells-project
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py &                                    # http://127.0.0.1:5000
python ../scripts/smoke_project1.py http://127.0.0.1:5000 --security

# Projeto 2
cd ../ecommerce-api-legacy
npm install
ADMIN_TOKEN=s3cr3t SEED_USER_PASSWORD=leonan123 npm start &          # http://localhost:3000
ADMIN_TOKEN=s3cr3t SEED_USER_PASSWORD=leonan123 sh ../scripts/smoke_project2.sh http://localhost:3000 --security

# Projeto 3 (autenticação ligada por padrão)
cd ../task-manager-api
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
SEED_PASSWORD=1234 python seed.py && python app.py &                 # http://127.0.0.1:5000
SEED_PASSWORD=1234 python ../scripts/smoke_project3.py http://127.0.0.1:5000 --auth --security
# contrato legado (sem auth): AUTH_REQUIRED=false python app.py  +  smoke sem --auth
```

Para comparar com o original, rode o mesmo smoke test no commit base e faça `diff` das saídas. Variáveis de ambiente de cada projeto estão em `.env.example` (`SECRET_KEY`, `ADMIN_TOKEN`, `AUTH_REQUIRED`, `SEED_*`, etc.).
