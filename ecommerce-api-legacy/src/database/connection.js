const crypto = require('crypto');
const sqlite3 = require('sqlite3');
const { PAYMENT_STATUS } = require('../config');

const SCHEMA = [
    'CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT)',
    'CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)',
    'CREATE TABLE IF NOT EXISTS enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER)',
    'CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)',
    'CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)',
];

// Integridade: um email por usuário e uma matrícula por (usuário, curso).
// Criados à parte para não impedir o boot de um banco legado que já tenha duplicatas.
const UNIQUE_INDEXES = [
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)',
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_enrollments_user_course ON enrollments(user_id, course_id)',
];

const DEMO_USER = Object.freeze({ name: 'Leonan', email: 'leonan@fullcycle.com.br' });
const DEMO_COURSES = [
    { title: 'Clean Architecture', price: 997.0 },
    { title: 'Docker', price: 497.0 },
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

async function initSchema(db, logger) {
    for (const statement of SCHEMA) {
        await db.run(statement);
    }
    for (const statement of UNIQUE_INDEXES) {
        try {
            await db.run(statement);
        } catch (err) {
            logger.warn(`Índice único não criado (dados duplicados legados): ${err.message}`);
        }
    }
}

function demoPassword(configured, logger) {
    if (configured) return configured;
    const generated = crypto.randomBytes(9).toString('base64url');
    logger.warn(`Seed de desenvolvimento: senha gerada para ${DEMO_USER.email} = ${generated} (defina SEED_USER_PASSWORD para fixar)`);
    return generated;
}

async function seed(db, { passwordService, seedUserPassword, logger }) {
    const { count } = await db.get('SELECT COUNT(*) AS count FROM courses');
    if (count > 0) return;

    const passwordHash = await passwordService.hash(demoPassword(seedUserPassword, logger));
    await db.transaction(async () => {
        const { lastID: userId } = await db.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [DEMO_USER.name, DEMO_USER.email, passwordHash]);
        const courseIds = [];
        for (const { title, price } of DEMO_COURSES) {
            const { lastID } = await db.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1)', [title, price]);
            courseIds.push(lastID);
        }
        const [firstCourse] = DEMO_COURSES;
        const { lastID: enrollmentId } = await db.run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [userId, courseIds[0]]);
        await db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, firstCourse.price, PAYMENT_STATUS.PAID]);
    });
}

async function createDatabase({ filename, passwordService, seedDemoData, seedUserPassword, logger }) {
    const db = new Database(filename);
    await initSchema(db, logger);
    if (seedDemoData) await seed(db, { passwordService, seedUserPassword, logger });
    return db;
}

module.exports = { Database, createDatabase };
