# Release v1.2.0 - Order Management Enhancements

**Date:** 3 Janvier 2026

---

## Nouvelles Fonctionnalités

### 1. Comptage des Commandes par Statut
- **Nouvel endpoint** `GET /orders/counts` pour obtenir le nombre de commandes par statut
- Retourne le total et le décompte par statut (brouillon, confirmee, payee, etc.)
- Idéal pour afficher les badges/compteurs sur les onglets de filtrage

### 2. Vérification des Articles
- **Nouveau statut de vérification** pour chaque article de commande : `a_verifier` ou `ok`
- Permet au back-office de checker si un article a été vérifié
- **Nouveaux endpoints :**
  - `PATCH /orders/<id>/items/<item_id>/verify` - Toggle ou définit le statut de vérification
  - `PATCH /orders/<id>/items/verify-all` - Vérifie tous les articles d'une commande

### 3. Modification de Quantité d'Article
- **Nouvel endpoint** `PATCH /orders/<id>/items/<item_id>` pour modifier la quantité d'un article
- Recalcul automatique du montant total de la commande
- Uniquement pour les commandes en statut `brouillon`

### 4. Endpoint Liste Minimale
- **Nouvel endpoint** `GET /orders_minimal_info` optimisé pour les listes
- Retourne uniquement les informations essentielles sans les détails des articles
- Inclut : `items_count`, `total_amount_ar`, `is_paid`, `courier_name`, etc.

### 5. Historique des Commandes
- **Nouvelle table** `order_history` pour tracer tous les événements d'une commande
- **Nouvel endpoint** `GET /orders/history/<id>` pour consulter l'historique
- Événements tracés : CREATED, CONFIRMED, PAID, IN_PREPARATION, IN_DELIVERY, DELIVERED, CANCELLED, etc.

### 6. Nouveaux Champs
- `ville` - Ville de livraison
- `date_souhaitee` - Date de livraison souhaitée par le client
- `items_count` - Nombre total d'articles (calculé)
- `total_amount_ar` - Montant total en Ariary (calculé)
- `is_paid` - Indicateur de paiement

---

## Nouveaux Endpoints API

### `GET /orders/counts`
Retourne le nombre de commandes par statut.

**Response:**
```json
{
  "counts": {
    "tous": 15,
    "brouillon": 3,
    "confirmee": 2,
    "payee": 4,
    "en_preparation": 2,
    "en_livraison": 1,
    "livree": 3,
    "annulee": 0
  }
}
```

### `PATCH /orders/<id>/items/<item_id>`
Modifie la quantité d'un article.

**Body:**
```json
{
  "quantity": 3
}
```

### `PATCH /orders/<id>/items/<item_id>/verify`
Toggle ou définit le statut de vérification d'un article.

**Body (optionnel):**
```json
{
  "verification_status": "ok"
}
```
*Sans body, bascule automatiquement entre `a_verifier` et `ok`*

### `PATCH /orders/<id>/items/verify-all`
Définit le statut de vérification de tous les articles.

**Body:**
```json
{
  "verification_status": "ok"
}
```

### `GET /orders_minimal_info`
Liste les commandes avec informations minimales (sans items).

**Paramètres:** `status`, `search`, `livreur_id`, `sort`, `order`, `page`, `per_page`

**Response:**
```json
{
  "orders": [
    {
      "id": 123,
      "order_number": "CMD-20260102-123",
      "status": "confirmee",
      "created_at": "2026-01-02T10:00:00",
      "customer_name": "Rakoto",
      "customer_phone": "0341234567",
      "city": "Antananarivo",
      "address": "Behoririka",
      "desired_date": "2026-01-03",
      "is_paid": false,
      "payment_type": null,
      "payment_ref": null,
      "payment_sender_phone": null,
      "courier_name": null,
      "items_count": 5,
      "total_amount_ar": 26000
    }
  ],
  "total": 15,
  "pages": 1,
  "current_page": 1,
  "per_page": 20,
  "has_next": false,
  "has_prev": false
}
```

### `GET /orders/history/<id>`
Retourne l'historique des événements d'une commande.

**Response:**
```json
{
  "order_id": 123,
  "order_number": "CMD-20260102-123",
  "history": [
    {
      "at": "2026-01-02T10:00:00",
      "by": "Rakoto Jean",
      "event": "CREATED",
      "note": null
    },
    {
      "at": "2026-01-02T10:05:00",
      "by": "Rakoto Jean",
      "event": "CONFIRMED",
      "note": null
    },
    {
      "at": "2026-01-02T11:00:00",
      "by": "Rabe Paul",
      "event": "PAID",
      "note": null
    }
  ]
}
```

---

## Nouveaux Champs API

### Order (Commande)
| Champ | Type | Description |
|-------|------|-------------|
| `ville` | string | Ville de livraison |
| `date_souhaitee` | date | Date de livraison souhaitée |
| `items_count` | integer | Nombre total d'articles (somme des quantités) |
| `total_amount_ar` | number | Montant total en Ariary |
| `is_paid` | boolean | True si la commande est payée |

### OrderItem (Ligne de commande)
| Champ | Type | Description |
|-------|------|-------------|
| `verification_status` | string | `a_verifier` ou `ok` |

### OrderHistory (Historique)
| Champ | Type | Description |
|-------|------|-------------|
| `at` | datetime | Date/heure de l'événement |
| `by` | string | Nom de l'utilisateur |
| `event` | string | Type d'événement |
| `note` | string | Note optionnelle |

---

## Types d'Événements Historique

| Event | Description |
|-------|-------------|
| `CREATED` | Commande créée |
| `CONFIRMED` | Commande confirmée |
| `PAID` | Commande payée |
| `IN_PREPARATION` | En préparation |
| `IN_DELIVERY` | En livraison |
| `DELIVERED` | Livrée |
| `CANCELLED` | Annulée |
| `ITEM_ADDED` | Article ajouté |
| `ITEM_REMOVED` | Article supprimé |
| `ITEM_UPDATED` | Article modifié |
| `COURIER_ASSIGNED` | Livreur assigné |

---

## Migrations Base de Données

Les migrations ont été appliquées. Scripts disponibles dans :
```
migrations/002_add_item_verification_status.sql
migrations/003_add_order_fields_and_history.sql
```

---

## Fichiers Modifiés

- `app/models/order.py` - Nouveaux champs, enums et modèle OrderHistory
- `app/api/v1/orders.py` - Nouveaux endpoints
- `migrations/002_add_item_verification_status.sql` - Migration vérification articles
- `migrations/003_add_order_fields_and_history.sql` - Migration ville, date_souhaitee, order_history
