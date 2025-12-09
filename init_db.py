"""
Script d'initialisation de la base de données.
Crée les tables et insère les données initiales.
"""
import os
import sys

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.app import create_app
from app.extensions import db
from app.models import User, Category, Product, Stock, StockMovement, Order, OrderItem


def init_database():
    """Initialise la base de données avec les tables et données de test."""
    app = create_app()

    with app.app_context():
        print("Création des tables...")
        db.create_all()
        print("Tables créées avec succès!")

        # Vérifier si des utilisateurs existent déjà
        if User.query.count() == 0:
            print("Création des utilisateurs par défaut...")
            create_default_users()
            print("Utilisateurs créés!")

        # Vérifier si des catégories existent déjà
        if Category.query.count() == 0:
            print("Création des catégories de test...")
            create_test_categories()
            print("Catégories créées!")

        # Vérifier si des produits existent déjà
        if Product.query.count() == 0:
            print("Création des produits de test...")
            create_test_products()
            print("Produits créés!")

        db.session.commit()
        print("\nBase de données initialisée avec succès!")
        print("\nUtilisateurs créés:")
        print("  - admin@example.com / admin123 (admin)")
        print("  - controleur@example.com / controleur123 (controleur)")
        print("  - livreur@example.com / livreur123 (livreur)")
        print("  - user@example.com / user123 (simple_utilisateur)")


def create_default_users():
    """Crée les utilisateurs par défaut."""
    users_data = [
        {
            'email': 'admin@example.com',
            'password': 'admin123',
            'nom': 'Admin',
            'prenom': 'Super',
            'role': 'admin',
            'telephone': '0600000001'
        },
        {
            'email': 'controleur@example.com',
            'password': 'controleur123',
            'nom': 'Controleur',
            'prenom': 'Jean',
            'role': 'controleur',
            'telephone': '0600000002'
        },
        {
            'email': 'livreur@example.com',
            'password': 'livreur123',
            'nom': 'Livreur',
            'prenom': 'Pierre',
            'role': 'livreur',
            'telephone': '0600000003'
        },
        {
            'email': 'user@example.com',
            'password': 'user123',
            'nom': 'Utilisateur',
            'prenom': 'Simple',
            'role': 'simple_utilisateur',
            'telephone': '0600000004'
        }
    ]

    for user_data in users_data:
        user = User(
            email=user_data['email'],
            nom=user_data['nom'],
            prenom=user_data['prenom'],
            telephone=user_data['telephone'],
            role=user_data['role'],
            is_active=True
        )
        user.set_password(user_data['password'])
        db.session.add(user)

    db.session.flush()


def create_test_categories():
    """Crée des catégories de test."""
    categories_data = [
        {'nom': 'Boissons', 'description': 'Boissons fraîches et chaudes', 'ordre': 1},
        {'nom': 'Entrées', 'description': 'Entrées et amuse-bouches', 'ordre': 2},
        {'nom': 'Plats', 'description': 'Plats principaux', 'ordre': 3},
        {'nom': 'Desserts', 'description': 'Desserts et gourmandises', 'ordre': 4},
        {'nom': 'Snacks', 'description': 'En-cas et petites faims', 'ordre': 5}
    ]

    for cat_data in categories_data:
        category = Category(**cat_data, is_active=True)
        db.session.add(category)

    db.session.flush()


def create_test_products():
    """Crée des produits de test avec leurs stocks."""
    # Récupérer les catégories
    boissons = Category.query.filter_by(nom='Boissons').first()
    entrees = Category.query.filter_by(nom='Entrées').first()
    plats = Category.query.filter_by(nom='Plats').first()
    desserts = Category.query.filter_by(nom='Desserts').first()
    snacks = Category.query.filter_by(nom='Snacks').first()

    products_data = [
        # Boissons
        {'nom': 'Coca-Cola 33cl', 'prix': 2.50, 'category_id': boissons.id, 'sku': 'COCA33', 'stock': 100},
        {'nom': 'Eau minérale 50cl', 'prix': 1.50, 'category_id': boissons.id, 'sku': 'EAU50', 'stock': 150},
        {'nom': 'Jus d\'orange 25cl', 'prix': 3.00, 'category_id': boissons.id, 'sku': 'JUS25', 'stock': 80},
        {'nom': 'Café espresso', 'prix': 1.80, 'category_id': boissons.id, 'sku': 'CAFE01', 'stock': 200},

        # Entrées
        {'nom': 'Salade verte', 'prix': 5.50, 'category_id': entrees.id, 'sku': 'SAL01', 'stock': 30},
        {'nom': 'Soupe du jour', 'prix': 4.50, 'category_id': entrees.id, 'sku': 'SOUP01', 'stock': 25},

        # Plats
        {'nom': 'Burger Classic', 'prix': 12.00, 'category_id': plats.id, 'sku': 'BURG01', 'stock': 50},
        {'nom': 'Pizza Margherita', 'prix': 10.00, 'category_id': plats.id, 'sku': 'PIZZ01', 'stock': 40},
        {'nom': 'Pâtes Carbonara', 'prix': 11.00, 'category_id': plats.id, 'sku': 'PAST01', 'stock': 35},
        {'nom': 'Poulet grillé', 'prix': 14.00, 'category_id': plats.id, 'sku': 'POUL01', 'stock': 20},

        # Desserts
        {'nom': 'Tiramisu', 'prix': 6.00, 'category_id': desserts.id, 'sku': 'TIRA01', 'stock': 15},
        {'nom': 'Crème brûlée', 'prix': 5.50, 'category_id': desserts.id, 'sku': 'CREM01', 'stock': 18},
        {'nom': 'Tarte aux pommes', 'prix': 5.00, 'category_id': desserts.id, 'sku': 'TART01', 'stock': 12},

        # Snacks
        {'nom': 'Chips nature', 'prix': 2.00, 'category_id': snacks.id, 'sku': 'CHIP01', 'stock': 60},
        {'nom': 'Cookie chocolat', 'prix': 2.50, 'category_id': snacks.id, 'sku': 'COOK01', 'stock': 45}
    ]

    for prod_data in products_data:
        stock_qty = prod_data.pop('stock')

        product = Product(
            nom=prod_data['nom'],
            prix=prod_data['prix'],
            category_id=prod_data['category_id'],
            sku=prod_data['sku'],
            description=f"Description de {prod_data['nom']}",
            is_active=True
        )
        db.session.add(product)
        db.session.flush()

        # Créer le stock
        stock = Stock(
            product_id=product.id,
            quantity=stock_qty,
            seuil_alerte=10
        )
        db.session.add(stock)

    db.session.flush()


def reset_database():
    """Supprime et recrée toutes les tables."""
    app = create_app()

    with app.app_context():
        print("Suppression des tables...")
        db.drop_all()
        print("Tables supprimées!")
        init_database()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Initialisation de la base de données')
    parser.add_argument('--reset', action='store_true', help='Supprime et recrée toutes les tables')

    args = parser.parse_args()

    if args.reset:
        reset_database()
    else:
        init_database()
