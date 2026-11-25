class CourseModel {
    constructor(db) {
        this.db = db;
    }

    findActiveById(id) {
        return this.db.get('SELECT * FROM courses WHERE id = ? AND active = 1', [id]);
    }

    /**
     * Linhas do relatório financeiro em UMA query (antes: 1 + C + 2·E queries).
     * Retorna uma linha por (curso, matrícula); cursos sem matrícula vêm com enrollment_id NULL.
     */
    findFinancialRows() {
        return this.db.all(`
            SELECT c.id          AS course_id,
                   c.title       AS course_title,
                   e.id          AS enrollment_id,
                   u.name        AS student_name,
                   p.amount      AS amount,
                   p.status      AS status
            FROM courses c
            LEFT JOIN enrollments e ON e.course_id = c.id
            LEFT JOIN users u       ON u.id = e.user_id
            LEFT JOIN payments p    ON p.enrollment_id = e.id
            ORDER BY c.id, e.id
        `);
    }
}

module.exports = CourseModel;
