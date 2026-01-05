# Release v1.2.2 - Paiement Flexible & Champ est_paye

**Date:** 5 Janvier 2026

---

## Nouveautés

### 1. Champ `est_paye` disponible partout
Le champ `est_paye` (boolean) est maintenant retourné dans **tous les endpoints** :
- `GET /orders` (liste)
- `GET /orders/{id}` (détail)
- `GET /orders_minimal_info` (liste minimale)

**Logique :** `est_paye = true` si `date_paiement` n'est pas null.

### 2. Paiement Flexible
Le paiement est maintenant **indépendant du flux de statuts**. Il peut être enregistré à tout moment :
- Après confirmation
- Pendant la préparation
- Pendant la livraison
- À la livraison

**Endpoint :** `POST /orders/{id}/pay`

### 3. Nouveau Workflow Simplifié
Le statut `payee` n'est plus obligatoire dans le flux.

**Ancien workflow :**
```
brouillon → confirmee → payee → en_preparation → en_livraison → livree
```

**Nouveau workflow :**
```
brouillon → confirmee → en_preparation → en_livraison → livree
```

Le paiement se fait via `POST /orders/{id}/pay` à n'importe quel moment.

---

## Changements API

### Nouveau champ dans les réponses

| Champ | Type | Description |
|-------|------|-------------|
| `est_paye` | boolean | `true` si la commande a été payée |

### Endpoint `POST /orders/{id}/pay` modifié

**Avant :**
- Requiert statut `confirmee`
- Change le statut vers `payee`

**Après :**
- Peut être appelé depuis n'importe quel statut (sauf `brouillon` et `annulee`)
- Ne change PAS le statut
- Enregistre uniquement les infos de paiement (`date_paiement`, `type_paiement`, etc.)

### Transitions de statut mises à jour

| Statut actuel | Transitions possibles |
|---------------|----------------------|
| brouillon | confirmee, annulee |
| confirmee | en_preparation, annulee |
| en_preparation | en_livraison, annulee |
| en_livraison | livree, annulee |
| livree | (aucune) |
| annulee | (aucune) |

---

## Exemple d'utilisation

### Scénario : Paiement à la livraison

```bash
# 1. Créer commande
POST /orders → status: brouillon

# 2. Confirmer
POST /orders/{id}/confirm → status: confirmee

# 3. Préparer (SANS payer)
PATCH /orders/{id}/status {"status": "en_preparation"} → status: en_preparation, est_paye: false

# 4. Expédier
PATCH /orders/{id}/status {"status": "en_livraison"} → status: en_livraison, est_paye: false

# 5. Payer (au moment de la livraison)
POST /orders/{id}/pay {"type_paiement": "cash", "montant_paye": 25000} → est_paye: true

# 6. Livrer
PATCH /orders/{id}/status {"status": "livree"} → status: livree, est_paye: true
```

---

## Corrections incluses (v1.2.1)

- **`items_count`** : Retourne le nombre de lignes distinctes (pas la somme des quantités)
- **Champ `repere`** : Point de repère pour la livraison
- **Standardisation FR** : Tous les noms de champs en français dans `/orders_minimal_info`

---

## Fichiers modifiés

- `app/models/order.py` - Nouveau workflow, propriété `is_paid` basée sur `date_paiement`
- `app/schemas/order.py` - Ajout champ `est_paye`
- `app/services/order_service.py` - Paiement flexible
- `app/api/v1/orders.py` - Documentation Swagger mise à jour
- `app/app.py` - Version API 1.2.2

---

## Migration

Aucune migration requise pour v1.2.2 (changements code uniquement).

Migration v1.2.1 (si pas encore appliquée) :
```sql
-- migrations/004_add_repere_field.sql
ALTER TABLE orders ADD COLUMN IF NOT EXISTS repere TEXT;
```

---

## Breaking Changes

**Attention** : Le comportement de `POST /orders/{id}/pay` a changé :
- Ne change plus automatiquement le statut vers `payee`
- Le statut reste inchangé après paiement

Les clients qui dépendaient du changement de statut automatique doivent adapter leur code.
