"""
Human-Like Conversational Intelligence Agent for UZEX AI.
Handles greetings, small talk, gratitude, farewells, apologies, and bot identity questions
in Uzbek (Latin and Cyrillic) and Russian without executing unnecessary SQL queries.
"""

import re
import random
from typing import Optional, Tuple, Dict, Any

class ConversationalAgent:
    """
    Detects and handles natural human conversational interactions with varied, 
    polite, and professional responses.
    """
    
    # 1. Greetings
    GREETINGS_UZ = [
        "salom", "assalomu alaykum", "assalom", "qandaysiz", "qalaysiz", 
        "ishlar qalay", "yaxshimisiz", "salomatmisiz", "xayrli tong", 
        "xayrli kun", "xayrli kech", "hormang", "charchamang"
    ]
    GREETINGS_UZ_CYR = [
        "салом", "ассалому алайкум", "ассалом", "қандайсиз", "қалайсиз",
        "ишлар қалай", "яхшимисиз", "саломатмисиз", "хайрли тонг",
        "хайрли кун", "хайрли кеч", "ҳорманг", "чарчаманг"
    ]
    GREETINGS_RU = [
        "привет", "здравствуйте", "здравствуй", "добрый день", "доброе утро",
        "добрый вечер", "салют", "приветствую", "как дела", "как поживаешь", "доброго времени суток"
    ]

    # 2. Gratitude
    THANKS_UZ = ["rahmat", "katta rahmat", "tashakkur", "minnatdorman", "raxmat", "tashakkurlar"]
    THANKS_UZ_CYR = ["раҳмат", "катта раҳмат", "ташаккур", "миннатдорман", "рахмат"]
    THANKS_RU = ["спасибо", "большое спасибо", "благодарю", "огромное спасибо", "мерси"]

    # 3. Farewells
    FAREWELL_UZ = ["xayr", "ko'rishguncha", "salomat bo'ling", "yaxshi qoling", "hayr", "omon bo'ling"]
    FAREWELL_UZ_CYR = ["хайр", "кўришгунча", "саломат бўлинг", "яхши қолинг", "омон бўлинг"]
    FAREWELL_RU = ["пока", "до свидания", "до встречи", "всего доброго", "увидимся", "прощай"]

    # 4. Identity & Capabilities
    IDENTITY_UZ = ["sen kimsan", "kim bu", "nima qila olasan", "qanday yordam berasan", "vazifang nima", "o'zing haqingda"]
    IDENTITY_UZ_CYR = ["сен кимсан", "ким бу", "нима қила оласан", "қандай ёрдам берасан", "вазифанг нима", "ўзинг ҳақингда"]
    IDENTITY_RU = ["кто ты", "что ты умеешь", "чем ты можешь помочь", "каковы твои функции", "расскажи о себе", "что это за бот"]

    # 5. Casual affirmative / acknowledgments
    CASUAL_UZ = ["tushunarli", "xo'p", "mayli", "ha", "yaxshi", "ok", "tushundim"]
    CASUAL_UZ_CYR = ["тушунарли", "хўп", "майли", "ҳа", "яхши", "тушундим"]
    CASUAL_RU = ["понятно", "хорошо", "ясно", "ок", "ладно", "понял", "отлично"]

    # Analytical indicators that mean the message is NOT pure small talk
    ANALYTICAL_INDICATORS = [
        "202", "19", "yil", "yili", "bitim", "tovar", "mahsulot", "kompaniya", 
        "broker", "summa", "aylanma", "narx", "narxi", "qancha", "nechta", "kim", 
        "kimlar", "sotgan", "olgan", "xarid", "eksport", "ichki", "hajm", "dinamika",
        "reyting", "top", "solishtir", "taqqosla", "bekor", "klaster", "stir", "inn",
        "год", "году", "сделка", "сделок", "товар", "товаров", "компания", "компаний",
        "брокер", "брокеров", "сумма", "оборот", "цена", "цены", "сколько", "кто", 
        "продал", "купил", "закуп", "экспорт", "объем", "динамика", "рейтинг", "сравни"
    ]

    @classmethod
    def is_conversational_only(cls, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Determines if the text is strictly a conversational phrase (greeting, thanks, etc.)
        without an analytical exchange query.
        Returns: (is_conversational, category, language)
        """
        t = text.lower().strip()
        # Clean punctuation for checking
        t_clean = re.sub(r'[!?,.:;]+', ' ', t).strip()
        t_clean = re.sub(r'\s+', ' ', t_clean)

        # If it has clear analytical terms, it's not conversational only
        words = t_clean.split()
        has_analytical = any(ind in t_clean for ind in cls.ANALYTICAL_INDICATORS)
        
        # 1. Identity & Capabilities (Checked first so 'sen kimsan', 'кто ты' aren't blocked)
        if any(i in t_clean for i in cls.IDENTITY_UZ) and not any(ind in t_clean for ind in ["202", "bitim", "tovar", "mahsulot", "narx", "aylanma", "сделок", "сделка", "товар"]):
            return (True, "identity", "uz")
        if any(i in t_clean for i in cls.IDENTITY_UZ_CYR) and not any(ind in t_clean for ind in ["202", "битим", "товар", "маҳсулот", "нарх", "айланма"]):
            return (True, "identity", "uz_cyr")
        if any(i in t_clean for i in cls.IDENTITY_RU) and not any(ind in t_clean for ind in ["202", "сделок", "сделка", "товар", "цена", "оборот"]):
            return (True, "identity", "ru")

        # 2. Farewells (Checked before Greetings so 'salomat bo'ling' isn't mistaken for 'salom')
        if any(f in t_clean for f in cls.FAREWELL_UZ) and not has_analytical:
            return (True, "farewell", "uz")
        if any(f in t_clean for f in cls.FAREWELL_UZ_CYR) and not has_analytical:
            return (True, "farewell", "uz_cyr")
        if any(f in t_clean for f in cls.FAREWELL_RU) and not has_analytical:
            return (True, "farewell", "ru")

        # 3. Thanks
        if any(g in t_clean for g in cls.THANKS_UZ) and not has_analytical:
            return (True, "thanks", "uz")
        if any(g in t_clean for g in cls.THANKS_UZ_CYR) and not has_analytical:
            return (True, "thanks", "uz_cyr")
        if any(g in t_clean for g in cls.THANKS_RU) and not has_analytical:
            return (True, "thanks", "ru")

        # 4. Greetings
        if any(g in t_clean for g in cls.GREETINGS_UZ) and not has_analytical:
            return (True, "greeting", "uz")
        if any(g in t_clean for g in cls.GREETINGS_UZ_CYR) and not has_analytical:
            return (True, "greeting", "uz_cyr")
        if any(g in t_clean for g in cls.GREETINGS_RU) and not has_analytical:
            return (True, "greeting", "ru")

        # 5. Casual
        if t_clean in cls.CASUAL_UZ:
            return (True, "casual", "uz")
        if t_clean in cls.CASUAL_UZ_CYR:
            return (True, "casual", "uz_cyr")
        if t_clean in cls.CASUAL_RU:
            return (True, "casual", "ru")

        return (False, None, None)

    @classmethod
    def generate_response(cls, category: str, lang: str) -> str:
        """
        Generates varied, natural human responses for conversational interactions.
        """
        if category == "greeting":
            if lang == "uz":
                return (
                    "Va alaykum assalom! Yaxshi, rahmat. Sizga qanday yordam bera olaman?\n\n"
                    "Men O'zbekiston Respublika tovar-xomashyo birjasi (UZEX) bo'yicha mustaqil ma'lumotlar tahlilchisiman. "
                    "2022–2026 yillardagi 500 000 ta birja bitimi, tovar narxlari, yetakchi sotuvchi va xaridor kompaniyalar "
                    "hamda brokerlik idoralari bo'yicha barcha savollaringizga aniq ma'lumot berishga tayyorman."
                )
            elif lang == "uz_cyr":
                return (
                    "Ва алайкум ассалом! Яхши, раҳмат. Сизга қандай ёрдам бера оламан?\n\n"
                    "Мен Ўзбекистон Республика товар-хомашё биржаси (UZEX) бўйича маълумотлар таҳлилчисиман. "
                    "2022–2026 йиллардаги 500 000 та битим, товарлар, сотувчи ва харидорлар ҳамда брокерлар бўйича "
                    "саволларингиз бўлса, бемалол сўранг."
                )
            else:
                return (
                    "Здравствуйте! Все отлично, спасибо. Чем могу вам помочь?\n\n"
                    "Я — интеллектуальный аналитик данных Узбекской республиканской товарно-сырьевой биржи (UZEX). "
                    "Анализирую реестр из 500 000 биржевых сделок (2022–2026 гг.), динамику цен на сырье и товары, "
                    "обороты ведущих поставщиков, покупателей и брокерских контор. Что вас интересует?"
                )

        elif category == "thanks":
            if lang == "uz":
                return "Arzimaydi! Yana biror ma'lumot yoki tahlil kerak bo'lsa, bemalol so'rang, yordam berishga doim tayyorman!"
            elif lang == "uz_cyr":
                return "Арзимайди! Яна бирор маълумот ёки таҳлил керак бўлса, бемалол сўранг, доим ёрдам беришга тайёрман!"
            else:
                return "Пожалуйста! Всегда рад помочь. Обращайтесь, если понадобятся дополнительные данные по бирже или конкретным контрактам!"

        elif category == "farewell":
            if lang == "uz":
                return "Xayr, salomat bo'ling! Birja tahlili yoki bitimlar bo'yicha savollaringiz tug'ilsa, har doim murojaat qilishingiz mumkin. Kuningiz xayrli o'tsin!"
            elif lang == "uz_cyr":
                return "Хайр, саломат бўлинг! Биржа маълумотлари бўйича яна саволларингиз бўлса, ҳар доим мурожаат қилишингиз мумкин. Кунингиз хайрли ўтсин!"
            else:
                return "До свидания! Всего доброго и успешных торгов! Обращайтесь в любое время, если потребуется аналитика по биржевым сделкам."

        elif category == "identity":
            if lang == "uz":
                return (
                    "Men **UZEX AI** — O'zbekiston Respublika tovar-xomashyo birjasining rasmiy ma'lumotlar tahlilchisiman.\n\n"
                    "**Mening imkoniyatlarim:**\n"
                    "- 📊 2022–2026 yillardagi **500 000 ta birja bitimini** to'liq tahlil qilish\n"
                    "- 🌾 Qishloq xo'jaligi, metall, sement, neft mahsulotlari va boshqa tovarlar narxlari va hajmlari dinamikasini chiqarish\n"
                    "- 🏭 14 000 dan ortiq sotuvchi va xaridor kompaniyalar (klasterlar, zavodlar) faoliyatini tahlil qilish\n"
                    "- 🤝 120 ta brokerlik idorasi aylanmasi va reytinglarini hisoblash\n"
                    "- 💵 Eksport (AQSh dollari) va ichki bozor (so'm) bitimlarini valyuta kurslari bo'yicha taqqoslash\n\n"
                    "Birja bo'yicha qanday ma'lumot olmoqchisiz?"
                )
            elif lang == "uz_cyr":
                return (
                    "Мен **UZEX AI** — Ўзбекистон Республика товар-хомашё биржасининг маълумотлар таҳлилчисиман.\n\n"
                    "**Менинг имкониятларим:**\n"
                    "- 📊 2022–2026 йиллардаги **500 000 та битимни** тўлиқ таҳлил қилиш\n"
                    "- 🌾 Товарлар (пахта, буғдой, цемент, металл, бензин) нархлари ва ҳажмларини кўрсатиш\n"
                    "- 🏭 Корхоналар савдо кўрсаткичлари ва брокерлар рейтингини аниқлаш\n\n"
                    "Қандай саволингиз бор?"
                )
            else:
                return (
                    "Я — **UZEX AI**, интеллектуальный аналитик данных Узбекской республиканской товарно-сырьевой биржи.\n\n"
                    "**Мои возможности:**\n"
                    "- 📊 Точный расчет показателей по **500 000 биржевым сделкам** за 2022–2026 годы\n"
                    "- 🌾 Анализ объемов и цен ключевых биржевых товаров (хлопок, пшеница, цемент, медь, бензин, сахар и др.)\n"
                    "- 🏭 Рейтинги и торговые показатели 14 000+ участников торгов (продавцов и покупателей)\n"
                    "- 🤝 Аналитика оборотов 120 аккредитованных брокерских контор\n"
                    "- 💵 Сравнение экспорта в долларах США и внутреннего рынка в сумах по официальным курсам ЦБ\n\n"
                    "Какой вопрос по биржевым торгам вас интересует?"
                )

        else: # casual
            if lang == "uz":
                return "Tushundim. Birja bo'yicha biror tahlil yoki ma'lumot kerak bo'lsa, savolingizni berishingiz mumkin."
            elif lang == "uz_cyr":
                return "Тушундим. Биржа бўйича бирор таҳлил керак бўлса, саволингизни беришингиз мумкин."
            else:
                return "Понял вас. Если потребуется расчет или аналитика по биржевым сделкам — задавайте вопрос!"
