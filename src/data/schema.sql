-- BitTrace DuckDB Schema
-- Elliptic++ dataset: transactions and wallet actors

-- Transactions table
CREATE OR REPLACE TABLE transactions AS
SELECT * FROM read_csv_auto('data/txs_features.csv');

-- Transaction class labels (1=illicit, 2=licit, 3=unknown)
CREATE OR REPLACE TABLE tx_classes AS
SELECT * FROM read_csv_auto('data/txs_classes.csv');

-- Transaction-to-transaction money flow edges
CREATE OR REPLACE TABLE tx_edges AS
SELECT * FROM read_csv_auto('data/txs_edgelist.csv');

-- Wallet/Actor features
CREATE OR REPLACE TABLE wallets AS
SELECT * FROM read_csv_auto('data/wallets_features.csv');

-- Wallet class labels
CREATE OR REPLACE TABLE wallet_classes AS
SELECT * FROM read_csv_auto('data/wallets_classes.csv');

-- Address-to-address interaction edges
CREATE OR REPLACE TABLE addr_addr_edges AS
SELECT * FROM read_csv_auto('data/AddrAddr_edgelist.csv');

-- Address-to-transaction edges
CREATE OR REPLACE TABLE addr_tx_edges AS
SELECT * FROM read_csv_auto('data/AddrTx_edgelist.csv');

-- Transaction-to-address edges
CREATE OR REPLACE TABLE tx_addr_edges AS
SELECT * FROM read_csv_auto('data/TxAddr_edgelist.csv');
