"""
Sécurité - JWT et gestion des rôles
"""
from functools import wraps
from flask import jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt

from app.core.audit_mixin import set_current_user_id


class UserRoles:
    """Constantes pour les rôles utilisateurs"""
    SIMPLE_UTILISATEUR = 'simple_utilisateur'
    CONTROLEUR = 'controleur'
    ADMIN = 'admin'
    LIVREUR = 'livreur'

    ALL_ROLES = [SIMPLE_UTILISATEUR, CONTROLEUR, ADMIN, LIVREUR]


def get_current_user():
    """Récupère l'utilisateur courant depuis le contexte"""
    return getattr(g, 'current_user', None)


def role_required(*roles):
    """
    Décorateur pour vérifier les rôles requis.
    Usage: @role_required('admin', 'controleur')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('role', None)

            if user_role not in roles:
                return jsonify({
                    'error': 'Accès refusé',
                    'message': f'Rôle requis: {", ".join(roles)}'
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def jwt_user_loader(fn):
    """
    Décorateur pour charger automatiquement l'utilisateur depuis le JWT
    et injecter son ID dans le contexte pour l'audit.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        set_current_user_id(user_id)

        # Charger l'utilisateur dans le contexte
        from app.models.user import User
        user = User.query.get(user_id)
        g.current_user = user

        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    """Décorateur raccourci pour admin uniquement"""
    @wraps(fn)
    @role_required(UserRoles.ADMIN)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper


def controleur_or_admin_required(fn):
    """Décorateur raccourci pour controleur ou admin"""
    @wraps(fn)
    @role_required(UserRoles.CONTROLEUR, UserRoles.ADMIN)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper
