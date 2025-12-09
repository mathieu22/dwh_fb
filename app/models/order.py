"""
Modèles Order et OrderItem - Gestion des commandes avec workflow et audit
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.extensions import db
from app.core.audit_mixin import AuditMixin, SoftDeleteMixin, register_audit_listeners


class OrderStatus(str, Enum):
    """Statuts de commande selon le workflow"""
    BROUILLON = 'brouillon'
    CONFIRMEE = 'confirmee'
    EN_PREPARATION = 'en_preparation'
    EN_LIVRAISON = 'en_livraison'
    LIVREE = 'livree'
    ANNULEE = 'annulee'


# Transitions valides du workflow
VALID_TRANSITIONS = {
    OrderStatus.BROUILLON: [OrderStatus.CONFIRMEE, OrderStatus.ANNULEE],
    OrderStatus.CONFIRMEE: [OrderStatus.EN_PREPARATION, OrderStatus.ANNULEE],
    OrderStatus.EN_PREPARATION: [OrderStatus.EN_LIVRAISON, OrderStatus.ANNULEE],
    OrderStatus.EN_LIVRAISON: [OrderStatus.LIVREE, OrderStatus.ANNULEE],
    OrderStatus.LIVREE: [],
    OrderStatus.ANNULEE: []
}


class Order(db.Model, AuditMixin, SoftDeleteMixin):
    """
    Modèle Order - Commande avec workflow de statuts.
    """
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default=OrderStatus.BROUILLON.value)

    # Client / Destinataire
    client_nom = db.Column(db.String(200), nullable=False)
    client_telephone = db.Column(db.String(20), nullable=True)
    client_email = db.Column(db.String(255), nullable=True)
    adresse_livraison = db.Column(db.Text, nullable=True)

    # Montants
    montant_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    montant_remise = db.Column(db.Numeric(10, 2), default=0)
    montant_livraison = db.Column(db.Numeric(10, 2), default=0)

    # Dates du workflow
    date_confirmation = db.Column(db.DateTime, nullable=True)
    date_preparation = db.Column(db.DateTime, nullable=True)
    date_expedition = db.Column(db.DateTime, nullable=True)
    date_livraison = db.Column(db.DateTime, nullable=True)

    # Notes
    notes = db.Column(db.Text, nullable=True)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # Créateur de la commande
    livreur_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Livreur assigné

    # Relations
    items = db.relationship('OrderItem', backref='order', lazy='joined', cascade='all, delete-orphan')
    livreur = db.relationship('User', foreign_keys=[livreur_id], backref='livraisons')

    def __repr__(self):
        return f'<Order {self.numero}>'

    @staticmethod
    def generate_numero():
        """Génère un numéro de commande unique"""
        from datetime import datetime
        import random
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_suffix = random.randint(100, 999)
        return f'CMD-{timestamp}-{random_suffix}'

    def can_transition_to(self, new_status):
        """Vérifie si la transition de statut est valide"""
        current = OrderStatus(self.status)
        target = OrderStatus(new_status) if isinstance(new_status, str) else new_status
        return target in VALID_TRANSITIONS.get(current, [])

    def update_status(self, new_status):
        """
        Met à jour le statut et enregistre la date correspondante.
        Retourne True si la transition est valide, False sinon.
        """
        if not self.can_transition_to(new_status):
            return False

        new_status_value = new_status.value if isinstance(new_status, OrderStatus) else new_status
        self.status = new_status_value

        # Enregistrer la date selon le statut
        now = datetime.utcnow()
        if new_status_value == OrderStatus.CONFIRMEE.value:
            self.date_confirmation = now
        elif new_status_value == OrderStatus.EN_PREPARATION.value:
            self.date_preparation = now
        elif new_status_value == OrderStatus.EN_LIVRAISON.value:
            self.date_expedition = now
        elif new_status_value == OrderStatus.LIVREE.value:
            self.date_livraison = now

        return True

    def calculate_total(self):
        """Recalcule le montant total de la commande"""
        total = sum(item.prix_total for item in self.items)
        self.montant_total = total + (self.montant_livraison or 0) - (self.montant_remise or 0)
        return self.montant_total

    @property
    def montant_net(self):
        """Montant net après remise"""
        return float(self.montant_total)

    def to_dict(self, include_items=True):
        """Conversion en dictionnaire"""
        data = {
            'id': self.id,
            'numero': self.numero,
            'status': self.status,
            'client_nom': self.client_nom,
            'client_telephone': self.client_telephone,
            'client_email': self.client_email,
            'adresse_livraison': self.adresse_livraison,
            'montant_total': float(self.montant_total) if self.montant_total else 0,
            'montant_remise': float(self.montant_remise) if self.montant_remise else 0,
            'montant_livraison': float(self.montant_livraison) if self.montant_livraison else 0,
            'date_confirmation': self.date_confirmation.isoformat() if self.date_confirmation else None,
            'date_preparation': self.date_preparation.isoformat() if self.date_preparation else None,
            'date_expedition': self.date_expedition.isoformat() if self.date_expedition else None,
            'date_livraison': self.date_livraison.isoformat() if self.date_livraison else None,
            'notes': self.notes,
            'user_id': self.user_id,
            'livreur_id': self.livreur_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }

        if include_items:
            data['items'] = [item.to_dict() for item in self.items]
            data['items_count'] = len(self.items)

        return data


class OrderItem(db.Model, AuditMixin):
    """
    Modèle OrderItem - Ligne de commande.
    """
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    prix_unitaire = db.Column(db.Numeric(10, 2), nullable=False)
    prix_total = db.Column(db.Numeric(12, 2), nullable=False)

    def __repr__(self):
        return f'<OrderItem Order:{self.order_id} Product:{self.product_id}>'

    def calculate_total(self):
        """Calcule le prix total de la ligne"""
        self.prix_total = self.prix_unitaire * self.quantity
        return self.prix_total

    def to_dict(self):
        """Conversion en dictionnaire"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_nom': self.product.nom if self.product else None,
            'quantity': self.quantity,
            'prix_unitaire': float(self.prix_unitaire) if self.prix_unitaire else 0,
            'prix_total': float(self.prix_total) if self.prix_total else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Enregistrer les listeners d'audit
register_audit_listeners(Order)
register_audit_listeners(OrderItem)
