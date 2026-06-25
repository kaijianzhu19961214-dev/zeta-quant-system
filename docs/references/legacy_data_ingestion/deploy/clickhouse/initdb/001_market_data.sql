CREATE DATABASE IF NOT EXISTS quant_market;

CREATE TABLE IF NOT EXISTS quant_market.market_data_1m_raw
(
    dataset_code LowCardinality(String),
    code LowCardinality(String),
    trade_time DateTime64(0, 'Asia/Shanghai'),
    date Date,
    open Nullable(Decimal(20, 6)),
    high Nullable(Decimal(20, 6)),
    low Nullable(Decimal(20, 6)),
    close Nullable(Decimal(20, 6)),
    pre_close Nullable(Decimal(20, 6)),
    change Nullable(Decimal(20, 6)),
    pct_chg Nullable(Decimal(20, 6)),
    vol Nullable(Int64),
    amount Nullable(Decimal(24, 6)),
    adj_factor Decimal(24, 10) DEFAULT 1,
    hfq_factor Decimal(24, 10) DEFAULT 1,
    source_name LowCardinality(String),
    created_at DateTime64(0, 'Asia/Shanghai') DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_time)
ORDER BY (dataset_code, code, trade_time);

CREATE TABLE IF NOT EXISTS quant_market.market_data_5m_raw
(
    dataset_code LowCardinality(String),
    code LowCardinality(String),
    trade_time DateTime64(0, 'Asia/Shanghai'),
    date Date,
    open Nullable(Decimal(20, 6)),
    high Nullable(Decimal(20, 6)),
    low Nullable(Decimal(20, 6)),
    close Nullable(Decimal(20, 6)),
    pre_close Nullable(Decimal(20, 6)),
    change Nullable(Decimal(20, 6)),
    pct_chg Nullable(Decimal(20, 6)),
    vol Nullable(Int64),
    amount Nullable(Decimal(24, 6)),
    adj_factor Decimal(24, 10) DEFAULT 1,
    hfq_factor Decimal(24, 10) DEFAULT 1,
    source_name LowCardinality(String),
    created_at DateTime64(0, 'Asia/Shanghai') DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_time)
ORDER BY (dataset_code, code, trade_time);

CREATE TABLE IF NOT EXISTS quant_market.market_data_1d_raw
(
    dataset_code LowCardinality(String),
    code LowCardinality(String),
    date Date,
    open Nullable(Decimal(20, 6)),
    high Nullable(Decimal(20, 6)),
    low Nullable(Decimal(20, 6)),
    close Nullable(Decimal(20, 6)),
    pre_close Nullable(Decimal(20, 6)),
    change Nullable(Decimal(20, 6)),
    pct_chg Nullable(Decimal(20, 6)),
    vol Nullable(Int64),
    amount Nullable(Decimal(24, 6)),
    vwap Nullable(Decimal(20, 6)),
    adj_factor Decimal(24, 10) DEFAULT 1,
    hfq_factor Decimal(24, 10) DEFAULT 1,
    source_name LowCardinality(String),
    created_at DateTime64(0, 'Asia/Shanghai') DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(date)
ORDER BY (dataset_code, code, date);

CREATE TABLE IF NOT EXISTS quant_market.adjustment_factors
(
    dataset_code LowCardinality(String),
    code LowCardinality(String),
    date Date,
    adj_factor Decimal(24, 10) DEFAULT 1,
    source_name LowCardinality(String),
    created_at DateTime64(0, 'Asia/Shanghai') DEFAULT now()
)
ENGINE = ReplacingMergeTree(created_at)
PARTITION BY toYYYYMM(date)
ORDER BY (dataset_code, code, date);

CREATE TABLE IF NOT EXISTS quant_market.qfq_batches
(
    batch_id String,
    qfq_base_date Date,
    status LowCardinality(String),
    description String,
    created_at DateTime64(0, 'Asia/Shanghai') DEFAULT now(),
    finished_at Nullable(DateTime64(0, 'Asia/Shanghai'))
)
ENGINE = ReplacingMergeTree(created_at)
ORDER BY batch_id;

CREATE TABLE IF NOT EXISTS quant_market.market_data_1m_qfq_cache
(
    batch_id String,
    qfq_base_date Date,
    dataset_code LowCardinality(String),
    code LowCardinality(String),
    trade_time DateTime64(0, 'Asia/Shanghai'),
    date Date,
    qfq_factor Decimal(24, 10) DEFAULT 1,
    qfq_open Nullable(Decimal(20, 6)),
    qfq_high Nullable(Decimal(20, 6)),
    qfq_low Nullable(Decimal(20, 6)),
    qfq_close Nullable(Decimal(20, 6)),
    qfq_pre_close Nullable(Decimal(20, 6)),
    qfq_change Nullable(Decimal(20, 6)),
    created_at DateTime64(0, 'Asia/Shanghai') DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY (batch_id, toYYYYMM(trade_time))
ORDER BY (batch_id, dataset_code, code, trade_time);

CREATE TABLE IF NOT EXISTS quant_market.market_data_5m_qfq_cache
(
    batch_id String,
    qfq_base_date Date,
    dataset_code LowCardinality(String),
    code LowCardinality(String),
    trade_time DateTime64(0, 'Asia/Shanghai'),
    date Date,
    qfq_factor Decimal(24, 10) DEFAULT 1,
    qfq_open Nullable(Decimal(20, 6)),
    qfq_high Nullable(Decimal(20, 6)),
    qfq_low Nullable(Decimal(20, 6)),
    qfq_close Nullable(Decimal(20, 6)),
    qfq_pre_close Nullable(Decimal(20, 6)),
    qfq_change Nullable(Decimal(20, 6)),
    created_at DateTime64(0, 'Asia/Shanghai') DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY (batch_id, toYYYYMM(trade_time))
ORDER BY (batch_id, dataset_code, code, trade_time);

CREATE TABLE IF NOT EXISTS quant_market.market_data_1d_qfq_cache
(
    batch_id String,
    qfq_base_date Date,
    dataset_code LowCardinality(String),
    code LowCardinality(String),
    date Date,
    qfq_factor Decimal(24, 10) DEFAULT 1,
    qfq_open Nullable(Decimal(20, 6)),
    qfq_high Nullable(Decimal(20, 6)),
    qfq_low Nullable(Decimal(20, 6)),
    qfq_close Nullable(Decimal(20, 6)),
    qfq_pre_close Nullable(Decimal(20, 6)),
    qfq_change Nullable(Decimal(20, 6)),
    qfq_vwap Nullable(Decimal(20, 6)),
    created_at DateTime64(0, 'Asia/Shanghai') DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY (batch_id, toYYYYMM(date))
ORDER BY (batch_id, dataset_code, code, date);

CREATE VIEW IF NOT EXISTS quant_market.v_market_data_1m_hfq AS
SELECT
    dataset_code,
    code,
    trade_time,
    date,
    open,
    high,
    low,
    close,
    pre_close,
    change,
    pct_chg,
    vol,
    amount,
    adj_factor,
    hfq_factor,
    open * hfq_factor AS hfq_open,
    high * hfq_factor AS hfq_high,
    low * hfq_factor AS hfq_low,
    close * hfq_factor AS hfq_close,
    pre_close * hfq_factor AS hfq_pre_close,
    change * hfq_factor AS hfq_change,
    source_name,
    created_at
FROM quant_market.market_data_1m_raw;

CREATE VIEW IF NOT EXISTS quant_market.v_market_data_5m_hfq AS
SELECT
    dataset_code,
    code,
    trade_time,
    date,
    open,
    high,
    low,
    close,
    pre_close,
    change,
    pct_chg,
    vol,
    amount,
    adj_factor,
    hfq_factor,
    open * hfq_factor AS hfq_open,
    high * hfq_factor AS hfq_high,
    low * hfq_factor AS hfq_low,
    close * hfq_factor AS hfq_close,
    pre_close * hfq_factor AS hfq_pre_close,
    change * hfq_factor AS hfq_change,
    source_name,
    created_at
FROM quant_market.market_data_5m_raw;

CREATE VIEW IF NOT EXISTS quant_market.v_market_data_1d_hfq AS
SELECT
    dataset_code,
    code,
    date,
    open,
    high,
    low,
    close,
    pre_close,
    change,
    pct_chg,
    vol,
    amount,
    vwap,
    adj_factor,
    hfq_factor,
    open * hfq_factor AS hfq_open,
    high * hfq_factor AS hfq_high,
    low * hfq_factor AS hfq_low,
    close * hfq_factor AS hfq_close,
    pre_close * hfq_factor AS hfq_pre_close,
    change * hfq_factor AS hfq_change,
    vwap * hfq_factor AS hfq_vwap,
    source_name,
    created_at
FROM quant_market.market_data_1d_raw;
