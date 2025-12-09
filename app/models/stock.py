"""
Modèles Stock et StockMovement - Gestion des stocks avec audit
"""
from datetime import datetime
from enum import Enum

from app.extensions import db
from app.core.audit_mixin import AuditMixin, register_audit_listeners


class MovementType(str, Enum):
    """Types de mouvement de stock"""
    ENTREE = 'entree'
    SORTIE = 'sortie'
    AJUSTEMENT = 'ajustement'
    VENTE = 'vente'
    RETOUR = 'retour'


class Stock(db.Model, AuditMixin):
    """
    Modèle Stock - État actuel du stock par produit.
    """
    __tablename__ = 'stocks'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, unique=True, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    seuil_alerte = db.Column(db.Integer, nullable=False, default=10)  # Seuil de stock faible

    # Relations
    movements = db.relationship('StockMovement', backref='stock', lazy='dynamic',
                               order_by='StockMovement.created_at.desc()')

    def __repr__(self):
        return f'<Stock Product:{self.product_id} Qty:{self.quantity}>'

    def add_movement(self, movement_type, quantity, reference=None, notes=None):
        """
        Ajoute un mouvement de stock et met à jour la quantité.
        """
        movement = StockMovement(
            stock_id=self.id,
            product_id=self.product_id,
            movement_type=movement_type,
            quantity=quantity,
            quantity_before=self.quantity,
            reference=reference,
            notes=notes
        )

        # Calculer la nouvelle quantité
        if movement_type in [MovementType.ENTREE, MovementType.RETOUR]:
            self.quantity += quantity
        elif movement_type in [MovementType.SORTIE, MovementType.VENTE]:
            self.quantity -= quantity
        elif movement_type == MovementType.AJUSTEMENT:
            self.quantity = quantity

        movement.quantity_after = self.quantity

        db.session.add(movement)
        return movement

    def to_dict(self):
        """Conversion en dictionnaire"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'seuil_alerte': self.seuil_alerte,
            'is_low_stock': self.quantity <= self.seuil_alerte,
            'is_out_of_stock': self.quantity <= 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StockMovement(db.Model, AuditMixin):
    """
    Modèle StockMovement - Historique des mouvements de stock.
    Chaque mouvement est horodaté et associé à un utilisateur.
    """
    __tablename__ = 'stock_movements'

    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    movement_type = db.Column(db.String(20), nullable=False)  # entree, sortie, ajustement, vente, retour
    quantity = db.Column(db.Integer, nullable=False)
    quantity_before = db.Column(db.Integer, nullable=False)
    quantity_after = db.Column(db.Integer, nullable=False)
    reference = db.Column(db.String(100), nullable=True)  # Numéro de commande, bon de livraison, etc.
    notes = db.Column(db.Text, nullable=True)

    # Relations
    product = db.relationship('Product', backref='stock_movements')

    def __repr__(self):
        return f'<StockMovement {self.movement_type} {self.quantity}>'

    def to_dict(self):
        """Conversion en dictionnaire"""
        return {
            'id': self.id,
            'stock_id': self.stock_id,
            'product_id': self.product_id,
            'product_nom': self.product.nom if self.product else None,
            'movement_type': self.movement_type,
            'quantity': self.quantity,
            'quantity_before': self.quantity_before,
            'quantity_after': self.quantity_after,
            'reference': self.reference,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }


# Enregistrer les listeners d'audit
register_audit_listeners(Stock)
register_audit_listeners(StockMovement)
