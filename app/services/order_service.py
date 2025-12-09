"""
Service Order - Gestion des commandes et workflow
"""
from app.extensions import db
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.services.stock_service import StockService


class OrderService:
    """Service pour la gestion des commandes"""

    @staticmethod
    def create_order(data, user_id=None):
        """
        Crée une nouvelle commande avec ses articles.
        """
        # Créer la commande
        order = Order(
            numero=Order.generate_numero(),
            status=OrderStatus.BROUILLON.value,
            client_nom=data['client_nom'],
            client_telephone=data.get('client_telephone'),
            client_email=data.get('client_email'),
            adresse_livraison=data.get('adresse_livraison'),
            montant_remise=data.get('montant_remise', 0),
            montant_livraison=data.get('montant_livraison', 0),
            notes=data.get('notes'),
            user_id=user_id
        )

        db.session.add(order)
        db.session.flush()

        # Ajouter les articles
        for item_data in data['items']:
            product = Product.query.get(item_data['product_id'])
            if not product:
                raise ValueError(f"Produit {item_data['product_id']} non trouvé")

            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item_data['quantity'],
                prix_unitaire=product.prix
            )
            item.calculate_total()
            db.session.add(item)

        db.session.flush()

        # Calculer le total
        order.calculate_total()

        return order

    @staticmethod
    def update_order(order, data):
        """
        Met à jour une commande (si elle est en brouillon).
        """
        if order.status != OrderStatus.BROUILLON.value:
            raise ValueError("Seules les commandes en brouillon peuvent être modifiées")

        # Mettre à jour les champs
        for field in ['client_nom', 'client_telephone', 'client_email',
                      'adresse_livraison', 'montant_remise', 'montant_livraison', 'notes']:
            if field in data:
                setattr(order, field, data[field])

        if 'livreur_id' in data:
            order.livreur_id = data['livreur_id']

        order.calculate_total()

        return order

    @staticmethod
    def add_item_to_order(order, product_id, quantity):
        """
        Ajoute un article à une commande.
        """
        if order.status != OrderStatus.BROUILLON.value:
            raise ValueError("Seules les commandes en brouillon peuvent être modifiées")

        product = Product.query.get(product_id)
        if not product:
            raise ValueError("Produit non trouvé")

        # Vérifier si l'article existe déjà
        existing_item = OrderItem.query.filter_by(
            order_id=order.id,
            product_id=product_id
        ).first()

        if existing_item:
            existing_item.quantity += quantity
            existing_item.calculate_total()
        else:
            item = OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=quantity,
                prix_unitaire=product.prix
            )
            item.calculate_total()
            db.session.add(item)

        db.session.flush()
        order.calculate_total()

        return order

    @staticmethod
    def remove_item_from_order(order, item_id):
        """
        Supprime un article d'une commande.
        """
        if order.status != OrderStatus.BROUILLON.value:
            raise ValueError("Seules les commandes en brouillon peuvent être modifiées")

        item = OrderItem.query.filter_by(id=item_id, order_id=order.id).first()
        if not item:
            raise ValueError("Article non trouvé")

        db.session.delete(item)
        db.session.flush()
        order.calculate_total()

        return order

    @staticmethod
    def confirm_order(order):
        """
        Confirme une commande et décrémente les stocks.
        """
        if not order.can_transition_to(OrderStatus.CONFIRMEE):
            raise ValueError(f"Transition invalide depuis le statut {order.status}")

        # Vérifier la disponibilité des stocks
        for item in order.items:
            stock = item.product.stock
            if not stock or stock.quantity < item.quantity:
                available = stock.quantity if stock else 0
                raise ValueError(
                    f"Stock insuffisant pour {item.product.nom}. "
                    f"Disponible: {available}, Demandé: {item.quantity}"
                )

        # Décrémenter les stocks
        StockService.deduct_for_order(order)

        # Mettre à jour le statut
        order.update_status(OrderStatus.CONFIRMEE)

        return order

    @staticmethod
    def update_status(order, new_status):
        """
        Met à jour le statut d'une commande selon le workflow.
        """
        # Cas spécial: annulation d'une commande confirmée = retour stock
        current_status = OrderStatus(order.status)
        target_status = OrderStatus(new_status) if isinstance(new_status, str) else new_status

        if target_status == OrderStatus.ANNULEE:
            if current_status in [OrderStatus.CONFIRMEE, OrderStatus.EN_PREPARATION, OrderStatus.EN_LIVRAISON]:
                # Retourner les stocks
                StockService.return_stock_for_order(order)

        if not order.update_status(new_status):
            raise ValueError(f"Transition invalide de {order.status} vers {new_status}")

        return order

    @staticmethod
    def cancel_order(order, reason=None):
        """
        Annule une commande.
        """
        if reason:
            order.notes = f"{order.notes or ''}\nAnnulation: {reason}".strip()

        return OrderService.update_status(order, OrderStatus.ANNULEE)

    @staticmethod
    def assign_livreur(order, livreur_id):
        """
        Assigne un livreur à une commande.
        """
        from app.models.user import User
        livreur = User.query.filter_by(id=livreur_id, role='livreur', is_active=True).first()

        if not livreur:
            raise ValueError("Livreur non trouvé ou inactif")

        order.livreur_id = livreur_id
        return order
