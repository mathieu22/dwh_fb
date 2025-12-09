"""
API Stocks - Gestion des stocks et mouvements
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from . import api_v1
from app.extensions import db
from app.models.stock import Stock, StockMovement, MovementType
from app.models.product import Product
from app.schemas.stock import StockSchema, StockMovementSchema, StockMovementCreateSchema, StockUpdateSchema
from app.core.audit_mixin import set_current_user_id
from app.core.security import role_required, UserRoles
from app.core.utils import paginate_query
from app.services.stock_service import StockService


# Schemas instances
stock_schema = StockSchema()
stocks_schema = StockSchema(many=True)
movement_schema = StockMovementSchema()
movements_schema = StockMovementSchema(many=True)


@api_v1.route('/stocks', methods=['GET'])
@jwt_required()
def get_stocks():
    """
    Liste tous les stocks avec pagination et filtres.
    ---
    tags:
      - Stocks
    summary: Liste des stocks
    description: |
      Retourne la liste paginée de tous les stocks avec les informations produit associées.
      Filtres disponibles: stocks faibles (sous seuil d'alerte), ruptures de stock, recherche par nom.
      Inclut: quantité actuelle, seuil d'alerte, nom et SKU du produit.
    security:
      - Bearer: []
    parameters:
      - name: low_stock
        in: query
        type: boolean
        description: Afficher uniquement les stocks faibles (quantité <= seuil d'alerte)
      - name: out_of_stock
        in: query
        type: boolean
        description: Afficher uniquement les ruptures de stock (quantité <= 0)
      - name: search
        in: query
        type: string
        description: Recherche par nom de produit
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
        description: Liste paginée des stocks avec informations produit
    """
    set_current_user_id(get_jwt_identity())

    query = db.session.query(Stock, Product).join(
        Product, Product.id == Stock.product_id
    ).filter(
        Product.is_deleted == False
    )

    # Filtres
    low_stock = request.args.get('low_stock')
    if low_stock and low_stock.lower() == 'true':
        query = query.filter(Stock.quantity <= Stock.seuil_alerte, Stock.quantity > 0)

    out_of_stock = request.args.get('out_of_stock')
    if out_of_stock and out_of_stock.lower() == 'true':
        query = query.filter(Stock.quantity <= 0)

    search = request.args.get('search')
    if search:
        query = query.filter(Product.nom.ilike(f'%{search}%'))

    # Pagination manuelle
    from app.core.utils import get_pagination_params
    page, per_page = get_pagination_params()

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    stocks_data = []
    for stock, product in items:
        data = stock.to_dict()
        data['product_nom'] = product.nom
        data['product_sku'] = product.sku
        stocks_data.append(data)

    return jsonify({
        'items': stocks_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'has_next': page * per_page < total,
            'has_prev': page > 1
        }
    }), 200


@api_v1.route('/stocks/<int:product_id>', methods=['GET'])
@jwt_required()
def get_stock(product_id):
    """
    Récupère le stock d'un produit.
    ---
    tags:
      - Stocks
    summary: Stock d'un produit
    description: |
      Retourne les informations de stock d'un produit spécifique.
      Si aucun stock n'existe pour ce produit, un stock vide est créé automatiquement.
      Inclut: quantité actuelle, seuil d'alerte, nom du produit.
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
        description: Informations de stock du produit
      404:
        description: Produit non trouvé
    """
    set_current_user_id(get_jwt_identity())

    product = Product.query.filter_by(id=product_id, is_deleted=False).first()
    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404

    stock = Stock.query.filter_by(product_id=product_id).first()

    if not stock:
        # Créer un stock vide si n'existe pas
        stock = Stock(product_id=product_id, quantity=0)
        db.session.add(stock)
        db.session.commit()

    data = stock.to_dict()
    data['product_nom'] = product.nom

    return jsonify({'stock': data}), 200


@api_v1.route('/stocks/<int:product_id>', methods=['PUT'])
@jwt_required()
@role_required(UserRoles.ADMIN, UserRoles.CONTROLEUR)
def update_stock_settings(product_id):
    """
    Met à jour les paramètres de stock (seuil d'alerte).
    ---
    tags:
      - Stocks
    summary: Modifier le seuil d'alerte
    description: |
      Met à jour le seuil d'alerte d'un stock produit.
      Le seuil d'alerte définit la quantité minimale avant déclenchement d'une alerte.
      Quand le stock descend sous ce seuil, le produit apparaît dans les alertes.
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
            seuil_alerte:
              type: integer
              description: Nouveau seuil d'alerte (quantité minimale)
    responses:
      200:
        description: Seuil d'alerte mis à jour
      404:
        description: Stock non trouvé
    """
    set_current_user_id(get_jwt_identity())

    stock = Stock.query.filter_by(product_id=product_id).first()

    if not stock:
        return jsonify({'error': 'Stock non trouvé'}), 404

    schema = StockUpdateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    if 'seuil_alerte' in data:
        stock.seuil_alerte = data['seuil_alerte']

    db.session.commit()

    return jsonify({
        'message': 'Paramètres de stock mis à jour',
        'stock': stock.to_dict()
    }), 200


@api_v1.route('/stocks/movements', methods=['GET'])
@jwt_required()
def get_movements():
    """
    Liste tous les mouvements de stock avec pagination.
    ---
    tags:
      - Stocks
    summary: Historique des mouvements
    description: |
      Retourne l'historique paginé de tous les mouvements de stock.
      Filtres disponibles: par produit, par type de mouvement.
      Triés par date décroissante (plus récents en premier).
      Types: entree, sortie, ajustement.
    security:
      - Bearer: []
    parameters:
      - name: product_id
        in: query
        type: integer
        description: Filtrer par produit
      - name: type
        in: query
        type: string
        enum: [entree, sortie, ajustement]
        description: Filtrer par type de mouvement
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
        description: Liste paginée des mouvements de stock
    """
    set_current_user_id(get_jwt_identity())

    query = StockMovement.query

    # Filtres
    product_id = request.args.get('product_id', type=int)
    if product_id:
        query = query.filter_by(product_id=product_id)

    movement_type = request.args.get('type')
    if movement_type and movement_type in [mt.value for mt in MovementType]:
        query = query.filter_by(movement_type=movement_type)

    # Tri par date décroissante
    query = query.order_by(StockMovement.created_at.desc())

    result = paginate_query(query, movements_schema)

    return jsonify(result), 200


@api_v1.route('/stocks/<int:product_id>/movements', methods=['GET'])
@jwt_required()
def get_product_movements(product_id):
    """
    Liste les mouvements de stock d'un produit.
    ---
    tags:
      - Stocks
    summary: Historique des mouvements d'un produit
    description: |
      Retourne l'historique paginé des mouvements de stock pour un produit spécifique.
      Inclut toutes les entrées, sorties et ajustements.
      Triés par date décroissante.
      Utile pour tracer l'évolution du stock d'un article.
    security:
      - Bearer: []
    parameters:
      - name: product_id
        in: path
        type: integer
        required: true
        description: ID du produit
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
        description: Liste paginée des mouvements du produit
      404:
        description: Produit non trouvé
    """
    set_current_user_id(get_jwt_identity())

    product = Product.query.filter_by(id=product_id, is_deleted=False).first()
    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404

    query = StockMovement.query.filter_by(product_id=product_id).order_by(
        StockMovement.created_at.desc()
    )

    result = paginate_query(query, movements_schema)

    return jsonify(result), 200


@api_v1.route('/stocks/movements', methods=['POST'])
@jwt_required()
@role_required(UserRoles.ADMIN, UserRoles.CONTROLEUR)
def create_movement():
    """
    Crée un mouvement de stock (entrée/sortie/ajustement).
    ---
    tags:
      - Stocks
    summary: Créer un mouvement de stock
    description: |
      Enregistre un mouvement de stock manuel avec traçabilité complète.
      Types de mouvements:
      - entree: Réception de marchandise, augmente le stock
      - sortie: Prélèvement manuel, diminue le stock
      - ajustement: Correction d'inventaire (peut augmenter ou diminuer)
      La quantité pour un ajustement représente la nouvelle quantité totale.
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
            - product_id
            - movement_type
            - quantity
          properties:
            product_id:
              type: integer
              description: ID du produit concerné
            movement_type:
              type: string
              enum: [entree, sortie, ajustement]
              description: Type de mouvement
            quantity:
              type: integer
              description: Quantité du mouvement (ou nouvelle quantité pour ajustement)
            reference:
              type: string
              description: Référence externe (bon de livraison, etc.)
            notes:
              type: string
              description: Notes ou commentaires
    responses:
      201:
        description: Mouvement créé avec nouvelle quantité en stock
      400:
        description: Stock insuffisant pour une sortie
      404:
        description: Produit non trouvé
    """
    set_current_user_id(get_jwt_identity())
    schema = StockMovementCreateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    product = Product.query.filter_by(id=data['product_id'], is_deleted=False).first()
    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404

    try:
        movement, stock = StockService.create_movement(
            product_id=data['product_id'],
            movement_type=MovementType(data['movement_type']),
            quantity=data['quantity'],
            reference=data.get('reference'),
            notes=data.get('notes')
        )

        db.session.commit()

        return jsonify({
            'message': 'Mouvement de stock créé avec succès',
            'movement': movement.to_dict(),
            'new_quantity': stock.quantity
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_v1.route('/stocks/entry', methods=['POST'])
@jwt_required()
@role_required(UserRoles.ADMIN, UserRoles.CONTROLEUR)
def create_entry():
    """
    Raccourci pour créer une entrée de stock.
    ---
    tags:
      - Stocks
    summary: Enregistrer une entrée de stock
    description: |
      Raccourci simplifié pour enregistrer une entrée de stock (réception).
      Augmente automatiquement la quantité en stock du produit.
      Crée un mouvement de type 'entree' dans l'historique.
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
            - product_id
            - quantity
          properties:
            product_id:
              type: integer
              description: ID du produit
            quantity:
              type: integer
              description: Quantité à ajouter au stock
              minimum: 1
            reference:
              type: string
              description: Référence du bon de livraison
            notes:
              type: string
              description: Notes (fournisseur, etc.)
    responses:
      201:
        description: Entrée enregistrée avec nouvelle quantité
      400:
        description: Données invalides
      404:
        description: Produit non trouvé
    """
    set_current_user_id(get_jwt_identity())

    data = request.get_json()

    if not data.get('product_id') or not data.get('quantity'):
        return jsonify({'error': 'product_id et quantity sont requis'}), 400

    product = Product.query.filter_by(id=data['product_id'], is_deleted=False).first()
    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404

    try:
        movement, stock = StockService.add_stock(
            product_id=data['product_id'],
            quantity=data['quantity'],
            reference=data.get('reference'),
            notes=data.get('notes')
        )

        db.session.commit()

        return jsonify({
            'message': 'Entrée de stock créée avec succès',
            'movement': movement.to_dict(),
            'new_quantity': stock.quantity
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_v1.route('/stocks/exit', methods=['POST'])
@jwt_required()
@role_required(UserRoles.ADMIN, UserRoles.CONTROLEUR)
def create_exit():
    """
    Raccourci pour créer une sortie de stock.
    ---
    tags:
      - Stocks
    summary: Enregistrer une sortie de stock
    description: |
      Raccourci simplifié pour enregistrer une sortie de stock (prélèvement).
      Diminue automatiquement la quantité en stock du produit.
      La sortie échoue si le stock est insuffisant.
      Crée un mouvement de type 'sortie' dans l'historique.
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
            - product_id
            - quantity
          properties:
            product_id:
              type: integer
              description: ID du produit
            quantity:
              type: integer
              description: Quantité à retirer du stock
              minimum: 1
            reference:
              type: string
              description: Référence du bon de sortie
            notes:
              type: string
              description: Notes (motif de sortie, etc.)
    responses:
      201:
        description: Sortie enregistrée avec nouvelle quantité
      400:
        description: Stock insuffisant ou données invalides
      404:
        description: Produit non trouvé
    """
    set_current_user_id(get_jwt_identity())

    data = request.get_json()

    if not data.get('product_id') or not data.get('quantity'):
        return jsonify({'error': 'product_id et quantity sont requis'}), 400

    product = Product.query.filter_by(id=data['product_id'], is_deleted=False).first()
    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404

    try:
        movement, stock = StockService.remove_stock(
            product_id=data['product_id'],
            quantity=data['quantity'],
            reference=data.get('reference'),
            notes=data.get('notes')
        )

        db.session.commit()

        return jsonify({
            'message': 'Sortie de stock créée avec succès',
            'movement': movement.to_dict(),
            'new_quantity': stock.quantity
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_v1.route('/stocks/alerts', methods=['GET'])
@jwt_required()
def get_stock_alerts():
    """
    Récupère les alertes de stock (ruptures et faibles).
    ---
    tags:
      - Stocks
    summary: Alertes de stock
    description: |
      Retourne les produits nécessitant une attention urgente:
      - low_stock: Produits avec quantité > 0 mais <= seuil d'alerte (à commander)
      - out_of_stock: Produits avec quantité <= 0 (rupture de stock)
      Utile pour le tableau de bord et les notifications de réapprovisionnement.
    security:
      - Bearer: []
    responses:
      200:
        description: Listes des produits en alerte et en rupture
    """
    set_current_user_id(get_jwt_identity())

    low_stocks = StockService.get_low_stock_products()
    out_of_stock = StockService.get_out_of_stock_products()

    return jsonify({
        'low_stock': [
            {
                'product_id': p.id,
                'product_nom': p.nom,
                'quantity': s.quantity,
                'seuil_alerte': s.seuil_alerte
            }
            for p, s in low_stocks if s.quantity > 0
        ],
        'out_of_stock': [
            {
                'product_id': p.id,
                'product_nom': p.nom,
                'quantity': s.quantity
            }
            for p, s in out_of_stock
        ]
    }), 200
