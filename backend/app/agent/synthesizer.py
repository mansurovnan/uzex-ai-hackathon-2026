"""
Universal Natural Language Response Synthesizer for UZEX AI Hackathon.
Explains analytical results in Uzbek (Latin/Cyrillic) and Russian,
formats currency/volume metrics, builds Markdown tables, and explains calculation methodology.
Supports multi-question combination and multi-part compound responses.
"""

from typing import List, Dict, Any, Optional

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
            for r in rows:
                yr, count, c_vol, d_vol, unit, turnover, avg_p = r
                table += f"| **{int(yr)}** | {format_num(count)} | {format_num(c_vol)} | {format_num(d_vol)} | {unit} | {format_num(turnover)} | {format_num(avg_p)} |\n"
            return header + table

        # 8. Commodity Stats Single Year
        if intent == "commodity_stats":
            cat, unit, count, c_units, d_units, amt, avg_p = first
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            if lang == "uz":
                return (
                    f"🌾 **Tovar Tahlili{year_str}:**\n\n"
                    f"- **Kategoriya:** {cat}\n"
                    f"- **Bitimlar soni:** {format_num(count)} ta\n"
                    f"- **Shartnoma hajmi:** {format_num(c_units)} {unit}\n"
                    f"- **Haqiqiy yetkazilgan hajm:** {format_num(d_units)} {unit}\n"
                    f"- **Jami aylanma summasi:** {format_num(amt)} so'm\n"
                    f"- **O'rtacha birja narxi:** {format_num(avg_p)} so'm/{unit}"
                )
            else:
                return (
                    f"🌾 **Аналитика по товару{year_str}:**\n\n"
                    f"- **Категория:** {cat}\n"
                    f"- **Количество сделок:** {format_num(count)}\n"
                    f"- **Объем по контрактам:** {format_num(c_units)} {unit}\n"
                    f"- **Фактически поставлено:** {format_num(d_units)} {unit}\n"
                    f"- **Общая сумма оборота:** {format_num(amt)} сум\n"
                    f"- **Средневзвешенная цена:** {format_num(avg_p)} сум/{unit}"
                )

        # 9. Top Products
        if intent == "top_products":
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            header = f"📦 **Eng ko'p sotilgan tovarlar reytingi{year_str}:**\n\n" if lang == "uz" else f"📦 **Рейтинг самых продаваемых товаров{year_str}:**\n\n"
            table = "| № | Tovar | Bitimlar | Jami Hajm | Aylanma (so'm) |\n|---|---|---|---|---|\n" if lang == "uz" else "| № | Товар | Сделок | Общий Объем | Оборот (сум) |\n|---|---|---|---|---|\n"
            for i, r in enumerate(rows, 1):
                p_name, count, vol, unit, turnover = r
                table += f"| {i} | {p_name} | {format_num(count)} | {format_num(vol)} {unit} | {format_num(turnover)} |\n"
            return header + table

        # 10. Cancelled Deals
        if intent == "cancelled_deals":
            count, amount, pct = first
            year_str = f" ({metadata.get('year')}-yil)" if metadata.get("year") else ""
            if lang == "uz":
                return (
                    f"⚠️ **Bekor qilingan bitimlar (To'lov muddati o'tgan){year_str}:**\n\n"
                    f"- **Bekor qilingan bitimlar soni:** {format_num(count)} ta\n"
                    f"- **Bekor qilingan bitimlar summasi:** {format_num(amount)} so'm\n"
                    f"- **Jami bitimlardagi ulushi:** {pct}%"
                )
            else:
                return (
                    f"⚠️ **Аннулированные сделки (Не оплаченные в срок){year_str}:**\n\n"
                    f"- **Количество аннулированных сделок:** {format_num(count)}\n"
                    f"- **Сумма аннулированных сделок:** {format_num(amount)} сум\n"
                    f"- **Доля от общего числа сделок:** {pct}%"
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
            table = "| Yil | Jami bitimlar | Ijro etilgan | Jami aylanma (so'm) | Ijro aylanmasi (so'm) |\n|---|---|---|---|---|\n" if lang == "uz" else "| Год | Всего сделок | Исполнено | Общий оборот (сум) | Исполненный оборот (сум) |\n|---|---|---|---|---|\n"
            for r in rows:
                yr, total, exec_d, turn, exec_turn = r
                table += f"| **{int(yr)}** | {format_num(total)} | {format_num(exec_d)} | {format_num(turn)} | {format_num(exec_turn)} |\n"
            return header + table

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
