-- ==============================================
-- Migration 001: Ajout des champs paiement, motif annulation et historique des prix
-- Date: 2025-12-30
-- ==============================================

-- ==============================================
-- 1. Ajout des nouveaux champs à la table orders
-- ==============================================

-- Motif d'annulation (obligatoire quand status = annulee)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS motif_annulation TEXT;

-- Informations de paiement (quand status = payee)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS type_paiement VARCHAR(20);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS mobile_money_numero VARCHAR(30);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS mobile_money_ref VARCHAR(100);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS montant_paye DECIMAL(12, 2);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS date_paiement TIMESTAMP;

-- Commentaires sur les nouveaux champs
COMMENT ON COLUMN orders.motif_annulation IS 'Motif obligatoire lors de l''annulation d''une commande';
COMMENT ON COLUMN orders.type_paiement IS 'Type de paiement: cash ou mobile_money';
COMMENT ON COLUMN orders.mobile_money_numero IS 'Numéro du client pour paiement mobile money';
COMMENT ON COLUMN orders.mobile_money_ref IS 'Référence de la transaction mobile money';
COMMENT ON COLUMN orders.montant_paye IS 'Montant effectivement payé';
COMMENT ON COLUMN orders.date_paiement IS 'Date et heure du paiement';

-- ==============================================
-- 2. Création de la table price_history
-- ==============================================
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    ancien_prix DECIMAL(10, 2) NOT NULL,
    nouveau_prix DECIMAL(10, 2) NOT NULL,
    date_changement TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    motif VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(date_changement);

-- Trigger pour updated_at
CREATE TRIGGER update_price_history_updated_at BEFORE UPDATE ON price_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE price_history IS 'Historique des changements de prix des produits';
COMMENT ON COLUMN price_history.ancien_prix IS 'Prix avant la modification';
COMMENT ON COLUMN price_history.nouveau_prix IS 'Nouveau prix après modification';
COMMENT ON COLUMN price_history.date_changement IS 'Date et heure du changement de prix';
COMMENT ON COLUMN price_history.motif IS 'Raison du changement de prix (optionnel)';

-- ==============================================
-- 3. Mise à jour du commentaire de la table orders
-- ==============================================
COMMENT ON TABLE orders IS 'Commandes avec workflow (brouillon -> confirmee -> payee -> en_preparation -> en_livraison -> livree)';

-- ==============================================
-- Note: Le nouveau workflow des commandes est:
-- brouillon -> confirmee -> payee -> en_preparation -> en_livraison -> livree
-- Tous les statuts peuvent aussi passer à "annulee" (sauf livree et annulee)
-- ==============================================
