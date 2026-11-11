-- Synthetic source only. Keep outbox rows until downstream retention is designed.
IF OBJECT_ID('dbo.Products') IS NULL CREATE TABLE dbo.Products(product_id varchar(32) PRIMARY KEY);
IF OBJECT_ID('dbo.ChangeCounter') IS NULL BEGIN
 CREATE TABLE dbo.ChangeCounter(id int PRIMARY KEY CHECK(id=1), last_seq bigint NOT NULL);
 INSERT dbo.ChangeCounter VALUES(1,0);
END;
IF OBJECT_ID('dbo.ChangeLog') IS NULL CREATE TABLE dbo.ChangeLog(
 change_seq bigint PRIMARY KEY, entity varchar(30) NOT NULL, source_key varchar(64) NOT NULL,
 payload nvarchar(max) NOT NULL CHECK(ISJSON(payload)=1));
IF OBJECT_ID('dbo.Inventory') IS NULL CREATE TABLE dbo.Inventory(
 product_id varchar(32) PRIMARY KEY REFERENCES dbo.Products, quantity int NOT NULL CHECK(quantity>=0),
 is_deleted bit NOT NULL DEFAULT 0, updated_at datetime2(6) NOT NULL DEFAULT SYSUTCDATETIME());
IF OBJECT_ID('dbo.StockMovements') IS NULL CREATE TABLE dbo.StockMovements(
 movement_id bigint PRIMARY KEY, product_id varchar(32) NOT NULL REFERENCES dbo.Products,
 delta int NOT NULL, is_deleted bit NOT NULL DEFAULT 0,
 updated_at datetime2(6) NOT NULL DEFAULT SYSUTCDATETIME());
GO
CREATE OR ALTER TRIGGER dbo.trg_Inventory_changes ON dbo.Inventory
AFTER INSERT, UPDATE, DELETE AS
BEGIN
 SET NOCOUNT ON;
 DECLARE @n bigint=(SELECT count(*) FROM inserted i FULL JOIN deleted d ON i.product_id=d.product_id);
 IF @n=0 RETURN;
 DECLARE @previous TABLE(value bigint);
 UPDATE dbo.ChangeCounter WITH (UPDLOCK,HOLDLOCK) SET last_seq=last_seq+@n
 OUTPUT deleted.last_seq INTO @previous WHERE id=1;
 DECLARE @start bigint=(SELECT value FROM @previous);
 INSERT dbo.ChangeLog(change_seq,entity,source_key,payload)
 SELECT @start+ROW_NUMBER() OVER(ORDER BY coalesce(i.product_id,d.product_id)),
 'inventory',convert(varchar(64),coalesce(i.product_id,d.product_id)),
 (SELECT coalesce(i.product_id,d.product_id) AS product_id,coalesce(i.quantity,d.quantity) AS quantity,
    convert(bit,CASE WHEN i.product_id IS NULL THEN 1 ELSE i.is_deleted END) AS is_deleted,
    coalesce(i.updated_at,SYSUTCDATETIME()) AS updated_at FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
 FROM inserted i FULL JOIN deleted d ON i.product_id=d.product_id;
END;
GO
CREATE OR ALTER TRIGGER dbo.trg_StockMovements_changes ON dbo.StockMovements
AFTER INSERT, UPDATE, DELETE AS
BEGIN
 SET NOCOUNT ON;
 DECLARE @n bigint=(SELECT count(*) FROM inserted i FULL JOIN deleted d ON i.movement_id=d.movement_id);
 IF @n=0 RETURN;
 DECLARE @previous TABLE(value bigint);
 UPDATE dbo.ChangeCounter WITH (UPDLOCK,HOLDLOCK) SET last_seq=last_seq+@n
 OUTPUT deleted.last_seq INTO @previous WHERE id=1;
 DECLARE @start bigint=(SELECT value FROM @previous);
 INSERT dbo.ChangeLog(change_seq,entity,source_key,payload)
 SELECT @start+ROW_NUMBER() OVER(ORDER BY coalesce(i.movement_id,d.movement_id)),
 'stock_movements',convert(varchar(64),coalesce(i.movement_id,d.movement_id)),
 (SELECT coalesce(i.movement_id,d.movement_id) AS movement_id,coalesce(i.product_id,d.product_id) AS product_id,coalesce(i.delta,d.delta) AS delta,
    convert(bit,CASE WHEN i.movement_id IS NULL THEN 1 ELSE i.is_deleted END) AS is_deleted,
    coalesce(i.updated_at,SYSUTCDATETIME()) AS updated_at FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
 FROM inserted i FULL JOIN deleted d ON i.movement_id=d.movement_id;
END;
GO
