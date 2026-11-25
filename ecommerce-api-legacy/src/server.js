const { config } = require('./config');
const { createApp } = require('./app');

createApp(config)
    .then(({ app, db, logger }) => {
        const server = app.listen(config.port, () => logger.info(`LMS API rodando na porta ${config.port}`));

        // Encerramento limpo: para de aceitar conexões e fecha o banco.
        const shutdown = (signal) => {
            logger.info(`${signal} recebido, encerrando...`);
            server.close(() => {
                db.close()
                    .catch((err) => logger.error(`Erro ao fechar o banco: ${err.message}`))
                    .finally(() => process.exit(0));
            });
        };
        process.on('SIGTERM', () => shutdown('SIGTERM'));
        process.on('SIGINT', () => shutdown('SIGINT'));
    })
    .catch((err) => {
        console.error('Falha ao iniciar a aplicação:', err);
        process.exit(1);
    });
