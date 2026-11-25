// Configuração lida do ambiente. Segredos não têm default "real" no código.
const config = Object.freeze({
    port: Number(process.env.PORT) || 3000,
    dbPath: process.env.DB_PATH || ':memory:',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
    adminToken: process.env.ADMIN_TOKEN || '',
    logLevel: process.env.LOG_LEVEL || 'info',
});

// Regras de domínio (antes "magic strings").
const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });
const APPROVED_CARD_PREFIX = '4';

module.exports = { config, PAYMENT_STATUS, APPROVED_CARD_PREFIX };
