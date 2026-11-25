================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.12 (local) + Flask 3.0.0 / Flask-SQLAlchemy 3.1.1 (SQLite)
Files:   27 analyzed | ~1192 lines of code
Date:    2026-11-25

> Nota: este projeto já passou por uma refatoração MVC (commit `e5f079a`). Esta auditoria
> avalia o estado **atual** do código; os findings abaixo são o que restou ou o que a
> refatoração anterior introduziu. Os itens #1 e #5 foram confirmados executando a aplicação
> com o Flask test client sobre um SQLite em memória.

## Summary
CRITICAL: 1 | HIGH: 0 | MEDIUM: 8 | LOW: 3

## Findings

### #1 [CRITICAL] Endpoint administrativo sem autorização — tomada de conta (AP-03)
File: config.py:26
File: middlewares/auth.py:11, 36-38
File: controllers/user_controller.py:25-31, 65-91
File: routes/user_routes.py:23-31
Description: `AUTH_REQUIRED` vem **desligado** por padrão, então `PUT/DELETE /users/<id>`, `DELETE /tasks/<id>`,
`DELETE /categories/<id>` e `/reports/*` ficam públicos. Mesmo com `AUTH_REQUIRED=true`, o middleware só checa
*autenticação*: não há verificação de dono nem de role em `update_user`/`delete_user` (só `role` é protegido por
`_ensure_can_assign_role`). Confirmado: um usuário comum autenticado executou `PUT /users/1 {"password":"hacked"}`
→ 200, o admin passou a logar com `hacked` → 200, e `DELETE /users/1` → 200.
Impact: Qualquer cliente (ou qualquer usuário logado) troca a senha de um admin, assume a conta e apaga usuários e as tasks deles. É escalonamento de privilégio completo.
Recommendation: Adicionar autorização por recurso: usuário só edita/apaga a si mesmo, a menos que seja admin. Restringir `DELETE` de usuários e categorias e `/reports/*` a admin/manager. Tornar `AUTH_REQUIRED=true` o padrão fora de dev, ou ao menos sempre aplicar a regra de ownership quando houver token (Playbook P-03).

### #2 [MEDIUM] Credenciais fracas em texto claro no seed (AP-02)
File: seed.py:23, 30, 37
Description: O seed cria `joao@email.com` com role **admin** e senha `'1234'`, além de `'abcd'` e `'pass'`, todas literais no código. Rebaixado de CRITICAL porque é script de dev. Mas `seed.py` não tem nenhuma trava de ambiente e apaga todas as tabelas (linhas 15-17).
Impact: Se rodar fora de dev, cria um admin com senha pública. Somado ao #1, dá acesso administrativo imediato. Também apaga os dados existentes.
Recommendation: Ler as senhas do seed de variáveis de ambiente (ou gerar aleatórias e imprimir uma vez) e recusar a execução quando `FLASK_DEBUG` for falso ou sem uma flag `--force` (Playbook P-02).

### #3 [MEDIUM] Acoplamento entre camadas / DI parcial (AP-07)
File: utils/validators.py:6
File: controllers/task_controller.py:10, 14, 68
File: controllers/user_controller.py:8-9
File: controllers/category_controller.py:6
File: controllers/report_controller.py:7-8
Description: As exceções de domínio (`ValidationError`, `NotFoundError`, ...) estão definidas em `middlewares/error_handler.py`, então validators e controllers dependem da camada de middleware. `user_controller` importa `issue_token` de `middlewares.auth`. `task_controller.create_task` instancia `NotificationService.from_config(current_app.config)` dentro do caso de uso. `report_controller` importa funções de outros controllers. Severidade reduzida porque acessar `db.session` direto é o idioma do Flask-SQLAlchemy e o factory `create_app(config_object)` já permite trocar o banco em teste.
Impact: A dependência vai para fora (domínio → infraestrutura HTTP). Não dá para testar controllers sem contexto Flask nem substituir o serviço de notificação por um fake.
Recommendation: Mover as exceções para `errors.py` / `domain/errors.py` (o middleware só as traduz para HTTP). Mover a emissão de token para um `auth_service`. Injetar `NotificationService` no app (`app.extensions['notifier']`) criado no composition root (Playbook P-07).

### #4 [MEDIUM] Hash legado MD5, política de senha fraca e login sem rate limit (AP-09)
File: models/user.py:1, 41-45
File: config.py:51
File: controllers/user_controller.py:113-121
Description: `check_password` ainda aceita `hashlib.md5(pwd)` sem salt para hashes legados. A migração para scrypt só ocorre no login, então hashes MD5 ficam no banco indefinidamente para quem não loga. `MIN_PASSWORD_LENGTH = 4`. `/login` não tem limite de tentativas. Rebaixado de HIGH porque o caminho MD5 é só compatibilidade e senhas novas usam scrypt.
Impact: Um vazamento do banco expõe senhas MD5 quebráveis instantaneamente. Senhas de 4 caracteres sem rate limit permitem força bruta online.
Recommendation: Forçar reset (ou re-hash em lote via `pbkdf2(md5)`) dos hashes legados e prazo para remover o caminho MD5. Mínimo de 8 caracteres. Rate limit / backoff por email+IP no `/login` (Playbook P-09).

### #5 [MEDIUM] Validação de tipo ausente → 500 em vez de 400 (AP-12)
File: utils/validators.py:61-62, 67-70, 74-75, 81-84, 128-133
File: controllers/task_controller.py:95
Description: `description`, `user_id`, `category_id`, `tags` (task) e `name`/`description` (user/category) não têm checagem de tipo. Confirmado: `POST /tasks {"title":"abc","tags":{"a":1}}` → 500, `{"description":{"a":1}}` → 500, `POST /categories {"name":["x"]}` → 500. Na busca, `like(f'%{query}%')` não escapa `%`/`_`. Não é injeção (é parametrizado), mas `q=%` casa tudo.
Impact: Entrada inválida do cliente gera "Erro interno" e log de exceção em vez de uma mensagem 400 acionável. Ruído em monitoramento.
Recommendation: Validar tipos de todos os campos aceitos (`str` para textos, `int` não-bool para FKs, `list[str] | str` para tags). Escapar curingas com `like(..., escape='\\')` (Playbook P-12).

### #6 [MEDIUM] Agregações em memória e varreduras completas (AP-11)
File: controllers/task_controller.py:37-39, 112-114
File: controllers/report_controller.py:16-26, 58-60, 66-69, 77-84
Description: `count_overdue` e `_overdue_tasks` carregam **todas** as tasks para filtrar `is_overdue` em Python. `user_report` carrega todas as tasks do usuário para contar status. `summary_report` faz 5 `COUNT` separados. `GET /tasks` não tem paginação. Não há N+1 clássico (já resolvido com `joinedload`/`GROUP BY`), mas o custo cresce linearmente com a tabela.
Impact: `/tasks/stats` e `/reports/summary` ficam O(n) em memória e latência a cada chamada. Degrada com volume.
Recommendation: Expressar o atraso em SQL (`due_date < :now AND status NOT IN CLOSED_STATUSES`) com `COUNT`/`GROUP BY`. Consolidar contagens. Paginação opcional via `?page=&per_page=` mantendo o default atual (Playbook P-11).

### #7 [MEDIUM] Dependências obsoletas com vulnerabilidades conhecidas / API legacy (AP-14)
File: requirements.txt:3, 5
File: models/task.py:21-22
File: middlewares/auth.py:3
Description: `flask-cors==4.0.0` (há correções de segurança em 4.0.1+/6.x, ex.: CVE-2024-6221) e `requests==2.31.0` (CVE-2024-35195, corrigido em 2.32.0) estão pinados em versões vulneráveis. `relationship(..., backref=...)` é considerado legacy no SQLAlchemy 2.x (instalado: 2.1.9). `itsdangerous` é importado diretamente mas não está declarado no `requirements.txt` (vem transitivamente pelo Flask).
Impact: Superfície de ataque conhecida em dependências. Builds podem quebrar se o Flask mudar a dependência transitiva.
Recommendation: Atualizar `flask-cors` para a versão atual (6.x), remover `requests` (não usado, ver #12) ou subir para ≥ 2.32.4, declarar `itsdangerous`. Trocar `backref` por `back_populates` explícito (Playbook P-14).

### #8 [MEDIUM] Defaults de configuração inseguros para produção (AP-15)
File: config.py:15, 20, 22
Description: `SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)`: sem a env, cada processo gera uma chave diferente **em silêncio**. Tokens são invalidados a cada restart e não funcionam entre workers. `HOST` default `"0.0.0.0"` e `CORS_ORIGINS` default `"*"`.
Impact: Falhas intermitentes de autenticação em deploy multi-worker. A API fica exposta na rede e para qualquer origem sem decisão explícita.
Recommendation: Exigir `SECRET_KEY` (erro no boot) quando `FLASK_DEBUG` for falso e logar warning em dev. Default `HOST=127.0.0.1`. CORS restrito por padrão fora de dev (Playbook P-02).

### #9 [MEDIUM] Envio SMTP síncrono no fluxo da requisição (AP-16)
File: services/notification_service.py:30-34
File: controllers/task_controller.py:67-68
Description: `create_task` chama `notify_task_assigned` → `smtplib.SMTP(..., timeout=10)` inline. Desligado por padrão (`NOTIFICATIONS_ENABLED=false`), daí MEDIUM.
Impact: Com notificações ligadas, `POST /tasks` pode levar até ~10 s (ou mais, com handshake TLS) quando o SMTP estiver lento, segurando um worker.
Recommendation: Enfileirar o envio (thread pool / fila tipo RQ/Celery) ou usar um hook pós-commit assíncrono. Manter o serviço injetável (Playbook P-06).

### #10 [LOW] Magic strings de status/role espalhadas (AP-17)
File: controllers/report_controller.py:30, 69, 80
File: controllers/user_controller.py:27
File: utils/validators.py:64, 92
File: models/task.py:12
File: models/user.py:20, 49
File: config.py:41
Description: `'done'`, `'pending'`, `'user'`, `'admin'` e a tupla `('done', 'pending', 'in_progress', 'cancelled')` (report_controller.py:80, que duplica `VALID_STATUSES` em outra ordem) são literais, embora `config.py` já defina `VALID_STATUSES` e `DEFAULT_ROLE` (este último nunca é usado).
Impact: Renomear/adicionar um status ou role exige caçar literais. Risco de divergência.
Recommendation: Usar constantes/enum (`TaskStatus.DONE`, `Role.ADMIN`, `DEFAULT_ROLE`) em todos os pontos (Playbook P-15).

### #11 [LOW] Nomes pouco descritivos (AP-18)
File: seed.py:20-65, 82-94
File: routes/category_routes.py:18-25
Description: `u1`/`u2`/`u3`, `c1`..`c4`, `td`, `t` no seed. `cat_id` nas rotas enquanto o controller usa `category_id`.
Impact: Legibilidade baixa e inconsistência de nomenclatura.
Recommendation: `admin_user`, `backend_category`, `task_data`… e `category_id` nas rotas (o path param não faz parte do contrato) (Playbook P-15).

### #12 [LOW] Código morto e dependências não usadas (AP-20)
File: requirements.txt:4-5
File: services/notification_service.py:47-50
File: controllers/user_controller.py:98-110
File: controllers/report_controller.py:87
Description: `marshmallow` e `requests` estão declarados mas nunca são importados. `notify_task_overdue` nunca é chamado. `get_user_tasks` e `user_report` serializam task/usuário manualmente, duplicando `to_dict()`.
Impact: Instalação maior, superfície de CVEs desnecessária (#7) e formatos de serialização que podem divergir.
Recommendation: Remover as dependências e o método não usados (ou ligá-lo a um job de atraso). Derivar as serializações parciais de `to_dict()` (Playbook P-15).

## Deprecated APIs
| File:Line | Deprecated | Modern replacement |
|---|---|---|
| models/task.py:21-22 | `db.relationship(..., backref=...)` (legacy no SQLAlchemy 2.x) | `relationship(..., back_populates=...)` nos dois lados |
| requirements.txt:3 | `flask-cors==4.0.0` (versão com CVEs) | `flask-cors` 6.x |
| requirements.txt:5 | `requests==2.31.0` (versão com CVEs, e não usado) | remover, ou `requests>=2.32.4` |

Nenhum uso de `datetime.utcnow()`, `Model.query.get()` ou `before_first_request` (já substituídos por `utils.helpers.utcnow()` e `db.session.get`).

## Architecture Overview (current → target)
- Current: MVC em camadas já adequado (config isolada, models com dados, controllers com regra, Blueprints finos, error handler central, factory). Restam falhas de **autorização**, robustez de validação, acoplamento domínio → middleware e higiene de dependências.
- Target:  MVC — config / models / controllers (+services, errors de domínio) / views(routes) / middlewares (auth com authorization por recurso) / entry point

================================
Total: 12 findings
================================
