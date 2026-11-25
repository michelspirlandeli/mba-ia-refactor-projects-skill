import hashlib
import hmac

from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from utils.helpers import utcnow

# Hashes gerados pelo werkzeug (scrypt/pbkdf2). Qualquer outro valor é MD5 legado.
MODERN_HASH_PREFIXES = ("scrypt:", "pbkdf2:")


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        # O hash da senha nunca é serializado.
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, pwd):
        self.password = generate_password_hash(pwd)

    def check_password(self, pwd):
        """Verifica a senha. Hashes MD5 legados são aceitos uma vez e migrados para scrypt."""
        if self.password.startswith(MODERN_HASH_PREFIXES):
            return check_password_hash(self.password, pwd)
        legacy = hashlib.md5(pwd.encode()).hexdigest()
        if hmac.compare_digest(self.password, legacy):
            self.set_password(pwd)  # caller faz commit
            return True
        return False

    def is_admin(self):
        return self.role == 'admin'
