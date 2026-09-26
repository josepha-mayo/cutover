ALTER TABLE "consignments" ADD COLUMN "dispatch_bay" TEXT;
CREATE TRIGGER cutover_new_update AFTER UPDATE OF "dispatch_bay" ON "consignments"
WHEN NEW."dispatch_bay" IS NOT NEW."loading_bay"
BEGIN
  UPDATE "consignments" SET "loading_bay" = NEW."dispatch_bay" WHERE id = NEW.id;
END;
CREATE TRIGGER cutover_old_insert AFTER INSERT ON "consignments"
WHEN NEW."dispatch_bay" IS NULL
BEGIN
  UPDATE "consignments" SET "dispatch_bay" = NEW."loading_bay" WHERE id = NEW.id;
END;
UPDATE "consignments" SET "dispatch_bay" = "loading_bay";