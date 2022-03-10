BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "users" (
	"id"	INTEGER,
	"name"	TEXT,
	"pass"	TEXT,
	"permission"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "customer" (
	"id"	INTEGER UNIQUE,
	"code"	INTEGER,
	"name"	TEXT,
	"phone"	TEXT,
	"balance"	REAL,
	"note"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "supplier" (
	"id"	INTEGER UNIQUE,
	"code"	INTEGER,
	"name"	TEXT,
	"phone"	TEXT,
	"address"	INTEGER,
	"balance"	REAL,
	"note"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "product" (
	"id"	INTEGER UNIQUE,
	"code"	INTEGER UNIQUE,
	"name"	INTEGER,
	"class"	TEXT,
	"type"	TEXT,
	"source"	TEXT,
	"quantity"	INTEGER,
	"less_quantity"	INTEGER,
	"buy_price"	NUMERIC,
	"sell_price"	NUMERIC,
	"buy_price_wh"	INTEGER,
	"price_range"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "bill_buy" (
	"id"	INTEGER UNIQUE,
	"bill_num"	INTEGER UNIQUE,
	"date"	TEXT,
	"s_id"	INTEGER,
	"total"	REAL,
	"discount"	REAL,
	"ispaid"	INTEGER,
	FOREIGN KEY("s_id") REFERENCES "supplier"("id"),
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
CREATE TABLE IF NOT EXISTS "bill_sell" (
	"id"	INTEGER UNIQUE,
	"code"	INTEGER UNIQUE,
	"date"	TEXT,
	"c_id"	INTEGER,
	"total"	REAL,
	"discount"	REAL,
	"ispaid"	INTEGER,
	FOREIGN KEY("c_id") REFERENCES "customer"("id"),
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
COMMIT;
