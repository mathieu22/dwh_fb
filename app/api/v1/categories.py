"""
API Categories - CRUD Catégories
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from . import api_v1
from app.extensions import db
from app.models.category import Category
from app.schemas.category import CategorySchema, CategoryCreateSchema, CategoryUpdateSchema
from app.core.audit_mixin import set_current_user_id
from app.core.security import role_required, UserRoles
from app.core.utils import paginate_query


# Schemas instances
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)


@api_v1.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """
    Liste toutes les catégories avec pagination.
    ---
    tags:
      - Categories
    summary: Liste des catégories
    description: |
      Retourne la liste paginée de toutes les catégories du catalogue.
      Les catégories sont triées par ordre d'affichage puis par nom.
      Filtre disponible: statut actif/inactif.
    security:
      - Bearer: []
    parameters:
      - name: is_active
        in: query
        type: boolean
        description: Filtrer par statut actif/inactif
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
        description: Liste paginée des catégories
    """
    set_current_user_id(get_jwt_identity())

    query = Category.query.filter_by(is_deleted=False)

    # Filtres
    is_active = request.args.get('is_active')
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == 'true')

    # Tri par ordre puis par nom
    query = query.order_by(Category.ordre.asc(), Category.nom.asc())

    result = paginate_query(query, categories_schema)

    return jsonify(result), 200


@api_v1.route('/categories/all', methods=['GET'])
@jwt_required()
def get_all_categories():
    """
    Liste toutes les catégories actives (sans pagination, pour les selects).
    ---
    tags:
      - Categories
    summary: Toutes les catégories actives
    description: |
      Retourne la liste complète des catégories actives sans pagination.
      Optimisé pour peupler les listes déroulantes et filtres côté frontend.
      Ne retourne que les catégories actives et non supprimées.
    security:
      - Bearer: []
    responses:
      200:
        description: Liste complète des catégories actives
    """
    set_current_user_id(get_jwt_identity())

    categories = Category.query.filter_by(
        is_deleted=False,
        is_active=True
    ).order_by(Category.ordre.asc(), Category.nom.asc()).all()

    return jsonify({
        'categories': [c.to_dict() for c in categories]
    }), 200


@api_v1.route('/categories/<int:category_id>', methods=['GET'])
@jwt_required()
def get_category(category_id):
    """
    Récupère une catégorie par son ID.
    ---
    tags:
      - Categories
    summary: Détail d'une catégorie
    description: |
      Retourne les informations complètes d'une catégorie.
      Inclut: nom, description, image, ordre d'affichage, statut.
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
        description: ID de la catégorie
    responses:
      200:
        description: Détail de la catégorie
      404:
        description: Catégorie non trouvée
    """
    set_current_user_id(get_jwt_identity())

    category = Category.query.filter_by(id=category_id, is_deleted=False).first()

    if not category:
        return jsonify({'error': 'Catégorie non trouvée'}), 404

    return jsonify({'category': category.to_dict()}), 200


@api_v1.route('/categories/<int:category_id>/products', methods=['GET'])
@jwt_required()
def get_category_products(category_id):
    """
    Liste les produits d'une catégorie.
    ---
    tags:
      - Categories
    summary: Produits d'une catégorie
    description: |
      Retourne tous les produits actifs appartenant à une catégorie donnée.
      Inclut les informations de la catégorie et la liste des produits avec leurs détails.
      Seuls les produits actifs et non supprimés sont retournés.
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
        description: ID de la catégorie
    responses:
      200:
        description: Catégorie avec ses produits
      404:
        description: Catégorie non trouvée
    """
    set_current_user_id(get_jwt_identity())

    category = Category.query.filter_by(id=category_id, is_deleted=False).first()

    if not category:
        return jsonify({'error': 'Catégorie non trouvée'}), 404

    products = category.products.filter_by(is_deleted=False, is_active=True).all()

    return jsonify({
        'category': category.to_dict(),
        'products': [p.to_dict() for p in products]
    }), 200


@api_v1.route('/categories', methods=['POST'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def create_category():
    """
    Crée une nouvelle catégorie.
    ---
    tags:
      - Categories
    summary: Créer une catégorie
    description: |
      Crée une nouvelle catégorie de produits.
      Le nom doit être unique parmi les catégories actives.
      L'ordre d'affichage permet de positionner la catégorie dans les listes.
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
            - nom
          properties:
            nom:
              type: string
            description:
              type: string
            image_url:
              type: string
            ordre:
              type: integer
            is_active:
              type: boolean
    responses:
      201:
        description: Catégorie créée
      400:
        description: Données invalides
    """
    set_current_user_id(get_jwt_identity())
    schema = CategoryCreateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    category = Category(
        nom=data['nom'],
        description=data.get('description'),
        image_url=data.get('image_url'),
        ordre=data.get('ordre', 0),
        is_active=data.get('is_active', True)
    )

    db.session.add(category)
    db.session.commit()

    return jsonify({
        'message': 'Catégorie créée avec succès',
        'category': category.to_dict()
    }), 201


@api_v1.route('/categories/<int:category_id>', methods=['PUT'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def update_category(category_id):
    """
    Met à jour une catégorie.
    ---
    tags:
      - Categories
    summary: Modifier une catégorie
    description: |
      Met à jour les informations d'une catégorie existante.
      Le nom doit rester unique s'il est modifié.
      Requiert le rôle ADMIN.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: category_id
        type: integer
        required: true
        description: ID de la catégorie
      - in: body
        name: body
        schema:
          type: object
          properties:
            nom:
              type: string
              description: Nom de la catégorie
            description:
              type: string
              description: Description de la catégorie
            image_url:
              type: string
              description: URL de l'image
            ordre:
              type: integer
              description: Ordre d'affichage
            is_active:
              type: boolean
              description: Statut actif/inactif
    responses:
      200:
        description: Catégorie mise à jour avec succès
      400:
        description: Nom déjà utilisé
      404:
        description: Catégorie non trouvée
    """
    set_current_user_id(get_jwt_identity())

    category = Category.query.filter_by(id=category_id, is_deleted=False).first()

    if not category:
        return jsonify({'error': 'Catégorie non trouvée'}), 404

    schema = CategoryUpdateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    # Vérifier le nom s'il est modifié
    if 'nom' in data and data['nom'] != category.nom:
        existing = Category.query.filter_by(nom=data['nom'], is_deleted=False).first()
        if existing:
            return jsonify({'error': 'Une catégorie avec ce nom existe déjà'}), 400

    # Mettre à jour les champs
    for field in ['nom', 'description', 'image_url', 'ordre', 'is_active']:
        if field in data:
            setattr(category, field, data[field])

    db.session.commit()

    return jsonify({
        'message': 'Catégorie mise à jour avec succès',
        'category': category.to_dict()
    }), 200


@api_v1.route('/categories/<int:category_id>', methods=['DELETE'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def delete_category(category_id):
    """
    Supprime une catégorie (soft delete).
    ---
    tags:
      - Categories
    summary: Supprimer une catégorie
    description: |
      Supprime logiquement une catégorie (soft delete).
      ATTENTION: La suppression est bloquée si des produits actifs existent dans cette catégorie.
      Il faut d'abord déplacer ou supprimer les produits.
      Requiert le rôle ADMIN.
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
        description: ID de la catégorie
    responses:
      200:
        description: Catégorie supprimée avec succès
      400:
        description: Catégorie non vide (contient des produits)
      403:
        description: Accès refusé (rôle ADMIN requis)
      404:
        description: Catégorie non trouvée
    """
    set_current_user_id(get_jwt_identity())

    category = Category.query.filter_by(id=category_id, is_deleted=False).first()

    if not category:
        return jsonify({'error': 'Catégorie non trouvée'}), 404

    # Vérifier s'il y a des produits actifs
    active_products = category.products.filter_by(is_deleted=False).count()
    if active_products > 0:
        return jsonify({
            'error': f'Impossible de supprimer: {active_products} produit(s) actif(s) dans cette catégorie'
        }), 400

    category.soft_delete()
    db.session.commit()

    return jsonify({'message': 'Catégorie supprimée avec succès'}), 200


@api_v1.route('/categories/reorder', methods=['POST'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def reorder_categories():
    """
    Réordonne les catégories.
    ---
    tags:
      - Categories
    summary: Réordonner les catégories
    description: |
      Met à jour l'ordre d'affichage de plusieurs catégories en une seule requête.
      Utile pour le drag & drop dans l'interface d'administration.
      Envoyer la liste complète des catégories avec leurs nouveaux ordres.
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
            - order
          properties:
            order:
              type: array
              description: Liste des catégories avec leur nouvel ordre
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: ID de la catégorie
                  ordre:
                    type: integer
                    description: Nouvel ordre d'affichage
    responses:
      200:
        description: Ordre mis à jour avec succès
      400:
        description: Données manquantes
    """
    set_current_user_id(get_jwt_identity())

    data = request.get_json()
    if not data or 'order' not in data:
        return jsonify({'error': 'Données manquantes'}), 400

    for item in data['order']:
        category = Category.query.get(item['id'])
        if category:
            category.ordre = item['ordre']

    db.session.commit()

    return jsonify({'message': 'Ordre mis à jour avec succès'}), 200
