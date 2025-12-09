"""
AuditMixin - Gestion automatique de l'historisation
Created_by, Updated_by, Created_at, Updated_at
"""
from datetime import datetime
from flask import g
from sqlalchemy import Column, Integer, DateTime, ForeignKey, event
from sqlalchemy.orm import declared_attr

from app.extensions import db


def get_current_user_id():
    """Récupère l'ID de l'utilisateur courant depuis le contexte Flask"""
    return getattr(g, 'current_user_id', None)


def set_current_user_id(user_id):
    """Définit l'ID de l'utilisateur courant dans le contexte Flask"""
    g.current_user_id = user_id


class AuditMixin:
    """
    Mixin pour l'audit automatique des entités.
    Ajoute les champs created_at, updated_at, created_by, updated_by
    avec injection automatique via events SQLAlchemy.
    """

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @declared_attr
    def created_by(cls):
        return Column(Integer, ForeignKey('users.id'), nullable=True)

    @declared_attr
    def updated_by(cls):
        return Column(Integer, ForeignKey('users.id'), nullable=True)


class SoftDeleteMixin:
    """
    Mixin pour la suppression logique (soft delete).
    Conserve l'historique en marquant les enregistrements comme supprimés.
    """
    is_deleted = Column(db.Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    @declared_attr
    def deleted_by(cls):
        return Column(Integer, ForeignKey('users.id'), nullable=True)

    def soft_delete(self):
        """Marque l'enregistrement comme supprimé"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = get_current_user_id()


def audit_listener_before_insert(mapper, connection, target):
    """Event listener pour injecter created_by et updated_by avant insertion"""
    user_id = get_current_user_id()
    if hasattr(target, 'created_by') and target.created_by is None:
        target.created_by = user_id
    if hasattr(target, 'updated_by') and target.updated_by is None:
        target.updated_by = user_id
    if hasattr(target, 'created_at') and target.created_at is None:
        target.created_at = datetime.utcnow()
    if hasattr(target, 'updated_at') and target.updated_at is None:
        target.updated_at = datetime.utcnow()


def audit_listener_before_update(mapper, connection, target):
    """Event listener pour injecter updated_by avant mise à jour"""
    user_id = get_current_user_id()
    if hasattr(target, 'updated_by'):
        target.updated_by = user_id
    if hasattr(target, 'updated_at'):
        target.updated_at = datetime.utcnow()


def register_audit_listeners(model_class):
    """Enregistre les listeners d'audit pour une classe de modèle"""
    event.listen(model_class, 'before_insert', audit_listener_before_insert)
    event.listen(model_class, 'before_update', audit_listener_before_update)
