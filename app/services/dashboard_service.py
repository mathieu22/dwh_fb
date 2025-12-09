"""
Service Dashboard - KPIs et statistiques
"""
from datetime import datetime, timedelta
from sqlalchemy import func, and_, extract
from decimal import Decimal

from app.extensions import db
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.category import Category
from app.models.stock import Stock


class DashboardService:
    """Service pour les indicateurs du dashboard"""

    @staticmethod
    def get_chiffre_affaires(start_date, end_date):
        """
        Calcule le chiffre d'affaires total sur une période.
        Ne compte que les commandes livrées ou confirmées+.
        """
        valid_statuses = [
            OrderStatus.CONFIRMEE.value,
            OrderStatus.EN_PREPARATION.value,
            OrderStatus.EN_LIVRAISON.value,
            OrderStatus.LIVREE.value
        ]

        result = db.session.query(
            func.coalesce(func.sum(Order.montant_total), 0)
        ).filter(
            Order.is_deleted == False,
            Order.status.in_(valid_statuses),
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).scalar()

        return float(result) if result else 0

    @staticmethod
    def get_ventes_par_jour(start_date, end_date):
        """
        Retourne les ventes groupées par jour.
        """
        valid_statuses = [
            OrderStatus.CONFIRMEE.value,
            OrderStatus.EN_PREPARATION.value,
            OrderStatus.EN_LIVRAISON.value,
            OrderStatus.LIVREE.value
        ]

        results = db.session.query(
            func.date(Order.created_at).label('date'),
            func.sum(Order.montant_total).label('total'),
            func.count(Order.id).label('nombre_commandes')
        ).filter(
            Order.is_deleted == False,
            Order.status.in_(valid_statuses),
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).group_by(
            func.date(Order.created_at)
        ).order_by(
            func.date(Order.created_at)
        ).all()

        return [
            {
                'date': str(r.date),
                'total': float(r.total) if r.total else 0,
                'nombre_commandes': r.nombre_commandes
            }
            for r in results
        ]

    @staticmethod
    def get_nombre_commandes(start_date, end_date, status=None):
        """
        Compte le nombre de commandes sur une période.
        """
        query = db.session.query(func.count(Order.id)).filter(
            Order.is_deleted == False,
            Order.created_at >= start_date,
            Order.created_at <= end_date
        )

        if status:
            query = query.filter(Order.status == status)

        return query.scalar() or 0

    @staticmethod
    def get_commandes_par_statut(start_date, end_date):
        """
        Retourne le nombre de commandes par statut.
        """
        results = db.session.query(
            Order.status,
            func.count(Order.id).label('count')
        ).filter(
            Order.is_deleted == False,
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).group_by(Order.status).all()

        return {r.status: r.count for r in results}

    @staticmethod
    def get_details_commandes_par_jour(start_date, end_date):
        """
        Retourne les détails des commandes par jour avec les articles.
        """
        valid_statuses = [
            OrderStatus.CONFIRMEE.value,
            OrderStatus.EN_PREPARATION.value,
            OrderStatus.EN_LIVRAISON.value,
            OrderStatus.LIVREE.value
        ]

        orders = Order.query.filter(
            Order.is_deleted == False,
            Order.status.in_(valid_statuses),
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).order_by(Order.created_at.desc()).all()

        # Grouper par jour
        by_day = {}
        for order in orders:
            day = order.created_at.strftime('%Y-%m-%d')
            if day not in by_day:
                by_day[day] = {
                    'date': day,
                    'commandes': [],
                    'total': 0,
                    'nombre': 0
                }
            by_day[day]['commandes'].append(order.to_dict(include_items=True))
            by_day[day]['total'] += float(order.montant_total)
            by_day[day]['nombre'] += 1

        return list(by_day.values())

    @staticmethod
    def get_ventes_par_article(start_date, end_date, limit=10):
        """
        Retourne les ventes par article (top vendus).
        """
        valid_statuses = [
            OrderStatus.CONFIRMEE.value,
            OrderStatus.EN_PREPARATION.value,
            OrderStatus.EN_LIVRAISON.value,
            OrderStatus.LIVREE.value
        ]

        results = db.session.query(
            Product.id,
            Product.nom,
            func.sum(OrderItem.quantity).label('quantity_sold'),
            func.sum(OrderItem.prix_total).label('total_revenue')
        ).join(
            OrderItem, OrderItem.product_id == Product.id
        ).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            Order.is_deleted == False,
            Order.status.in_(valid_statuses),
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).group_by(
            Product.id, Product.nom
        ).order_by(
            func.sum(OrderItem.quantity).desc()
        ).limit(limit).all()

        return [
            {
                'product_id': r.id,
                'product_nom': r.nom,
                'quantity_sold': r.quantity_sold or 0,
                'total_revenue': float(r.total_revenue) if r.total_revenue else 0
            }
            for r in results
        ]

    @staticmethod
    def get_ventes_par_categorie(start_date, end_date):
        """
        Retourne les ventes groupées par catégorie.
        """
        valid_statuses = [
            OrderStatus.CONFIRMEE.value,
            OrderStatus.EN_PREPARATION.value,
            OrderStatus.EN_LIVRAISON.value,
            OrderStatus.LIVREE.value
        ]

        results = db.session.query(
            Category.id,
            Category.nom,
            func.sum(OrderItem.quantity).label('quantity_sold'),
            func.sum(OrderItem.prix_total).label('total_revenue')
        ).join(
            Product, Product.category_id == Category.id
        ).join(
            OrderItem, OrderItem.product_id == Product.id
        ).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            Order.is_deleted == False,
            Order.status.in_(valid_statuses),
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).group_by(
            Category.id, Category.nom
        ).order_by(
            func.sum(OrderItem.prix_total).desc()
        ).all()

        return [
            {
                'category_id': r.id,
                'category_nom': r.nom,
                'quantity_sold': r.quantity_sold or 0,
                'total_revenue': float(r.total_revenue) if r.total_revenue else 0
            }
            for r in results
        ]

    @staticmethod
    def get_etat_stocks():
        """
        Retourne l'état des stocks (ruptures, faibles stocks).
        """
        stocks = db.session.query(
            Stock, Product
        ).join(
            Product, Product.id == Stock.product_id
        ).filter(
            Product.is_deleted == False,
            Product.is_active == True
        ).all()

        ruptures = []
        faibles = []
        normaux = []

        for stock, product in stocks:
            item = {
                'product_id': product.id,
                'product_nom': product.nom,
                'quantity': stock.quantity,
                'seuil_alerte': stock.seuil_alerte
            }

            if stock.quantity <= 0:
                ruptures.append(item)
            elif stock.quantity <= stock.seuil_alerte:
                faibles.append(item)
            else:
                normaux.append(item)

        return {
            'ruptures': ruptures,
            'faibles_stocks': faibles,
            'normaux': normaux,
            'stats': {
                'total_ruptures': len(ruptures),
                'total_faibles': len(faibles),
                'total_normaux': len(normaux)
            }
        }

    @staticmethod
    def get_panier_moyen(start_date, end_date):
        """
        Calcule le panier moyen sur une période.
        """
        valid_statuses = [
            OrderStatus.CONFIRMEE.value,
            OrderStatus.EN_PREPARATION.value,
            OrderStatus.EN_LIVRAISON.value,
            OrderStatus.LIVREE.value
        ]

        result = db.session.query(
            func.avg(Order.montant_total)
        ).filter(
            Order.is_deleted == False,
            Order.status.in_(valid_statuses),
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).scalar()

        return float(result) if result else 0

    @staticmethod
    def get_kpis_avances(start_date, end_date):
        """
        Retourne les KPIs avancés.
        """
        ca_total = DashboardService.get_chiffre_affaires(start_date, end_date)
        nb_commandes = DashboardService.get_nombre_commandes(start_date, end_date)
        panier_moyen = DashboardService.get_panier_moyen(start_date, end_date)
        top_articles = DashboardService.get_ventes_par_article(start_date, end_date, limit=5)
        etat_stocks = DashboardService.get_etat_stocks()

        # Calcul période précédente pour comparaison
        delta = end_date - start_date
        previous_start = start_date - delta
        previous_end = start_date

        ca_precedent = DashboardService.get_chiffre_affaires(previous_start, previous_end)
        nb_commandes_precedent = DashboardService.get_nombre_commandes(previous_start, previous_end)

        # Évolution en %
        evolution_ca = ((ca_total - ca_precedent) / ca_precedent * 100) if ca_precedent > 0 else 0
        evolution_commandes = ((nb_commandes - nb_commandes_precedent) / nb_commandes_precedent * 100) if nb_commandes_precedent > 0 else 0

        return {
            'chiffre_affaires': {
                'actuel': ca_total,
                'precedent': ca_precedent,
                'evolution_pct': round(evolution_ca, 2)
            },
            'nombre_commandes': {
                'actuel': nb_commandes,
                'precedent': nb_commandes_precedent,
                'evolution_pct': round(evolution_commandes, 2)
            },
            'panier_moyen': round(panier_moyen, 2),
            'top_articles': top_articles,
            'alertes_stock': {
                'ruptures': etat_stocks['stats']['total_ruptures'],
                'faibles': etat_stocks['stats']['total_faibles']
            }
        }
