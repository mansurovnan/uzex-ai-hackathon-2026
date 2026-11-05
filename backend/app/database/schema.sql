-- ==============================================================================
-- UZEX AI HACKATHON 2026 — DUCKDB DATABASE SCHEMA
-- Preserves complete financial precision (DECIMAL) and enforces relational integrity
-- ==============================================================================

-- 1. BROKERS TABLE
CREATE TABLE IF NOT EXISTS brokers (
    broker_code VARCHAR PRIMARY KEY,          -- Unique broker code (e.g., 'BK001')
    name VARCHAR NOT NULL,                     -- Legal name of brokerage firm
    inn VARCHAR(9) NOT NULL,                   -- 9-digit tax ID
    region VARCHAR NOT NULL                    -- Region of operation (e.g., 'Toshkent shahri')
);

-- 2. PARTICIPANTS TABLE (COMPANIES)
CREATE TABLE IF NOT EXISTS participants (
    inn VARCHAR(9) PRIMARY KEY,                -- 9-digit tax ID
    name VARCHAR NOT NULL,                     -- Company legal name
    region VARCHAR NOT NULL,                   -- Region of registration
    activity_type VARCHAR NOT NULL,            -- Business activity (e.g., 'Производитель', 'Торговая компания')
    role VARCHAR NOT NULL,                     -- Primary role: 'Продавец' (Seller) or 'Покупатель' (Buyer)
    vat_payer BOOLEAN NOT NULL                 -- VAT payer flag (TRUE / FALSE)
);

-- 3. CONTRACTS TABLE (MASTER PRODUCT CARDS)
CREATE TABLE IF NOT EXISTS contracts (
    contract_number VARCHAR PRIMARY KEY,       -- Contract reference ID
    product_name VARCHAR NOT NULL,             -- Primary product description
    product_mark VARCHAR,                      -- Product mark / brand
    product_size VARCHAR,                      -- Technical size / dimensions
    product_grade VARCHAR,                     -- Quality grade / sort
    product_type VARCHAR,                      -- Product type
    product_class VARCHAR,                     -- Product class
    tnved_code VARCHAR,                        -- Commodity code (TN VED)
    product_group VARCHAR,                     -- Group (e.g. 'Высоколиквидные товары', 'Прочие товары')
    product_category VARCHAR,                  -- Category (e.g. 'Сельскохозяйственная продукция', 'Строительные материалы')
    industry VARCHAR,                          -- Industry sector
    unit VARCHAR NOT NULL,                     -- Unit of measurement (e.g. 'тонна', 'килограмм', 'куб.метр')
    lot_size DECIMAL(18, 4) NOT NULL,          -- Quantity per lot
    currency VARCHAR NOT NULL,                 -- 'Узбекский сум' or 'Доллар США'
    base_price DECIMAL(18, 4) NOT NULL,        -- Baseline price per unit at registration
    deposit_percent DECIMAL(8, 4) NOT NULL,    -- Required deposit percentage
    delivery_basis VARCHAR NOT NULL,           -- Delivery terms (e.g. 'EXW', 'FCA', 'CPT')
    region VARCHAR NOT NULL,                   -- Warehouse region
    warehouse_address VARCHAR,                 -- Warehouse physical location
    trade_type VARCHAR NOT NULL,               -- Auction type ('Английский аукцион', 'Обратный аукцион', 'Двусторонний аукцион')
    contract_type VARCHAR NOT NULL,            -- 'Внутренний' (Domestic) or 'Экспортный' (Export)
    contract_form VARCHAR NOT NULL,            -- 'Спот' (Spot), 'Форвард' (Forward), 'Фьючерс' (Futures)
    payment_term_days INTEGER NOT NULL,        -- Payment term in calendar days from deal date
    delivery_term_days INTEGER NOT NULL,       -- Delivery term in calendar days from payment date
    packaging VARCHAR,                         -- Packaging specification
    seller_inn VARCHAR(9) NOT NULL REFERENCES participants(inn),
    registration_date DATE NOT NULL,           -- Contract registration date
    valid_until DATE NOT NULL                  -- Expiration date
);

-- 4. USD EXCHANGE RATES TABLE
CREATE TABLE IF NOT EXISTS usd_rates (
    rate_date DATE PRIMARY KEY,                -- Calendar date (YYYY-MM-DD)
    rate_uzs DECIMAL(12, 4) NOT NULL           -- Official exchange rate (UZS per 1 USD)
);

-- 5. DEALS TABLE (EXCHANGE TRANSACTIONS)
CREATE TABLE IF NOT EXISTS deals (
    deal_id BIGINT PRIMARY KEY,                -- Sequential transaction ID
    deal_date DATE NOT NULL,                   -- Transaction date
    deal_time TIME NOT NULL,                   -- Transaction time (Tashkent timezone)
    trade_type VARCHAR NOT NULL,               -- 'Английский аукцион', 'Обратный аукцион', 'Двусторонний аукцион'
    quantity_lots DECIMAL(18, 4) NOT NULL,     -- Quantity of lots purchased
    deal_amount DECIMAL(24, 4) NOT NULL,       -- Total deal sum in contract currency
    start_price DECIMAL(18, 4) NOT NULL,       -- Starting auction price per unit
    contract_number VARCHAR NOT NULL REFERENCES contracts(contract_number),
    product_raw_name VARCHAR NOT NULL,         -- Full item description as logged in deal
    lot_size DECIMAL(18, 4) NOT NULL,          -- Units per lot
    unit VARCHAR NOT NULL,                     -- Measurement unit
    region VARCHAR NOT NULL,                   -- Seller warehouse region
    contract_type VARCHAR NOT NULL,            -- 'Внутренний' or 'Экспортный'
    contract_form VARCHAR NOT NULL,            -- 'Спот', 'Форвард', 'Фьючерс'
    status VARCHAR NOT NULL,                   -- Deal status: Исполнен, Аннулирован(Не оплачен), etc.
    seller_inn VARCHAR(9) NOT NULL REFERENCES participants(inn),
    buyer_inn VARCHAR(9) NOT NULL REFERENCES participants(inn),
    seller_broker VARCHAR NOT NULL REFERENCES brokers(broker_code),
    buyer_broker VARCHAR NOT NULL REFERENCES brokers(broker_code),
    payment_date DATE,                         -- Actual payment date (NULL if unpaid)
    delivery_date DATE,                        -- Actual delivery date (NULL if undelivered)
    delivered_lots DECIMAL(18, 4)              -- Quantity of lots physically delivered
);

-- ==============================================================================
-- SECONDARY INDEXES FOR ULTRA-FAST ANALYTICAL RETRIEVAL
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_deals_date ON deals(deal_date);
CREATE INDEX IF NOT EXISTS idx_deals_contract ON deals(contract_number);
CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status);
CREATE INDEX IF NOT EXISTS idx_deals_seller_inn ON deals(seller_inn);
CREATE INDEX IF NOT EXISTS idx_deals_buyer_inn ON deals(buyer_inn);
CREATE INDEX IF NOT EXISTS idx_deals_seller_broker ON deals(seller_broker);
CREATE INDEX IF NOT EXISTS idx_deals_buyer_broker ON deals(buyer_broker);
CREATE INDEX IF NOT EXISTS idx_deals_contract_type ON deals(contract_type);

CREATE INDEX IF NOT EXISTS idx_contracts_seller ON contracts(seller_inn);
CREATE INDEX IF NOT EXISTS idx_contracts_category ON contracts(product_category);
CREATE INDEX IF NOT EXISTS idx_contracts_industry ON contracts(industry);

-- ==============================================================================
-- ENRICHED ANALYTICAL VIEW (BUSINESS RULES & TRANSACTION STATUS LOGIC)
-- ==============================================================================
-- Transaction Status Classification Rules:
-- 1. 'EXECUTED': 'Исполнен' (100% paid and delivered).
-- 2. 'PARTIALLY_EXECUTED': 'Исполнен(Частично)' (paid, partially delivered; delivered volume = delivered_lots * lot_size).
-- 3. 'CANCELLED': 'Аннулирован(Не оплачен)' (unpaid and terminated, NOT counted in fulfilled trade volume).
-- 4. 'PAID_PENDING_DELIVERY': 'Оплачен' (paid, awaiting goods delivery).
-- 5. 'AWAITING_PAYMENT': 'Ждёт оплату' (spot signed, awaiting payment).
-- 6. 'SIGNED_FORWARD_FUTURES': 'Заключен' (forward/futures signed, payment active).
-- 7. 'NEW_SAME_DAY': 'Новый' (logged on the final day 30.10.2026).
-- 8. 'UNSIGNED': 'Не подписан' (parties have not yet signed).
-- ==============================================================================

CREATE OR REPLACE VIEW v_deals_enriched AS
SELECT
    d.deal_id,
    d.deal_date,
    d.deal_time,
    d.trade_type,
    d.contract_type,
    d.contract_form,
    d.status,
    
    -- Status semantic flags
    CASE 
        WHEN d.status = 'Исполнен' THEN 'EXECUTED'
        WHEN d.status = 'Исполнен(Частично)' THEN 'PARTIALLY_EXECUTED'
        WHEN d.status = 'Аннулирован(Не оплачен)' THEN 'CANCELLED'
        WHEN d.status = 'Оплачен' THEN 'PAID_PENDING_DELIVERY'
        WHEN d.status = 'Ждёт оплату' THEN 'AWAITING_PAYMENT'
        WHEN d.status = 'Заключен' THEN 'SIGNED_FORWARD_FUTURES'
        WHEN d.status = 'Новый' THEN 'NEW_SAME_DAY'
        WHEN d.status = 'Не подписан' THEN 'UNSIGNED'
        ELSE 'OTHER'
    END AS status_category,
    
    (d.status IN ('Исполнен', 'Исполнен(Частично)')) AS is_executed,
    (d.status = 'Аннулирован(Не оплачен)') AS is_cancelled,
    (d.status IN ('Оплачен', 'Ждёт оплату', 'Заключен', 'Новый', 'Не подписан')) AS is_pending,
    
    -- Volumes
    d.quantity_lots,
    d.lot_size,
    d.unit,
    (d.quantity_lots * d.lot_size) AS contracted_volume_units,
    CASE 
        WHEN d.status = 'Исполнен' THEN (d.quantity_lots * d.lot_size)
        WHEN d.status = 'Исполнен(Частично)' THEN (COALESCE(d.delivered_lots, 0) * d.lot_size)
        ELSE 0
    END AS executed_volume_units,
    
    -- Financial amounts (original currency)
    c.currency,
    d.deal_amount AS amount_contract_currency,
    d.start_price,
    (d.deal_amount / NULLIF(d.quantity_lots * d.lot_size, 0)) AS unit_price_contract_currency,
    
    -- Financial amounts normalized to UZS (using daily FX rate on deal date)
    r.rate_uzs AS fx_rate_usd_uzs,
    CASE 
        WHEN d.contract_type = 'Экспортный' THEN (d.deal_amount * r.rate_uzs)
        ELSE d.deal_amount
    END AS amount_uzs,
    
    -- Executed Turnover in UZS (strictly reflects fulfilled trade deliveries)
    CASE 
        WHEN d.status = 'Исполнен' THEN 
            CASE WHEN d.contract_type = 'Экспортный' THEN (d.deal_amount * r.rate_uzs) ELSE d.deal_amount END
        WHEN d.status = 'Исполнен(Частично)' THEN 
            (COALESCE(d.delivered_lots, 0) / NULLIF(d.quantity_lots, 0)) * 
            CASE WHEN d.contract_type = 'Экспортный' THEN (d.deal_amount * r.rate_uzs) ELSE d.deal_amount END
        ELSE 0
    END AS executed_amount_uzs,
    
    -- Dates and Deliveries
    d.payment_date,
    d.delivery_date,
    d.delivered_lots,
    
    -- Product & Contract Details
    d.contract_number,
    d.product_raw_name,
    c.product_name,
    c.product_mark,
    c.product_size,
    c.product_grade,
    c.product_type,
    c.product_class,
    c.product_group,
    c.product_category,
    c.industry,
    c.tnved_code,
    c.delivery_basis,
    
    -- Seller Details
    d.seller_inn,
    sp.name AS seller_name,
    sp.region AS seller_region,
    sp.activity_type AS seller_activity,
    sp.vat_payer AS seller_vat_payer,
    
    -- Buyer Details
    d.buyer_inn,
    bp.name AS buyer_name,
    bp.region AS buyer_region,
    bp.activity_type AS buyer_activity,
    bp.vat_payer AS buyer_vat_payer,
    
    -- Broker Details
    d.seller_broker AS seller_broker_code,
    sb.name AS seller_broker_name,
    sb.region AS seller_broker_region,
    
    d.buyer_broker AS buyer_broker_code,
    bb.name AS buyer_broker_name,
    bb.region AS buyer_broker_region

FROM deals d
JOIN contracts c ON d.contract_number = c.contract_number
JOIN participants sp ON d.seller_inn = sp.inn
JOIN participants bp ON d.buyer_inn = bp.inn
JOIN brokers sb ON d.seller_broker = sb.broker_code
JOIN brokers bb ON d.buyer_broker = bb.broker_code
JOIN usd_rates r ON d.deal_date = r.rate_date;
