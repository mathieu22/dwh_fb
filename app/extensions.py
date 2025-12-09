"""
Extensions Flask - Initialisation centralisée
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_marshmallow import Marshmallow

# Database
db = SQLAlchemy()

# Migrations
migrate = Migrate()

# JWT Authentication
jwt = JWTManager()

# CORS
cors = CORS()

# Marshmallow pour la sérialisation
ma = Marshmallow()
