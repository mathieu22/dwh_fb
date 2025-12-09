# Contexte et Statut de Développement - Backend Flask Dashboard FB

## 1. Vue d'ensemble du projet

### Description
Backend API REST Flask pour une plateforme de gestion des commandes avec :
- Dashboard pour le suivi des ventes et KPIs
- Module Admin pour la gestion complète (articles, utilisateurs, stocks, commandes)
- Historisation complète de toutes les entités (audit trail)

### Stack technique
- **Framework**: Flask 3.0
- **ORM**: SQLAlchemy 2.0 + Flask-SQLAlchemy
- **Base de données**: PostgreSQL
- **Authentification**: JWT (Flask-JWT-Extended)
- **Sérialisation**: Marshmallow
- **Migrations**: Flask-Migrate (Alembic)

---

## 2. Architecture du projet

```
backend/
├── app/
│   ├── __init__.py           # Export create_app
│   ├── app.py                # Factory Flask + configuration
│   ├── config.py             # Configuration multi-environnement
│   ├── extensions.py         # Extensions Flask (db, jwt, cors, etc.)
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py   # Blueprint API v1
│   │       ├── auth.py       # Authentification (login, me, refresh)
│   │       ├── dashboard.py  # KPIs et statistiques
│   │       ├── products.py   # CRUD Produits
│   │       ├── categories.py # CRUD Catégories
│   │       ├── users.py      # CRUD Utilisateurs
│   │       ├── stocks.py     # Gestion des stocks
│   │       └── orders.py     # Gestion des commandes
│   │
│   ├── models/
│   │   ├── __init__.py       # Export des modèles
│   │   ├── user.py           # Modèle User
│   │   ├── category.py       # Modèle Category
│   │   ├── product.py        # Modèle Product
│   │   ├── stock.py          # Modèles Stock + StockMovement
│   │   └── order.py          # Modèles Order + OrderItem
│   │
│   ├── schemas/
│   │   ├── __init__.py       # Export des schemas
│   │   ├── user.py           # Schemas User
│   │   ├── category.py       # Schemas Category
│   │   ├── product.py        # Schemas Product
│   │   ├── stock.py          # Schemas Stock
│   │   └── order.py          # Schemas Order
│   │
│   ├── services/
│   │   ├── __init__.py       # Export des services
│   │   ├── dashboard_service.py  # Logique KPIs
│   │   ├── stock_service.py      # Logique stocks
│   │   └── order_service.py      # Logique commandes
│   │
│   └── core/
│       ├── __init__.py       # Export core
│       ├── audit_mixin.py    # AuditMixin + SoftDeleteMixin
│       ├── security.py       # JWT + décorateurs rôles
│       └── utils.py          # Utilitaires (pagination, etc.)
│
├── migrations/               # Migrations Alembic
├── tests/                    # Tests unitaires et intégration
├── .env                      # Variables d'environnement
├── requirements.txt          # Dépendances Python
├── init_db.py               # Script init DB Python
└── init_db.sql              # Script init DB SQL
```

---

## 3. Fonctionnalités implémentées

### 3.1 Système d'audit (Historisation)

**AuditMixin** - Automatique sur toutes les entités :
- `created_at` : Date de création (auto)
- `updated_at` : Date de modification (auto)
- `created_by` : ID utilisateur créateur (auto via JWT)
- `updated_by` : ID utilisateur modificateur (auto via JWT)

**SoftDeleteMixin** - Suppression logique :
- `is_deleted` : Marqueur de suppression
- `deleted_at` : Date de suppression
- `deleted_by` : ID utilisateur suppresseur

### 3.2 Authentification et Sécurité

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/v1/auth/login` | POST | Connexion (retourne JWT) |
| `/api/v1/auth/refresh` | POST | Rafraîchir le token |
| `/api/v1/auth/me` | GET | Profil utilisateur connecté |
| `/api/v1/auth/change-password` | POST | Changer mot de passe |

**Rôles disponibles** :
- `admin` : Accès complet
- `controleur` : Gestion produits, stocks, commandes
- `livreur` : Gestion livraisons
- `simple_utilisateur` : Accès lecture

### 3.3 Dashboard (KPIs)

| Endpoint | Description |
|----------|-------------|
| `/api/v1/dashboard/summary` | Résumé complet avec tous les KPIs |
| `/api/v1/dashboard/chiffre-affaires` | CA total sur période |
| `/api/v1/dashboard/ventes-par-jour` | Ventes groupées par jour |
| `/api/v1/dashboard/commandes` | Stats commandes par statut |
| `/api/v1/dashboard/commandes-details` | Détails commandes avec articles |
| `/api/v1/dashboard/ventes-par-article` | Top articles vendus |
| `/api/v1/dashboard/ventes-par-categorie` | Ventes par catégorie |
| `/api/v1/dashboard/etat-stocks` | État stocks (ruptures, alertes) |
| `/api/v1/dashboard/panier-moyen` | Panier moyen |

**Paramètres de période** : `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

### 3.4 CRUD Produits

| Endpoint | Méthode | Rôle requis |
|----------|---------|-------------|
| `/api/v1/products` | GET | Tous |
| `/api/v1/products/{id}` | GET | Tous |
| `/api/v1/products` | POST | Admin, Controleur |
| `/api/v1/products/{id}` | PUT | Admin, Controleur |
| `/api/v1/products/{id}` | DELETE | Admin |
| `/api/v1/products/{id}/toggle-status` | PATCH | Admin, Controleur |

### 3.5 CRUD Catégories

| Endpoint | Méthode | Rôle requis |
|----------|---------|-------------|
| `/api/v1/categories` | GET | Tous |
| `/api/v1/categories/all` | GET | Tous (sans pagination) |
| `/api/v1/categories/{id}` | GET | Tous |
| `/api/v1/categories/{id}/products` | GET | Tous |
| `/api/v1/categories` | POST | Admin |
| `/api/v1/categories/{id}` | PUT | Admin |
| `/api/v1/categories/{id}` | DELETE | Admin |
| `/api/v1/categories/reorder` | POST | Admin |

### 3.6 CRUD Utilisateurs

| Endpoint | Méthode | Rôle requis |
|----------|---------|-------------|
| `/api/v1/users` | GET | Admin |
| `/api/v1/users/{id}` | GET | Admin |
| `/api/v1/users` | POST | Admin |
| `/api/v1/users/{id}` | PUT | Admin |
| `/api/v1/users/{id}` | DELETE | Admin |
| `/api/v1/users/{id}/toggle-status` | PATCH | Admin |
| `/api/v1/users/livreurs` | GET | Tous |
| `/api/v1/users/roles` | GET | Admin |

### 3.7 Gestion des Stocks

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/v1/stocks` | GET | Liste tous les stocks |
| `/api/v1/stocks/{product_id}` | GET | Stock d'un produit |
| `/api/v1/stocks/{product_id}` | PUT | Modifier seuil alerte |
| `/api/v1/stocks/movements` | GET | Historique mouvements |
| `/api/v1/stocks/{product_id}/movements` | GET | Mouvements d'un produit |
| `/api/v1/stocks/movements` | POST | Créer un mouvement |
| `/api/v1/stocks/entry` | POST | Entrée de stock |
| `/api/v1/stocks/exit` | POST | Sortie de stock |
| `/api/v1/stocks/alerts` | GET | Alertes stock |

**Types de mouvement** : `entree`, `sortie`, `ajustement`, `vente`, `retour`

### 3.8 Gestion des Commandes

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/v1/orders` | GET | Liste commandes |
| `/api/v1/orders/{id}` | GET | Détail commande |
| `/api/v1/orders/by-numero/{numero}` | GET | Commande par numéro |
| `/api/v1/orders` | POST | Créer commande |
| `/api/v1/orders/{id}` | PUT | Modifier commande |
| `/api/v1/orders/{id}` | DELETE | Supprimer commande |
| `/api/v1/orders/{id}/items` | POST | Ajouter article |
| `/api/v1/orders/{id}/items/{item_id}` | DELETE | Supprimer article |
| `/api/v1/orders/{id}/confirm` | POST | Confirmer commande |
| `/api/v1/orders/{id}/status` | PATCH | Changer statut |
| `/api/v1/orders/{id}/cancel` | POST | Annuler commande |
| `/api/v1/orders/{id}/assign-livreur` | POST | Assigner livreur |
| `/api/v1/orders/statuses` | GET | Liste statuts |

**Workflow commandes** :
```
brouillon → confirmée → en_preparation → en_livraison → livrée
     ↓           ↓              ↓               ↓
  annulée    annulée        annulée         annulée
```

---

## 4. Instructions de déploiement

### 4.1 Installation

```bash
# Cloner et aller dans le dossier
cd backend

# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos paramètres
```

### 4.2 Base de données

```bash
# Créer la base PostgreSQL
createdb dashboard_fb

# Initialiser avec Flask-Migrate
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# OU utiliser le script Python
python init_db.py

# OU utiliser le script SQL
psql -d dashboard_fb -f init_db.sql
```

### 4.3 Lancer le serveur

```bash
# Développement
flask run --debug

# OU
python -m app.app

# Production (gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

---

## 5. Utilisateurs de test

| Email | Mot de passe | Rôle |
|-------|--------------|------|
| admin@example.com | admin123 | admin |
| controleur@example.com | controleur123 | controleur |
| livreur@example.com | livreur123 | livreur |
| user@example.com | user123 | simple_utilisateur |

---

## 6. Exemples d'utilisation API

### Login
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'
```

### Créer un produit
```bash
curl -X POST http://localhost:5000/api/v1/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "nom": "Nouveau Produit",
    "prix": 15.99,
    "category_id": 1,
    "stock_initial": 50
  }'
```

### Créer une commande
```bash
curl -X POST http://localhost:5000/api/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "client_nom": "Jean Dupont",
    "client_telephone": "0612345678",
    "items": [
      {"product_id": 1, "quantity": 2},
      {"product_id": 3, "quantity": 1}
    ]
  }'
```

### Dashboard
```bash
curl -X GET "http://localhost:5000/api/v1/dashboard/summary?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer <token>"
```

---

## 7. Statut de développement

### Complété
- [x] Architecture projet Flask
- [x] Configuration multi-environnement
- [x] AuditMixin avec historisation automatique
- [x] SoftDelete pour toutes les entités
- [x] Authentification JWT complète
- [x] Système de rôles avec décorateurs
- [x] CRUD Produits avec stock initial
- [x] CRUD Catégories
- [x] CRUD Utilisateurs
- [x] Gestion des stocks + mouvements
- [x] Gestion des commandes avec workflow
- [x] Dashboard avec KPIs complets
- [x] Script d'initialisation DB

### À faire (optionnel)
- [ ] Tests unitaires et intégration
- [ ] Documentation OpenAPI/Swagger
- [ ] Dockerfile et docker-compose
- [ ] Cache Redis pour les KPIs
- [ ] Webhooks pour notifications
- [ ] Export CSV/Excel des rapports

---

## 8. Notes importantes

### Sécurité
- Tous les mots de passe sont hashés (Werkzeug)
- JWT avec expiration configurable
- CORS configuré pour les origines autorisées
- Headers de sécurité (X-Frame-Options, etc.)

### Performance
- Pagination sur toutes les listes
- Index sur les colonnes fréquemment requêtées
- Jointures optimisées pour le dashboard

### Audit
- Chaque modification est tracée
- Impossible d'insérer sans `created_by`
- Soft delete pour conserver l'historique
