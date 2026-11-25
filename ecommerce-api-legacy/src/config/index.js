// Configuração lida do ambiente. Segredos não têm default "real" no código.
const config = Object.freeze({
    port: Number(process.env.PORT) || 3000,
    dbPath: process.env.DB_PATH || ':memory:',
    // Obrigatório para usar as rotas administrativas. Vazio = rotas admin desabilitadas (403).
    adminToken: process.env.ADMIN_TOKEN || '',
    logLevel: process.env.LOG_LEVEL || 'info',
    // Dados de demonstração só fora de produção. Senha do usuário demo vem do ambiente
    // (se ausente, é gerada aleatoriamente e exibida uma vez no log do boot).
    seedDemoData: (process.env.NODE_ENV || 'development') !== 'production',
    seedUserPassword: process.env.SEED_USER_PASSWORD || '',
});

// Regras de domínio (antes "magic strings").
const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });
const APPROVED_CARD_PREFIX = '4';
const MIN_PASSWORD_LENGTH = 6;

module.exports = { config, PAYMENT_STATUS, APPROVED_CARD_PREFIX, MIN_PASSWORD_LENGTH };
