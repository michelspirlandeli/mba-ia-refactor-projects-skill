const express = require('express');
const { asyncHandler } = require('../middlewares/errorHandler');

// View/rota: traduz o contrato HTTP (campos usr, eml, pwd, c_id, card) para o controller.
module.exports = function checkoutRoutes(checkoutController) {
    const router = express.Router();

    router.post('/api/checkout', asyncHandler(async (req, res) => {
        const { usr, eml, pwd, c_id: courseId, card } = req.body || {};
        const result = await checkoutController.checkout({ name: usr, email: eml, password: pwd, courseId, card });
        res.status(200).json(result);
    }));

    return router;
};
