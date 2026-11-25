from flask import Blueprint

from config import API_VERSION
from utils.helpers import utcnow

system_bp = Blueprint('system', __name__)


@system_bp.route('/health')
def health():
    return {'status': 'ok', 'timestamp': str(utcnow())}


@system_bp.route('/')
def index():
    return {'message': 'Task Manager API', 'version': API_VERSION}
