const { AppError, NotFoundError } = require('../errors/AppError');

// Envolve handlers async para que rejeições cheguem ao error handler (Express 4 não faz isso sozinho).
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

const notFoundHandler = (req, res, next) => next(new NotFoundError(`Cannot ${req.method} ${req.path}`));

const isClientError = (status) => Number.isInteger(status) && status >= 400 && status < 500;

// Error handler central. Mantém o formato de erro do projeto original (texto puro).
const createErrorHandler = (logger) => (err, req, res, next) => {
    if (res.headersSent) return next(err);

    if (err instanceof AppError) {
        return res.status(err.statusCode).send(err.message);
    }
    if (err.type === 'entity.parse.failed') {
        return res.status(400).send('Bad Request');
    }
    // Demais erros 4xx do body-parser (413 payload grande, 415 charset inválido...) são erro do cliente.
    if (isClientError(err.status) && err.expose) {
        logger.warn(`Requisição rejeitada ${req.method} ${req.path}: ${err.status} ${err.message}`);
        return res.status(err.status).send(err.message);
    }

    logger.error(`Erro não tratado em ${req.method} ${req.path}: ${err.stack || err}`);
    return res.status(500).send('Erro interno');
};

module.exports = { asyncHandler, notFoundHandler, createErrorHandler };
