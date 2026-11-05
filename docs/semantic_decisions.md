# UZEX AI — Semantic Layer Decisions & Definitions

## 1. Metric Definitions & Formulas

### 1.1 Physical Volume (Fizik hajm / Физический объем)
* **Definition:** Total quantity of goods contracted or delivered in physical units.
* **SQL Expression:** `SUM(contracted_volume_units)` or `SUM(executed_volume_units)`.
* **Rules:**
  * Must always be reported with the source-defined unit (`unit`).
  * Never aggregate across differing units. Rankings across products must report units per row or group by `(product_name, unit)`.

### 1.2 Monetary Turnover (Aylanma / Общий оборот)
* **Contracted Turnover (Shartnoma aylanmasi):** `SUM(amount_uzs)`. Reflects total registered contract value across all concluded deals.
* **Delivered/Executed Turnover (Faktik aylanma):** `SUM(executed_amount_uzs)`. Reflects delivered goods turnover (`delivered_lots * lot_size * unit_price * fx_rate`).
* **Export Turnover (Eksport summasi):** Reported in native USD (`SUM(amount_contract_currency) WHERE contract_type = 'Экспортный'`) and UZS equivalent (`SUM(amount_uzs)`).

### 1.3 Deal Count vs Contract Count
* **Deal Count (Bitimlar soni):** `COUNT(*)` on deals grain.
* **Distinct Contract Count (Shartnomalar soni):** `COUNT(DISTINCT contract_number)`.

### 1.4 Average Unit Price (O'rtacha narx / Средневзвешенная цена)
* **Primary (Quantity-Weighted Average Price):**
  $$\text{Weighted Avg Price} = \frac{\sum \text{amount\_uzs}}{\sum \text{contracted\_volume\_units}}$$
  Calculated strictly within the same unit and currency.
* **Secondary (Simple Arithmetic Mean of Unit Price):**
  `AVG(unit_price_contract_currency)`
* **Reporting Rule:** The narrative clearly labels whether the weighted average or simple arithmetic mean is presented.

---

## 2. Temporal & Coverage Semantics

### 2.1 Standard Date Column
* **Primary Date:** `deal_date` (the actual trade execution date on the exchange floor).
* **Payment Date:** `payment_date` (relevant for payment settlement).
* **Delivery Date:** `delivery_date` (relevant for physical commodity delivery).

### 2.2 Relative Date Baseline
* Expressions such as *"o'tgan yil"* (last year), *"so'nggi 6 oy"* (last 6 months), *"в прошлом году"* are calculated relative to the dataset's maximum date (`2026-10-30`), **never** wall-clock today.

### 2.3 Partial Period Caveat (Year 2026)
* Data for 2026 covers only **January 2 through October 30** (10 months).
* Whenever 2026 is analyzed in a multi-year comparison or trend, the response must state:
  > *"2026-yil ma'lumotlari to'liq emas (10 oy: yanvar–oktyabr). Shuning uchun 2026-yil ko'rsatkichlarini butun yilga tenglashtirib bo'lmaydi."*

---

## 3. Status Semantics

### 3.1 Concluded Deals (Tuzilgan bitimlar / Заключенные сделки)
* All 500,000 transactions registered in the exchange registry (`status IS NOT NULL`).

### 3.2 Executed Deals (Ijro etilgan bitimlar / Исполненные сделки)
* Transactions where goods delivery took place:
  `status IN ('Исполнен', 'Исполнен(Частично)')`
* Total in dataset: 453,709 deals.

### 3.3 Cancelled Deals (Bekor qilingan bitimlar / Аннулированные сделки)
* Transactions cancelled due to non-payment within the regulatory payment window:
  `status = 'Аннулирован(Не оплачен)'`
* Total in dataset: 33,719 deals.

---

## 4. Disambiguation & Tie-Breaking

### 4.1 "Most Sold" (Eng ko'p sotilgan / Самый продаваемый)
When a user asks for *"eng ko'p sotilgan"* without specifying volume, turnover, or deal count:
1. **Primary Default Metric:** Monetary turnover (`SUM(amount_uzs)`).
2. **Transparency Rule:** The narrative states the ranking was performed by turnover, and the accompanying table displays physical volume, turnover, and deal counts side-by-side so the user has complete visibility.

### 4.2 Deterministic Ranking Ties
* Every `ORDER BY` clause includes a deterministic secondary tie-breaker:
  `ORDER BY <metric> DESC, <entity_id_or_name> ASC`
  This guarantees identical result sets across runs.

### 4.3 Role Semantics
* **"Sotgan" / "Sotuvchi" / "Продавец" / "Поставщик":** Maps strictly to `seller_inn`, `seller_name`, `seller_region`, `seller_broker_code`.
* **"Xarid qilgan" / "Xaridor" / "Покупатель" / "Закуп":** Maps strictly to `buyer_inn`, `buyer_name`, `buyer_region`, `buyer_broker_code`.
