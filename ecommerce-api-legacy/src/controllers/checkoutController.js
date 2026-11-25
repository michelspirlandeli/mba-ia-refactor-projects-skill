const { PAYMENT_STATUS, MIN_PASSWORD_LENGTH } = require('../config');
const {
    ValidationError, NotFoundError, PaymentDeniedError, UnauthorizedError, ConflictError,
} = require('../errors/AppError');

const EMAIL_REGEX = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const CARD_REGEX = /^\d+$/;
const MAX_TEXT_LENGTH = 200;

const isText = (value) => typeof value === 'string' && value.trim() !== '' && value.length <= MAX_TEXT_LENGTH;
const isUniqueViolation = (err) => err && err.code === 'SQLITE_CONSTRAINT';

class CheckoutController {
    constructor({ db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentService, passwordService, logger }) {
        Object.assign(this, { db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentService, passwordService, logger });
    }

    // Validação de presença E de tipo: entradas com tipo errado viram 400 (antes: gravadas como "[object Object]" ou 500).
    static validate({ name, email, password, courseId, card }) {
        if (!name || !email || !courseId || !card) throw new ValidationError('Bad Request');
        if (!isText(name)) throw new ValidationError('Nome inválido');
        if (typeof email !== 'string' || !EMAIL_REGEX.test(email)) throw new ValidationError('Email inválido');
        if (password !== undefined && password !== null && typeof password !== 'string') {
            throw new ValidationError('Senha inválida');
        }
        if (!Number.isInteger(Number(courseId)) || Number(courseId) <= 0 || typeof courseId === 'boolean') {
            throw new ValidationError('Curso inválido');
        }
        if (!['string', 'number'].includes(typeof card) || !CARD_REGEX.test(String(card))) {
            throw new ValidationError('Cartão inválido');
        }
    }

    // Usuário existente precisa provar a senha; novo usuário precisa de senha válida (já devolve o hash).
    async resolveUser({ email, password }) {
        const existing = await this.userModel.findCredentialsByEmail(email);
        if (existing) {
            if (!password || !(await this.passwordService.verify(password, existing.pass))) {
                throw new UnauthorizedError('Credenciais inválidas');
            }
            return { existingUserId: existing.id, passwordHash: null };
        }
        if (!password) throw new ValidationError('Senha obrigatória para novo usuário');
        if (password.length < MIN_PASSWORD_LENGTH) {
            throw new ValidationError(`Senha deve ter no mínimo ${MIN_PASSWORD_LENGTH} caracteres`);
        }
        return { existingUserId: null, passwordHash: await this.passwordService.hash(password) };
    }

    async checkout(input) {
        CheckoutController.validate(input);
        const { name, email, password, courseId, card } = input;

        const course = await this.courseModel.findActiveById(courseId);
        if (!course) throw new NotFoundError('Curso não encontrado');

        // Toda validação (credenciais, hash, duplicidade) acontece ANTES de autorizar o pagamento.
        const { existingUserId, passwordHash } = await this.resolveUser({ email, password });
        if (existingUserId && (await this.enrollmentModel.exists(existingUserId, course.id))) {
            throw new ConflictError('Usuário já matriculado neste curso');
        }

        const status = this.paymentService.authorize(card, course.price);
        if (status !== PAYMENT_STATUS.PAID) throw new PaymentDeniedError();

        let result;
        try {
            result = await this.db.transaction(async () => {
                const uid = existingUserId || (await this.userModel.create({ name, email, passwordHash }));
                const eid = await this.enrollmentModel.create(uid, course.id);
                await this.paymentModel.create(eid, course.price, status);
                await this.auditLogModel.create(`Checkout curso ${course.id} por ${uid}`);
                return { userId: uid, enrollmentId: eid };
            });
        } catch (err) {
            // Índices UNIQUE (email / user_id+course_id) barram requisições concorrentes duplicadas.
            if (isUniqueViolation(err)) throw new ConflictError('Checkout duplicado');
            throw err;
        }

        this.logger.info(`Checkout concluído enrollment=${result.enrollmentId} user=${result.userId} course=${course.id}`);
        return { msg: 'Sucesso', enrollment_id: result.enrollmentId };
    }
}

module.exports = CheckoutController;
