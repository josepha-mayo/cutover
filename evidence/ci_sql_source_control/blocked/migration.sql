ALTER TABLE stock_items ADD COLUMN fulfillment_bin TEXT;
CREATE TRIGGER sync_insert_to_fulfillment AFTER INSERT ON stock_items
WHEN NEW.fulfillment_bin IS NULL
BEGIN
  UPDATE stock_items SET fulfillment_bin = NEW.pick_bin WHERE id = NEW.id;
END;
UPDATE stock_items SET fulfillment_bin = pick_bin WHERE fulfillment_bin IS NULL;