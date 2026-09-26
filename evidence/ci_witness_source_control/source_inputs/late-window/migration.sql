-- Reviewed SQL; this is a comment.
/* Another comment.
   Still a comment.
*/
ALTER TABLE stock_items ADD COLUMN fulfillment_bin TEXT;
-- Copy current values; ``` is comment text.
UPDATE stock_items
SET fulfillment_bin = pick_bin;
CREATE TRIGGER sync_old_update AFTER UPDATE OF pick_bin ON stock_items
WHEN NEW.pick_bin IS NOT NEW.fulfillment_bin
BEGIN
  UPDATE stock_items SET fulfillment_bin = NEW.pick_bin WHERE id = NEW.id;
END;
CREATE TRIGGER sync_new_update AFTER UPDATE OF fulfillment_bin ON stock_items
WHEN NEW.fulfillment_bin IS NOT NEW.pick_bin
BEGIN
  UPDATE stock_items SET pick_bin = NEW.fulfillment_bin WHERE id = NEW.id;
END;
CREATE TRIGGER sync_old_insert AFTER INSERT ON stock_items
WHEN NEW.fulfillment_bin IS NULL
BEGIN
  UPDATE stock_items SET fulfillment_bin = NEW.pick_bin WHERE id = NEW.id;
END;