# Playbook de Refatoração (Fase 3)

Padrões concretos de transformação. Cada padrão indica os anti-patterns que resolve,
os passos e um exemplo **antes/depois** em Python e/ou JavaScript. Adapte os idiomas à stack.

| Padrão | Resolve |
|---|---|
| P-01 Queries parametrizadas | AP-01 |
| P-02 Extrair configuração para env vars | AP-02, AP-15 |
| P-03 Remover/proteger endpoints perigosos | AP-03 |
| P-04 Decompor God Class em camadas MVC | AP-04 |
| P-05 Serialização segura (DTO) | AP-05 |
| P-06 Extrair regra de negócio para controller/service | AP-06, AP-16 |
| P-07 Injeção de dependência / composition root | AP-07 |
| P-08 Eliminar estado global mutável | AP-08 |
| P-09 Hash de senha forte | AP-09 |
| P-10 Transações e integridade referencial | AP-10 |
| P-11 Eliminar N+1 (JOIN / eager loading / agregação) | AP-11 |
| P-12 Validação centralizada | AP-12 |
| P-13 Error handler centralizado | AP-13 |
| P-14 Substituir APIs deprecated | AP-14 |
| P-15 Constantes nomeadas, nomes claros, remover código morto | AP-17, AP-18, AP-20 |
| P-16 Logging estruturado | AP-19 |

---

## P-01 — Queries parametrizadas

**Antes (Python/sqlite3)**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query += " AND (nome LIKE '%" + termo + "%')"
```
**Depois**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
clauses, params = ["1=1"], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
cursor.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params)
```
**Antes (Node)** `` db.get(`SELECT * FROM users WHERE email = '${email}'`) ``
**Depois** `db.get("SELECT * FROM users WHERE email = ?", [email])`

> Só nomes de colunas/cláusulas fixas podem ser interpolados — nunca valores vindos do usuário.

---

## P-02 — Extrair configuração para variáveis de ambiente

**Antes**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.run(host="0.0.0.0", port=5000, debug=True)
```
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_123", port: 3000 };
```
**Depois**
```python
# src/config/settings.py
import os, secrets

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)  # efêmera em dev
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
```
```js
// src/config/index.js
module.exports = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  dbPath: process.env.DB_PATH || ':memory:',
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',   // sem default real
});
```
E crie `.env.example` listando as variáveis (sem valores reais).

---

## P-03 — Remover ou proteger endpoints perigosos

**Antes**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json().get("sql"))
```
**Depois** — remova a execução arbitrária (não há forma segura de expô-la). Para rotas
administrativas legítimas (reset, relatórios), exija um token de admin via config:
```python
def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Admin-Token")
        if not current_app.config["ADMIN_TOKEN"] or token != current_app.config["ADMIN_TOKEN"]:
            raise ForbiddenError("Acesso administrativo negado")
        return fn(*args, **kwargs)
    return wrapper
```
Documente a mudança de contrato no resumo da Fase 3.

---

## P-04 — Decompor God Class/God File em camadas MVC

**Antes (Node)** — `AppManager` cria o banco, faz seed, define rotas, valida, processa pagamento e loga.
```js
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE ... INSERT ... */ }
  setupRoutes(app) { app.post('/api/checkout', (req, res) => { /* 50 linhas */ }); }
}
```
**Depois**
```
database/connection.js   -> abre db + schema + seed
models/courseModel.js    -> findActiveById(id)
models/userModel.js      -> findByEmail(email), create(...)
services/paymentService.js -> charge(card, amount)
controllers/checkoutController.js -> checkout({ name, email, password, courseId, card })
routes/checkoutRoutes.js -> router.post('/api/checkout', ...)
app.js                   -> compõe tudo
```
Passos: (1) liste as responsabilidades do arquivo; (2) crie um módulo por responsabilidade
× domínio; (3) mova o código **sem alterar comportamento**; (4) troque as chamadas internas;
(5) apague o arquivo original quando estiver vazio.

---

## P-05 — Serialização segura (DTO / whitelist de campos)

**Antes**
```python
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password}
```
**Depois**
```python
PUBLIC_FIELDS = ("id", "name", "email", "role", "active", "created_at")

def to_dict(self):
    return {"id": self.id, "name": self.name, "email": self.email,
            "role": self.role, "active": self.active, "created_at": str(self.created_at)}
```
Remova também `secret_key`/`debug`/`db_path` de health checks e não logue cartões
(`****${card.slice(-4)}` se precisar).

---

## P-06 — Extrair regra de negócio para controller/service

**Antes (regra no model + notificação no handler)**
```python
def relatorio_vendas():
    ...
    if faturamento > 10000: desconto = faturamento * 0.1
    elif faturamento > 5000: desconto = faturamento * 0.05
```
```python
def criar_pedido():
    resultado = models.criar_pedido(usuario_id, itens)
    print("ENVIANDO EMAIL: ...")
```
**Depois**
```python
# config/settings.py
DESCONTO_FAIXAS = ((10000, 0.10), (5000, 0.05), (1000, 0.02))

# controllers/relatorio_controller.py
def calcular_desconto(faturamento):
    for limite, taxa in DESCONTO_FAIXAS:
        if faturamento > limite:
            return faturamento * taxa
    return 0

# controllers/pedido_controller.py
def criar_pedido(dados, notifier=notification_service):
    pedido = pedido_model.criar(usuario_id, itens)
    notifier.pedido_criado(pedido)
    return pedido
```
**Node — callback hell → async/await em controller**
```js
// Antes: 5 níveis de db.get/db.run aninhados dentro de app.post(...)
// Depois
async checkout(input) {
  const course = await this.courses.findActiveById(input.courseId);
  if (!course) throw new NotFoundError('Curso não encontrado');
  const userId = await this.users.findOrCreate(input);
  if (!this.payments.authorize(input.card)) throw new PaymentDeniedError('Pagamento recusado');
  return this.enrollments.enrollWithPayment(userId, course);
}
```

---

## P-07 — Injeção de dependência / composition root

**Antes**
```python
# controllers.py
from database import get_db
def health_check():
    db = get_db(); cursor = db.cursor() ...
```
**Depois**
```python
# controllers/health_controller.py
def health_check():
    return {"status": "ok", "counts": health_model.contar_registros()}
```
```js
// app.js (composition root)
function createApp({ db }) {
  const userModel = new UserModel(db);
  const checkoutController = new CheckoutController({ userModel, courseModel, paymentService });
  app.use(checkoutRoutes(checkoutController));
  app.use(errorHandler);
  return app;
}
```
Controllers recebem dependências pelo construtor (Node) ou importam models por módulo, com a
conexão obtida via contexto de request (`flask.g`) — nunca a criando.

---

## P-08 — Eliminar estado global mutável

**Antes**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
```
```js
let globalCache = {}; let totalRevenue = 0;
module.exports = { globalCache, totalRevenue };
```
**Depois**
```python
from flask import g, current_app

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
# em create_app: app.teardown_appcontext(close_db)
```
```js
class CacheService {           // instância criada no composition root e injetada
  #store = new Map();
  set(key, value) { this.#store.set(key, value); }
  get(key) { return this.#store.get(key); }
}
```

---

## P-09 — Hash de senha forte

**Antes**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
```
```js
function badCrypto(pwd) { let h=""; for (let i=0;i<10000;i++) h += Buffer.from(pwd).toString('base64').substring(0,2); return h.substring(0,10); }
```
**Depois**
```python
from werkzeug.security import generate_password_hash, check_password_hash  # já vem com Flask

def set_password(self, pwd):
    self.password = generate_password_hash(pwd)

def check_password(self, pwd):
    return check_password_hash(self.password, pwd)
```
```js
const crypto = require('crypto');
function hashPassword(pwd) {
  const salt = crypto.randomBytes(16).toString('hex');
  return `${salt}:${crypto.scryptSync(pwd, salt, 64).toString('hex')}`;
}
function verifyPassword(pwd, stored) {
  const [salt, hash] = stored.split(':');
  return crypto.timingSafeEqual(Buffer.from(hash, 'hex'), crypto.scryptSync(pwd, salt, 64));
}
```
Login: buscar por e-mail com query parametrizada e verificar o hash em código — nunca
comparar senha no `WHERE`. Não aplicar senha default quando o campo vier vazio: retornar 400.

---

## P-10 — Transações e integridade referencial

**Antes**
```python
cursor.execute("INSERT INTO pedidos ...")
for item in itens:
    cursor.execute("INSERT INTO itens_pedido ...")
    cursor.execute("UPDATE produtos SET estoque = ...")
db.commit()   # se falhar no meio, estado parcial em memória da conexão global
```
**Depois**
```python
with db:   # sqlite3: commit no sucesso, rollback em exceção
    pedido_id = db.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
                           (usuario_id, total)).lastrowid
    db.executemany("INSERT INTO itens_pedido (...) VALUES (?, ?, ?, ?)", linhas)
    db.executemany("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", baixas)
```
```js
await db.run('BEGIN');
try { /* inserts */ await db.run('COMMIT'); } catch (e) { await db.run('ROLLBACK'); throw e; }
```
Delete de pai: remova/arquive os filhos na mesma transação (ou `ON DELETE CASCADE`).

---

## P-11 — Eliminar N+1

**Antes**
```python
for row in pedidos:
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in cursor2.fetchall():
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
**Depois — uma query com JOIN e agrupamento em memória**
```python
rows = db.execute("""
    SELECT i.pedido_id, i.produto_id, i.quantidade, i.preco_unitario,
           COALESCE(p.nome, 'Desconhecido') AS produto_nome
    FROM itens_pedido i LEFT JOIN produtos p ON p.id = i.produto_id
    WHERE i.pedido_id IN ({})""".format(",".join("?" * len(ids))), ids).fetchall()
```
**SQLAlchemy**
```python
# Antes: for t in Task.query.all(): User.query.get(t.user_id)
tasks = db.session.execute(
    db.select(Task).options(joinedload(Task.user), joinedload(Task.category))
).scalars().all()
# Contagens: uma query agregada em vez de .count() por status
db.session.execute(db.select(Task.status, func.count()).group_by(Task.status)).all()
```

---

## P-12 — Validação centralizada

**Antes** — a mesma validação copiada em `create` e `update`, sem checar tipo:
```python
if priority < 1 or priority > 5: ...          # TypeError se vier "alta"
if status not in ['pending', 'in_progress', 'done', 'cancelled']: ...
```
**Depois**
```python
# utils/validators.py
def validate_task_payload(data, partial=False):
    errors = []
    if not partial or "priority" in data:
        p = data.get("priority", DEFAULT_PRIORITY)
        if not isinstance(p, int) or not MIN_PRIORITY <= p <= MAX_PRIORITY:
            raise ValidationError(f"Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}")
    ...
```
E na rota: `data = request.get_json(silent=True)`; se `None` → `ValidationError("Dados inválidos")`.

---

## P-13 — Error handler centralizado

**Antes** — em todo handler:
```python
try: ...
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```
**Depois**
```python
# middlewares/error_handler.py
class AppError(Exception):
    status_code = 400
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code: self.status_code = status_code

class NotFoundError(AppError): status_code = 404

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"erro": err.message, "sucesso": False}), err.status_code

    @app.errorhandler(404)
    def handle_404(_):
        return jsonify({"erro": "Recurso não encontrado"}), 404

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        app.logger.exception("Erro não tratado")
        return jsonify({"erro": "Erro interno do servidor"}), 500
```
```js
// middlewares/errorHandler.js
module.exports = (err, req, res, next) => {
  const status = err.statusCode || 500;
  if (status >= 500) console.error(err);
  res.status(status).send(status >= 500 ? 'Erro interno' : err.message);
};
```
Mantenha o **formato** de erro que o projeto já usava (`erro` vs `error`, JSON vs texto).

---

## P-14 — Substituir APIs deprecated

```python
# Antes
from datetime import datetime
task = Task.query.get(task_id)
created_at = db.Column(db.DateTime, default=datetime.utcnow)
if type(tags) == list: ...

# Depois
from datetime import datetime, timezone
def utcnow():                              # naive UTC, compatível com dados já gravados
    return datetime.now(timezone.utc).replace(tzinfo=None)
task = db.session.get(Task, task_id)
created_at = db.Column(db.DateTime, default=utcnow)
if isinstance(tags, list): ...
```
```js
// Antes
var x = new Buffer(str);
db.get(sql, params, (err, row) => { ... })
// Depois
const x = Buffer.from(str);
const row = await dbGet(sql, params);   // util.promisify / wrapper Promise
```

---

## P-15 — Constantes nomeadas, nomes claros, código morto

**Antes**
```js
let u = req.body.usr; let e = req.body.eml; let cc = req.body.card;
let status = cc.startsWith("4") ? "PAID" : "DENIED";
```
```python
import os, sys, json, datetime   # nunca usados
if len(password) < 4: ...
```
**Depois**
```js
const APPROVED_CARD_PREFIX = '4';
const { usr: name, eml: email, pwd: password, c_id: courseId, card } = req.body; // contrato mantido
const status = card.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
```
```python
from config import MIN_PASSWORD_LENGTH
if len(password) < MIN_PASSWORD_LENGTH: ...
```
Remova imports e funções sem uso; troque serializações manuais duplicadas por `to_dict()`.

---

## P-16 — Logging estruturado

**Antes** `print("Login bem-sucedido: " + email)` / `console.log(\`Processando cartão ${cc}\`)`
**Depois**
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Login bem-sucedido usuario_id=%s", usuario["id"])   # sem PII desnecessária
```
```js
logger.info(`Processando pagamento enrollment=${enrollmentId} card=****${card.slice(-4)}`);
```

---

## Ordem de aplicação sugerida

P-02 → P-08 → P-01 → P-05 → P-09 → P-04/P-07 (estrutura) → P-06 → P-10 → P-11 → P-12 → P-13 → P-14 → P-15 → P-16
Valide (boot + endpoints) após a reestruturação (P-04/P-07) e novamente ao final.
