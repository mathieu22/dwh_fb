"""
API Users - CRUD Utilisateurs
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from . import api_v1
from app.extensions import db
from app.models.user import User
from app.schemas.user import UserSchema, UserCreateSchema, UserUpdateSchema
from app.core.audit_mixin import set_current_user_id
from app.core.security import role_required, UserRoles
from app.core.utils import paginate_query


# Schemas instances
user_schema = UserSchema()
users_schema = UserSchema(many=True)


@api_v1.route('/users', methods=['GET'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def get_users():
    """
    Liste tous les utilisateurs avec pagination et filtres.
    ---
    tags:
      - Users
    summary: Liste des utilisateurs
    description: |
      Retourne la liste paginée de tous les utilisateurs du système.
      Filtres disponibles: rôle, statut actif/inactif, recherche par nom/prénom/email.
      Les utilisateurs sont triés par nom puis prénom.
      Requiert le rôle ADMIN.
    security:
      - Bearer: []
    parameters:
      - name: role
        in: query
        type: string
        enum: [admin, controleur, livreur, simple_utilisateur]
        description: Filtrer par rôle
      - name: is_active
        in: query
        type: boolean
        description: Filtrer par statut actif/inactif
      - name: search
        in: query
        type: string
        description: Recherche sur nom, prénom ou email
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: Liste paginée des utilisateurs
      403:
        description: Accès refusé (rôle ADMIN requis)
    """
    set_current_user_id(get_jwt_identity())

    query = User.query.filter_by(is_deleted=False)

    # Filtres
    role = request.args.get('role')
    if role and role in UserRoles.ALL_ROLES:
        query = query.filter_by(role=role)

    is_active = request.args.get('is_active')
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == 'true')

    search = request.args.get('search')
    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            db.or_(
                User.nom.ilike(search_filter),
                User.prenom.ilike(search_filter),
                User.email.ilike(search_filter)
            )
        )

    # Tri
    query = query.order_by(User.nom.asc(), User.prenom.asc())

    result = paginate_query(query, users_schema)

    return jsonify(result), 200


@api_v1.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def get_user(user_id):
    """
    Récupère un utilisateur par son ID.
    ---
    tags:
      - Users
    summary: Détail d'un utilisateur
    description: |
      Retourne les informations complètes d'un utilisateur.
      Inclut: email, nom, prénom, téléphone, rôle, statut, dates de création et dernière connexion.
      Le mot de passe n'est jamais retourné.
      Requiert le rôle ADMIN.
    security:
      - Bearer: []
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID de l'utilisateur
    responses:
      200:
        description: Détail de l'utilisateur
      403:
        description: Accès refusé
      404:
        description: Utilisateur non trouvé
    """
    set_current_user_id(get_jwt_identity())

    user = User.query.filter_by(id=user_id, is_deleted=False).first()

    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    return jsonify({'user': user_schema.dump(user)}), 200


@api_v1.route('/users', methods=['POST'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def create_user():
    """
    Crée un nouvel utilisateur.
    ---
    tags:
      - Users
    summary: Créer un utilisateur
    description: |
      Crée un nouveau compte utilisateur dans le système.
      L'email doit être unique.
      Rôles disponibles: admin, controleur, livreur, simple_utilisateur.
      Le mot de passe est hashé automatiquement avant stockage.
      Requiert le rôle ADMIN.
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
            - nom
            - prenom
          properties:
            email:
              type: string
            password:
              type: string
            nom:
              type: string
            prenom:
              type: string
            telephone:
              type: string
            role:
              type: string
              enum: [admin, controleur, livreur, simple_utilisateur]
            is_active:
              type: boolean
    responses:
      201:
        description: Utilisateur créé
      400:
        description: Données invalides
    """
    set_current_user_id(get_jwt_identity())
    schema = UserCreateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    user = User(
        email=data['email'],
        nom=data['nom'],
        prenom=data['prenom'],
        telephone=data.get('telephone'),
        role=data.get('role', 'simple_utilisateur'),
        is_active=data.get('is_active', True)
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': 'Utilisateur créé avec succès',
        'user': user_schema.dump(user)
    }), 201


@api_v1.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def update_user(user_id):
    """
    Met à jour un utilisateur.
    ---
    tags:
      - Users
    summary: Modifier un utilisateur
    description: |
      Met à jour les informations d'un utilisateur existant.
      L'email doit rester unique s'il est modifié.
      Le mot de passe n'est mis à jour que s'il est fourni (optionnel).
      Pour désactiver un utilisateur, utilisez plutôt toggle-status.
      Requiert le rôle ADMIN.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: ID de l'utilisateur
      - in: body
        name: body
        schema:
          type: object
          properties:
            email:
              type: string
              description: Adresse email (doit être unique)
            password:
              type: string
              description: Nouveau mot de passe (optionnel)
            nom:
              type: string
              description: Nom de famille
            prenom:
              type: string
              description: Prénom
            telephone:
              type: string
              description: Numéro de téléphone
            role:
              type: string
              description: Rôle (admin, controleur, livreur, simple_utilisateur)
            is_active:
              type: boolean
              description: Statut actif/inactif
    responses:
      200:
        description: Utilisateur mis à jour avec succès
      400:
        description: Email déjà utilisé
      404:
        description: Utilisateur non trouvé
    """
    set_current_user_id(get_jwt_identity())

    user = User.query.filter_by(id=user_id, is_deleted=False).first()

    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    schema = UserUpdateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    # Vérifier l'email s'il est modifié
    if 'email' in data and data['email'] != user.email:
        existing = User.query.filter_by(email=data['email'], is_deleted=False).first()
        if existing:
            return jsonify({'error': 'Cet email est déjà utilisé'}), 400

    # Mettre à jour les champs
    for field in ['email', 'nom', 'prenom', 'telephone', 'role', 'is_active']:
        if field in data:
            setattr(user, field, data[field])

    # Mettre à jour le mot de passe si fourni
    if 'password' in data:
        user.set_password(data['password'])

    db.session.commit()

    return jsonify({
        'message': 'Utilisateur mis à jour avec succès',
        'user': user_schema.dump(user)
    }), 200


@api_v1.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def delete_user(user_id):
    """
    Supprime un utilisateur (soft delete).
    ---
    tags:
      - Users
    summary: Supprimer un utilisateur
    description: |
      Supprime logiquement un utilisateur (soft delete).
      L'utilisateur ne peut plus se connecter mais ses données sont conservées.
      ATTENTION: Vous ne pouvez pas supprimer votre propre compte.
      Requiert le rôle ADMIN.
    security:
      - Bearer: []
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID de l'utilisateur
    responses:
      200:
        description: Utilisateur supprimé avec succès
      400:
        description: Impossible de supprimer son propre compte
      403:
        description: Accès refusé
      404:
        description: Utilisateur non trouvé
    """
    current_user_id = get_jwt_identity()
    set_current_user_id(current_user_id)

    if user_id == current_user_id:
        return jsonify({'error': 'Vous ne pouvez pas supprimer votre propre compte'}), 400

    user = User.query.filter_by(id=user_id, is_deleted=False).first()

    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    user.soft_delete()
    db.session.commit()

    return jsonify({'message': 'Utilisateur supprimé avec succès'}), 200


@api_v1.route('/users/<int:user_id>/toggle-status', methods=['PATCH'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def toggle_user_status(user_id):
    """
    Active/désactive un utilisateur.
    ---
    tags:
      - Users
    summary: Basculer le statut actif/inactif
    description: |
      Inverse le statut actif/inactif d'un utilisateur.
      Un utilisateur désactivé ne peut plus se connecter mais son compte est conservé.
      Utile pour suspendre temporairement un accès sans supprimer le compte.
      ATTENTION: Vous ne pouvez pas désactiver votre propre compte.
      Requiert le rôle ADMIN.
    security:
      - Bearer: []
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID de l'utilisateur
    responses:
      200:
        description: Statut modifié avec succès
      400:
        description: Impossible de désactiver son propre compte
      403:
        description: Accès refusé
      404:
        description: Utilisateur non trouvé
    """
    current_user_id = get_jwt_identity()
    set_current_user_id(current_user_id)

    if user_id == current_user_id:
        return jsonify({'error': 'Vous ne pouvez pas désactiver votre propre compte'}), 400

    user = User.query.filter_by(id=user_id, is_deleted=False).first()

    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    user.is_active = not user.is_active
    db.session.commit()

    return jsonify({
        'message': f"Utilisateur {'activé' if user.is_active else 'désactivé'}",
        'user': user_schema.dump(user)
    }), 200


@api_v1.route('/users/livreurs', methods=['GET'])
@jwt_required()
def get_livreurs():
    """
    Liste les livreurs actifs (pour assignation).
    ---
    tags:
      - Users
    summary: Liste des livreurs disponibles
    description: |
      Retourne la liste des utilisateurs avec le rôle LIVREUR et actifs.
      Utilisé pour peupler les listes de sélection lors de l'assignation d'une commande.
      Accessible à tous les utilisateurs authentifiés.
    security:
      - Bearer: []
    responses:
      200:
        description: Liste des livreurs actifs
    """
    set_current_user_id(get_jwt_identity())

    livreurs = User.query.filter_by(
        role=UserRoles.LIVREUR,
        is_active=True,
        is_deleted=False
    ).order_by(User.nom.asc()).all()

    return jsonify({
        'livreurs': [user_schema.dump(l) for l in livreurs]
    }), 200


@api_v1.route('/users/roles', methods=['GET'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def get_roles():
    """
    Liste les rôles disponibles.
    ---
    tags:
      - Users
    summary: Liste des rôles
    description: |
      Retourne la liste de tous les rôles utilisateur disponibles.
      Rôles: admin, controleur, livreur, simple_utilisateur.
      Utile pour peupler les listes déroulantes lors de la création/modification d'utilisateurs.
      Requiert le rôle ADMIN.
    security:
      - Bearer: []
    responses:
      200:
        description: Liste des rôles disponibles
    """
    return jsonify({
        'roles': UserRoles.ALL_ROLES
    }), 200
