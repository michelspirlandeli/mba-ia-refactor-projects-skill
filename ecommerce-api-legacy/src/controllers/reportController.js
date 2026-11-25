const { PAYMENT_STATUS } = require('../config');

class ReportController {
    constructor({ courseModel }) {
        this.courseModel = courseModel;
    }

    async financialReport() {
        const rows = await this.courseModel.findFinancialRows();
        const report = new Map();

        for (const row of rows) {
            if (!report.has(row.course_id)) {
                report.set(row.course_id, { course: row.course_title, revenue: 0, students: [] });
            }
            if (row.enrollment_id === null) continue;

            const courseData = report.get(row.course_id);
            if (row.status === PAYMENT_STATUS.PAID) courseData.revenue += row.amount;
            courseData.students.push({
                student: row.student_name ?? 'Unknown',
                paid: row.amount ?? 0,
            });
        }

        return [...report.values()];
    }
}

module.exports = ReportController;
