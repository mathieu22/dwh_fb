"""
Application Flask - Factory Pattern
"""
import os
from flask import Flask, jsonify
from flask_jwt_extended import get_jwt_identity
from flasgger import Swagger

from app.config import config
from app.extensions import db, migrate, jwt, cors, ma
from app.core.audit_mixin import set_current_user_id


# Configuration Swagger
SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "parse": True
}

SWAGGER_TEMPLATE = {
    "info": {
        "title": "Dashboard FB API",
        "description": "API REST pour la gestion des commandes, produits, stocks et utilisateurs avec historisation complète.\n\n## Changelog v1.2.0\n- Comptage des commandes par statut\n- Vérification des articles\n- Modification quantité article\n- Liste minimale des commandes\n- Historique des commandes",
        "version": "1.2.0",
        "contact": {
            "name": "Support API",
            "email": "support@example.com"
        }
    },
    "basePath": "/api-fb",
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header. Example: 'Bearer {token}'"
        }
    },
    "security": [{"Bearer": []}],
    "tags": [
        {"name": "Auth", "description": "Authentification et gestion des tokens JWT"},
        {"name": "Dashboard", "description": "KPIs et statistiques de ventes"},
        {"name": "Products", "description": "Gestion des produits/articles"},
        {"name": "Categories", "description": "Gestion des catégories"},
        {"name": "Users", "description": "Gestion des utilisateurs"},
        {"name": "Stocks", "description": "Gestion des stocks et mouvements"},
        {"name": "Orders", "description": "Gestion des commandes avec workflow complet"}
    ],
    "definitions": {
        "Error": {
            "type": "object",
            "properties": {
                "error": {"type": "string", "description": "Message d'erreur"},
                "message": {"type": "string", "description": "Description détaillée"}
            }
        },
        "OrderMinimal": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "order_number": {"type": "string"},
                "status": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"},
                "customer_name": {"type": "string"},
                "customer_phone": {"type": "string"},
                "city": {"type": "string"},
                "address": {"type": "string"},
                "desired_date": {"type": "string", "format": "date"},
                "is_paid": {"type": "boolean"},
                "payment_type": {"type": "string"},
                "payment_ref": {"type": "string"},
                "payment_sender_phone": {"type": "string"},
                "courier_name": {"type": "string"},
                "items_count": {"type": "integer"},
                "total_amount_ar": {"type": "number"}
            }
        },
        "OrderHistory": {
            "type": "object",
            "properties": {
                "at": {"type": "string", "format": "date-time"},
                "by": {"type": "string"},
                "event": {"type": "string", "enum": ["CREATED", "CONFIRMED", "PAID", "IN_PREPARATION", "IN_DELIVERY", "DELIVERED", "CANCELLED"]},
                "note": {"type": "string"}
            }
        },
        "OrderItem": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "order_id": {"type": "integer"},
                "product_id": {"type": "integer"},
                "quantity": {"type": "integer"},
                "prix_unitaire": {"type": "number"},
                "prix_total": {"type": "number"},
                "verification_status": {"type": "string", "enum": ["a_verifier", "ok"]},
                "product": {"type": "object"}
            }
        },
        "StatusCounts": {
            "type": "object",
            "properties": {
                "tous": {"type": "integer"},
                "brouillon": {"type": "integer"},
                "confirmee": {"type": "integer"},
                "payee": {"type": "integer"},
                "en_preparation": {"type": "integer"},
                "en_livraison": {"type": "integer"},
                "livree": {"type": "integer"},
                "annulee": {"type": "integer"}
            }
        }
    }
}


def create_app(config_name=None):
    """
    Factory pour créer l'application Flask.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialiser les extensions
    register_extensions(app)

    # Initialiser Swagger
    Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)

    # Enregistrer les blueprints
    register_blueprints(app)

    # Enregistrer les callbacks JWT
    register_jwt_callbacks(app)

    # Enregistrer les error handlers
    register_error_handlers(app)

    # Enregistrer les hooks
    register_hooks(app)

    return app


def register_extensions(app):
    """
    Initialise les extensions Flask.
    """
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)

    # CORS avec les origines configurées
    cors.init_app(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": False
        }
    })


def register_blueprints(app):
    """
    Enregistre les blueprints de l'API.
    """
    from app.api.v1 import api_v1
    app.register_blueprint(api_v1)

    # Route de santé
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy', 'version': '1.1.0'}), 200

    # Route racine
    @app.route('/')
    def index():
        return jsonify({
            'name': 'Dashboard FB API',
            'version': '1.1.0',
            'endpoints': {
                'health': '/health',
                'api': '/api/v1',
                'auth': '/api/v1/auth',
                'dashboard': '/api/v1/dashboard',
                'products': '/api/v1/products',
                'categories': '/api/v1/categories',
                'users': '/api/v1/users',
                'stocks': '/api/v1/stocks',
                'orders': '/api/v1/orders'
            }
        }), 200


def register_jwt_callbacks(app):
    """
    Enregistre les callbacks JWT pour la gestion des tokens.
    """
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token expiré',
            'message': 'Veuillez vous reconnecter'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'error': 'Token invalide',
            'message': str(error)
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'error': 'Token manquant',
            'message': 'Authentification requise'
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token révoqué',
            'message': 'Ce token a été révoqué'
        }), 401


def register_error_handlers(app):
    """
    Enregistre les gestionnaires d'erreurs globaux.
    """
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Requête invalide',
            'message': str(error.description) if hasattr(error, 'description') else 'Données invalides'
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Non trouvé',
            'message': 'La ressource demandée n\'existe pas'
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'error': 'Méthode non autorisée',
            'message': 'Cette méthode HTTP n\'est pas supportée pour cette route'
        }), 405

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({
            'error': 'Erreur serveur',
            'message': 'Une erreur interne est survenue'
        }), 500


def register_hooks(app):
    """
    Enregistre les hooks de requête.
    """
    @app.before_request
    def before_request():
        # Importer ici pour éviter les imports circulaires
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        from flask import request

        # Ne pas vérifier JWT pour certaines routes
        public_routes = ['/', '/health', '/api/v1/auth/login', '/api/v1/auth/refresh']
        public_prefixes = ['/apidocs', '/apispec', '/flasgger_static']

        if request.path in public_routes or request.method == 'OPTIONS':
            return

        # Routes Swagger publiques
        if any(request.path.startswith(prefix) for prefix in public_prefixes):
            return

        # Pour les autres routes, essayer de charger l'utilisateur
        try:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if user_id:
                set_current_user_id(user_id)
        except Exception:
            pass

    @app.after_request
    def after_request(response):
        # Headers de sécurité
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response


# Point d'entrée pour le développement
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
