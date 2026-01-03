-- ==============================================
-- Migration 004: Ajout du champ repere (point de repère)
-- Date: 2026-01-03
-- ==============================================

-- Ajout du champ repere à la table orders
ALTER TABLE orders ADD COLUMN IF NOT EXISTS repere TEXT;
COMMENT ON COLUMN orders.repere IS 'Point de repère pour la livraison';
