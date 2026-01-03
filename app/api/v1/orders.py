"""
API Orders - Gestion des commandes
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from . import api_v1
from app.extensions import db
from app.models.order import Order, OrderItem, OrderStatus, ItemVerificationStatus, OrderHistory, OrderHistoryEvent
from app.schemas.order import (
    OrderSchema, OrderCreateSchema, OrderUpdateSchema,
    OrderStatusUpdateSchema, OrderItemCreateSchema,
    OrderPaymentSchema, OrderCancelSchema
)
from app.core.audit_mixin import set_current_user_id
from app.core.security import role_required, UserRoles
from app.core.utils import paginate_query
from app.services.order_service import OrderService


# Schemas instances
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)


@api_v1.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    """
    Liste toutes les commandes avec pagination et filtres.
    ---
    tags:
      - Orders
    summary: Liste des commandes
    description: |
      Retourne la liste paginée des commandes avec possibilité de filtrage.
      Filtres disponibles: statut, recherche (numéro/client/téléphone), livreur assigné.
      Tri configurable par n'importe quel champ (défaut: created_at desc).
    security:
      - Bearer: []
    parameters:
      - name: status
        in: query
        type: string
        enum: [brouillon, confirmee, en_preparation, en_livraison, livree, annulee]
        description: Filtrer par statut
      - name: search
        in: query
        type: string
        description: Recherche sur numéro, nom client ou téléphone
      - name: livreur_id
        in: query
        type: integer
        description: Filtrer par livreur assigné
      - name: sort
        in: query
        type: string
        default: created_at
        description: Champ de tri
      - name: order
        in: query
        type: string
        enum: [asc, desc]
        default: desc
        description: Ordre de tri
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
        description: Liste paginée des commandes
    """
    set_current_user_id(get_jwt_identity())

    query = Order.query.filter_by(is_deleted=False)

    # Filtres
    status = request.args.get('status')
    if status and status in [s.value for s in OrderStatus]:
        query = query.filter_by(status=status)

    search = request.args.get('search')
    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            db.or_(
                Order.numero.ilike(search_filter),
                Order.client_nom.ilike(search_filter),
                Order.client_telephone.ilike(search_filter)
            )
        )

    livreur_id = request.args.get('livreur_id', type=int)
    if livreur_id:
        query = query.filter_by(livreur_id=livreur_id)

    # Tri
    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')
    if hasattr(Order, sort):
        sort_col = getattr(Order, sort)
        query = query.order_by(sort_col.desc() if order == 'desc' else sort_col.asc())

    result = paginate_query(query, orders_schema)

    return jsonify(result), 200


@api_v1.route('/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """
    Récupère une commande par son ID.
    ---
    tags:
      - Orders
    summary: Détail d'une commande
    description: |
      Retourne les informations complètes d'une commande incluant tous ses articles.
      Inclut: informations client, statut, montant total, livreur assigné, historique.
    security:
      - Bearer: []
    parameters:
      - name: order_id
        in: path
        type: integer
        required: true
        description: ID de la commande
    responses:
      200:
        description: Détail complet de la commande avec articles
      404:
        description: Commande non trouvée
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()

    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    return jsonify({'order': order.to_dict(include_items=True)}), 200


@api_v1.route('/orders/by-numero/<string:numero>', methods=['GET'])
@jwt_required()
def get_order_by_numero(numero):
    """
    Récupère une commande par son numéro.
    ---
    tags:
      - Orders
    summary: Recherche par numéro de commande
    description: |
      Recherche une commande par son numéro unique (ex: CMD-2024-00001).
      Utile pour la recherche rapide par scan de code-barres ou saisie manuelle.
    security:
      - Bearer: []
    parameters:
      - name: numero
        in: path
        type: string
        required: true
        description: "Numéro de commande (ex: CMD-2024-00001)"
    responses:
      200:
        description: Détail complet de la commande
      404:
        description: Commande non trouvée
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(numero=numero, is_deleted=False).first()

    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    return jsonify({'order': order.to_dict(include_items=True)}), 200


@api_v1.route('/orders', methods=['POST'])
@jwt_required()
def create_order():
    """
    Crée une nouvelle commande.
    ---
    tags:
      - Orders
    summary: Créer une commande
    description: |
      Crée une nouvelle commande en statut 'brouillon'.
      La commande contient les informations client et la liste des articles.
      Un numéro unique est généré automatiquement (format: CMD-YYYY-NNNNN).
      Le stock n'est pas décrémenté à cette étape (seulement à la confirmation).
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - client_nom
            - client_telephone
            - items
          properties:
            client_nom:
              type: string
            client_telephone:
              type: string
            items:
              type: array
              items:
                type: object
                properties:
                  product_id:
                    type: integer
                  quantity:
                    type: integer
    responses:
      201:
        description: Commande créée avec succès
      400:
        description: Données invalides
    """
    user_id = get_jwt_identity()
    set_current_user_id(user_id)
    schema = OrderCreateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    try:
        order = OrderService.create_order(data, user_id=user_id)
        db.session.commit()

        return jsonify({
            'message': 'Commande créée avec succès',
            'order': order.to_dict(include_items=True)
        }), 201

    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@api_v1.route('/orders/<int:order_id>', methods=['PUT'])
@jwt_required()
def update_order(order_id):
    """
    Met à jour une commande (si en brouillon).
    ---
    tags:
      - Orders
    summary: Modifier une commande
    description: |
      Met à jour les informations d'une commande existante.
      ATTENTION: Seules les commandes en statut 'brouillon' peuvent être modifiées.
      Pour modifier une commande confirmée, il faut d'abord l'annuler.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: order_id
        type: integer
        required: true
        description: ID de la commande
      - in: body
        name: body
        schema:
          type: object
          properties:
            client_nom:
              type: string
              description: Nom du client
            client_telephone:
              type: string
              description: Téléphone du client
            client_adresse:
              type: string
              description: Adresse de livraison
    responses:
      200:
        description: Commande mise à jour avec succès
      400:
        description: Commande non modifiable (statut != brouillon)
      404:
        description: Commande non trouvée
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()

    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    schema = OrderUpdateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    try:
        order = OrderService.update_order(order, data)
        db.session.commit()

        return jsonify({
            'message': 'Commande mise à jour avec succès',
            'order': order.to_dict(include_items=True)
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_v1.route('/orders/<int:order_id>', methods=['DELETE'])
@jwt_required()
@role_required(UserRoles.ADMIN)
def delete_order(order_id):
    """
    Supprime une commande (soft delete).
    ---
    tags:
      - Orders
    summary: Supprimer une commande
    description: |
      Supprime logiquement une commande (soft delete - la donnée est conservée).
      ATTENTION: Seules les commandes en statut 'brouillon' ou 'annulee' peuvent être supprimées.
      Requiert le rôle ADMIN.
    security:
      - Bearer: []
    parameters:
      - name: order_id
        in: path
        type: integer
        required: true
        description: ID de la commande
    responses:
      200:
        description: Commande supprimée avec succès
      400:
        description: Commande non supprimable (statut invalide)
      403:
        description: Accès refusé (rôle ADMIN requis)
      404:
        description: Commande non trouvée
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()

    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    if order.status not in [OrderStatus.BROUILLON.value, OrderStatus.ANNULEE.value]:
        return jsonify({'error': 'Seules les commandes en brouillon ou annulées peuvent être supprimées'}), 400

    order.soft_delete()
    db.session.commit()

    return jsonify({'message': 'Commande supprimée avec succès'}), 200


@api_v1.route('/orders/<int:order_id>/items', methods=['POST'])
@jwt_required()
def add_order_item(order_id):
    """
    Ajoute un article à une commande.
    ---
    tags:
      - Orders
    summary: Ajouter un article
    description: |
      Ajoute un produit à une commande existante.
      Si le produit existe déjà, la quantité est incrémentée.
      Le montant total de la commande est recalculé automatiquement.
      ATTENTION: Seules les commandes en statut 'brouillon' peuvent être modifiées.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: order_id
        type: integer
        required: true
        description: ID de la commande
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
              description: ID du produit à ajouter
            quantity:
              type: integer
              description: Quantité à ajouter
              minimum: 1
    responses:
      201:
        description: Article ajouté avec succès
      400:
        description: Données invalides ou commande non modifiable
      404:
        description: Commande ou produit non trouvé
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()

    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    schema = OrderItemCreateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    try:
        order = OrderService.add_item_to_order(order, data['product_id'], data['quantity'])
        db.session.commit()

        return jsonify({
            'message': 'Article ajouté avec succès',
            'order': order.to_dict(include_items=True)
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_v1.route('/orders/<int:order_id>/items/<int:item_id>', methods=['PATCH'])
@jwt_required()
def update_order_item(order_id, item_id):
    """
    Met à jour la quantité d'un article.
    ---
    tags:
      - Orders
    summary: Modifier quantité article
    description: |
      Met à jour la quantité d'un article dans une commande.
      Le montant total de la commande est recalculé automatiquement.
      ATTENTION: Seules les commandes en statut 'brouillon' peuvent être modifiées.
    security:
      - Bearer: []
    parameters:
      - name: order_id
        in: path
        type: integer
        required: true
        description: ID de la commande
      - name: item_id
        in: path
        type: integer
        required: true
        description: ID de l'article
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - quantity
          properties:
            quantity:
              type: integer
              minimum: 1
              description: Nouvelle quantité
    responses:
      200:
        description: Quantité mise à jour avec succès
      400:
        description: Données invalides ou commande non modifiable
      404:
        description: Commande ou article non trouvé
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()
    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    if order.status != OrderStatus.BROUILLON.value:
        return jsonify({'error': 'Seules les commandes en brouillon peuvent être modifiées'}), 400

    item = OrderItem.query.filter_by(id=item_id, order_id=order_id).first()
    if not item:
        return jsonify({'error': 'Article non trouvé'}), 404

    data = request.get_json() or {}
    if 'quantity' not in data:
        return jsonify({'error': 'quantity est requis'}), 400

    quantity = data['quantity']
    if not isinstance(quantity, int) or quantity < 1:
        return jsonify({'error': 'quantity doit être un entier >= 1'}), 400

    item.quantity = quantity
    item.calculate_total()
    order.calculate_total()

    db.session.commit()

    return jsonify({
        'message': 'Quantité mise à jour avec succès',
        'order': order.to_dict(include_items=True)
    }), 200


@api_v1.route('/orders/<int:order_id>/items/<int:item_id>', methods=['DELETE'])
@jwt_required()
def remove_order_item(order_id, item_id):
    """
    Supprime un article d'une commande.
    ---
    tags:
      - Orders
    summary: Retirer un article
    description: |
      Supprime un article d'une commande existante.
      Le montant total de la commande est recalculé automatiquement.
      ATTENTION: Seules les commandes en statut 'brouillon' peuvent être modifiées.
    security:
      - Bearer: []
    parameters:
      - name: order_id
        in: path
        type: integer
        required: true
        description: ID de la commande
      - name: item_id
        in: path
        type: integer
        required: true
        description: ID de la ligne article à supprimer
    responses:
      200:
        description: Article supprimé avec succès
      400:
        description: Commande non modifiable
      404:
        description: Commande ou article non trouvé
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()

    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    try:
        order = OrderService.remove_item_from_order(order, item_id)
        db.session.commit()

        return jsonify({
            'message': 'Article supprimé avec succès',
            'order': order.to_dict(include_items=True)
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_v1.route('/orders/<int:order_id>/confirm', methods=['POST'])
@jwt_required()
def confirm_order(order_id):
    """
    Confirme une commande et décrémente les stocks.
    ---
    tags:
      - Orders
    summary: Confirmer une commande
    description: |
      Passe la commande du statut 'brouillon' à 'confirmee'.
      IMPORTANT: Cette action décrémente automatiquement les stocks des produits commandés.
      La commande doit avoir au moins un article pour être confirmée.
      En cas de stock insuffisant, la confirmation échoue avec un message d'erreur.
    security:
      - Bearer: []
    parameters:
      - name: order_id
        in: path
        type: integer
        required: true
        description: ID de la commande
    responses:
      200:
        description: Commande confirmée, stocks décrémentés
      400:
        description: Stock insuffisant ou commande vide
      404:
        description: Commande non trouvée
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()

    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    try:
        order = OrderService.confirm_order(order)
        db.session.commit()

        return jsonify({
            'message': 'Commande confirmée avec succès',
            'order': order.to_dict(include_items=True)
        }), 200

    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@api_v1.route('/orders/<int:order_id>/status', methods=['PATCH'])
@jwt_required()
@role_required(UserRoles.ADMIN, UserRoles.CONTROLEUR, UserRoles.LIVREUR)
def update_order_status(order_id):
    """
    Met à jour le statut d'une commande.
    ---
    tags:
      - Orders
    summary: Changer le statut
    description: |
      Fait progresser une commande dans le workflow de traitement.
      Workflow: brouillon → confirmee → en_preparation → en_livraison → livree.
      Les transitions invalides sont rejetées (ex: brouillon → livree directement).
      Requiert un des rôles: ADMIN, CONTROLEUR ou LIVREUR.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: order_id
        type: integer
        required: true
        description: ID de la commande
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - status
          properties:
            status:
              type: string
              enum: [brouillon, confirmee, en_preparation, en_livraison, livree, annulee]
              description: Nouveau statut de la commande
    responses:
      200:
        description: Statut mis à jour avec succès
      400:
        description: Transition de statut invalide
      403:
        description: Accès refusé (rôle insuffisant)
      404:
        description: Commande non trouvée
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()

    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    schema = OrderStatusUpdateSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    try:
        order = OrderService.update_status(order, data['status'])
        db.session.commit()

        return jsonify({
            'message': f"Statut mis à jour: {order.status}",
            'order': order.to_dict(include_items=True)
        }), 200

    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@api_v1.route('/orders/<int:order_id>/cancel', methods=['POST'])
@jwt_required()
@role_required(UserRoles.ADMIN, UserRoles.CONTROLEUR)
def cancel_order(order_id):
    """
    Annule une commande.
    ---
    tags:
      - Orders
    summary: Annuler une commande
    description: |
      Annule une commande et restaure les stocks si nécessaire.
      Si la commande était confirmée, les quantités sont réintégrées au stock.
      Le motif d'annulation est OBLIGATOIRE.
      Les commandes déjà livrées ne peuvent pas être annulées.
      Requiert le rôle ADMIN ou CONTROLEUR.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: order_id
        type: integer
        required: true
        description: ID de la commande
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - motif_annulation
          properties:
            motif_annulation:
              type: string
              description: Motif de l'annulation (obligatoire)
    responses:
      200:
        description: Commande annulée, stocks restaurés si applicable
      400:
        description: Commande non annulable (déjà livrée) ou motif manquant
      403:
        description: Accès refusé (rôle insuffisant)
      404:
        description: Commande non trouvée
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()

    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    schema = OrderCancelSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    try:
        order = OrderService.cancel_order(order, data['motif_annulation'])
        db.session.commit()

        return jsonify({
            'message': 'Commande annulée avec succès',
            'order': order.to_dict(include_items=True)
        }), 200

    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@api_v1.route('/orders/<int:order_id>/pay', methods=['POST'])
@jwt_required()
@role_required(UserRoles.ADMIN, UserRoles.CONTROLEUR)
def pay_order(order_id):
    """
    Enregistre le paiement d'une commande.
    ---
    tags:
      - Orders
    summary: Payer une commande
    description: |
      Enregistre les informations de paiement et passe la commande au statut 'payee'.
      La commande doit être en statut 'confirmee' pour être payée.
      Pour un paiement mobile money, le numéro et la référence sont obligatoires.
      Requiert le rôle ADMIN ou CONTROLEUR.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: order_id
        type: integer
        required: true
        description: ID de la commande
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - type_paiement
            - montant_paye
          properties:
            type_paiement:
              type: string
              enum: [cash, mobile_money]
              description: Type de paiement
            montant_paye:
              type: number
              description: Montant payé
            mobile_money_numero:
              type: string
              description: Numéro mobile money du client (requis si type=mobile_money)
            mobile_money_ref:
              type: string
              description: Référence de la transaction (requis si type=mobile_money)
    responses:
      200:
        description: Paiement enregistré avec succès
      400:
        description: Données invalides ou commande non payable
      403:
        description: Accès refusé (rôle insuffisant)
      404:
        description: Commande non trouvée
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()

    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    schema = OrderPaymentSchema()

    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Données invalides', 'details': err.messages}), 400

    try:
        order = OrderService.pay_order(order, data)
        db.session.commit()

        return jsonify({
            'message': 'Paiement enregistré avec succès',
            'order': order.to_dict(include_items=True)
        }), 200

    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@api_v1.route('/orders/<int:order_id>/assign-livreur', methods=['POST'])
@jwt_required()
@role_required(UserRoles.ADMIN, UserRoles.CONTROLEUR)
def assign_livreur(order_id):
    """
    Assigne un livreur à une commande.
    ---
    tags:
      - Orders
    summary: Assigner un livreur
    description: |
      Attribue un livreur à une commande pour la livraison.
      Le livreur doit avoir le rôle LIVREUR et être actif.
      Une fois assigné, le livreur peut faire progresser la commande vers 'en_livraison' puis 'livree'.
      Requiert le rôle ADMIN ou CONTROLEUR.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: order_id
        type: integer
        required: true
        description: ID de la commande
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - livreur_id
          properties:
            livreur_id:
              type: integer
              description: ID de l'utilisateur livreur à assigner
    responses:
      200:
        description: Livreur assigné avec succès
      400:
        description: Utilisateur invalide ou n'est pas livreur
      403:
        description: Accès refusé (rôle insuffisant)
      404:
        description: Commande ou livreur non trouvé
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()

    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    data = request.get_json()
    if not data or 'livreur_id' not in data:
        return jsonify({'error': 'livreur_id est requis'}), 400

    try:
        order = OrderService.assign_livreur(order, data['livreur_id'])
        db.session.commit()

        return jsonify({
            'message': 'Livreur assigné avec succès',
            'order': order.to_dict(include_items=True)
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_v1.route('/orders/statuses', methods=['GET'])
@jwt_required()
def get_order_statuses():
    """
    Liste les statuts de commande disponibles.
    ---
    tags:
      - Orders
    summary: Liste des statuts
    description: |
      Retourne la liste de tous les statuts de commande possibles.
      Utile pour peupler les filtres et listes déroulantes côté frontend.
      Statuts: brouillon, confirmee, en_preparation, en_livraison, livree, annulee.
    security:
      - Bearer: []
    responses:
      200:
        description: Liste des statuts disponibles
    """
    return jsonify({
        'statuses': [s.value for s in OrderStatus]
    }), 200


@api_v1.route('/orders/counts', methods=['GET'])
@jwt_required()
def get_order_counts():
    """
    Retourne le nombre de commandes par statut.
    ---
    tags:
      - Orders
    summary: Comptage par statut
    description: |
      Retourne le nombre de commandes pour chaque statut.
      Inclut également le total de toutes les commandes (tous).
      Utile pour afficher les badges/compteurs sur les onglets de filtrage.
    security:
      - Bearer: []
    responses:
      200:
        description: Comptage des commandes par statut
        schema:
          type: object
          properties:
            counts:
              type: object
              properties:
                tous:
                  type: integer
                  description: Nombre total de commandes
                brouillon:
                  type: integer
                confirmee:
                  type: integer
                payee:
                  type: integer
                en_preparation:
                  type: integer
                en_livraison:
                  type: integer
                livree:
                  type: integer
                annulee:
                  type: integer
    """
    set_current_user_id(get_jwt_identity())

    # Initialiser les compteurs à 0 pour chaque statut
    counts = {status.value: 0 for status in OrderStatus}

    # Compter les commandes par statut
    status_counts = db.session.query(
        Order.status,
        db.func.count(Order.id)
    ).filter(
        Order.is_deleted == False
    ).group_by(
        Order.status
    ).all()

    # Mettre à jour les compteurs avec les valeurs de la base
    for status, count in status_counts:
        counts[status] = count

    # Calculer le total
    total = sum(counts.values())

    return jsonify({
        'counts': {
            'tous': total,
            **counts
        }
    }), 200


@api_v1.route('/orders/<int:order_id>/items/<int:item_id>/verify', methods=['PATCH'])
@jwt_required()
def verify_order_item(order_id, item_id):
    """
    Met à jour le statut de vérification d'un article.
    ---
    tags:
      - Orders
    summary: Vérifier un article
    description: |
      Change le statut de vérification d'un article de commande.
      Permet de basculer entre 'a_verifier' et 'ok'.
      Si aucun statut n'est fourni, bascule automatiquement vers l'état opposé.
    security:
      - Bearer: []
    parameters:
      - name: order_id
        in: path
        type: integer
        required: true
        description: ID de la commande
      - name: item_id
        in: path
        type: integer
        required: true
        description: ID de l'article
      - in: body
        name: body
        schema:
          type: object
          properties:
            verification_status:
              type: string
              enum: [a_verifier, ok]
              description: Nouveau statut de vérification (optionnel - toggle si absent)
    responses:
      200:
        description: Statut de vérification mis à jour
      404:
        description: Commande ou article non trouvé
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()
    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    item = OrderItem.query.filter_by(id=item_id, order_id=order_id).first()
    if not item:
        return jsonify({'error': 'Article non trouvé'}), 404

    data = request.get_json() or {}

    if 'verification_status' in data:
        new_status = data['verification_status']
        if new_status not in [s.value for s in ItemVerificationStatus]:
            return jsonify({'error': 'Statut de vérification invalide'}), 400
        item.verification_status = new_status
    else:
        # Toggle automatique
        if item.verification_status == ItemVerificationStatus.A_VERIFIER.value:
            item.verification_status = ItemVerificationStatus.OK.value
        else:
            item.verification_status = ItemVerificationStatus.A_VERIFIER.value

    db.session.commit()

    return jsonify({
        'message': 'Statut de vérification mis à jour',
        'item': item.to_dict()
    }), 200


@api_v1.route('/orders/<int:order_id>/items/verify-all', methods=['PATCH'])
@jwt_required()
def verify_all_order_items(order_id):
    """
    Met à jour le statut de vérification de tous les articles d'une commande.
    ---
    tags:
      - Orders
    summary: Vérifier tous les articles
    description: |
      Change le statut de vérification de tous les articles d'une commande.
    security:
      - Bearer: []
    parameters:
      - name: order_id
        in: path
        type: integer
        required: true
        description: ID de la commande
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - verification_status
          properties:
            verification_status:
              type: string
              enum: [a_verifier, ok]
              description: Nouveau statut de vérification
    responses:
      200:
        description: Statuts de vérification mis à jour
      400:
        description: Statut invalide
      404:
        description: Commande non trouvée
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()
    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    data = request.get_json() or {}

    if 'verification_status' not in data:
        return jsonify({'error': 'verification_status est requis'}), 400

    new_status = data['verification_status']
    if new_status not in [s.value for s in ItemVerificationStatus]:
        return jsonify({'error': 'Statut de vérification invalide'}), 400

    for item in order.items:
        item.verification_status = new_status

    db.session.commit()

    return jsonify({
        'message': f'Tous les articles sont maintenant: {new_status}',
        'order': order.to_dict(include_items=True)
    }), 200


@api_v1.route('/orders_minimal_info', methods=['GET'])
@jwt_required()
def get_orders_minimal_info():
    """
    Liste les commandes avec informations minimales (sans items).
    ---
    tags:
      - Orders
    summary: Liste minimale des commandes
    description: |
      Retourne une liste paginée des commandes avec uniquement les informations essentielles.
      Optimisé pour les listes et tableaux de bord.
    security:
      - Bearer: []
    parameters:
      - name: status
        in: query
        type: string
        enum: [brouillon, confirmee, payee, en_preparation, en_livraison, livree, annulee]
        description: Filtrer par statut
      - name: search
        in: query
        type: string
        description: Recherche sur numéro, nom client ou téléphone
      - name: livreur_id
        in: query
        type: integer
        description: Filtrer par livreur assigné
      - name: sort
        in: query
        type: string
        default: created_at
        description: Champ de tri
      - name: order
        in: query
        type: string
        enum: [asc, desc]
        default: desc
        description: Ordre de tri
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
        description: Liste paginée des commandes (format minimal)
    """
    set_current_user_id(get_jwt_identity())

    query = Order.query.filter_by(is_deleted=False)

    # Filtres
    status = request.args.get('status')
    if status and status in [s.value for s in OrderStatus]:
        query = query.filter_by(status=status)

    search = request.args.get('search')
    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            db.or_(
                Order.numero.ilike(search_filter),
                Order.client_nom.ilike(search_filter),
                Order.client_telephone.ilike(search_filter)
            )
        )

    livreur_id = request.args.get('livreur_id', type=int)
    if livreur_id:
        query = query.filter_by(livreur_id=livreur_id)

    # Tri
    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')
    if hasattr(Order, sort):
        sort_col = getattr(Order, sort)
        query = query.order_by(sort_col.desc() if order == 'desc' else sort_col.asc())

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'orders': [order.to_minimal_dict() for order in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'per_page': per_page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }), 200


@api_v1.route('/orders/history/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_history(order_id):
    """
    Retourne l'historique des événements d'une commande.
    ---
    tags:
      - Orders
    summary: Historique de la commande
    description: |
      Retourne la liste chronologique des événements d'une commande
      (création, confirmation, paiement, etc.).
    security:
      - Bearer: []
    parameters:
      - name: order_id
        in: path
        type: integer
        required: true
        description: ID de la commande
    responses:
      200:
        description: Historique de la commande
      404:
        description: Commande non trouvée
    """
    set_current_user_id(get_jwt_identity())

    order = Order.query.filter_by(id=order_id, is_deleted=False).first()
    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    history = OrderHistory.query.filter_by(order_id=order_id).order_by(OrderHistory.created_at.asc()).all()

    return jsonify({
        'order_id': order_id,
        'order_number': order.numero,
        'history': [h.to_dict() for h in history]
    }), 200


def add_order_history(order_id, event, user_id=None, note=None):
    """
    Helper function pour ajouter un événement à l'historique d'une commande.
    """
    history_entry = OrderHistory(
        order_id=order_id,
        event=event,
        user_id=user_id,
        note=note
    )
    db.session.add(history_entry)
    return history_entry
