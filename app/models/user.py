"""
Modèle User - Utilisateurs avec rôles et audit
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.core.audit_mixin import AuditMixin, SoftDeleteMixin, register_audit_listeners


class User(db.Model, AuditMixin, SoftDeleteMixin):
    """
    Modèle Utilisateur avec historisation complète.
    Rôles: simple_utilisateur, controleur, admin, livreur
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(50), nullable=False, default='simple_utilisateur')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relations
    orders = db.relationship('Order', backref='user', lazy='dynamic', foreign_keys='Order.user_id')

    def __repr__(self):
        return f'<User {self.email}>'

    def set_password(self, password):
        """Hash et stocke le mot de passe"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Vérifie le mot de passe"""
        return check_password_hash(self.password_hash, password)

    def update_last_login(self):
        """Met à jour la date de dernière connexion"""
        self.last_login = datetime.utcnow()

    @property
    def full_name(self):
        """Retourne le nom complet"""
        return f'{self.prenom} {self.nom}'

    def to_dict(self):
        """Conversion en dictionnaire (sans mot de passe)"""
        return {
            'id': self.id,
            'email': self.email,
            'nom': self.nom,
            'prenom': self.prenom,
            'telephone': self.telephone,
            'role': self.role,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# Enregistrer les listeners d'audit
register_audit_listeners(User)
