const crypto = require('crypto');
const { ForbiddenError } = require('../errors/AppError');

const safeEqual = (a, b) => {
    const bufA = Buffer.from(String(a));
    const bufB = Buffer.from(String(b));
    return bufA.length === bufB.length && crypto.timingSafeEqual(bufA, bufB);
};

// Protege rotas administrativas com o header X-Admin-Token.
// Fail-closed: sem ADMIN_TOKEN configurado as rotas admin ficam desabilitadas (403).
const createRequireAdmin = ({ adminToken, logger }) => (req, res, next) => {
    if (!adminToken) {
        logger.warn(`Rota administrativa ${req.method} ${req.path} bloqueada: ADMIN_TOKEN não configurado`);
        return next(new ForbiddenError('Rotas administrativas desabilitadas: configure ADMIN_TOKEN'));
    }
    if (!safeEqual(req.get('X-Admin-Token') || '', adminToken)) {
        return next(new ForbiddenError('Acesso administrativo negado'));
    }
    return next();
};

module.exports = { createRequireAdmin };
