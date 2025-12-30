"""
API Products - CRUD Articles/Produits
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from . import api_v1
from app.extensions import db
from app.models.product import Product, PriceHistory
from app.models.stock import Stock
from app.schemas.product import ProductSchema, ProductCreateSchema, ProductUpdateSchema
from app.core.audit_mixin import set_current_user_id
from app.core.security import role_required, UserRoles
from app.core.utils import paginate_query
from app.services.stock_service import StockService


# Schemas instances
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)


@api_v1.route('/products', methods=['GET'])
@jwt_required()
def get_products():
    """
    Liste tous les produits avec pagination et filtres.
    ---
    tags:
      - Products
    summary: Liste des produits
    description: |
      Retourne la liste paginée de tous les produits du catalogue.
      Filtres disponibles: catégorie, statut actif/inactif, recherche par nom.
      Inclut les informations de base: nom, prix, catégorie, SKU, statut.
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: query
        type: integer
        description: Filtrer par catégorie
      - name: is_active
        in: query
        type: boolean
        description: Filtrer par statut (actif/inactif)
      - name: search
        in: query
        type: string
        description: Recherche par nom de produit
      - name: sort
        in: query
        type: string
        default: nom
        description: Champ de tri
      - name: order
        in: query
        type: string
        enum: [asc, desc]
        default: asc
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
        description: Liste paginée des produits
    """
    set_current_user_id(get_jwt_identity())

    query = Product.query.filter_by(is_deleted=False)

    # Filtres
    category_id = request.args.get('category_id', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)

    is_active = request.args.get('is_active')
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == 'true')

    search = request.args.get('search')
    if search:
        query = query.filter(Product.nom.ilike(f'%{search}%'))

    # Tri
    sort = request.args.get('sort', 'nom')
    order = request.args.get('order', 'asc')
    if hasattr(Product, sort):
        sort_col = getattr(Product, sort)
        query = query.order_by(sort_col.desc() if order == 'desc' else sort_col.asc())

    result = paginate_query(query, products_schema)

    return jsonify(result), 200


@api_v1.route('/products/<int:product_id>', methods=['GET'])
@jwt_required()
def get_product(product_id):
    """
    Récupère un produit par son ID.
    ---
    tags:
      - Products
    summary: Détail d'un produit
    description: |
      Retourne les informations complètes d'un produit.
      Inclut: nom, description, prix, catégorie, SKU, photo, statut, dates de création/modification.
    security:
      - Bearer: []
    parameters:
      - name: product_id
        in: path
        type: integer
        required: true
        description: ID du produit
    responses:
      200:
        description: Détail complet du produit
      404:
        description: Produit non trouvé
    """
    set_current_user_id(get_jwt_identity())

    product = Product.query.filter_by(id=product_id, is_deleted=False).first()

    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404

    return jsonify({'product': product.to_dict()}), 200


@api_v1.route('/products', methods=['POST'])
@jwt_required()
@role_required(UserRoles.ADMIN, UserRoles.CONTROLEUR)
def create_product():
    """
    Crée un nouveau produit.
    ---
    tags:
      - Products
    summary: Créer un produit
    description: |
      Crée un nouveau produit dans le catalogue.
      Le stock initial et le seuil d'alerte peuvent être définis à la création.
      Un SKU unique peut être attribué pour la gestion des références.
      Requiert le rôle ADMIN ou CONTROLEUR.
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
            - prix
            - category_id
          properties:
            nom:
              type: string
            prix:
              type: number
            category_id:
              type: integer
            description:
              type: string
            photo_url:
              type: string
            sku:
              type: string
            stock_initial:
              type: integer
            seuil_alerte:
              type: integer
    responses:
      201:
        description: Produit créé
      400:
        description: Données invalides
    """
    set_current_user_id(get_jwt_identity())
    schema = ProductCreateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    # Créer le produit
    product = Product(
        nom=data['nom'],
        description=data.get('description'),
        prix=data['prix'],
        photo_url=data.get('photo_url'),
        sku=data.get('sku'),
        is_active=data.get('is_active', True),
        category_id=data['category_id']
    )

    db.session.add(product)
    db.session.flush()

    # Créer le stock initial
    stock_initial = data.get('stock_initial', 0)
    seuil_alerte = data.get('seuil_alerte', 10)

    stock = Stock(
        product_id=product.id,
        quantity=stock_initial,
        seuil_alerte=seuil_alerte
    )
    db.session.add(stock)

    db.session.commit()

    return jsonify({
        'message': 'Produit créé avec succès',
        'product': product.to_dict()
    }), 201


@api_v1.route('/products/<int:product_id>', methods=['PUT'])
@jwt_required()
@role_required(UserRoles.ADMIN, UserRoles.CONTROLEUR)
def update_product(product_id):
    """
    Met à jour un produit.
    ---
    tags:
      - Products
    summary: Modifier un produit
    description: |
      Met à jour les informations d'un produit existant.
      Le SKU doit rester unique s'il est modifié.
      La catégorie doit exister et être active.
      Pour modifier le stock, utilisez les endpoints de gestion des stocks.
      Requiert le rôle ADMIN ou CONTROLEUR.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: product_id
        type: integer
        required: true
        description: ID du produit
      - in: body
        name: body
        schema:
          type: object
          properties:
            nom:
              type: string
              description: Nom du produit
            prix:
              type: number
              description: Prix unitaire
            description:
              type: string
              description: Description détaillée
            photo_url:
              type: string
              description: URL de la photo
            sku:
              type: string
              description: Code SKU unique
            category_id:
              type: integer
              description: ID de la catégorie
            is_active:
              type: boolean
              description: Statut actif/inactif
    responses:
      200:
        description: Produit mis à jour avec succès
      400:
        description: SKU déjà utilisé ou catégorie invalide
      404:
        description: Produit non trouvé
    """
    set_current_user_id(get_jwt_identity())

    product = Product.query.filter_by(id=product_id, is_deleted=False).first()

    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404

    schema = ProductUpdateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    # Vérifier le SKU s'il est modifié
    if 'sku' in data and data['sku'] != product.sku:
        existing = Product.query.filter_by(sku=data['sku'], is_deleted=False).first()
        if existing:
            return jsonify({'error': 'Ce SKU est déjà utilisé'}), 400

    # Vérifier la catégorie
    if 'category_id' in data:
        from app.models.category import Category
        category = Category.query.filter_by(id=data['category_id'], is_deleted=False).first()
        if not category:
            return jsonify({'error': 'Catégorie non trouvée'}), 400

    # Enregistrer l'historique des prix si le prix change
    if 'prix' in data and data['prix'] != float(product.prix):
        price_history = PriceHistory(
            product_id=product.id,
            ancien_prix=product.prix,
            nouveau_prix=data['prix'],
            motif=data.get('motif_changement_prix')
        )
        db.session.add(price_history)

    # Mettre à jour les champs
    for field in ['nom', 'description', 'prix', 'photo_url', 'sku', 'is_active', 'category_id']:
        if field in data:
            setattr(product, field, data[field])

    db.session.commit()

    return jsonify({
        'message': 'Produit mis à jour avec succès',
        'product': product.to_dict()
    }), 200


@api_v1.route('/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def delete_product(product_id):
    """
    Supprime un produit (soft delete).
    ---
    tags:
      - Products
    summary: Supprimer un produit
    description: |
      Supprime logiquement un produit du catalogue (soft delete).
      Le produit reste en base mais n'apparaît plus dans les listes.
      Les commandes existantes référençant ce produit sont conservées.
      Requiert le rôle ADMIN.
    security:
      - Bearer: []
    parameters:
      - name: product_id
        in: path
        type: integer
        required: true
        description: ID du produit
    responses:
      200:
        description: Produit supprimé avec succès
      403:
        description: Accès refusé (rôle ADMIN requis)
      404:
        description: Produit non trouvé
    """
    set_current_user_id(get_jwt_identity())

    product = Product.query.filter_by(id=product_id, is_deleted=False).first()

    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404

    product.soft_delete()
    db.session.commit()

    return jsonify({'message': 'Produit supprimé avec succès'}), 200


@api_v1.route('/products/<int:product_id>/toggle-status', methods=['PATCH'])
@jwt_required()
@role_required(UserRoles.ADMIN, UserRoles.CONTROLEUR)
def toggle_product_status(product_id):
    """
    Active/désactive un produit.
    ---
    tags:
      - Products
    summary: Basculer le statut actif/inactif
    description: |
      Inverse le statut actif/inactif d'un produit.
      Un produit inactif n'apparaît plus dans le catalogue public mais reste accessible en admin.
      Utile pour retirer temporairement un produit sans le supprimer.
      Requiert le rôle ADMIN ou CONTROLEUR.
    security:
      - Bearer: []
    parameters:
      - name: product_id
        in: path
        type: integer
        required: true
        description: ID du produit
    responses:
      200:
        description: Statut modifié avec succès
      403:
        description: Accès refusé
      404:
        description: Produit non trouvé
    """
    set_current_user_id(get_jwt_identity())

    product = Product.query.filter_by(id=product_id, is_deleted=False).first()

    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404

    product.is_active = not product.is_active
    db.session.commit()

    return jsonify({
        'message': f"Produit {'activé' if product.is_active else 'désactivé'}",
        'product': product.to_dict()
    }), 200


@api_v1.route('/products/<int:product_id>/price-history', methods=['GET'])
@jwt_required()
def get_product_price_history(product_id):
    """
    Récupère l'historique des prix d'un produit.
    ---
    tags:
      - Products
    summary: Historique des prix
    description: |
      Retourne l'historique complet des changements de prix d'un produit.
      Les entrées sont triées par date décroissante (plus récent en premier).
      Inclut l'ancien prix, le nouveau prix, la date du changement et le motif si fourni.
    security:
      - Bearer: []
    parameters:
      - name: product_id
        in: path
        type: integer
        required: true
        description: ID du produit
      - name: limit
        in: query
        type: integer
        default: 50
        description: Nombre maximum d'entrées à retourner
    responses:
      200:
        description: Historique des prix
      404:
        description: Produit non trouvé
    """
    set_current_user_id(get_jwt_identity())

    product = Product.query.filter_by(id=product_id, is_deleted=False).first()

    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404

    limit = request.args.get('limit', 50, type=int)

    history = PriceHistory.query.filter_by(product_id=product_id)\
        .order_by(PriceHistory.date_changement.desc())\
        .limit(limit)\
        .all()

    return jsonify({
        'product_id': product_id,
        'product_nom': product.nom,
        'prix_actuel': float(product.prix),
        'history': [h.to_dict() for h in history],
        'count': len(history)
    }), 200
