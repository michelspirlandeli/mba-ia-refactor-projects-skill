from flask import Blueprint, jsonify

from controllers import report_controller
from middlewares.auth import current_actor

report_bp = Blueprint('reports', __name__)


@report_bp.route('/reports/summary', methods=['GET'])
def summary_report():
    return jsonify(report_controller.summary_report(current_actor())), 200


@report_bp.route('/reports/user/<int:user_id>', methods=['GET'])
def user_report(user_id):
    return jsonify(report_controller.user_report(user_id, current_actor())), 200
