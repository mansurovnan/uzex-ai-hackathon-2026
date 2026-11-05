"""
Human-Like Conversational Intelligence Agent & Strict Scope Router for UZEX AI.
Implements Section E & Section I:
Classifies messages into:
1. 'small_talk' — greetings, thanks, polite conversation, assistant identity.
2. 'in_scope' — analytical questions on products, deals, companies, brokers, prices, volumes, turnover.
3. 'database_out_of_scope' — exchange-related questions requiring data not in DuckDB (crypto, stock dividends, live weather, future predictions).
4. 'unrelated' — completely unrelated questions (sports/football, movies, cooking recipes, poetry, anecdotes).
"""

import re
import random
from typing import Optional, Tuple, Dict, Any

class ConversationalAgent:
    """
    Detects and handles natural human conversational interactions with varied, 
    polite, and professional responses in Uzbek (Latin and Cyrillic) and Russian.
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
    IDENTITY_UZ = [
        "sen kimsan", "siz kimsiz", "kim bu", "kimsan", "kimsiz", "kim siz",
        "nima qila olasan", "nima qila olasiz", "qanday yordam berasan", "qanday yordam bera olasiz",
        "vazifang nima", "vazifangiz nima", "o'zing haqingda"
    ]
    IDENTITY_UZ_CYR = [
        "сен кимсан", "сиз кимсиз", "ким бу", "кимсан", "кимсиз", "ким сиз",
        "нима қила оласан", "нима қила оласиз", "қандай ёрдам берасан", "қандай ёрдам бера оласиз",
        "вазифанг нима", "вазифангиз нима", "ўзинг ҳақингда"
    ]
    IDENTITY_RU = [
        "кто ты", "кто вы", "что ты умеешь", "что вы умеете",
        "чем ты можешь помочь", "чем вы можете помочь", "каковы твои функции", "каковы ваши функции",
        "расскажи о себе", "расскажите о себе", "что это за бот"
    ]

    # 5. Casual affirmative / acknowledgments
    CASUAL_UZ = ["tushunarli", "xo'p", "mayli", "ha", "yaxshi", "ok", "tushundim"]
    CASUAL_UZ_CYR = ["тушунарли", "хўп", "майли", "ҳа", "яхши", "тушундим"]
    CASUAL_RU = ["понятно", "хорошо", "ясно", "ок", "ладно", "понял", "отлично"]

    # 6. Database out-of-scope markers (finance/economic concepts not in commodity exchange DB)
    OUT_OF_SCOPE_MARKERS = [
        "ob-havo", "weather", "pogoda", "погода", "aktsiya dividendi", "акциялар",
        "dividendi", "дивиденд", "kriptovalyuta", "криптовалют", "bitcoin", "биткоин",
        "kursi bugun", "prognoz", "kelajakda", "prognozlash", "прогноз на будущее"
    ]

    # 7. Unrelated markers (totally outside stock exchange analysis)
    UNRELATED_MARKERS = [
        "futbol", "football", "футбол", "messi", "ronaldo", "kino", "film", "фильм",
        "retsept", "рецепт", "ovqat pishirish", "dori", "лекарств", "she'r", "стих",
        "anekdot", "анекдот", "restoran", "kafe", "tarixiy sana", "prezident kim"
    ]

    # Analytical indicators that signify a valid in-scope query
    ANALYTICAL_INDICATORS = [
        "202", "19", "yil", "yili", "bitim", "tovar", "mahsulot", "kompaniya", 
        "broker", "summa", "aylanma", "narx", "narxi", "qancha", "nechta", 
        "sotgan", "olgan", "xarid", "eksport", "ichki", "hajm", "dinamika",
        "reyting", "top", "solishtir", "taqqosla", "bekor", "klaster", "stir", "inn",
        "год", "году", "сделка", "сделок", "товар", "товаров", "компания", "компаний",
        "брокер", "брокеров", "сумма", "оборот", "цена", "цены", "сколько", 
        "продал", "купил", "закуп", "экспорт", "объем", "динамика", "рейтинг", "сравни"
    ]

    @classmethod
    def classify_message(cls, text: str) -> Tuple[str, Optional[str], str]:
        """
        Classifies message into: ('small_talk' | 'database_out_of_scope' | 'unrelated' | 'in_scope', sub_type, lang)
        """
        t = text.lower().strip()
        t_clean = re.sub(r'[!?,.:;]+', ' ', t).strip()
        t_clean = re.sub(r'\s+', ' ', t_clean)

        # Detect language / script
        if any(ch in t for ch in ["ў", "қ", "ғ", "ҳ"]):
            lang = "uz_cyr"
        elif any(ch in t for ch in ["ы", "щ", "э", "ъ", "ь"]) or re.search(r'[а-яА-ЯёЁ]', text):
            lang = "ru"
        else:
            lang = "uz"

        has_analytical = any(ind in t_clean for ind in cls.ANALYTICAL_INDICATORS)

        # 1. Identity & Capabilities (Check first to avoid misrouting "sen kimsan")
        if any(i in t_clean for i in cls.IDENTITY_UZ) and not any(w in t_clean for w in ["bitim", "tovar", "narx", "aylanma"]):
            return ("small_talk", "identity", "uz")
        if any(i in t_clean for i in cls.IDENTITY_UZ_CYR) and not any(w in t_clean for w in ["битим", "товар", "нарх", "айланма"]):
            return ("small_talk", "identity", "uz_cyr")
        if any(i in t_clean for i in cls.IDENTITY_RU) and not any(w in t_clean for w in ["сделок", "товар", "цена", "оборот"]):
            return ("small_talk", "identity", "ru")

        # 2. Farewells
        if any(f in t_clean for f in cls.FAREWELL_UZ) and not has_analytical:
            return ("small_talk", "farewell", "uz")
        if any(f in t_clean for f in cls.FAREWELL_UZ_CYR) and not has_analytical:
            return ("small_talk", "farewell", "uz_cyr")
        if any(f in t_clean for f in cls.FAREWELL_RU) and not has_analytical:
            return ("small_talk", "farewell", "ru")

        # 3. Gratitude
        if any(g in t_clean for g in cls.THANKS_UZ) and not has_analytical:
            return ("small_talk", "thanks", "uz")
        if any(g in t_clean for g in cls.THANKS_UZ_CYR) and not has_analytical:
            return ("small_talk", "thanks", "uz_cyr")
        if any(g in t_clean for g in cls.THANKS_RU) and not has_analytical:
            return ("small_talk", "thanks", "ru")

        # 4. Greetings
        if any(g in t_clean for g in cls.GREETINGS_UZ) and not has_analytical:
            return ("small_talk", "greeting", "uz")
        if any(g in t_clean for g in cls.GREETINGS_UZ_CYR) and not has_analytical:
            return ("small_talk", "greeting", "uz_cyr")
        if any(g in t_clean for g in cls.GREETINGS_RU) and not has_analytical:
            return ("small_talk", "greeting", "ru")

        # 5. Casual
        if t_clean in cls.CASUAL_UZ:
            return ("small_talk", "casual", "uz")
        if t_clean in cls.CASUAL_UZ_CYR:
            return ("small_talk", "casual", "uz_cyr")
        if t_clean in cls.CASUAL_RU:
            return ("small_talk", "casual", "ru")

        # 6. Unrelated check (sports, movies, cooking, etc.)
        if any(u in t_clean for u in cls.UNRELATED_MARKERS) and not has_analytical:
            return ("unrelated", "unrelated_topic", lang)

        # 7. Database out of scope check (crypto, weather, stock dividends, etc.)
        if any(o in t_clean for o in cls.OUT_OF_SCOPE_MARKERS) and not has_analytical:
            return ("database_out_of_scope", "out_of_scope_topic", lang)

        return ("in_scope", None, lang)

    @classmethod
    def is_conversational_only(cls, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        category, sub_type, lang = cls.classify_message(text)
        if category == "small_talk":
            return (True, sub_type, lang)
        return (False, None, None)

    @classmethod
    def generate_response(cls, category: str, lang: str, sub_type: Optional[str] = None) -> str:
        """
        Generates varied, natural human responses for conversational interactions.
        """
        # A. Unrelated topics
        if category == "unrelated":
            if lang in ["uz", "uz_cyr"]:
                return (
                    "Kechirasiz, men O'zbekiston tovar-xomashyo birjasi (UZEX) bitimlari va tovarlar tahliliga "
                    "ixtisoslashgan tahlilchiman. Ushbu savol birja faoliyatiga tegishli emas.\n\n"
                    "Men birja tovarlari (paxta, bug'doy, sement, metall, benzin), shartnomalar, narxlar dinamikasi, "
                    "sotuvchi/xaridor kompaniyalar va brokerlar bo'yicha ma'lumot berishga tayyorman."
                )
            else:
                return (
                    "Извините, я специализируюсь исключительно на аналитике биржевых торгов Узбекской республиканской "
                    "товарно-сырьевой биржи (UZEX). Данная тема не относится к биржевой деятельности.\n\n"
                    "Вы можете задать вопрос по биржевым товарам (хлопок, пшеница, цемент, металл, бензин), "
                    "котировкам, объемам торгов, предприятиям-участникам или брокерам."
                )

        # B. Database out of scope
        if category == "database_out_of_scope":
            if lang in ["uz", "uz_cyr"]:
                return (
                    "ℹ️ **Ma'lumot mavjud emas:**\n"
                    "Ushbu ko'rsatkich yoki mavzu birja faoliyatiga tegishli emas yoki UZEX tovar-xomashyo birjasi "
                    "ma'lumotlar bazasida mavjud emas. Men 2022–2026 yillardagi tovar-xomashyo bitimlari, shartnomalar, "
                    "spot narxlar, sotuvchi va xaridor korxonalar hamda brokerlar faoliyatini tahlil qila olaman."
                )
            else:
                return (
                    "ℹ️ **Информация отсутствует в базе биржи:**\n"
                    "Данный показатель или тема не относится к биржевой деятельности или отсутствует в реестре "
                    "сделок товарно-сырьевой биржи (UZEX). Я предоставляю аналитику по товарным сделкам за 2022–2026 годы, "
                    "спотовым ценам на сырье, объемам поставок, компаниям и брокерам."
                )

        # C. Small-talk greetings
        target = sub_type or category
        if target == "greeting":
            if lang == "uz":
                return "Va alaykum assalom! Yaxshi, rahmat. Sizga birja tahlili bo'yicha qanday yordam bera olaman?"
            elif lang == "uz_cyr":
                return "Ва алайкум ассалом! Яхши, раҳмат. Сизга биржа маълумотлари бўйича қандай ёрдам бера оламан?"
            else:
                return "Здравствуйте! Все отлично, спасибо. Чем могу помочь вам по биржевым торгам UZEX?"

        elif target == "thanks":
            if lang == "uz":
                return "Arzimaydi! Yana biror ma'lumot yoki tahlil kerak bo'lsa, bemalol so'rang, yordam berishga doim tayyorman!"
            elif lang == "uz_cyr":
                return "Арзимайди! Яна бирор маълумот ёки таҳлил керак бўлса, бемалол сўранг, доим ёрдам беришга тайёрман!"
            else:
                return "Пожалуйста! Всегда рад помочь. Обращайтесь, если понадобятся дополнительные данные по бирже или конкретным контрактам!"

        elif target == "farewell":
            if lang == "uz":
                return "Xayr, salomat bo'ling! Birja tahlili yoki bitimlar bo'yicha savollaringiz tug'ilsa, har doim murojaat qilishingiz mumkin. Kuningiz xayrli o'tsin!"
            elif lang == "uz_cyr":
                return "Хайр, саломат бўлинг! Биржа маълумотлари бўйича яна саволларингиз бўлса, ҳар доим мурожаат қилишингиз мумкин. Кунингиз хайрли ўтсин!"
            else:
                return "До свидания! Всего доброго и успешных торгов! Обращайтесь в любое время, если потребуется аналитика по биржевым сделкам."

        elif target == "identity":
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
