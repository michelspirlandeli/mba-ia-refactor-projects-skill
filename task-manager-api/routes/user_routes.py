from flask import Blueprint, current_app, jsonify, request

from controllers import user_controller
from middlewares.auth import current_actor

user_bp = Blueprint('users', __name__)


@user_bp.route('/users', methods=['GET'])
def get_users():
    return jsonify(user_controller.list_users()), 200


@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    return jsonify(user_controller.get_user(user_id)), 200


@user_bp.route('/users', methods=['POST'])
def create_user():
    return jsonify(user_controller.create_user(request.get_json(silent=True), current_actor())), 201


@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    return jsonify(user_controller.update_user(user_id, request.get_json(silent=True), current_actor())), 200


@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user_controller.delete_user(user_id, current_actor())
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200


@user_bp.route('/users/<int:user_id>/tasks', methods=['GET'])
def get_user_tasks(user_id):
    return jsonify(user_controller.get_user_tasks(user_id)), 200


@user_bp.route('/login', methods=['POST'])
def login():
    result = user_controller.login(
        request.get_json(silent=True),
        client_key=request.remote_addr,
        throttle=current_app.extensions['login_throttle'],
        token_service=current_app.extensions['token_service'],
    )
    return jsonify(result), 200
