const express = require('express');
const { asyncHandler } = require('../middlewares/errorHandler');

module.exports = function adminRoutes({ reportController, userController, requireAdmin }) {
    const router = express.Router();

    router.get('/api/admin/financial-report', requireAdmin, asyncHandler(async (req, res) => {
        res.json(await reportController.financialReport());
    }));

    router.delete('/api/users/:id', requireAdmin, asyncHandler(async (req, res) => {
        res.send(await userController.deleteUser(req.params.id));
    }));

    return router;
};
