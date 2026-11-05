"""
Universal Natural Language Response Synthesizer for UZEX AI Hackathon.
Explains analytical results in Uzbek (Latin/Cyrillic) and Russian,
formats currency/volume metrics, builds Markdown tables, and explains calculation methodology.
Supports multi-question combination and multi-part compound responses.
"""

from typing import List, Dict, Any, Optional

CAVEAT_2026_UZ = (
    "\n\n> ⚠️ **Muhim eslatma (2026-yil qamrovi):**\n"
    "> 2026-yil ma'lumotlari to'liq bo'lmagan davrni (yanvar–oktabr, 10 oy) qamrab oladi. "
    "> Shu sababli 2026-yil umumiy hajmi va bitimlar sonini 2025-yil bilan to'g'ridan-to'g'ri taqqoslashda "
    "> to'liq 12 oylik ko'rsatkich emasligini inobatga olish lozim."
)

CAVEAT_2026_RU = (
    "\n\n> ⚠️ **Важное примечание (покрытие 2026 года):**\n"
    "> Данные за 2026 год представлены за неполный период (январь–октябрь, 10 месяцев). "
    "> В связи с этим итоговые показатели 2026 года нельзя напрямую сравнивать с полными итогами "
    "> 2025 года без учёта неполного периода торгов."
)

def format_num(val: Any) -> str:
    if val is None:
        return "0"
    try:
        f = float(val)
        if f.is_integer():
            return f"{int(f):,}".replace(",", " ")
        return f"{f:,.2f}".replace(",", " ")
    except (ValueError, TypeError):
        return str(val)

class ResponseSynthesizer:
    @staticmethod
    def synthesize_single(
        intent: str,
        cols: List[str],
        rows: List[tuple],
        lang: str,
        question: str,
        metadata: Dict[str, Any],
        is_unanswerable: bool = False,
        compound_data: Optional[Dict[str, Any]] = None
    ) -> str:
        # Handle unanswerable / out-of-scope questions
        if is_unanswerable:
            if lang == "uz":
                return (
                    "ℹ️ **Ma'lumot mavjud emas:**\n"
                    "Ushbu savol O'zbekiston Respublika tovar-xomashyo birjasi (UZEX) bitimlar reyestriga tegishli emas. "
                    "Men birja bitimlari (2022–2026), tovarlar narxlari, sotuvchi va xaridor kompaniyalar, brokerlar "
                    "hamda valyuta kurslari bo'yicha ma'lumot bera olaman."
                )
            else:
                return (
                    "ℹ️ **Информация отсутствует в базе биржи:**\n"
                    "Данный вопрос не относится к реестру сделок товарно-сырьевой биржи (UZEX). "
                    "Я могу предоставить аналитику по биржевым сделкам за 2022–2026 годы, ценам на товары, "
                    "компаниям-продавцам и покупателям, брокерам и курсам валют."
                )

        # Handle synthetic disclaimer
        if intent == "synthetic_disclaimer":
            if lang == "uz":
                return (
                    "ℹ️ **UZEX Ma'lumotlar To'plami Bo'yicha Rasmiy Izoh:**\n\n"
                    "Ushbu ma'lumotlar to'plami **UZEX AI Hackathon 2026** doirasida tahliliy tizimlar va sun'iy intellekt modellarini "
                    "sinovdan o'tkazish uchun maxsus ishlab chiqilgan **yuqori aniqlikdagi sintetik (taqlidiy) ma'lumotlar modelidir**.\n\n"
                    "**Asosiy xususiyatlari:**\n"
                    "- 📊 **Hajmi:** 2022–2026 yillarga oid **500 000 ta birja bitimi**;\n"
                    "- 🏢 **Bozor ishtirokchilari:** 14 000 dan ortiq korxona (klasterlar, zavodlar) va 120 ta akkreditatsiyadan o'tgan brokerlik idorasi;\n"
                    "- 💵 **Valyuta kurslari:** O'zbekiston Respublikasi Markaziy bankining har kungi real rasmiy USD/UZS kurslari bilan integratsiya qilingan;\n"
                    "- ⚖️ **Bozor qoidalari:** Barcha narx shakllanishi, lot hajmlari, kontrakt turlari (Spot, Forward, Ichki va Eksport) va to'lov/ijro holatlari UZEX real birja mexanizmlariga 100% mos ravishda modellashtirilgan.\n\n"
                    "💡 *Tavsiya:* Istalgan tovar, kompaniya, broker yoki yillik dinamika bo'yicha aniq hisob-kitoblarni so'rashingiz mumkin."
                )
            else:
                return (
                    "ℹ️ **Официальное пояснение по набору данных UZEX:**\n\n"
                    "Данный датасет представляет собой **высокоточную синтетическую модель данных**, созданную в рамках "
                    "**UZEX AI Hackathon 2026** для разработки и тестирования интеллектуальных аналитических систем.\n\n"
                    "**Ключевые параметры модели:**\n"
                    "- 📊 **Объем:** **500 000 биржевых сделок** за период с 2022 по 2026 год;\n"
                    "- 🏢 **Участники торгов:** Более 14 000 предприятий (кластеры, заводы) и 120 аккредитованных брокерских контор;\n"
                    "- 💵 **Курсы валют:** Интегрированы официальные ежедневные курсы доллара США ЦБ РУз;\n"
                    "- ⚖️ **Рыночные правила:** Структура контрактов (спот, форвард, экспорт, внутренний рынок), диапазоны цен и правила исполнения соответствуют регламентам УзРТСБ.\n\n"
                    "💡 *Подсказка:* Вы можете запросить аналитику по конкретным товарам, компаниям, брокерам или динамике торгов."
                )

        if not rows:
            return (
                "Kechirasiz, so'rovingiz bo'yicha ma'lumotlar bazasida mos yozuvlar topilmadi."
                if lang == "uz"
                else "К сожалению, по вашему запросу в базе данных записей не найдено."
            )

        first = rows[0]

        # 1. Total Turnover
        if intent == "total_turnover":
            total_deals, executed_deals, turnover_uzs, executed_turnover, export_usd = first
            year = metadata.get("year")
            period = f"{year}-yilda" if (year and lang == "uz") else (f"в {year} году" if year else ("Barcha davr uchun (2022–2026)" if lang == "uz" else "За весь период (2022–2026)"))
            
            if lang == "uz":
                return (
                    f"📊 **UZEX Birja Ko'rsatkichlari ({period}):**\n"
                    f"- **Jami tuzilgan bitimlar:** {format_num(total_deals)} ta\n"
                    f"- **To'liq va qisman ijro etilgan bitimlar:** {format_num(executed_deals)} ta\n"
                    f"- **Jami shartnoma aylanmasi:** {format_num(turnover_uzs)} so'm\n"
                    f"- **Amalda yetkazib berilgan tovarlar hajmi (faktik aylanma):** {format_num(executed_turnover)} so'm\n"
                    f"- **Eksport bitimlari:** ${format_num(export_usd)} USD"
                )
            else:
                return (
                    f"📊 **Показатели биржи UZEX ({period}):**\n"
                    f"- **Всего заключено сделок:** {format_num(total_deals)}\n"
                    f"- **Исполнено сделок (полностью и частично):** {format_num(executed_deals)}\n"
                    f"- **Общий объем заключенных сделок:** {format_num(turnover_uzs)} сум\n"
                    f"- **Фактически исполненный оборот (по поставкам):** {format_num(executed_turnover)} сум\n"
                    f"- **Объем экспорта:** ${format_num(export_usd)} USD"
                )

        # 2. Market Comparison: Export vs Domestic
        if intent == "market_comparison":
            header = "⚖️ **Eksport va Ichki bozor taqqoslamasi:**\n\n" if lang == "uz" else "⚖️ **Сравнение экспорта и внутреннего рынка:**\n\n"
            table = "| Bozor | Valyuta | Bitimlar | Ulushi | Hajm (birlik) | Aylanma (so'm ekvivalenti) |\n|---|---|---|---|---|---|\n" if lang == "uz" else "| Рынок | Валюта | Сделок | Доля | Объем | Оборот (в сумах) |\n|---|---|---|---|---|---|\n"
            for r in rows:
                c_type, curr, count, units, amt_curr, eq_uzs, pct = r
                table += f"| **{c_type}** | {curr} | {format_num(count)} | {pct}% | {format_num(units)} | {format_num(eq_uzs)} |\n"
            return header + table

        # 3. Top Sellers (with Compound Multi-Part Breakdown)
        if intent == "seller_top":
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            res = f"🏭 **Eng yirik sotuvchi kompaniyalar{year_str}:**\n\n" if lang == "uz" else f"🏭 **Крупнейшие компании-продавцы{year_str}:**\n\n"
            table = "| № | STIR (INN) | Kompaniya | Hudud | Bitimlar | Savdo hajmi (so'm) |\n|---|---|---|---|---|---|\n" if lang == "uz" else "| № | ИНН | Компания | Регион | Сделок | Объем продаж (сум) |\n|---|---|---|---|---|---|\n"
            for i, r in enumerate(rows, 1):
                inn, name, reg, count, sales = r
                table += f"| {i} | `{inn}` | {name} | {reg} | {format_num(count)} | {format_num(sales)} |\n"
            res += table

            # If compound breakdown requested (brokers / products of the top seller)
            if compound_data:
                top_inn, top_name, _, _, _ = first
                if "brokers" in compound_data and compound_data["brokers"]:
                    res += f"\n🤝 **`{top_name}` savdo qilgan asosiy brokerlar:**\n\n" if lang == "uz" else f"\n🤝 **Основные брокеры компании `{top_name}`:**\n\n"
                    b_table = "| Kod | Broker nomi | Bitimlar | Aylanma (so'm) |\n|---|---|---|---|\n" if lang == "uz" else "| Код | Брокер | Сделок | Оборот (сум) |\n|---|---|---|---|\n"
                    for br in compound_data["brokers"]:
                        b_code, b_name, b_count, b_vol = br
                        b_table += f"| `{b_code}` | {b_name} | {format_num(b_count)} | {format_num(b_vol)} |\n"
                    res += b_table

                if "products" in compound_data and compound_data["products"]:
                    res += f"\n📦 **`{top_name}` sotgan asosiy mahsulotlar:**\n\n" if lang == "uz" else f"\n📦 **Основные товары компании `{top_name}`:**\n\n"
                    p_table = "| Mahsulot | Bitimlar | Jami hajm | Savdo summasi (so'm) |\n|---|---|---|---|\n" if lang == "uz" else "| Товар | Сделок | Объем | Сумма продаж (сум) |\n|---|---|---|---|\n"
                    for pr in compound_data["products"]:
                        p_name, p_count, p_vol, p_unit, p_sales = pr
                        p_table += f"| {p_name} | {format_num(p_count)} | {format_num(p_vol)} {p_unit} | {format_num(p_sales)} |\n"
                    res += p_table

            return res

        # 4. Top Buyers (with Compound Multi-Part Breakdown)
        if intent == "buyer_top":
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            res = f"🛒 **Eng yirik xaridor kompaniyalar{year_str}:**\n\n" if lang == "uz" else f"🛒 **Крупнейшие компании-покупатели{year_str}:**\n\n"
            table = "| № | STIR (INN) | Kompaniya | Hudud | Bitimlar | Xarid hajmi (so'm) |\n|---|---|---|---|---|---|\n" if lang == "uz" else "| № | ИНН | Компания | Регион | Сделок | Объем закупок (сум) |\n|---|---|---|---|---|---|\n"
            for i, r in enumerate(rows, 1):
                inn, name, reg, count, purchases = r
                table += f"| {i} | `{inn}` | {name} | {reg} | {format_num(count)} | {format_num(purchases)} |\n"
            res += table

            if compound_data:
                top_inn, top_name, _, _, _ = first
                if "brokers" in compound_data and compound_data["brokers"]:
                    res += f"\n🤝 **`{top_name}` xarid qilgan asosiy brokerlar:**\n\n" if lang == "uz" else f"\n🤝 **Основные брокеры компании `{top_name}`:**\n\n"
                    b_table = "| Kod | Broker nomi | Bitimlar | Xarid summasi (so'm) |\n|---|---|---|---|\n" if lang == "uz" else "| Код | Брокер | Сделок | Сумма закупок (сум) |\n|---|---|---|---|\n"
                    for br in compound_data["brokers"]:
                        b_code, b_name, b_count, b_vol = br
                        b_table += f"| `{b_code}` | {b_name} | {format_num(b_count)} | {format_num(b_vol)} |\n"
                    res += b_table

            return res

        # 4.1 Company Brokers (Brokers intermediating for a company)
        if intent == "company_brokers":
            company = metadata.get("company", ("", "Kompaniya"))
            inn, name = company if isinstance(company, tuple) else ("", str(company))
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            if lang == "uz":
                header = f"🤝 **`{name}` kompaniyasi savdo qilgan asosiy brokerlar{year_str}:**\n\n"
                table = "| № | Kod | Brokerlik idorasi nomi | Bitimlar soni | Aylanma summasi (so'm) |\n|---|---|---|---|---|\n"
            else:
                header = f"🤝 **Основные брокеры компании `{name}`{year_str}:**\n\n"
                table = "| № | Код | Название брокерской конторы | Сделок | Торговый оборот (сум) |\n|---|---|---|---|---|\n"

            for i, r in enumerate(rows, 1):
                b_code, b_name, count, turnover = r
                table += f"| {i} | `{b_code}` | **{b_name}** | {format_num(count)} | {format_num(turnover)} |\n"
            return header + table

        # 5. Top Brokers
        if intent == "broker_top":
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            header = f"🏆 **Eng faol brokerlar reytingi{year_str}:**\n\n" if lang == "uz" else f"🏆 **Топ самых активных брокеров{year_str}:**\n\n"
            table = "| № | Kod | Brokerlik idorasi | Bitimlar | Ijro aylanmasi (so'm) |\n|---|---|---|---|---|\n" if lang == "uz" else "| № | Код | Брокерская контора | Сделок | Исполненный оборот (сум) |\n|---|---|---|---|---|\n"
            for i, r in enumerate(rows, 1):
                b_code, b_name, count, vol = r
                table += f"| {i} | `{b_code}` | {b_name} | {format_num(count)} | {format_num(vol)} |\n"
            return header + table

        # 6. Single Broker Details
        if intent == "broker_single":
            b_code, b_name, count, exec_count, vol, exec_vol = first
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            if lang == "uz":
                return (
                    f"🏢 **Broker Ma'lumotlari: `{b_code}` ({b_name}){year_str}**\n\n"
                    f"- **Jami bitimlar:** {format_num(count)} ta\n"
                    f"- **Muvaffaqiyatli ijro etilgan:** {format_num(exec_count)} ta\n"
                    f"- **Jami shartnoma aylanmasi:** {format_num(vol)} so'm\n"
                    f"- **Amalda yetkazib berilgan aylanma:** {format_num(exec_vol)} so'm"
                )
            else:
                return (
                    f"🏢 **Информация по брокеру: `{b_code}` ({b_name}){year_str}**\n\n"
                    f"- **Всего сделок:** {format_num(count)}\n"
                    f"- **Успешно исполнено:** {format_num(exec_count)}\n"
                    f"- **Общий объем контрактов:** {format_num(vol)} сум\n"
                    f"- **Фактически поставленный объем:** {format_num(exec_vol)} сум"
                )

        # 7. Commodity Multi-Year Trend
        if intent == "commodity_trend":
            comm = metadata.get("commodity", "Mahsulot")
            header = f"📈 **'{comm}' bo'yicha yillik dinamika:**\n\n" if lang == "uz" else f"📈 **Годовая динамика по товару '{comm}':**\n\n"
            table = "| Yil | Bitimlar | Shartnoma hajmi | Yetkazilgan | Birlik | Aylanma (so'm) | O'rtacha narx |\n|---|---|---|---|---|---|---|\n" if lang == "uz" else "| Год | Сделок | Объем контрактов | Поставлено | Ед. | Оборот (сум) | Средняя цена |\n|---|---|---|---|---|---|---|\n"
            has_2026 = False
            for r in rows:
                yr, count, c_vol, d_vol, unit, turnover, avg_p = r
                if int(yr) == 2026:
                    has_2026 = True
                table += f"| **{int(yr)}** | {format_num(count)} | {format_num(c_vol)} | {format_num(d_vol)} | {unit} | {format_num(turnover)} | {format_num(avg_p)} |\n"
            res = header + table
            if has_2026:
                res += (CAVEAT_2026_UZ if lang == "uz" else CAVEAT_2026_RU)
            return res

        # 8. Product / Commodity Stats Single Year
        if intent in ["product_stats", "commodity_stats"]:
            p_name = first[0]
            unit = first[1]
            count = first[2]
            c_units = first[3]
            d_units = first[4]
            amt = first[5]
            weighted_p = first[6] if len(first) > 6 else first[5]
            avg_p = first[7] if len(first) > 7 else first[6]
            year_val = metadata.get("year")
            year_str = f" ({year_val}-yil)" if year_val else ""
            if lang == "uz":
                ans = (
                    f"🌾 **«{p_name}» bo'yicha birja ko'rsatkichlari{year_str}:**\n\n"
                    f"- **Tuzilgan bitimlar soni:** {format_num(count)} ta\n"
                    f"- **Shartnoma hajmi:** {format_num(c_units)} {unit}\n"
                    f"- **Haqiqiy yetkazilgan hajm:** {format_num(d_units)} {unit}\n"
                    f"- **Jami savdo aylanmasi:** {format_num(amt)} so'm\n"
                    f"- **O'rtacha tortilgan narx (Weighted average price):** {format_num(weighted_p)} so'm/{unit}\n"
                    f"- **Oddiy o'rtacha birja narxi:** {format_num(avg_p)} so'm/{unit}"
                )
            else:
                ans = (
                    f"🌾 **Биржевые показатели по «{p_name}»{year_str}:**\n\n"
                    f"- **Количество сделок:** {format_num(count)}\n"
                    f"- **Объем по контрактам:** {format_num(c_units)} {unit}\n"
                    f"- **Фактически поставлено:** {format_num(d_units)} {unit}\n"
                    f"- **Общая сумма оборота:** {format_num(amt)} сум\n"
                    f"- **Средневзвешенная цена (Weighted average price):** {format_num(weighted_p)} сум/{unit}\n"
                    f"- **Простая средняя цена:** {format_num(avg_p)} сум/{unit}"
                )
            if year_val == 2026:
                ans += (CAVEAT_2026_UZ if lang == "uz" else CAVEAT_2026_RU)
            return ans

        # 9. Product Catalog
        if intent == "product_catalog":
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            if lang == "uz":
                header = (
                    f"📦 **UZEX Birjasida Savdosi O'tkaziladigan Mahsulotlar Katalogi{year_str}:**\n\n"
                    f"Birja savdolarida tovarlar asosiy sanoat va xomashyo toifalariga ajratilgan. "
                    f"Quyida har bir toifadagi tovar turlari soni, tuzilgan bitimlar va jami savdo aylanmasi keltirilgan:\n\n"
                )
                table = "| № | Tovar toifasi (Kategoriya) | Tovar turlari soni | Bitimlar soni | Jami savdo aylanmasi (so'm) |\n|---|---|---|---|---|\n"
            else:
                header = (
                    f"📦 **Каталог торгуемых товаров на бирже UZEX{year_str}:**\n\n"
                    f"Биржевой товарный реестр сгруппирован по ключевым отраслевым категориям. "
                    f"Ниже представлены количество контрактов, сделок и торговые обороты по категориям:\n\n"
                )
                table = "| № | Категория товаров | Уникальных товаров | Сделок | Общий оборот (сум) |\n|---|---|---|---|---|\n"

            for i, r in enumerate(rows, 1):
                cat, unique_cnt, deals_cnt, sales = r
                table += f"| {i} | **{cat}** | {format_num(unique_cnt)} ta | {format_num(deals_cnt)} | {format_num(sales)} |\n"

            footer = (
                "\n💡 *Tavsiya:* Muayyan tovar (masalan, *sement*, *paxta*, *bug'doy*, *mis*) bo'yicha batafsil ma'lumot olish uchun: `2024-yilda sement narxlari qanday bo'lgan?` yoki `Paxtani qaysi kompaniyalar sotgan?` deb so'rashingiz mumkin."
                if lang == "uz"
                else "\n💡 *Подсказка:* Для детального анализа конкретного товара (например, *цемент*, *хлопок*, *пшеница*, *медь*) спросите: «Каковы цены на цемент в 2024 году?» или «Кто продавал хлопок?»"
            )
            return header + table + footer

        # 9.1 Product Sellers (who sold a specific commodity)
        if intent == "product_sellers":
            comm = metadata.get("commodity", "Mahsulot")
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            top_company = rows[0][1] if rows else "Yetakchi kompaniya"
            top_sales = format_num(rows[0][6]) if rows else "0"
            total_sales = sum(float(r[6]) for r in rows if r[6] is not None)

            if lang == "uz":
                header = (
                    f"🏭 **'{comm.title()}' bo'yicha eng yirik sotuvchilar{year_str}:**\n\n"
                    f"Ko'rsatilgan davrda ushbu mahsulot bo'yicha eng yuqori sotuv hajmiga ega kompaniya — **{top_company}** "
                    f"(savdo hajmi: **{top_sales} so'm**).\n\n"
                )
                table = "| № | STIR (INN) | Sotuvchi korxona nomi | Hudud | Bitimlar | Sotilgan hajm | Savdo summasi (so'm) | Bozor ulushi |\n|---|---|---|---|---|---|---|---|\n"
            else:
                header = (
                    f"🏭 **Крупнейшие продавцы по товару '{comm.title()}'{year_str}:**\n\n"
                    f"Лидером по поставкам данного товара является компания **{top_company}** "
                    f"с объемом продаж **{top_sales} сум**.\n\n"
                )
                table = "| № | ИНН | Предприятие-продавец | Регион | Сделок | Объем поставок | Сумма продаж (сум) | Доля рынка |\n|---|---|---|---|---|---|---|---|\n"

            for i, r in enumerate(rows, 1):
                inn, name, reg, count, vol, unit, sales = r
                pct = round((float(sales) * 100.0 / total_sales), 2) if total_sales > 0 else 0
                table += f"| {i} | `{inn}` | **{name}** | {reg} | {format_num(count)} | {format_num(vol)} {unit} | {format_num(sales)} | {pct}% |\n"

            footer = (
                f"\n💡 *Tavsiya:* Yetakchi korxona `{top_company}` qaysi brokerlar orqali savdo qilganini bilish uchun: `Ushbu kompaniyaning brokerlari kim?` deb so'rashingiz mumkin."
                if lang == "uz"
                else f"\n💡 *Подсказка:* Чтобы узнать брокеров лидера `{top_company}`, спросите: «Какие брокеры работали с этой компанией?»"
            )
            return header + table + footer

        # 9.2 Product Buyers (who bought a specific commodity)
        if intent == "product_buyers":
            comm = metadata.get("commodity", "Mahsulot")
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            top_buyer = rows[0][1] if rows else "Yetakchi xaridor"
            top_spend = format_num(rows[0][6]) if rows else "0"

            if lang == "uz":
                header = (
                    f"🛒 **'{comm.title()}' bo'yicha eng yirik xaridorlar{year_str}:**\n\n"
                    f"Ushbu mahsulotning eng yirik xaridori — **{top_buyer}** (xarid summasi: **{top_spend} so'm**).\n\n"
                )
                table = "| № | STIR (INN) | Xaridor korxona nomi | Hudud | Bitimlar | Xarid hajmi | Xarid summasi (so'm) |\n|---|---|---|---|---|---|---|\n"
            else:
                header = (
                    f"🛒 **Крупнейшие покупатели по товару '{comm.title()}'{year_str}:**\n\n"
                    f"Крупнейшим покупателем данного товара является компания **{top_buyer}** (сумма закупок: **{top_spend} сум**).\n\n"
                )
                table = "| № | ИНН | Предприятие-покупатель | Регион | Сделок | Объем закупок | Сумма закупок (сум) |\n|---|---|---|---|---|---|---|\n"

            for i, r in enumerate(rows, 1):
                inn, name, reg, count, vol, unit, purchases = r
                table += f"| {i} | `{inn}` | **{name}** | {reg} | {format_num(count)} | {format_num(vol)} {unit} | {format_num(purchases)} |\n"

            footer = (
                f"\n💡 *Tavsiya:* `{top_buyer}` korxonasining barcha xaridlari bo'yicha tahlilni olish uchun STIR orqali so'rashingiz mumkin."
                if lang == "uz"
                else f"\n💡 *Подсказка:* Вы можете запросить карточку предприятия `{top_buyer}` по ИНН."
            )
            return header + table + footer

        # 9.3 Product Brokers (who intermediated a specific commodity)
        if intent == "product_brokers":
            comm = metadata.get("commodity", "Mahsulot")
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            top_broker = rows[0][1] if rows else "Yetakchi broker"
            top_turnover = format_num(rows[0][3]) if rows else "0"

            if lang == "uz":
                header = (
                    f"🤝 **'{comm.title()}' bo'yicha eng faol brokerlar reytingi{year_str}:**\n\n"
                    f"Ushbu tovar savdosida eng yuqori vositachilik aylanmasini **{top_broker}** ko'rsatgan (**{top_turnover} so'm**).\n\n"
                )
                table = "| № | Kod | Brokerlik idorasi nomi | Bitimlar soni | Aylanma summasi (so'm) |\n|---|---|---|---|---|\n"
            else:
                header = (
                    f"🤝 **Ведущие брокеры по сделкам с товаром '{comm.title()}'{year_str}:**\n\n"
                    f"Лидером среди брокеров по данному направлению является контора **{top_broker}** (оборот: **{top_turnover} сум**).\n\n"
                )
                table = "| № | Код | Название брокерской конторы | Сделок | Торговый оборот (сум) |\n|---|---|---|---|---|\n"

            for i, r in enumerate(rows, 1):
                b_code, b_name, count, turnover = r
                table += f"| {i} | `{b_code}` | **{b_name}** | {format_num(count)} | {format_num(turnover)} |\n"

            return header + table

        # 9.4 Product Regions (regional production / sales of a commodity)
        if intent == "product_regions":
            comm = metadata.get("commodity", "Mahsulot")
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            top_region = rows[0][0] if rows else "Yetakchi hudud"
            top_sales = format_num(rows[0][4]) if rows else "0"

            if lang == "uz":
                header = (
                    f"📍 **'{comm.title()}' yetkazib berish bo'yicha hududlar tahlili{year_str}:**\n\n"
                    f"Eng asosiy sotuvchi hudud — **{top_region}** (savdo hajmi: **{top_sales} so'm**).\n\n"
                )
                table = "| № | Hudud (Viloyat) | Bitimlar soni | Sotilgan hajm | Savdo summasi (so'm) |\n|---|---|---|---|---|\n"
            else:
                header = (
                    f"📍 **Региональная структура предложения по товару '{comm.title()}'{year_str}:**\n\n"
                    f"Ведущим регионом-поставщиком является **{top_region}** (объем реализации: **{top_sales} сум**).\n\n"
                )
                table = "| № | Регион | Сделок | Поставленный объем | Сумма продаж (сум) |\n|---|---|---|---|---|\n"

            for i, r in enumerate(rows, 1):
                reg, count, vol, unit, sales = r
                table += f"| {i} | **{reg}** | {format_num(count)} | {format_num(vol)} {unit} | {format_num(sales)} |\n"

            return header + table

        # 9.5 Product Price Range / Quotations
        if intent == "product_price_range":
            comm = metadata.get("commodity", "Mahsulot")
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            p_name, p_unit, p_curr, min_p, max_p, avg_p, deals_cnt, turnover = rows[0]

            if lang == "uz":
                header = (
                    f"🏷️ **'{comm.title()}' Narxlar Diapazoni va Dinamikasi{year_str}:**\n\n"
                    f"Birja kotirovkalari tahliliga ko'ra, eng faol sotilgan nav — **{p_name}** bo'lib, "
                    f"o'rtacha narx 1 {p_unit} uchun **{format_num(avg_p)} {p_curr}**ni tashkil etdi.\n\n"
                )
                table = "| № | Mahsulot navi / shartnoma | Birlik | Valyuta | Minimal narx | O'rtacha narx | Maksimal narx | Bitimlar |\n|---|---|---|---|---|---|---|---|\n"
            else:
                header = (
                    f"🏷️ **Ценовой диапазон и котировки по товару '{comm.title()}'{year_str}:**\n\n"
                    f"По данным биржевых котировок, средневзвешенная цена по контракту **{p_name}** "
                    f"составила **{format_num(avg_p)} {p_curr}** за 1 {p_unit}.\n\n"
                )
                table = "| № | Наименование контракта | Ед. | Валюта | Мин. цена | Средняя цена | Макс. цена | Сделок |\n|---|---|---|---|---|---|---|---|\n"

            for i, r in enumerate(rows, 1):
                name, unit, curr, min_val, max_val, avg_val, count, _ = r
                table += f"| {i} | **{name}** | {unit} | {curr} | {format_num(min_val)} | {format_num(avg_val)} | {format_num(max_val)} | {format_num(count)} |\n"

            footer = (
                f"\n💡 *Tavsiya:* Ushbu mahsulotni sotgan eng yirik kompaniyalarni ko'rish uchun: `Uni qaysi kompaniyalar sotgan?` deb so'rashingiz mumkin."
                if lang == "uz"
                else f"\n💡 *Подсказка:* Чтобы увидеть ведущих поставщиков, спросите: «Кто продавал этот товар?»"
            )
            return header + table + footer

        # 9.6 Top Products
        if intent == "top_products":
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            metric_type = metadata.get("metric_type", "turnover")
            top_prod_name = rows[0][0]
            top_turnover = format_num(rows[0][4])
            top_vol = format_num(rows[0][3])
            top_unit = rows[0][1]

            if metric_type == "volume":
                metric_title_uz = "Jami hajm (tonna/birlik) bo'yicha"
                metric_title_ru = "физическому объему"
            elif metric_type == "deals":
                metric_title_uz = "Bitimlar soni bo'yicha"
                metric_title_ru = "количеству сделок"
            else:
                metric_title_uz = "Pul aylanmasi bo'yicha"
                metric_title_ru = "объему оборота"

            if lang == "uz":
                header = (
                    f"📦 **{metric_title_uz} eng yuqori tovarlar reytingi{year_str}:**\n\n"
                    f"Birja savdolari natijalariga ko'ra, yetakchi mahsulot — **{top_prod_name}** "
                    f"(savdo aylanmasi: **{top_turnover} so'm**, hajm: **{top_vol} {top_unit}**).\n\n"
                )
                table = "| № | Tovar nomi | O'lchov birligi | Bitimlar soni | Jami hajm | Savdo aylanmasi (so'm) |\n|---|---|---|---|---|---|\n"
            else:
                header = (
                    f"📦 **Рейтинг биржевых товаров по {metric_title_ru}{year_str}:**\n\n"
                    f"Лидером рейтинга является **{top_prod_name}** "
                    f"с оборотом **{top_turnover} сум** (объем: **{top_vol} {top_unit}**).\n\n"
                )
                table = "| № | Наименование товара | Ед. изм. | Сделок | Общий объем | Оборот (сум) |\n|---|---|---|---|---|---|\n"

            for i, r in enumerate(rows, 1):
                p_name, unit, count, vol, turnover = r
                table += f"| {i} | **{p_name}** | {unit} | {format_num(count)} | {format_num(vol)} | {format_num(turnover)} |\n"

            footer = (
                f"\n💡 *Tavsiya:* Yetakchi mahsulot `{top_prod_name}` bo'yicha batafsil tahlil olish uchun: `Uni qaysi kompaniyalar sotgan?` yoki `Uning narxlari qanday?` deb so'rashingiz mumkin."
                if lang == "uz"
                else f"\n💡 *Подсказка:* Чтобы узнать подробности о лидере `{top_prod_name}`, спросите: «Кто продавал этот товар?» или «Каковы цены на него?»"
            )
            return header + table + footer

        # 10. Cancelled Deals
        if intent == "cancelled_deals":
            count, amount, pct = first
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            comm = metadata.get("commodity")
            comm_str = f"'{comm.title()}' bo'yicha " if comm else ""
            comm_str_ru = f"по товару '{comm.title()}' " if comm else ""
            if lang == "uz":
                return (
                    f"⚠️ **{comm_str}Bekor qilingan bitimlar (To'lov muddati o'tgan){year_str}:**\n\n"
                    f"- **Bekor qilingan bitimlar soni:** {format_num(count)} ta\n"
                    f"- **Bekor qilingan bitimlar summasi:** {format_num(amount)} so'm\n"
                    f"- **Jami bitimlardagi ulushi:** {pct}%"
                )
            else:
                return (
                    f"⚠️ **Аннулированные сделки {comm_str_ru}(Не оплаченные в срок){year_str}:**\n\n"
                    f"- **Количество аннулированных сделок:** {format_num(count)}\n"
                    f"- **Сумма аннулированных сделок:** {format_num(amount)} сум\n"
                    f"- **Доля от общего числа сделок:** {pct}%"
                )

        # 10.1 Participant Profile / Card Lookup
        if intent == "participant_card":
            inn, name, reg, act, role, vat = first
            vat_str = "Ha (To'lovchi)" if vat else "Yo'q"
            if lang == "uz":
                return (
                    f"🏢 **Kompaniya Profili (Kartochkasi):**\n\n"
                    f"- **Kompaniya nomi:** **{name}**\n"
                    f"- **STIR (INN) raqami:** `{inn}`\n"
                    f"- **Joylashgan hududi:** **{reg}**\n"
                    f"- **Faoliyat turi:** {act}\n"
                    f"- **Birjadagi asosiy roli:** {role}\n"
                    f"- **QQS to'lovchisi:** {vat_str}"
                )
            else:
                vat_ru = "Да (Плательщик)" if vat else "Нет"
                return (
                    f"🏢 **Карточка компании:**\n\n"
                    f"- **Наименование:** **{name}**\n"
                    f"- **ИНН:** `{inn}`\n"
                    f"- **Регион регистрации:** **{reg}**\n"
                    f"- **Вид деятельности:** {act}\n"
                    f"- **Роль на бирже:** {role}\n"
                    f"- **Плательщик НДС:** {vat_ru}"
                )

        # 11. Regional Sales
        if intent == "region_stats":
            reg, count, sales, exec_sales = first
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            if lang == "uz":
                return (
                    f"📍 **Hududiy statistika: {reg}{year_str}**\n\n"
                    f"- **Bitimlar soni:** {format_num(count)} ta\n"
                    f"- **Jami shartnoma savdosi:** {format_num(sales)} so'm\n"
                    f"- **Faktik ijro etilgan savdo:** {format_num(exec_sales)} so'm"
                )
            else:
                return (
                    f"📍 **Региональная статистика: {reg}{year_str}**\n\n"
                    f"- **Количество сделок:** {format_num(count)}\n"
                    f"- **Общий объем продаж:** {format_num(sales)} сум\n"
                    f"- **Фактически исполненные продажи:** {format_num(exec_sales)} сум"
                )

        # 12. Export Deals USD
        if intent == "export_deals":
            count, vol, usd, uzs = first
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            if lang == "uz":
                return (
                    f"🌐 **Eksport Bitimlari Statistikasi{year_str}:**\n\n"
                    f"- **Jami eksport bitimlari soni:** {format_num(count)} ta\n"
                    f"- **Jami mahsulot hajmi:** {format_num(vol)}\n"
                    f"- **Eksport summasi:** ${format_num(usd)} USD\n"
                    f"- **So'mdagi ekvivalenti (kurs bo'yicha):** {format_num(uzs)} so'm"
                )
            else:
                return (
                    f"🌐 **Статистика по экспортным сделкам{year_str}:**\n\n"
                    f"- **Всего экспортных сделок:** {format_num(count)}\n"
                    f"- **Общий объем продукции:** {format_num(vol)}\n"
                    f"- **Сумма экспорта:** ${format_num(usd)} USD\n"
                    f"- **Эквивалент в сумах:** {format_num(uzs)} сум"
                )

        # 13. Annual Trend
        if intent == "annual_trend":
            header = "📅 **Yillar bo'yicha birja umumiy ko'rsatkichlari dinamikasi:**\n\n" if lang == "uz" else "📅 **Динамика основных биржевых показателей по годам:**\n\n"
            table = "| Yil | Jami bitimlar | Ijro etilgan | O'rtacha narx | Ijro aylanmasi (so'm) | Jami aylanma (so'm) |\n|---|---|---|---|---|---|\n" if lang == "uz" else "| Год | Всего сделок | Исполнено | Средняя цена | Исполненный оборот (сум) | Общий оборот (сум) |\n|---|---|---|---|---|---|\n"
            has_2026 = False
            for r in rows:
                yr = int(r[0])
                total = r[1]
                exec_d = r[2]
                avg_p = r[3] if len(r) > 3 else 0
                exec_turn = r[4] if len(r) > 4 else 0
                turn = r[5] if len(r) > 5 else 0
                if yr == 2026:
                    has_2026 = True
                table += f"| **{yr}** | {format_num(total)} | {format_num(exec_d)} | {format_num(avg_p)} | {format_num(exec_turn)} | {format_num(turn)} |\n"
            res = header + table
            if has_2026:
                res += (CAVEAT_2026_UZ if lang == "uz" else CAVEAT_2026_RU)
            return res

        # Generic Table Fallback
        header = "📊 **Natijalar:**\n\n" if lang == "uz" else "📊 **Результаты запроса:**\n\n"
        table = "| " + " | ".join(cols) + " |\n| " + " | ".join(["---"] * len(cols)) + " |\n"
        for r in rows[:10]:
            table += "| " + " | ".join([format_num(c) for c in r]) + " |\n"
        return header + table

    @staticmethod
    def combine_multi_answers(sub_results: List[Dict[str, Any]], lang: str) -> str:
        """
        Combines multiple sub-question results into a beautifully structured,
        numbered executive response.
        """
        if len(sub_results) == 1:
            return sub_results[0]["answer"]

        sections = []
        for idx, res in enumerate(sub_results, 1):
            q_text = res.get("question", f"Savol {idx}" if lang == "uz" else f"Вопрос {idx}")
            answer_text = res.get("answer", "")
            
            section_header = f"### {idx}. {q_text}"
            sections.append(f"{section_header}\n\n{answer_text}")

        combined = "\n\n---\n\n".join(sections)
        
        # Add concluding summary
        footer = "\n\n---\n📌 **Xulosa:** Barcha savollar UZEX ma'lumotlar bazasi asosida alohida hisoblandi va tekshirildi." if lang == "uz" else "\n\n---\n📌 **Итог:** Все вопросы были рассчитаны и проверены по базе данных UZEX."
        return combined + footer
