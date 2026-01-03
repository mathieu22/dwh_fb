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
    PAYEE = 'payee'
    EN_PREPARATION = 'en_preparation'
    EN_LIVRAISON = 'en_livraison'
    LIVREE = 'livree'
    ANNULEE = 'annulee'


class ItemVerificationStatus(str, Enum):
    """Statuts de vérification d'un article"""
    A_VERIFIER = 'a_verifier'
    OK = 'ok'


class TypePaiement(str, Enum):
    """Types de paiement disponibles"""
    CASH = 'cash'
    MOBILE_MONEY = 'mobile_money'


# Transitions valides du workflow
VALID_TRANSITIONS = {
    OrderStatus.BROUILLON: [OrderStatus.CONFIRMEE, OrderStatus.ANNULEE],
    OrderStatus.CONFIRMEE: [OrderStatus.PAYEE, OrderStatus.ANNULEE],
    OrderStatus.PAYEE: [OrderStatus.EN_PREPARATION, OrderStatus.ANNULEE],
    OrderStatus.EN_PREPARATION: [OrderStatus.EN_LIVRAISON, OrderStatus.ANNULEE],
    OrderStatus.EN_LIVRAISON: [OrderStatus.LIVREE, OrderStatus.ANNULEE],
    OrderStatus.LIVREE: [],
    OrderStatus.ANNULEE: []
}


class OrderHistoryEvent(str, Enum):
    """Types d'événements de l'historique"""
    CREATED = 'CREATED'
    CONFIRMED = 'CONFIRMED'
    PAID = 'PAID'
    IN_PREPARATION = 'IN_PREPARATION'
    IN_DELIVERY = 'IN_DELIVERY'
    DELIVERED = 'DELIVERED'
    CANCELLED = 'CANCELLED'
    ITEM_ADDED = 'ITEM_ADDED'
    ITEM_REMOVED = 'ITEM_REMOVED'
    ITEM_UPDATED = 'ITEM_UPDATED'
    COURIER_ASSIGNED = 'COURIER_ASSIGNED'


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
    ville = db.Column(db.String(100), nullable=True)
    adresse_livraison = db.Column(db.Text, nullable=True)
    date_souhaitee = db.Column(db.Date, nullable=True)  # Date de livraison souhaitée

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

    # Motif d'annulation (obligatoire si status = annulee)
    motif_annulation = db.Column(db.Text, nullable=True)

    # Informations de paiement (quand status = payee)
    type_paiement = db.Column(db.String(20), nullable=True)  # cash ou mobile_money
    mobile_money_numero = db.Column(db.String(30), nullable=True)  # Numéro du client
    mobile_money_ref = db.Column(db.String(100), nullable=True)  # Référence transaction
    montant_paye = db.Column(db.Numeric(12, 2), nullable=True)
    date_paiement = db.Column(db.DateTime, nullable=True)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # Créateur de la commande
    livreur_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Livreur assigné

    # Relations
    items = db.relationship('OrderItem', backref='order', lazy='joined', cascade='all, delete-orphan')
    livreur = db.relationship('User', foreign_keys=[livreur_id], backref='livraisons')
    creator = db.relationship('User', foreign_keys=[user_id], backref='orders_created')
    history = db.relationship('OrderHistory', backref='order', lazy='dynamic', order_by='OrderHistory.created_at.desc()')

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
        elif new_status_value == OrderStatus.PAYEE.value:
            self.date_paiement = now
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

    @property
    def items_count(self):
        """Nombre total d'articles (somme des quantités)"""
        return sum(item.quantity for item in self.items)

    @property
    def total_amount(self):
        """Montant total calculé à partir des items"""
        return float(self.montant_total) if self.montant_total else 0

    @property
    def is_paid(self):
        """Vérifie si la commande est payée"""
        return self.status in [OrderStatus.PAYEE.value, OrderStatus.EN_PREPARATION.value,
                               OrderStatus.EN_LIVRAISON.value, OrderStatus.LIVREE.value]

    def to_minimal_dict(self):
        """Conversion en dictionnaire minimal (sans items)"""
        return {
            'id': self.id,
            'order_number': self.numero,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'customer_name': self.client_nom,
            'customer_phone': self.client_telephone,
            'city': self.ville,
            'address': self.adresse_livraison,
            'desired_date': self.date_souhaitee.isoformat() if self.date_souhaitee else None,
            'is_paid': self.is_paid,
            'payment_type': self.type_paiement,
            'payment_ref': self.mobile_money_ref,
            'payment_sender_phone': self.mobile_money_numero,
            'courier_name': f"{self.livreur.prenom} {self.livreur.nom}" if self.livreur else None,
            'items_count': self.items_count,
            'total_amount_ar': self.total_amount
        }

    def to_dict(self, include_items=True):
        """Conversion en dictionnaire"""
        data = {
            'id': self.id,
            'numero': self.numero,
            'status': self.status,
            'client_nom': self.client_nom,
            'client_telephone': self.client_telephone,
            'client_email': self.client_email,
            'ville': self.ville,
            'adresse_livraison': self.adresse_livraison,
            'date_souhaitee': self.date_souhaitee.isoformat() if self.date_souhaitee else None,
            'montant_total': float(self.montant_total) if self.montant_total else 0,
            'items_count': self.items_count,
            'total_amount_ar': self.total_amount,
            'montant_remise': float(self.montant_remise) if self.montant_remise else 0,
            'montant_livraison': float(self.montant_livraison) if self.montant_livraison else 0,
            'date_confirmation': self.date_confirmation.isoformat() if self.date_confirmation else None,
            'date_paiement': self.date_paiement.isoformat() if self.date_paiement else None,
            'date_preparation': self.date_preparation.isoformat() if self.date_preparation else None,
            'date_expedition': self.date_expedition.isoformat() if self.date_expedition else None,
            'date_livraison': self.date_livraison.isoformat() if self.date_livraison else None,
            'notes': self.notes,
            'motif_annulation': self.motif_annulation,
            # Informations de paiement
            'type_paiement': self.type_paiement,
            'mobile_money_numero': self.mobile_money_numero,
            'mobile_money_ref': self.mobile_money_ref,
            'montant_paye': float(self.montant_paye) if self.montant_paye else None,
            'user_id': self.user_id,
            'livreur_id': self.livreur_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }

        # Ajouter les coordonnées du livreur si assigné
        if self.livreur:
            data['livreur'] = {
                'id': self.livreur.id,
                'nom': self.livreur.nom,
                'prenom': self.livreur.prenom,
                'telephone': self.livreur.telephone
            }
        else:
            data['livreur'] = None

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
    verification_status = db.Column(
        db.String(20),
        nullable=False,
        default=ItemVerificationStatus.A_VERIFIER.value
    )

    def __repr__(self):
        return f'<OrderItem Order:{self.order_id} Product:{self.product_id}>'

    def calculate_total(self):
        """Calcule le prix total de la ligne"""
        self.prix_total = self.prix_unitaire * self.quantity
        return self.prix_total

    def to_dict(self):
        """Conversion en dictionnaire"""
        data = {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'prix_unitaire': float(self.prix_unitaire) if self.prix_unitaire else 0,
            'prix_total': float(self.prix_total) if self.prix_total else 0,
            'verification_status': self.verification_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

        # Ajouter tous les attributs du produit
        if self.product:
            data['product'] = {
                'id': self.product.id,
                'nom': self.product.nom,
                'description': self.product.description,
                'sku': self.product.sku,
                'photo_url': self.product.photo_url,
                'prix_actuel': float(self.product.prix) if self.product.prix else 0,
                'category_id': self.product.category_id,
                'category_nom': self.product.category.nom if self.product.category else None,
                'is_active': self.product.is_active
            }
        else:
            data['product'] = None

        return data


class OrderHistory(db.Model):
    """
    Modèle OrderHistory - Historique des événements d'une commande.
    """
    __tablename__ = 'order_history'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    event = db.Column(db.String(50), nullable=False)
    note = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relation vers l'utilisateur
    user = db.relationship('User', backref='order_history_entries')

    def __repr__(self):
        return f'<OrderHistory Order:{self.order_id} Event:{self.event}>'

    def to_dict(self):
        """Conversion en dictionnaire"""
        return {
            'at': self.created_at.isoformat() if self.created_at else None,
            'by': f"{self.user.prenom} {self.user.nom}" if self.user else None,
            'event': self.event,
            'note': self.note
        }


# Enregistrer les listeners d'audit
register_audit_listeners(Order)
register_audit_listeners(OrderItem)
