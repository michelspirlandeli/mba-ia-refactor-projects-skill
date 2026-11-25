const sqlite3 = require('sqlite3');

const SCHEMA = [
    'CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT)',
    'CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)',
    'CREATE TABLE IF NOT EXISTS enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER)',
    'CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)',
    'CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)',
];

/**
 * Wrapper com Promises sobre o driver sqlite3 (substitui a API de callbacks aninhados).
 * `transaction()` serializa transações para que requests concorrentes não se misturem
 * na mesma conexão.
 */
class Database {
    constructor(filename) {
        this.connection = new sqlite3.Database(filename);
        this.queue = Promise.resolve();
    }

    run(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.connection.run(sql, params, function onRun(err) {
                if (err) return reject(err);
                resolve({ lastID: this.lastID, changes: this.changes });
            });
        });
    }

    get(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.connection.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
        });
    }

    all(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.connection.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
        });
    }

    transaction(work) {
        const execute = async () => {
            await this.run('BEGIN');
            try {
                const result = await work();
                await this.run('COMMIT');
                return result;
            } catch (err) {
                await this.run('ROLLBACK');
                throw err;
            }
        };
        const result = this.queue.then(execute, execute);
        this.queue = result.catch(() => {});
        return result;
    }

    close() {
        return new Promise((resolve, reject) => this.connection.close((err) => (err ? reject(err) : resolve())));
    }
}

async function initSchema(db) {
    for (const statement of SCHEMA) {
        await db.run(statement);
    }
}

async function seed(db, passwordService) {
    const { count } = await db.get('SELECT COUNT(*) AS count FROM courses');
    if (count > 0) return;

    await db.transaction(async () => {
        const passwordHash = await passwordService.hash('123');
        await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', ['Leonan', 'leonan@fullcycle.com.br', passwordHash]);
        await db.run('INSERT INTO courses (title, price, active) VALUES (?, ?, ?), (?, ?, ?)', ['Clean Architecture', 997.0, 1, 'Docker', 497.0, 1]);
        await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [1, 1]);
        await db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [1, 997.0, 'PAID']);
    });
}

async function createDatabase({ filename, passwordService }) {
    const db = new Database(filename);
    await initSchema(db);
    await seed(db, passwordService);
    return db;
}

module.exports = { Database, createDatabase };
