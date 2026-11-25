const { ValidationError, NotFoundError } = require('../errors/AppError');

class UserController {
    constructor({ db, userModel, enrollmentModel, paymentModel, logger }) {
        Object.assign(this, { db, userModel, enrollmentModel, paymentModel, logger });
    }

    async deleteUser(rawId) {
        const userId = Number(rawId);
        if (!Number.isInteger(userId) || userId <= 0) throw new ValidationError('ID inválido');

        const user = await this.userModel.findById(userId);
        if (!user) throw new NotFoundError('Usuário não encontrado');

        // Remove pagamentos e matrículas junto com o usuário (antes ficavam órfãos).
        await this.db.transaction(async () => {
            await this.paymentModel.deleteByUserId(userId);
            await this.enrollmentModel.deleteByUserId(userId);
            await this.userModel.deleteById(userId);
        });

        this.logger.info(`Usuário ${userId} removido com matrículas e pagamentos`);
        return 'Usuário deletado com suas matrículas e pagamentos.';
    }
}

module.exports = UserController;
