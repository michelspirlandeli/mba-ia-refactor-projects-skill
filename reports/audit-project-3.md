```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.12 (local)
Framework:     Flask 3.0.0
Dependencies:  flask-sqlalchemy 3.1.1 (SQLAlchemy 2.x), flask-cors 4.0.0, marshmallow 3.20.1 (não usado),
               requests 2.31.0 (não usado), python-dotenv 1.0.0 (não usado)
Domain:        Task Manager (tasks, usuários, categorias, relatórios de produtividade)
Architecture:  Parcialmente em camadas — pacotes models/, routes/, services/, utils/ existem, mas as rotas
               concentram validação, regra de negócio, queries e serialização; não há camada de controller;
               service de notificação e helpers de validação não são usados; config no entry point
Source files:  15 files analyzed (~1160 lines)
DB tables:     users, tasks, categories (SQLite via Flask-SQLAlchemy, instance/tasks.db)
Entry point:   app.py (python seed.py && python app.py, porta 5000)
Endpoints:     22 routes mapped
================================
```

================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (SQLAlchemy 2.x via Flask-SQLAlchemy 3.1.1, SQLite)
Files:   15 analyzed | ~1160 lines of code
Date:    2026-11-25

## Summary
CRITICAL: 3 | HIGH: 3 | MEDIUM: 7 | LOW: 4

## Findings

### #1 [CRITICAL] Hardcoded Credentials (AP-02)
File: app.py:11, 13
File: services/notification_service.py:7-10
Description: `SECRET_KEY = 'super-secret-key-123'` e URI do banco literais no entry point; `NotificationService` tem host, usuário `taskmanager@gmail.com` e senha SMTP `'senha123'` hardcoded.
Impact: Segredos versionados; sessão forjável e conta de email comprometida para quem tem acesso ao código.
Recommendation: `config.py` lendo variáveis de ambiente (python-dotenv já é dependência) + `.env.example`; service recebe config injetada (Playbook P-02).

### #2 [CRITICAL] Exposição do hash de senha nas respostas (AP-05)
File: models/user.py:16-25
File: routes/user_routes.py:33, 85, 129, 209
Description: `User.to_dict()` inclui o campo `password`, retornado por `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `POST /login` (confirmado: login devolve `"password": "81dc9bdb52d04dc20036dbd8313ed055"`, o MD5 de "1234").
Impact: Combinado com MD5 sem salt (#4), qualquer cliente recupera as senhas reais por rainbow table.
Recommendation: Remover `password` do `to_dict()` (Playbook P-05).

### #3 [CRITICAL] Autenticação/autorização inexistente (AP-03)
File: routes/user_routes.py:52, 71-72, 207-211
File: routes/task_routes.py:11, 85, 156, 225
File: routes/report_routes.py:12, 103, 167, 190, 211
Description: `/login` devolve um token previsível `'fake-jwt-token-' + str(user.id)` que nunca é verificado; nenhuma rota exige autenticação; `POST /users` aceita `role: "admin"` vindo do próprio cliente.
Impact: Qualquer pessoa cria um usuário admin, lê/edita/apaga tasks, usuários e relatórios de todos.
Recommendation: Gerar token assinado (`itsdangerous`, já dependência do Flask) com `SECRET_KEY` da config e verificar em um decorator; restringir atribuição de role (Playbook P-03). Mudanças de contrato devem ser avaliadas — no mínimo o token deve deixar de ser forjável.

### #4 [HIGH] Hash de senha fraco (MD5 sem salt) (AP-09)
File: models/user.py:3, 27-32
Description: `hashlib.md5(pwd.encode()).hexdigest()` para gravar e comparar senhas; seed usa senhas de 4 caracteres.
Impact: MD5 é quebrado em segundos por GPU/rainbow tables; senhas iguais geram hashes iguais.
Recommendation: `werkzeug.security.generate_password_hash`/`check_password_hash` (Playbook P-09).

### #5 [HIGH] Regra de negócio nas rotas — ausência de camada de controller (AP-06)
File: routes/task_routes.py:11-63, 85-154, 156-223, 273-299
File: routes/user_routes.py:42-90, 92-132
File: routes/report_routes.py:12-101, 103-155
Description: As funções de rota fazem validação, regras de domínio (atraso, prioridade, taxa de conclusão), queries, montagem manual de JSON e commit. `summary_report` tem 90 linhas. Categorias (CRUD) estão em `report_routes.py`. `services/` existe mas `NotificationService` nunca é usado.
Impact: Regras não reutilizáveis nem testáveis sem HTTP; arquivos de rota com 200-300 linhas.
Recommendation: Criar `controllers/` (task, user, report, category) com a lógica; rotas apenas extraem request e serializam; mover categorias para `category_routes.py` (Playbook P-06, P-04).

### #6 [HIGH] Acoplamento forte / sem application factory (AP-07)
File: app.py:9-31
File: seed.py:2
File: services/notification_service.py:5-10, 15-17
Description: A app é criada, configurada e `db.create_all()` executado no import do módulo; `seed.py` importa `app` diretamente; rotas importam models e `db` globais; `NotificationService` instancia `smtplib.SMTP` com config fixa no próprio construtor.
Impact: Impossível criar a app com outra config (ex.: banco de teste); importar o módulo tem efeitos colaterais.
Recommendation: `create_app(config)` como composition root, `seed.py` usando a factory, service recebendo config por injeção (Playbook P-07).

### #7 [MEDIUM] Queries N+1 (AP-11)
File: routes/task_routes.py:14-57
File: routes/user_routes.py:12-24
File: routes/report_routes.py:15-28, 53-68, 159-164
Description: `GET /tasks` faz `User.query.get` e `Category.query.get` para cada task; `GET /users` acessa `len(u.tasks)` (lazy load por usuário); `summary_report` faz 11 `count()` separados e uma query de tasks por usuário; `GET /categories` faz um `count()` por categoria.
Impact: Número de queries cresce linearmente com os dados.
Recommendation: `joinedload(Task.user, Task.category)`, agregações com `GROUP BY` (Playbook P-11).

### #8 [MEDIUM] Validação de entrada ausente/fraca (AP-12)
File: routes/task_routes.py:113, 182, 261, 264
File: routes/report_routes.py:196-202
File: routes/user_routes.py:102-103, 124-125
Description: `priority < 1` com string lança `TypeError` → 500 (confirmado com `"priority": "alta"`); `int(priority)` na busca com valor não numérico → 500; `update_category` usa `data` sem checar `None`; cor da categoria não validada (`is_valid_color` existe e não é usado); `name`/`active` do usuário aceitos sem validação.
Impact: Erros 500 para entrada inválida; dados inconsistentes.
Recommendation: Validadores centralizados em `utils/validators.py` usados por controllers, retornando 400 (Playbook P-12).

### #9 [MEDIUM] Regra de domínio duplicada (AP-12 / AP-20)
File: routes/task_routes.py:17-28, 30-39, 71-80, 110, 177, 283-287
File: routes/user_routes.py:61, 71, 106, 120, 162-180
File: routes/report_routes.py:33-43, 132-135
File: utils/helpers.py:57-108
Description: A lógica de "task atrasada" está copiada 6 vezes, embora `Task.is_overdue()` exista (models/task.py:50-60); a lista de status válidos aparece em 5 lugares; a regex de email em 2; a serialização de task é refeita à mão em vez de `to_dict()`; `process_task_data` implementa a validação completa e nunca é chamada.
Impact: Qualquer mudança de regra precisa ser replicada; cópias já divergem (ex.: update não faz `strip` do título).
Recommendation: Usar `Task.is_overdue()`/`to_dict()`, constantes únicas e um validador (Playbook P-12, P-15).

### #10 [MEDIUM] Error handling inconsistente / `except:` nu (AP-13)
File: routes/task_routes.py:62, 137, 204, 236
File: routes/user_routes.py:130, 149
File: routes/report_routes.py:186, 207, 221
File: utils/helpers.py:46, 49, 88
Description: `except:` nu engole qualquer exceção (inclusive `KeyboardInterrupt`); não há error handler global — exceções não tratadas devolvem a página HTML do debugger Werkzeug; 404 de rota inexistente retorna HTML.
Impact: Bugs mascarados, respostas inconsistentes, stack trace exposto.
Recommendation: `middlewares/error_handler.py` com `AppError` + handlers JSON para 404/405/500 (Playbook P-13).

### #11 [MEDIUM] APIs deprecated (AP-14)
File: routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227
File: routes/user_routes.py:29, 94, 136, 155
File: routes/report_routes.py:105, 192, 213
File: models/task.py:15, 16, 52
File: models/user.py:14
File: models/category.py:11
File: routes/task_routes.py:31, 72, 215, 285
File: routes/user_routes.py:172
File: routes/report_routes.py:35, 42, 45, 71, 133
File: services/notification_service.py:35
File: utils/helpers.py:38
File: seed.py:66-74
Description: `Model.query.get(id)` é API legada no SQLAlchemy 2.x; `datetime.utcnow()` está deprecated desde Python 3.12 (o seed emite `DeprecationWarning`); `type(x) == list` (task_routes.py:141, 210; utils/helpers.py:103).
Impact: Warnings hoje, quebra em versões futuras.
Recommendation: `db.session.get(Model, id)`, helper `utcnow()` com `datetime.now(timezone.utc)`, `isinstance` (Playbook P-14).

### #12 [MEDIUM] Configuração acoplada / debug em produção (AP-15)
File: app.py:11-13, 15, 34
Description: `app.run(debug=True, host='0.0.0.0')` expõe o debugger interativo do Werkzeug na rede; URI do banco e CORS aberto fixos no código; `python-dotenv` está nas dependências mas não é usado.
Impact: Execução remota de código via console do debugger; sem configuração por ambiente.
Recommendation: `FLASK_DEBUG`, `HOST`, `PORT`, `DATABASE_URL`, `CORS_ORIGINS` via env (Playbook P-02).

### #13 [MEDIUM] Integridade referencial em deletes (AP-10)
File: routes/report_routes.py:211-223
File: routes/user_routes.py:140-142
Description: Deletar uma categoria deixa tasks com `category_id` apontando para registro inexistente (SQLite não aplica FK por padrão); deletar usuário apaga as tasks uma a uma em laço no handler.
Impact: Referências órfãs; regra de cascata escondida na rota.
Recommendation: Regra de cascata/desvinculação no controller (`category_id = NULL` nas tasks da categoria) em uma única transação (Playbook P-10).

### #14 [LOW] Imports não usados e código morto (AP-20)
File: app.py:7
File: routes/task_routes.py:7
File: routes/user_routes.py:6
File: routes/report_routes.py:7-8
File: models/task.py:3, 38-48
File: utils/helpers.py:3-7, 9-55, 110-116
File: services/notification_service.py:1-48
Description: `import os, sys, json, datetime` (só `datetime` é usado), `json, os, sys, time`, `hashlib, json`, `format_date`, `json`, `math`… não usados; `Task.validate_status/validate_priority`, a maioria dos helpers, as constantes de `helpers.py` e todo o `NotificationService` nunca são chamados.
Impact: Ruído; falsa sensação de que validação/notificação existem.
Recommendation: Remover imports; usar as constantes e helpers ou apagá-los (Playbook P-15).

### #15 [LOW] Magic numbers e strings (AP-17)
File: routes/task_routes.py:96, 99, 104, 113, 167, 169, 182
File: routes/user_routes.py:64, 115
File: routes/report_routes.py:45, 129, 180
Description: Limites `3`/`200` de título, prioridade `1..5` e default `3`, senha mínima `4`, janela de `7` dias, `priority <= 2` = alta prioridade, cor `'#000000'` — enquanto `MIN_TITLE_LENGTH`, `MAX_TITLE_LENGTH`, `DEFAULT_PRIORITY`, `MIN_PASSWORD_LENGTH`, `DEFAULT_COLOR` já existem em utils/helpers.py:110-116 sem uso.
Impact: Regras de negócio escondidas e duplicadas.
Recommendation: Constantes em `config.py` usadas por validadores e controllers (Playbook P-15).

### #16 [LOW] Logging com print (AP-19)
File: routes/task_routes.py:149, 153, 219, 234
File: routes/user_routes.py:83, 89, 147
File: services/notification_service.py:21, 24
Description: `print` como mecanismo de log.
Impact: Sem níveis, sem contexto; não integra com o logger do Flask.
Recommendation: `logging.getLogger(__name__)` (Playbook P-16).

### #17 [LOW] Condicionais verbosas (AP-18)
File: models/task.py:38-60
File: models/user.py:34-38
Description: `if cond: return True else: return False` e ifs aninhados de 3 níveis em `is_overdue`, `is_admin`, `validate_*`.
Impact: Legibilidade.
Recommendation: Retornar a expressão booleana diretamente (Playbook P-15).

## Deprecated APIs
| File:Line | Deprecated | Modern replacement |
|---|---|---|
| routes/*.py (16 ocorrências, ver #11) | `Model.query.get(id)` (legado SQLAlchemy 2.x) | `db.session.get(Model, id)` |
| models/*.py, routes/*.py, services, utils, seed (22 ocorrências, ver #11) | `datetime.utcnow()` (deprecated Python 3.12) | `datetime.now(timezone.utc)` |
| routes/task_routes.py:141, 210; utils/helpers.py:103 | `type(x) == list` | `isinstance(x, list)` |

## Architecture Overview (current → target)
- Current: camadas parciais — models ok, rotas "gordas" sem controllers, services/utils não utilizados, config no entry point.
- Target:  MVC — config.py / models / controllers (NOVO) / routes (views finas) / services / middlewares (NOVO) / create_app()

================================
Total: 17 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
