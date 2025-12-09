"""
API Auth - Authentification JWT
"""
from datetime import datetime, timezone
from flask import request, jsonify, g
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from marshmallow import ValidationError

from . import api_v1
from app.extensions import db
from app.models.user import User
from app.schemas.user import LoginSchema, UserSchema
from app.core.audit_mixin import set_current_user_id


@api_v1.route('/auth/login', methods=['POST'])
def login():
    """
    Authentification utilisateur
    ---
    tags:
      - Auth
    summary: Connexion utilisateur
    description: |
      Authentifie un utilisateur avec son email et mot de passe.
      Retourne un access_token JWT (valide 1h) et un refresh_token (valide 30j).
      L'access_token doit être envoyé dans le header Authorization: Bearer <token>
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: admin@example.com
            password:
              type: string
              example: admin123
    responses:
      200:
        description: Connexion réussie
        schema:
          type: object
          properties:
            access_token:
              type: string
            refresh_token:
              type: string
            token_type:
              type: string
            user:
              type: object
      401:
        description: Email ou mot de passe incorrect
      403:
        description: Compte désactivé
    """
    schema = LoginSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    user = User.query.filter_by(email=data['email'], is_deleted=False).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Email ou mot de passe incorrect'}), 401

    if not user.is_active:
        return jsonify({'error': 'Compte désactivé'}), 403

    # Mettre à jour la dernière connexion
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    # Créer les tokens avec les claims personnalisés
    additional_claims = {
        'role': user.role,
        'email': user.email,
        'nom': user.full_name
    }

    access_token = create_access_token(
        identity=user.id,
        additional_claims=additional_claims
    )
    refresh_token = create_refresh_token(
        identity=user.id,
        additional_claims=additional_claims
    )

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'user': UserSchema().dump(user)
    }), 200


@api_v1.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Rafraîchir le token d'accès
    ---
    tags:
      - Auth
    summary: Renouveler le token d'accès
    description: |
      Génère un nouveau access_token à partir du refresh_token.
      Utilisez cette route quand l'access_token expire (erreur 401).
      Le refresh_token doit être envoyé dans le header Authorization: Bearer <refresh_token>
    security:
      - Bearer: []
    responses:
      200:
        description: Token rafraîchi
        schema:
          type: object
          properties:
            access_token:
              type: string
            token_type:
              type: string
      401:
        description: Token invalide ou utilisateur inactif
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or not user.is_active:
        return jsonify({'error': 'Utilisateur invalide ou inactif'}), 401

    additional_claims = {
        'role': user.role,
        'email': user.email,
        'nom': user.full_name
    }

    access_token = create_access_token(
        identity=user_id,
        additional_claims=additional_claims
    )

    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer'
    }), 200


@api_v1.route('/auth/me', methods=['GET'])
@jwt_required()
def me():
    """
    Récupère le profil de l'utilisateur connecté
    ---
    tags:
      - Auth
    summary: Profil utilisateur courant
    description: |
      Retourne les informations complètes de l'utilisateur authentifié.
      Inclut: id, email, nom, prénom, rôle, téléphone, date de création et dernière connexion.
    security:
      - Bearer: []
    responses:
      200:
        description: Profil utilisateur complet
        schema:
          type: object
          properties:
            user:
              type: object
              properties:
                id:
                  type: integer
                email:
                  type: string
                nom:
                  type: string
                prenom:
                  type: string
                role:
                  type: string
      404:
        description: Utilisateur non trouvé
    """
    user_id = get_jwt_identity()
    set_current_user_id(user_id)

    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    return jsonify({
        'user': UserSchema().dump(user)
    }), 200


@api_v1.route('/auth/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Changer le mot de passe
    ---
    tags:
      - Auth
    summary: Modifier le mot de passe
    description: |
      Permet à l'utilisateur connecté de changer son mot de passe.
      Le mot de passe actuel doit être fourni pour validation.
      Le nouveau mot de passe doit contenir au moins 6 caractères.
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - current_password
            - new_password
          properties:
            current_password:
              type: string
            new_password:
              type: string
              minLength: 6
    responses:
      200:
        description: Mot de passe modifié
      400:
        description: Données invalides ou mot de passe incorrect
      404:
        description: Utilisateur non trouvé
    """
    user_id = get_jwt_identity()
    set_current_user_id(user_id)

    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    data = request.get_json()

    if not data.get('current_password') or not data.get('new_password'):
        return jsonify({'error': 'Les deux mots de passe sont requis'}), 400

    if not user.check_password(data['current_password']):
        return jsonify({'error': 'Mot de passe actuel incorrect'}), 400

    if len(data['new_password']) < 6:
        return jsonify({'error': 'Le nouveau mot de passe doit faire au moins 6 caractères'}), 400

    user.set_password(data['new_password'])
    db.session.commit()

    return jsonify({'message': 'Mot de passe modifié avec succès'}), 200
