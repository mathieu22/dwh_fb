-- ==============================================
-- Migration 003: Ajout des champs ville, date_souhaitee et table order_history
-- Date: 2025-01-03
-- ==============================================

-- ==============================================
-- 1. Ajout des nouveaux champs à la table orders
-- ==============================================

-- Ville de livraison
ALTER TABLE orders ADD COLUMN IF NOT EXISTS ville VARCHAR(100);
COMMENT ON COLUMN orders.ville IS 'Ville de livraison';

-- Date souhaitée de livraison
ALTER TABLE orders ADD COLUMN IF NOT EXISTS date_souhaitee DATE;
COMMENT ON COLUMN orders.date_souhaitee IS 'Date de livraison souhaitée par le client';

-- ==============================================
-- 2. Création de la table order_history
-- ==============================================

CREATE TABLE IF NOT EXISTS order_history (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    event VARCHAR(50) NOT NULL,
    note TEXT,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_order_history_order ON order_history(order_id);
CREATE INDEX IF NOT EXISTS idx_order_history_created_at ON order_history(created_at);

COMMENT ON TABLE order_history IS 'Historique des événements des commandes';
COMMENT ON COLUMN order_history.event IS 'Type d''événement: CREATED, CONFIRMED, PAID, IN_PREPARATION, IN_DELIVERY, DELIVERED, CANCELLED, etc.';
COMMENT ON COLUMN order_history.note IS 'Note optionnelle associée à l''événement';
COMMENT ON COLUMN order_history.user_id IS 'Utilisateur ayant effectué l''action';

-- ==============================================
-- Note: Les événements possibles sont:
-- - CREATED : Commande créée
-- - CONFIRMED : Commande confirmée
-- - PAID : Commande payée
-- - IN_PREPARATION : En préparation
-- - IN_DELIVERY : En livraison
-- - DELIVERED : Livrée
-- - CANCELLED : Annulée
-- - ITEM_ADDED : Article ajouté
-- - ITEM_REMOVED : Article supprimé
-- - ITEM_UPDATED : Article modifié
-- - COURIER_ASSIGNED : Livreur assigné
-- ==============================================
