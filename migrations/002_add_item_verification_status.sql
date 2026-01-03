-- ==============================================
-- Migration 002: Ajout du statut de vérification sur les articles
-- Date: 2025-01-03
-- ==============================================

-- ==============================================
-- 1. Ajout du champ verification_status à la table order_items
-- ==============================================

ALTER TABLE order_items ADD COLUMN IF NOT EXISTS verification_status VARCHAR(20) NOT NULL DEFAULT 'a_verifier';

-- Commentaire sur le nouveau champ
COMMENT ON COLUMN order_items.verification_status IS 'Statut de vérification de l''article: a_verifier ou ok';

-- ==============================================
-- Note: Les valeurs possibles sont:
-- - 'a_verifier' : Article à vérifier (valeur par défaut)
-- - 'ok' : Article vérifié
-- ==============================================
