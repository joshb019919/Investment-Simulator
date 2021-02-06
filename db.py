"""Reset finance.db tables to factory."""

import sqlite3

db = sqlite3.connect("finance.db")

db.executescript("""
DROP TABLE IF EXISTS 'users';
DROP TABLE IF EXISTS 'pins';
DROP TABLE IF EXISTS 'transactions';
DROP INDEX IF EXISTS 'idx_id';
DROP INDEX IF EXISTS 'idx_transactions';
DROP INDEX IF EXISTS 'idx_users';
DROP INDEX IF EXISTS 'idx_pins';
DROP INDEX IF EXISTS 'idx_tid';
DROP INDEX IF EXISTS 'idx_uid';
DROP INDEX IF EXISTS 'idx_datetime';
DROP INDEX IF EXISTS 'idx_company';
DROP INDEX IF EXISTS 'idx_symbol';
DROP INDEX IF EXISTS 'idx_action';
DROP INDEX IF EXISTS 'idx_shares';
DROP INDEX IF EXISTS 'idx_value';
DROP INDEX IF EXISTS 'idx_user_history';
DROP INDEX IF EXISTS 'idx_stocks_traded';""")

db.executescript("""CREATE TABLE IF NOT EXISTS 'users' (
        'id' INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        'email' VARCHAR(50) UNIQUE NOT NULL,
        'hash' VARCHAR(150) NOT NULL,
        'cash' DECIMAL(10, 2) NOT NULL,
        'transactions' TEXT,

        FOREIGN KEY ('id')
                REFERENCES 'pins' ('user_id')),
        FOREIGN KEY ('transactions')
                REFERENCES 'transactions' ('id');

CREATE TABLE IF NOT EXISTS 'pins' (
        'user_id' INTEGER NOT NULL PRIMARY KEY,
        'pin' DECIMAL(4),

        FOREIGN KEY ('user_id')
                REFERENCES 'users' ('id'));

CREATE TABLE IF NOT EXISTS 'transactions' (
        'id' INTEGER NOT NULL PRIMARY KEY,
        'user_id' INTEGER NOT NULL,
        'datetime' VARCHAR UNIQUE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        'company' VARCHAR(50) NOT NULL,
        'symbol' VARCHAR(5) NOT NULL,
        'action' VARCHAR(4) NOT NULL,
        'shares' INTEGER NOT NULL,
        'price' DECIMAL(6,2) NOT NULL,
        'value' DECIMAL(10,2) NOT NULL,

        FOREIGN KEY ('user_id')
                REFERENCES 'users' ('id'));

CREATE INDEX IF NOT EXISTS 'idx_id' ON 'users' ('id');
CREATE INDEX IF NOT EXISTS 'idx_transactions' ON 'users' ('transactions');
CREATE INDEX IF NOT EXISTS 'idx_users' ON 'users' ('id', 'email', 'cash', 'transactions');

CREATE INDEX IF NOT EXISTS 'idx_pins' ON 'pins' ('user_id');

CREATE INDEX IF NOT EXISTS 'idx_tid' ON 'transactions' ('transaction_id');
CREATE INDEX IF NOT EXISTS 'idx_uid' ON 'transactions' ('user_id');
CREATE INDEX IF NOT EXISTS 'idx_datetime' ON 'transactions' ('datetime');
CREATE INDEX IF NOT EXISTS 'idx_company' ON 'transactions' ('company');
CREATE INDEX IF NOT EXISTS 'idx_symbol' ON 'transactions' ('symbol');
CREATE INDEX IF NOT EXISTS 'idx_action' ON 'transactions' ('action');
CREATE INDEX IF NOT EXISTS 'idx_shares' ON 'transactions' ('shares');
CREATE INDEX IF NOT EXISTS 'idx_value' ON 'transactions' ('value');
CREATE INDEX IF NOT EXISTS 'idx_user_history' ON 'transactions' ('user_id', 'datetime', 'company', 'symbol', 'action', 'shares', 'price', 'value');
CREATE INDEX IF NOT EXISTS 'idx_stocks_traded' ON 'transactions' ('id', 'datetime', 'company', 'symbol', 'action', 'shares', 'price', 'value');""")
