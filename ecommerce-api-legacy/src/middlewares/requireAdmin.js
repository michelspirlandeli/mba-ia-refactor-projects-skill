const crypto = require('crypto');
const { ForbiddenError } = require('../errors/AppError');

const safeEqual = (a, b) => {
    const bufA = Buffer.from(String(a));
    const bufB = Buffer.from(String(b));
    return bufA.length === bufB.length && crypto.timingSafeEqual(bufA, bufB);
};

// Protege rotas administrativas com o header X-Admin-Token quando ADMIN_TOKEN está configurado.
// Sem ADMIN_TOKEN as rotas ficam abertas (compatibilidade com o contrato legado — apenas para dev).
const createRequireAdmin = ({ adminToken, logger }) => (req, res, next) => {
    if (!adminToken) {
        logger.warn(`Rota administrativa ${req.method} ${req.path} acessada sem ADMIN_TOKEN configurado`);
        return next();
    }
    if (!safeEqual(req.get('X-Admin-Token') || '', adminToken)) {
        return next(new ForbiddenError('Acesso administrativo negado'));
    }
    return next();
};

module.exports = { createRequireAdmin };
