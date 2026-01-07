"""
API v1 - Blueprints
"""
from flask import Blueprint

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Import des routes après création du blueprint
from . import auth, dashboard, products, categories, users, stocks, orders, uploads
