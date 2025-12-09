"""
Service Stock - Gestion des stocks et mouvements
"""
from app.extensions import db
from app.models.stock import Stock, StockMovement, MovementType
from app.models.product import Product


class StockService:
    """Service pour la gestion des stocks"""

    @staticmethod
    def get_or_create_stock(product_id, initial_quantity=0, seuil_alerte=10):
        """
        Récupère ou crée un stock pour un produit.
        """
        stock = Stock.query.filter_by(product_id=product_id).first()

        if not stock:
            stock = Stock(
                product_id=product_id,
                quantity=initial_quantity,
                seuil_alerte=seuil_alerte
            )
            db.session.add(stock)
            db.session.flush()

        return stock

    @staticmethod
    def create_movement(product_id, movement_type, quantity, reference=None, notes=None):
        """
        Crée un mouvement de stock.
        Retourne le mouvement créé et met à jour le stock.
        """
        stock = StockService.get_or_create_stock(product_id)
        movement = stock.add_movement(
            movement_type=movement_type,
            quantity=quantity,
            reference=reference,
            notes=notes
        )

        return movement, stock

    @staticmethod
    def add_stock(product_id, quantity, reference=None, notes=None):
        """
        Ajoute du stock (entrée).
        """
        return StockService.create_movement(
            product_id=product_id,
            movement_type=MovementType.ENTREE,
            quantity=quantity,
            reference=reference,
            notes=notes
        )

    @staticmethod
    def remove_stock(product_id, quantity, reference=None, notes=None):
        """
        Retire du stock (sortie).
        Vérifie la disponibilité.
        """
        stock = StockService.get_or_create_stock(product_id)

        if stock.quantity < quantity:
            raise ValueError(f"Stock insuffisant. Disponible: {stock.quantity}, Demandé: {quantity}")

        return StockService.create_movement(
            product_id=product_id,
            movement_type=MovementType.SORTIE,
            quantity=quantity,
            reference=reference,
            notes=notes
        )

    @staticmethod
    def adjust_stock(product_id, new_quantity, notes=None):
        """
        Ajuste le stock à une nouvelle quantité (inventaire).
        """
        return StockService.create_movement(
            product_id=product_id,
            movement_type=MovementType.AJUSTEMENT,
            quantity=new_quantity,
            notes=notes
        )

    @staticmethod
    def deduct_for_order(order):
        """
        Déduit le stock pour une commande confirmée.
        Crée automatiquement les mouvements de type 'vente'.
        """
        movements = []

        for item in order.items:
            stock = StockService.get_or_create_stock(item.product_id)

            if stock.quantity < item.quantity:
                raise ValueError(
                    f"Stock insuffisant pour {item.product.nom}. "
                    f"Disponible: {stock.quantity}, Demandé: {item.quantity}"
                )

            movement = stock.add_movement(
                movement_type=MovementType.VENTE,
                quantity=item.quantity,
                reference=order.numero,
                notes=f"Vente commande {order.numero}"
            )
            movements.append(movement)

        return movements

    @staticmethod
    def return_stock_for_order(order):
        """
        Retourne le stock pour une commande annulée.
        """
        movements = []

        for item in order.items:
            stock = StockService.get_or_create_stock(item.product_id)
            movement = stock.add_movement(
                movement_type=MovementType.RETOUR,
                quantity=item.quantity,
                reference=order.numero,
                notes=f"Retour annulation commande {order.numero}"
            )
            movements.append(movement)

        return movements

    @staticmethod
    def get_movements_history(product_id=None, limit=50):
        """
        Récupère l'historique des mouvements de stock.
        """
        query = StockMovement.query

        if product_id:
            query = query.filter_by(product_id=product_id)

        return query.order_by(StockMovement.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_low_stock_products():
        """
        Récupère les produits en stock faible.
        """
        return db.session.query(Product, Stock).join(
            Stock, Stock.product_id == Product.id
        ).filter(
            Product.is_deleted == False,
            Product.is_active == True,
            Stock.quantity <= Stock.seuil_alerte
        ).all()

    @staticmethod
    def get_out_of_stock_products():
        """
        Récupère les produits en rupture de stock.
        """
        return db.session.query(Product, Stock).join(
            Stock, Stock.product_id == Product.id
        ).filter(
            Product.is_deleted == False,
            Product.is_active == True,
            Stock.quantity <= 0
        ).all()
