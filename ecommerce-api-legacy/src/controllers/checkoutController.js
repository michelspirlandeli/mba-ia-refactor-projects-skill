const { PAYMENT_STATUS } = require('../config');
const { ValidationError, NotFoundError, PaymentDeniedError } = require('../errors/AppError');

const EMAIL_REGEX = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const CARD_REGEX = /^\d+$/;

class CheckoutController {
    constructor({ db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentService, passwordService, cacheService, logger }) {
        Object.assign(this, { db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentService, passwordService, cacheService, logger });
    }

    static validate({ name, email, courseId, card }) {
        if (!name || !email || !courseId || !card) throw new ValidationError('Bad Request');
        if (!EMAIL_REGEX.test(String(email))) throw new ValidationError('Email inválido');
        if (!Number.isInteger(Number(courseId)) || Number(courseId) <= 0) throw new ValidationError('Curso inválido');
        if (!CARD_REGEX.test(String(card))) throw new ValidationError('Cartão inválido');
    }

    async checkout(input) {
        CheckoutController.validate(input);
        const { name, email, password, courseId, card } = input;

        const course = await this.courseModel.findActiveById(courseId);
        if (!course) throw new NotFoundError('Curso não encontrado');

        const existingUser = await this.userModel.findByEmail(email);
        if (!existingUser && !password) {
            // Antes era criada uma conta com a senha fixa "123456".
            throw new ValidationError('Senha obrigatória para novo usuário');
        }

        // Pagamento é decidido ANTES de qualquer escrita (antes o usuário era criado mesmo com pagamento recusado).
        const status = this.paymentService.authorize(card, course.price);
        if (status !== PAYMENT_STATUS.PAID) throw new PaymentDeniedError();

        const passwordHash = existingUser ? null : await this.passwordService.hash(password);

        const { userId, enrollmentId } = await this.db.transaction(async () => {
            const uid = existingUser ? existingUser.id : await this.userModel.create({ name, email, passwordHash });
            const eid = await this.enrollmentModel.create(uid, course.id);
            await this.paymentModel.create(eid, course.price, status);
            await this.auditLogModel.create(`Checkout curso ${course.id} por ${uid}`);
            return { userId: uid, enrollmentId: eid };
        });

        this.cacheService.set(`last_checkout_${userId}`, course.title);
        this.logger.info(`Checkout concluído enrollment=${enrollmentId} user=${userId} course=${course.id}`);
        return { msg: 'Sucesso', enrollment_id: enrollmentId };
    }
}

module.exports = CheckoutController;
