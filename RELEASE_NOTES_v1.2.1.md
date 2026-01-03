# Release v1.2.1 - Standardisation et Corrections

**Date:** 3 Janvier 2026

---

## Corrections

### 1. Correction de `items_count`
- **Avant** : Retournait la somme des quantités (ex: bracelet x5 + collier x2 = 7)
- **Après** : Retourne le nombre de lignes d'articles distinctes (ex: bracelet x5 + collier x2 = 2)

### 2. Nouveau Champ `repere`
- Ajout du champ `repere` (TEXT) pour le point de repère de livraison
- Disponible dans tous les endpoints :
  - `GET /orders` (liste)
  - `GET /orders/{id}` (détail)
  - `GET /orders_minimal_info` (liste minimale)
  - `POST /orders` (création)
  - `PUT /orders/{id}` (mise à jour)

### 3. Standardisation des Noms de Champs (Français)
Tous les champs de l'endpoint `GET /orders_minimal_info` sont maintenant en français pour être cohérents avec les autres endpoints :

| Ancien nom (EN) | Nouveau nom (FR) |
|-----------------|------------------|
| `order_number` | `numero` |
| `customer_name` | `client_nom` |
| `customer_phone` | `client_telephone` |
| `city` | `ville` |
| `address` | `adresse_livraison` |
| `desired_date` | `date_souhaitee` |
| `is_paid` | `est_paye` |
| `payment_type` | `type_paiement` |
| `payment_ref` | `mobile_money_ref` |
| `payment_sender_phone` | `mobile_money_numero` |
| `courier_name` | `livreur_nom` |
| `total_amount_ar` | `montant_total` |

---

## Nouveau Format `GET /orders_minimal_info`

```json
{
  "orders": [
    {
      "id": 123,
      "numero": "CMD-20260102-123",
      "status": "confirmee",
      "created_at": "2026-01-02T10:00:00",
      "client_nom": "Rakoto",
      "client_telephone": "0341234567",
      "ville": "Antananarivo",
      "adresse_livraison": "Behoririka",
      "repere": "Près de la pharmacie",
      "date_souhaitee": "2026-01-03",
      "est_paye": false,
      "type_paiement": null,
      "mobile_money_ref": null,
      "mobile_money_numero": null,
      "livreur_nom": null,
      "items_count": 2,
      "montant_total": 26000
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

---

## Swagger

- Mise à jour de la documentation Swagger avec les nouveaux noms de champs
- Ajout des schemas de réponse pour tous les endpoints Orders
- Version API : 1.2.1

---

## Migration Base de Données

Script disponible :
```
migrations/004_add_repere_field.sql
```

Contenu :
```sql
ALTER TABLE orders ADD COLUMN IF NOT EXISTS repere TEXT;
COMMENT ON COLUMN orders.repere IS 'Point de repère pour la livraison';
```

---

## Fichiers Modifiés

- `app/models/order.py` - Ajout repere, correction items_count, standardisation to_minimal_dict()
- `app/schemas/order.py` - Ajout champ repere dans les schemas
- `app/api/v1/orders.py` - Mise à jour Swagger documentation
- `app/app.py` - Mise à jour définitions Swagger globales
- `migrations/004_add_repere_field.sql` - Migration pour le champ repere

---

## Breaking Changes

**Attention** : L'endpoint `GET /orders_minimal_info` a changé ses noms de champs.
Les clients utilisant cet endpoint doivent mettre à jour leur code pour utiliser les nouveaux noms français.
