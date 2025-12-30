# Release v1.1.0 - Payment Workflow & Price History

**Date:** 30 Décembre 2025

---

## Nouvelles Fonctionnalités

### Workflow de Paiement
- **Nouveau statut "PAYEE"** ajouté au workflow des commandes
- Nouveau workflow complet : `BROUILLON → CONFIRMEE → PAYEE → EN_PREPARATION → EN_LIVRAISON → LIVREE`
- **Nouvel endpoint** `POST /orders/<id>/pay` pour enregistrer les paiements
- Support des types de paiement : `cash` et `mobile_money`
- Champs de paiement : numéro mobile money, référence transaction, montant payé

### Annulation avec Motif Obligatoire
- Le champ `motif_annulation` est maintenant **obligatoire** lors de l'annulation d'une commande
- L'endpoint `POST /orders/<id>/cancel` exige désormais un motif

### Historique des Prix
- **Nouvelle table `price_history`** pour tracer les changements de prix des produits
- Enregistrement automatique lors de la modification du prix d'un produit
- **Nouvel endpoint** `GET /products/<id>/price-history` pour consulter l'historique

### Détails Enrichis dans les Commandes
- Les items de commande incluent maintenant **tous les attributs du produit** :
  - `nom`, `sku`, `photo_url`, `description`
  - `category_id`, `category_nom`
  - `prix_actuel`, `is_active`
- Les coordonnées du **livreur** sont exposées dans les détails de commande (nom, prénom, téléphone)

---

## Nouveaux Endpoints API

### `POST /orders/<id>/pay`
Enregistre le paiement d'une commande confirmée.

**Body:**
```json
{
  "type_paiement": "mobile_money",
  "montant_paye": 150000,
  "mobile_money_numero": "034 12 345 67",
  "mobile_money_ref": "TXN123456789"
}
```

### `POST /orders/<id>/cancel`
Annule une commande (motif obligatoire).

**Body:**
```json
{
  "motif_annulation": "Client a changé d'avis"
}
```

### `GET /products/<id>/price-history`
Retourne l'historique des prix d'un produit.

**Response:**
```json
{
  "product_id": 1,
  "product_nom": "Produit A",
  "prix_actuel": 25000,
  "history": [
    {
      "ancien_prix": 20000,
      "nouveau_prix": 25000,
      "date_changement": "2025-12-30T10:00:00",
      "motif": "Augmentation fournisseur"
    }
  ],
  "count": 1
}
```

---

## Nouveaux Champs API

### Order (Commande)
| Champ | Type | Description |
|-------|------|-------------|
| `motif_annulation` | string | Observation si annulé |
| `type_paiement` | string | "cash" ou "mobile_money" |
| `mobile_money_numero` | string | Numéro du client |
| `mobile_money_ref` | string | Référence transaction |
| `montant_paye` | number | Montant payé |
| `date_paiement` | datetime | Date du paiement |
| `livreur` | object | {id, nom, prenom, telephone} |

### OrderItem (Ligne de commande)
| Champ | Type | Description |
|-------|------|-------------|
| `product` | object | Tous les attributs du produit |

**Structure de `product` dans un item:**
```json
{
  "id": 45,
  "nom": "Produit Example",
  "description": "Description du produit",
  "sku": "SKU-001",
  "photo_url": "https://example.com/photo.jpg",
  "prix_actuel": 15000.00,
  "category_id": 3,
  "category_nom": "Catégorie A",
  "is_active": true
}
```

---

## Migration Base de Données

La migration a déjà été appliquée. Pour référence, le script est disponible dans :
```
migrations/001_add_payment_and_price_history.sql
```

---

## Fichiers Modifiés
- `app/models/order.py` - Nouveaux champs et statuts
- `app/models/product.py` - Modèle PriceHistory
- `app/schemas/order.py` - Nouveaux schemas
- `app/services/order_service.py` - Méthodes pay_order et cancel_order
- `app/api/v1/orders.py` - Endpoints pay et cancel
- `app/api/v1/products.py` - Endpoint price-history
- `migrations/001_add_payment_and_price_history.sql` - Script de migration
