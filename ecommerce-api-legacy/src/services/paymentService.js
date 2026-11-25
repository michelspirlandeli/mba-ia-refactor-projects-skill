const { PAYMENT_STATUS, APPROVED_CARD_PREFIX } = require('../config');

const maskCard = (card) => `****${String(card).slice(-4)}`;

// Gateway simulado: aprova cartões que começam com APPROVED_CARD_PREFIX.
class PaymentService {
    constructor({ logger }) {
        this.logger = logger;
    }

    authorize(card, amount) {
        const status = String(card).startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
        // Nunca logar o cartão completo.
        this.logger.info(`Pagamento ${status} card=${maskCard(card)} amount=${amount}`);
        return status;
    }
}

module.exports = PaymentService;
