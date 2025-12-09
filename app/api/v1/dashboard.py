"""
API Dashboard - KPIs et statistiques
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from . import api_v1
from app.core.audit_mixin import set_current_user_id
from app.core.utils import get_date_range_params
from app.services.dashboard_service import DashboardService


@api_v1.route('/dashboard/summary', methods=['GET'])
@jwt_required()
def dashboard_summary():
    """
    Résumé du dashboard avec tous les KPIs principaux
    ---
    tags:
      - Dashboard
    summary: Vue d'ensemble des KPIs
    description: |
      Retourne tous les indicateurs clés de performance (KPIs) en un seul appel.
      Inclut: chiffre d'affaires, nombre de commandes, panier moyen, taux de livraison,
      évolution par rapport à la période précédente, top produits et alertes stock.
      Par défaut, retourne les données des 30 derniers jours.
    security:
      - Bearer: []
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
        description: Date de début (YYYY-MM-DD). Par défaut J-30.
      - name: end_date
        in: query
        type: string
        format: date
        description: Date de fin (YYYY-MM-DD). Par défaut aujourd'hui.
    responses:
      200:
        description: Ensemble des KPIs avec période et comparaison
    """
    set_current_user_id(get_jwt_identity())
    start_date, end_date = get_date_range_params()

    return jsonify({
        'periode': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        },
        'kpis': DashboardService.get_kpis_avances(start_date, end_date)
    }), 200


@api_v1.route('/dashboard/chiffre-affaires', methods=['GET'])
@jwt_required()
def chiffre_affaires():
    """
    Chiffre d'affaires total sur la période
    ---
    tags:
      - Dashboard
    summary: Chiffre d'affaires
    description: |
      Calcule le chiffre d'affaires total sur la période spécifiée.
      Seules les commandes avec statut 'livree' sont comptabilisées.
      Le montant est exprimé dans la devise configurée (Ariary par défaut).
    security:
      - Bearer: []
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
        description: Date de début (YYYY-MM-DD)
      - name: end_date
        in: query
        type: string
        format: date
        description: Date de fin (YYYY-MM-DD)
    responses:
      200:
        description: Montant total du chiffre d'affaires
    """
    set_current_user_id(get_jwt_identity())
    start_date, end_date = get_date_range_params()

    ca = DashboardService.get_chiffre_affaires(start_date, end_date)

    return jsonify({
        'periode': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        },
        'chiffre_affaires': ca
    }), 200


@api_v1.route('/dashboard/ventes-par-jour', methods=['GET'])
@jwt_required()
def ventes_par_jour():
    """
    Ventes groupées par jour
    ---
    tags:
      - Dashboard
    summary: Évolution des ventes quotidiennes
    description: |
      Retourne les ventes agrégées par jour pour construire un graphique d'évolution.
      Chaque entrée contient: date, nombre de commandes, montant total.
      Utile pour visualiser les tendances et identifier les pics de vente.
    security:
      - Bearer: []
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
        description: Date de début (YYYY-MM-DD)
      - name: end_date
        in: query
        type: string
        format: date
        description: Date de fin (YYYY-MM-DD)
    responses:
      200:
        description: Liste des ventes par jour avec date, nb_commandes et montant
    """
    set_current_user_id(get_jwt_identity())
    start_date, end_date = get_date_range_params()

    ventes = DashboardService.get_ventes_par_jour(start_date, end_date)

    return jsonify({
        'periode': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        },
        'ventes': ventes
    }), 200


@api_v1.route('/dashboard/commandes', methods=['GET'])
@jwt_required()
def commandes_stats():
    """
    Statistiques des commandes par statut
    ---
    tags:
      - Dashboard
    summary: Répartition des commandes par statut
    description: |
      Retourne le nombre total de commandes et leur répartition par statut.
      Statuts: brouillon, confirmee, en_preparation, en_livraison, livree, annulee.
      Permet de visualiser le pipeline des commandes et identifier les goulots d'étranglement.
    security:
      - Bearer: []
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
        description: Date de début (YYYY-MM-DD)
      - name: end_date
        in: query
        type: string
        format: date
        description: Date de fin (YYYY-MM-DD)
    responses:
      200:
        description: Total et décompte par statut
    """
    set_current_user_id(get_jwt_identity())
    start_date, end_date = get_date_range_params()

    total = DashboardService.get_nombre_commandes(start_date, end_date)
    par_statut = DashboardService.get_commandes_par_statut(start_date, end_date)

    return jsonify({
        'periode': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        },
        'total': total,
        'par_statut': par_statut
    }), 200


@api_v1.route('/dashboard/commandes-details', methods=['GET'])
@jwt_required()
def commandes_details():
    """
    Détails des commandes par jour avec articles
    ---
    tags:
      - Dashboard
    summary: Détails complets des commandes quotidiennes
    description: |
      Retourne les commandes groupées par jour avec le détail des articles vendus.
      Inclut pour chaque jour: liste des commandes, articles par commande, quantités et prix.
      Idéal pour les rapports détaillés et l'analyse fine des ventes.
    security:
      - Bearer: []
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
        description: Date de début (YYYY-MM-DD)
      - name: end_date
        in: query
        type: string
        format: date
        description: Date de fin (YYYY-MM-DD)
    responses:
      200:
        description: Commandes détaillées groupées par jour
    """
    set_current_user_id(get_jwt_identity())
    start_date, end_date = get_date_range_params()

    details = DashboardService.get_details_commandes_par_jour(start_date, end_date)

    return jsonify({
        'periode': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        },
        'details': details
    }), 200


@api_v1.route('/dashboard/ventes-par-article', methods=['GET'])
@jwt_required()
def ventes_par_article():
    """
    Ventes par article (top vendus)
    ---
    tags:
      - Dashboard
    summary: Classement des produits les plus vendus
    description: |
      Retourne le classement des articles par quantité vendue et chiffre d'affaires généré.
      Inclut: nom du produit, quantité totale vendue, montant total, prix unitaire moyen.
      Le paramètre limit permet de limiter le nombre de résultats (défaut: 10).
    security:
      - Bearer: []
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
        description: Date de début (YYYY-MM-DD)
      - name: end_date
        in: query
        type: string
        format: date
        description: Date de fin (YYYY-MM-DD)
      - name: limit
        in: query
        type: integer
        default: 10
        description: Nombre maximum de produits à retourner
    responses:
      200:
        description: Liste des top produits avec statistiques de vente
    """
    set_current_user_id(get_jwt_identity())
    start_date, end_date = get_date_range_params()
    limit = request.args.get('limit', 10, type=int)

    ventes = DashboardService.get_ventes_par_article(start_date, end_date, limit=limit)

    return jsonify({
        'periode': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        },
        'ventes': ventes
    }), 200


@api_v1.route('/dashboard/ventes-par-categorie', methods=['GET'])
@jwt_required()
def ventes_par_categorie():
    """
    Ventes par catégorie
    ---
    tags:
      - Dashboard
    summary: Répartition des ventes par catégorie
    description: |
      Retourne les ventes agrégées par catégorie de produits.
      Inclut: nom de la catégorie, nombre d'articles vendus, montant total, pourcentage du CA.
      Utile pour analyser la performance des différentes gammes de produits.
    security:
      - Bearer: []
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
        description: Date de début (YYYY-MM-DD)
      - name: end_date
        in: query
        type: string
        format: date
        description: Date de fin (YYYY-MM-DD)
    responses:
      200:
        description: Ventes agrégées par catégorie avec pourcentages
    """
    set_current_user_id(get_jwt_identity())
    start_date, end_date = get_date_range_params()

    ventes = DashboardService.get_ventes_par_categorie(start_date, end_date)

    return jsonify({
        'periode': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        },
        'ventes': ventes
    }), 200


@api_v1.route('/dashboard/etat-stocks', methods=['GET'])
@jwt_required()
def etat_stocks():
    """
    État des stocks (ruptures, faibles stocks)
    ---
    tags:
      - Dashboard
    summary: Alertes et état des stocks
    description: |
      Retourne l'état actuel des stocks avec les alertes.
      Catégories: ruptures de stock (quantité = 0), stocks faibles (quantité <= seuil d'alerte).
      Inclut pour chaque produit: nom, quantité actuelle, seuil d'alerte configuré.
      Permet d'anticiper les réapprovisionnements.
    security:
      - Bearer: []
    responses:
      200:
        description: Liste des ruptures et stocks faibles
    """
    set_current_user_id(get_jwt_identity())

    etat = DashboardService.get_etat_stocks()

    return jsonify(etat), 200


@api_v1.route('/dashboard/panier-moyen', methods=['GET'])
@jwt_required()
def panier_moyen():
    """
    Panier moyen sur la période
    ---
    tags:
      - Dashboard
    summary: Valeur moyenne du panier
    description: |
      Calcule le panier moyen (montant moyen par commande) sur la période.
      Formule: Chiffre d'affaires total / Nombre de commandes livrées.
      Indicateur clé pour mesurer la valeur client et l'efficacité des ventes additionnelles.
    security:
      - Bearer: []
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
        description: Date de début (YYYY-MM-DD)
      - name: end_date
        in: query
        type: string
        format: date
        description: Date de fin (YYYY-MM-DD)
    responses:
      200:
        description: Montant du panier moyen arrondi à 2 décimales
    """
    set_current_user_id(get_jwt_identity())
    start_date, end_date = get_date_range_params()

    panier = DashboardService.get_panier_moyen(start_date, end_date)

    return jsonify({
        'periode': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        },
        'panier_moyen': round(panier, 2)
    }), 200
