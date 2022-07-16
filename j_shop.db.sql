BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "bill_buy" (
	"id"	INTEGER UNIQUE,
	"code"	TEXT UNIQUE,
	"date"	TEXT,
	"s_id"	INTEGER,
	"total"	REAL,
	"discount"	REAL,
	"ispaid"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("s_id") REFERENCES "supplier"("id")
);
CREATE TABLE IF NOT EXISTS "bill_sell" (
	"id"	INTEGER UNIQUE,
	"code"	TEXT UNIQUE,
	"date"	TEXT,
	"c_id"	INTEGER,
	"total"	REAL,
	"discount"	REAL,
	"ispaid"	INTEGER DEFAULT 0,
	FOREIGN KEY("c_id") REFERENCES "customer"("id"),
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "box" (
	"id"	INTEGER UNIQUE,
	"in_out"	INTEGER,
	"type"	TEXT,
	"name"	TEXT,
	"money"	REAL,
	"date"	TEXT,
	"note"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "buy_order" (
	"id"	INTEGER UNIQUE,
	"p_id"	INTEGER,
	"b_id"	INTEGER,
	"quantity"	INTEGER,
	"total"	REAL,
	"discount"	REAL,
	FOREIGN KEY("p_id") REFERENCES "product"("id"),
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("b_id") REFERENCES "bill_buy"("id")
);
CREATE TABLE IF NOT EXISTS "creditor" (
	"id"	integer NOT NULL,
	"c_id"	integer NOT NULL,
	CONSTRAINT "creditor_pk" PRIMARY KEY("id" AUTOINCREMENT),
	CONSTRAINT "creditor_customer_id_fk" FOREIGN KEY("c_id") REFERENCES "customer" on delete cascade
);
CREATE TABLE IF NOT EXISTS "customer" (
	"id"	INTEGER UNIQUE,
	"code"	TEXT,
	"name"	TEXT,
	"phone"	TEXT,
	"balance"	REAL,
	"note"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "product" (
	"id"	INTEGER UNIQUE,
	"code"	TEXT UNIQUE,
	"name"	TEXT,
	"class"	TEXT,
	"type"	TEXT,
	"source"	TEXT,
	"quantity"	INTEGER,
	"less_quantity"	INTEGER,
	"buy_price"	NUMERIC,
	"sell_price"	NUMERIC,
	"sell_price_wh"	INTEGER,
	"price_range"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "sell_order" (
	"id"	INTEGER,
	"p_id"	INTEGER,
	"b_id"	INTEGER,
	"quantity"	INTEGER,
	"total"	REAL,
	"discount"	REAL,
	FOREIGN KEY("p_id") REFERENCES "product"("id"),
	FOREIGN KEY("b_id") REFERENCES "bill_sell"("id")
);
CREATE TABLE IF NOT EXISTS "supplier" (
	"id"	INTEGER UNIQUE,
	"code"	TEXT,
	"name"	TEXT,
	"phone"	TEXT,
	"address"	TEXT,
	"balance"	REAL,
	"note"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "users" (
	"id"	INTEGER,
	"name"	TEXT,
	"pass"	TEXT,
	"permission"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE VIEW sell_order_v as SELECT sell_order.id, product.id as p_id, sell_order.b_id, product.code, product.name, sell_order.quantity, product.sell_price, sell_order.discount, sell_order.total from product, sell_order WHERE sell_order.p_id = product.id;
CREATE UNIQUE INDEX IF NOT EXISTS "creditor_id_uindex" ON "creditor" (
	"id"
);
COMMIT;
