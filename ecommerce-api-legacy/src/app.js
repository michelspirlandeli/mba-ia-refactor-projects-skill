const express = require('express');

const { config } = require('./config');
const { createDatabase } = require('./database/connection');
const { createLogger } = require('./services/logger');
const passwordService = require('./services/passwordService');
const PaymentService = require('./services/paymentService');
const CacheService = require('./services/cacheService');
const UserModel = require('./models/userModel');
const CourseModel = require('./models/courseModel');
const EnrollmentModel = require('./models/enrollmentModel');
const PaymentModel = require('./models/paymentModel');
const AuditLogModel = require('./models/auditLogModel');
const CheckoutController = require('./controllers/checkoutController');
const ReportController = require('./controllers/reportController');
const UserController = require('./controllers/userController');
const checkoutRoutes = require('./routes/checkoutRoutes');
const adminRoutes = require('./routes/adminRoutes');
const { createRequireAdmin } = require('./middlewares/requireAdmin');
const { notFoundHandler, createErrorHandler } = require('./middlewares/errorHandler');

/**
 * Composition root: cria as dependências e as injeta camada a camada
 * (database → models → services → controllers → routes).
 */
async function createApp(appConfig = config) {
    const logger = createLogger(appConfig.logLevel);
    const db = await createDatabase({ filename: appConfig.dbPath, passwordService });

    const models = {
        userModel: new UserModel(db),
        courseModel: new CourseModel(db),
        enrollmentModel: new EnrollmentModel(db),
        paymentModel: new PaymentModel(db),
        auditLogModel: new AuditLogModel(db),
    };
    const paymentService = new PaymentService({ gatewayKey: appConfig.paymentGatewayKey, logger });
    const cacheService = new CacheService();

    const checkoutController = new CheckoutController({ db, ...models, paymentService, passwordService, cacheService, logger });
    const reportController = new ReportController(models);
    const userController = new UserController({ db, ...models, logger });
    const requireAdmin = createRequireAdmin({ adminToken: appConfig.adminToken, logger });

    const app = express();
    app.use(express.json());
    app.use(checkoutRoutes(checkoutController));
    app.use(adminRoutes({ reportController, userController, requireAdmin }));
    app.use(notFoundHandler);
    app.use(createErrorHandler(logger));

    return { app, db, logger };
}

module.exports = { createApp };
