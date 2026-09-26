ALTER TABLE orders ADD COLUMN shipping_address TEXT;

-- Preserve both reader contracts throughout the rollback window.
CREATE TRIGGER sync_old_update AFTER UPDATE OF delivery_address ON orders
WHEN NEW.delivery_address IS NOT NEW.shipping_address
BEGIN
  UPDATE orders SET shipping_address = NEW.delivery_address WHERE id = NEW.id;
END;

CREATE TRIGGER sync_new_update AFTER UPDATE OF shipping_address ON orders
WHEN NEW.shipping_address IS NOT NEW.delivery_address
BEGIN
  UPDATE orders SET delivery_address = NEW.shipping_address WHERE id = NEW.id;
END;

CREATE TRIGGER sync_old_insert AFTER INSERT ON orders
WHEN NEW.shipping_address IS NULL
BEGIN
  UPDATE orders SET shipping_address = NEW.delivery_address WHERE id = NEW.id;
END;

-- Backfill only after the synchronization triggers are active.
UPDATE orders SET shipping_address = delivery_address;
