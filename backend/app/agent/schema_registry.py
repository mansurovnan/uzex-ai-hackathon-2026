"""
Machine-readable database schema registry for UZEX AI Hackathon.
Contains full metadata, column definitions, data types, relationships,
primary keys, foreign keys, and business logic from README.
"""

from typing import Dict, Any

SCHEMA_METADATA: Dict[str, Any] = {
    "tables": {
        "brokers": {
            "description": "Brokerage firms registered on the exchange",
            "primary_key": "broker_code",
            "columns": {
                "broker_code": {"type": "VARCHAR", "description": "Unique broker code (e.g. 'BK001')"},
                "name": {"type": "VARCHAR", "description": "Legal name of brokerage firm"},
                "inn": {"type": "VARCHAR(9)", "description": "9-digit tax ID of the broker"},
                "region": {"type": "VARCHAR", "description": "Region of broker office"}
            }
        },
        "participants": {
            "description": "Market participants (companies acting as sellers or buyers)",
            "primary_key": "inn",
            "columns": {
                "inn": {"type": "VARCHAR(9)", "description": "9-digit company tax identification number"},
                "name": {"type": "VARCHAR", "description": "Legal company name"},
                "region": {"type": "VARCHAR", "description": "Region of registration"},
                "activity_type": {"type": "VARCHAR", "description": "Business activity ('Производитель', 'Торговая компания', etc.)"},
                "role": {"type": "VARCHAR", "description": "Primary role: 'Продавец' (Seller) or 'Покупатель' (Buyer)"},
                "vat_payer": {"type": "BOOLEAN", "description": "VAT payer status (TRUE / FALSE)"}
            }
        },
        "contracts": {
            "description": "Master contract cards registered on the exchange",
            "primary_key": "contract_number",
            "foreign_keys": {
                "seller_inn": "participants.inn"
            },
            "columns": {
                "contract_number": {"type": "VARCHAR", "description": "Contract identifier"},
                "product_name": {"type": "VARCHAR", "description": "Primary product name"},
                "product_mark": {"type": "VARCHAR", "description": "Product brand or mark"},
                "product_size": {"type": "VARCHAR", "description": "Product dimensions or size"},
                "product_grade": {"type": "VARCHAR", "description": "Quality sort or grade"},
                "product_type": {"type": "VARCHAR", "description": "Product type"},
                "product_class": {"type": "VARCHAR", "description": "Product class"},
                "tnved_code": {"type": "VARCHAR", "description": "TN VED customs classification code"},
                "product_group": {"type": "VARCHAR", "description": "Commodity group (e.g. 'Высоколиквидные товары')"},
                "product_category": {"type": "VARCHAR", "description": "Category (e.g. 'Сельскохозяйственная продукция', 'Строительные материалы')"},
                "industry": {"type": "VARCHAR", "description": "Industry sector (e.g. 'Сельское хозяйство', 'Строительная индустрия')"},
                "unit": {"type": "VARCHAR", "description": "Unit of measurement (тонна, килограмм, куб.метр, штука, метр)"},
                "lot_size": {"type": "DECIMAL(18,4)", "description": "Physical units per lot"},
                "currency": {"type": "VARCHAR", "description": "Contract currency: 'Узбекский сум' or 'Доллар США'"},
                "base_price": {"type": "DECIMAL(18,4)", "description": "Base price per unit at registration"},
                "deposit_percent": {"type": "DECIMAL(8,4)", "description": "Required deposit percentage"},
                "delivery_basis": {"type": "VARCHAR", "description": "Incoterms delivery condition (EXW, FCA, CPT, etc.)"},
                "region": {"type": "VARCHAR", "description": "Warehouse region"},
                "trade_type": {"type": "VARCHAR", "description": "Auction type ('Английский аукцион', 'Обратный аукцион', 'Двусторонний аукцион')"},
                "contract_type": {"type": "VARCHAR", "description": "'Внутренний' (Domestic) or 'Экспортный' (Export)"},
                "contract_form": {"type": "VARCHAR", "description": "'Спот' (Spot), 'Форвард' (Forward), 'Фьючерс' (Futures)"},
                "payment_term_days": {"type": "INTEGER", "description": "Payment term in calendar days from deal date"},
                "delivery_term_days": {"type": "INTEGER", "description": "Delivery term in calendar days from payment date"},
                "seller_inn": {"type": "VARCHAR(9)", "description": "Seller company INN"},
                "registration_date": {"type": "DATE", "description": "Contract registration date"},
                "valid_until": {"type": "DATE", "description": "Contract validity expiration date"}
            }
        },
        "usd_rates": {
            "description": "Daily official USD to UZS exchange rates",
            "primary_key": "rate_date",
            "columns": {
                "rate_date": {"type": "DATE", "description": "Calendar date (YYYY-MM-DD)"},
                "rate_uzs": {"type": "DECIMAL(12,4)", "description": "Exchange rate: UZS per 1 USD"}
            }
        },
        "deals": {
            "description": "500,000 exchange transactions between 2022-01-03 and 2026-10-30",
            "primary_key": "deal_id",
            "foreign_keys": {
                "contract_number": "contracts.contract_number",
                "seller_inn": "participants.inn",
                "buyer_inn": "participants.inn",
                "seller_broker": "brokers.broker_code",
                "buyer_broker": "brokers.broker_code"
            },
            "columns": {
                "deal_id": {"type": "BIGINT", "description": "Sequential transaction ID"},
                "deal_date": {"type": "DATE", "description": "Date of transaction"},
                "deal_time": {"type": "TIME", "description": "Time of transaction (Tashkent timezone)"},
                "trade_type": {"type": "VARCHAR", "description": "Type of auction"},
                "quantity_lots": {"type": "DECIMAL(18,4)", "description": "Purchased volume in lots"},
                "deal_amount": {"type": "DECIMAL(24,4)", "description": "Transaction total amount in contract currency"},
                "start_price": {"type": "DECIMAL(18,4)", "description": "Starting auction price per unit"},
                "contract_number": {"type": "VARCHAR", "description": "Referenced contract number"},
                "product_raw_name": {"type": "VARCHAR", "description": "Full product title as logged in deal"},
                "lot_size": {"type": "DECIMAL(18,4)", "description": "Units per lot"},
                "unit": {"type": "VARCHAR", "description": "Unit of measurement"},
                "region": {"type": "VARCHAR", "description": "Seller warehouse region"},
                "contract_type": {"type": "VARCHAR", "description": "'Внутренний' or 'Экспортный'"},
                "contract_form": {"type": "VARCHAR", "description": "'Спот', 'Форвард', 'Фьючерс'"},
                "status": {"type": "VARCHAR", "description": "Transaction status (Исполнен, Аннулирован(Не оплачен), etc.)"},
                "seller_inn": {"type": "VARCHAR(9)", "description": "Seller INN"},
                "buyer_inn": {"type": "VARCHAR(9)", "description": "Buyer INN"},
                "seller_broker": {"type": "VARCHAR", "description": "Seller broker code"},
                "buyer_broker": {"type": "VARCHAR", "description": "Buyer broker code"},
                "payment_date": {"type": "DATE", "description": "Payment date (NULL if unpaid)"},
                "delivery_date": {"type": "DATE", "description": "Delivery date (NULL if undelivered)"},
                "delivered_lots": {"type": "DECIMAL(18,4)", "description": "Lots physically delivered (NULL if undelivered)"}
            }
        }
    },
    "views": {
        "v_deals_enriched": {
            "description": "Pre-joined enriched analytical view across all 5 tables + USD exchange rates with transaction status logic",
            "key_columns": [
                "deal_id", "deal_date", "trade_type", "contract_type", "contract_form", "status", "status_category",
                "is_executed", "is_cancelled", "is_pending",
                "contracted_volume_units", "executed_volume_units",
                "amount_contract_currency", "amount_uzs", "executed_amount_uzs",
                "unit_price_contract_currency", "unit", "currency", "fx_rate_usd_uzs",
                "product_name", "product_category", "product_group", "industry",
                "seller_inn", "seller_name", "seller_region", "seller_activity",
                "buyer_inn", "buyer_name", "buyer_region", "buyer_activity",
                "seller_broker_code", "seller_broker_name", "buyer_broker_code", "buyer_broker_name"
            ]
        }
    },
    "business_rules": {
        "volume_calculation": "Contracted Volume = quantity_lots * lot_size. Executed Volume = CASE WHEN status = 'Исполнен' THEN quantity_lots * lot_size WHEN status = 'Исполнен(Частично)' THEN COALESCE(delivered_lots, 0) * lot_size ELSE 0 END.",
        "turnover_calculation": "Executed Turnover (UZS) = delivered lots fraction * amount in UZS. Cancelled transactions (status = 'Аннулирован(Не оплачен)') have 0 executed volume and 0 executed turnover.",
        "currency_conversion": "Export deals are denominated in USD ($). To convert to UZS, multiply by rate_uzs from usd_rates on the exact deal_date. Domestic deals are already in UZS.",
        "statuses": {
            "Исполнен": "Executed: paid and completely delivered.",
            "Исполнен(Частично)": "Partially Executed: paid, partially delivered.",
            "Аннулирован(Не оплачен)": "Cancelled: unpaid within deadline, deal terminated.",
            "Оплачен": "Paid, awaiting goods delivery.",
            "Ждёт оплату": "Spot signed, awaiting buyer payment.",
            "Заключен": "Forward/Futures signed, active payment term.",
            "Новый": "New transaction on last day of data.",
            "Не подписан": "Unsigned transaction."
        }
    }
}

def get_schema_summary_text() -> str:
    """Returns a compact textual summary of the schema for prompt injection."""
    lines = [
        "DATABASE SCHEMA (DuckDB):",
        "- brokers (broker_code PK, name, inn, region)",
        "- participants (inn PK, name, region, activity_type, role, vat_payer)",
        "- contracts (contract_number PK, product_name, product_mark, product_grade, product_category, industry, unit, lot_size, currency, base_price, contract_type, contract_form, seller_inn, registration_date, valid_until)",
        "- usd_rates (rate_date PK, rate_uzs)",
        "- deals (deal_id PK, deal_date, trade_type, quantity_lots, deal_amount, start_price, contract_number, product_raw_name, lot_size, unit, contract_type, contract_form, status, seller_inn, buyer_inn, seller_broker, buyer_broker, payment_date, delivery_date, delivered_lots)",
        "- v_deals_enriched (analytical view joining all tables: deal_id, deal_date, status, is_executed, is_cancelled, contracted_volume_units, executed_volume_units, amount_contract_currency, amount_uzs, executed_amount_uzs, unit, currency, fx_rate_usd_uzs, product_name, product_category, industry, seller_inn, seller_name, seller_region, buyer_inn, buyer_name, buyer_region, seller_broker_code, seller_broker_name, buyer_broker_code, buyer_broker_name)"
    ]
    return "\n".join(lines)
