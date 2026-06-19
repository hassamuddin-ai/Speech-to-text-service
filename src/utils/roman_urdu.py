"""
src/utils/roman_urdu.py
====================================================
Urdu → Roman Urdu transliterator.

Rules:
- Latin/English words are kept as-is
- Urdu script words are converted to Roman Urdu
- Numbers and punctuation are preserved

Usage:
    from src.utils.roman_urdu import to_roman_urdu
    result = to_roman_urdu("مجھے glossary چاہیے patriotism کی")
    # → "mujhe glossary chahiye patriotism ki"
"""

import re

# ── Character-level mapping: Urdu → Roman Urdu ───────────────────────────────
# Each entry: (urdu_char_or_sequence, roman_equivalent)
# Order matters — longer sequences first

CHAR_MAP = [
    # ── Special combinations (must come before single chars) ──
    ("آ",  "aa"),
    ("اے", "ay"),
    ("او", "oo"),
    ("ائ", "ai"),
    ("اِ", "i"),
    ("اُ", "u"),
    ("خو", "kho"),
    ("غو", "gho"),
    ("شو", "sho"),

    # ── Hamza / Ain forms ──
    ("ء",  ""),
    ("ؤ",  "w"),
    ("ئ",  "y"),
    ("ع",  ""),      # ayn — silent in Roman Urdu

    # ── Alef forms ──
    ("ا",  "a"),
    ("أ",  "a"),
    ("إ",  "i"),

    # ── Ba group ──
    ("ب",  "b"),
    ("پ",  "p"),

    # ── Ta group ──
    ("ت",  "t"),
    ("ٹ",  "t"),
    ("ث",  "s"),

    # ── Jeem group ──
    ("ج",  "j"),
    ("چ",  "ch"),

    # ── Haa group ──
    ("ح",  "h"),
    ("خ",  "kh"),

    # ── Dal group ──
    ("د",  "d"),
    ("ڈ",  "d"),
    ("ذ",  "z"),

    # ── Ra group ──
    ("ر",  "r"),
    ("ڑ",  "r"),
    ("ز",  "z"),
    ("ژ",  "zh"),

    # ── Seen group ──
    ("س",  "s"),
    ("ش",  "sh"),

    # ── Suad group ──
    ("ص",  "s"),
    ("ض",  "z"),

    # ── Toa group ──
    ("ط",  "t"),
    ("ظ",  "z"),

    # ── Ghain group ──
    ("غ",  "gh"),

    # ── Fa group ──
    ("ف",  "f"),
    ("ق",  "q"),

    # ── Kaf group ──
    ("ک",  "k"),
    ("گ",  "g"),

    # ── Lam group ──
    ("ل",  "l"),

    # ── Meem group ──
    ("م",  "m"),

    # ── Noon group ──
    ("ن",  "n"),
    ("ں",  "n"),
    ("ڻ",  "n"),

    # ── Wao group ──
    ("و",  "w"),

    # ── Heh group ──
    ("ہ",  "h"),
    ("ھ",  "h"),
    ("ه",  "h"),
    ("ح",  "h"),

    # ── Ya group ──
    ("ی",  "i"),
    ("ے",  "e"),
    ("ى",  "i"),

    # ── Diacritics (zabar/zer/pesh) ──
    ("َ",  "a"),   # zabar
    ("ِ",  "i"),   # zer
    ("ُ",  "u"),   # pesh
    ("ّ",  ""),    # tashdid — double consonant (skip, handled by context)
    ("ً",  "an"),  # tanwin zabar
    ("ٍ",  "in"),  # tanwin zer
    ("ٌ",  "un"),  # tanwin pesh
    ("ْ",  ""),    # sukun — no vowel
    ("ٰ",  "a"),   # khari zabar

    # ── Misc ──
    ("۔",  "."),   # Urdu full stop
    ("،",  ","),   # Urdu comma
    ("؟",  "?"),   # Urdu question mark
    ("!",  "!"),
]

# Pre-process: longest sequences first to avoid partial matches
_SORTED_MAP = sorted(CHAR_MAP, key=lambda x: len(x[0]), reverse=True)

# Common whole-word Urdu → Roman Urdu overrides (more natural than char-by-char)
WORD_MAP = {
    "میں":    "mein",
    "مجھے":  "mujhe",
    "مجھ":   "mujh",
    "میرا":  "mera",
    "میری":  "meri",
    "میرے":  "mere",
    "ہے":    "hai",
    "ہیں":   "hain",
    "ہو":    "ho",
    "ہوں":   "hoon",
    "ہوگا":  "hoga",
    "ہوگی":  "hogi",
    "تھا":   "tha",
    "تھی":   "thi",
    "تھے":   "the",
    "کا":    "ka",
    "کی":    "ki",
    "کے":    "ke",
    "کو":    "ko",
    "کر":    "kar",
    "کرو":   "karo",
    "کریں":  "karein",
    "کرنا":  "karna",
    "کرتا":  "karta",
    "کرتی":  "karti",
    "کیا":   "kya",
    "کیجیے": "kijiye",
    "نہیں":  "nahi",
    "نہ":    "na",
    "نے":    "ne",
    "اور":   "aur",
    "یا":    "ya",
    "اگر":   "agar",
    "تو":    "to",
    "لیکن":  "lekin",
    "مگر":   "magar",
    "بھی":   "bhi",
    "سے":    "se",
    "پر":    "par",
    "میں":   "mein",
    "آپ":    "aap",
    "تم":    "tum",
    "وہ":    "woh",
    "یہ":    "yeh",
    "اس":    "is",
    "اُس":   "us",
    "ان":    "un",
    "جو":    "jo",
    "جب":    "jab",
    "کب":    "kab",
    "کیسے":  "kaise",
    "کہاں":  "kahan",
    "کیوں":  "kyun",
    "کون":   "kaun",
    "کیا":   "kya",
    "دو":    "do",
    "دیں":   "dein",
    "دے":    "de",
    "لو":    "lo",
    "لیں":   "lein",
    "آ":     "aa",
    "جا":    "ja",
    "جاؤ":   "jao",
    "جائیں": "jaein",
    "بتاؤ":  "batao",
    "بتائیں":"batain",
    "بتاؤ":  "batao",
    "چاہیے": "chahiye",
    "چاہتا": "chahta",
    "چاہتی": "chahti",
    "چاہیں": "chahein",
    "ہاں":   "haan",
    "نہاں":  "nahan",
    "ٹھیک":  "theek",
    "اچھا":  "acha",
    "اچھی":  "achi",
    "بہت":   "bahut",
    "تھوڑا": "thora",
    "زیادہ": "zyada",
    "کم":    "kam",
    "پہلا":  "pehla",
    "پہلی":  "pehli",
    "دوسرا": "doosra",
    "دوسری": "doosri",
    "تیسرا": "teesra",
    "چوتھا": "chautha",
    "پانچواں":"paanchwan",
    "والا":  "wala",
    "والی":  "wali",
    "والے":  "wale",
    "ابھی":  "abhi",
    "پھر":   "phir",
    "صرف":   "sirf",
    "سب":    "sab",
    "کچھ":   "kuch",
    "سارا":  "sara",
    "ساری":  "sari",
    "ساتھ":  "saath",
    "لیے":   "liye",
    "وقت":   "waqt",
    "بعد":   "baad",
    "پہلے":  "pehle",
    "اب":    "ab",
    "یہاں":  "yahan",
    "وہاں":  "wahan",
    # Curriculum-specific
    "گلوسری":   "glossary",
    "پیراگراف": "paragraph",
    "سمری":     "summary",
    "یونٹ":     "unit",
    "چیپٹر":    "chapter",
    "سوال":     "sawal",
    "جواب":     "jawab",
    "کتاب":     "kitaab",
    "سبق":      "sabaq",
    "نظم":      "nazm",
    "کہانی":    "kahani",
    "خط":       "khat",
    "مضمون":    "mazmoon",
    # ── English loanwords (Urdu-pronounced → correct English spelling) ──
    # Technology
    "اپلیکیشن":  "application",
    "اپلیکیشنز": "applications",
    "ایپ":       "app",
    "ایپس":      "apps",
    "موبائل":    "mobile",
    "فون":       "phone",
    "کمپیوٹر":   "computer",
    "لیپ ٹاپ":  "laptop",
    "لیپ‌ٹاپ":  "laptop",
    "انٹرنیٹ":   "internet",
    "وائی فائی": "WiFi",
    "وائی‌فائی": "WiFi",
    "ویب سائٹ":  "website",
    "ویب‌سائٹ":  "website",
    "سافٹ ویئر": "software",
    "سافٹ‌ویئر": "software",
    "ہارڈ ویئر": "hardware",
    "ہارڈ‌ویئر": "hardware",
    "ڈاؤن لوڈ":  "download",
    "ڈاؤن‌لوڈ":  "download",
    "اپ لوڈ":    "upload",
    "اپ‌لوڈ":    "upload",
    "پاس ورڈ":   "password",
    "پاس‌ورڈ":   "password",
    "اسکرین":    "screen",
    "کی بورڈ":   "keyboard",
    "کی‌بورڈ":   "keyboard",
    "ماؤس":      "mouse",
    "پرنٹر":     "printer",
    "سکینر":     "scanner",
    "سرور":      "server",
    "ڈیٹا":      "data",
    "ڈیٹابیس":   "database",
    "کوڈ":       "code",
    "پروگرام":   "program",
    "پروگرامنگ": "programming",
    "فائل":      "file",
    "فولڈر":     "folder",
    "سسٹم":      "system",
    "نیٹ ورک":   "network",
    "نیٹ‌ورک":   "network",
    "بٹن":       "button",
    "مینو":      "menu",
    "لنک":       "link",
    "ای میل":    "email",
    "ای‌میل":    "email",
    "میسج":      "message",
    "چیٹ":       "chat",
    "ویڈیو":     "video",
    "آڈیو":      "audio",
    "مائیک":     "mic",
    "مائیکروفون": "microphone",
    "کیمرہ":     "camera",
    "اسپیکر":    "speaker",
    # AI / ML
    "اے آئی":       "AI",
    "اے۔آئی":       "AI",
    "اے":           "A",
    "آئی":          "I",
    "آرٹیفیشل":     "artificial",
    "آرٹیفیشل انٹیلیجنس": "artificial intelligence",
    "انٹیلیجنس":    "intelligence",
    "جنریٹیو":      "generative",
    "جنریٹیف":      "generative",
    "جنریٹو":       "generative",
    "مشین لرننگ":   "machine learning",
    "مشین":         "machine",
    "لرننگ":        "learning",
    "ڈیپ لرننگ":    "deep learning",
    "ڈیپ":          "deep",
    "نیورل":        "neural",
    "نیورل نیٹ ورک": "neural network",
    "ماڈل":         "model",
    "ماڈلز":        "models",
    "الگورتھم":     "algorithm",
    "الگورتھمز":    "algorithms",
    "ٹریننگ":       "training",
    "ٹیسٹنگ":       "testing",
    "ڈیٹا سائنس":   "data science",
    "چیٹ جی پی ٹی": "ChatGPT",
    "جی پی ٹی":     "GPT",
    "ملٹیپلیکیشن":    "multiplication",
    "ایل ایل ایم":  "LLM",
    "کلاؤڈ":        "Claude",
    "اوپن اے آئی":  "OpenAI",
    "پرامپٹ":       "prompt",
    "پرامپٹس":      "prompts",
    "ٹوکن":         "token",
    "ٹوکنز":        "tokens",
    "انفرنس":       "inference",
    "فائن ٹیوننگ":  "fine-tuning",
    "فائن‌ٹیوننگ":  "fine-tuning",
    "امبیڈنگ":      "embedding",
    "امبیڈنگز":     "embeddings",
    "ویکٹر":        "vector",
    "ویکٹرز":       "vectors",
    # Internship / career
    "انٹرنشپ":      "internship",
    "انٹرنشپس":     "internships",
    "انٹرن":        "intern",
    "فری لانس":     "freelance",
    "فری لانسر":    "freelancer",
    "ریموٹ":        "remote",
    "ہائبرڈ":       "hybrid",
    "آن سائٹ":      "onsite",
    # Education
    "ٹیچر":      "teacher",
    "اسٹوڈنٹ":   "student",
    "اسٹوڈنٹس":  "students",
    "کلاس":      "class",
    "اسکول":     "school",
    "کالج":      "college",
    "یونیورسٹی": "university",
    "ٹیسٹ":      "test",
    "ایگزام":    "exam",
    "پروجیکٹ":   "project",
    "اسائنمنٹ":  "assignment",
    "پریزنٹیشن": "presentation",
    "نوٹس":      "notes",
    "سلیبس":     "syllabus",
    "سبجیکٹ":    "subject",
    "ٹاپک":      "topic",
    "لیکچر":     "lecture",
    # General common loanwords
    "آفس":       "office",
    "میٹنگ":     "meeting",
    "ٹیم":       "team",
    "مینیجر":    "manager",
    "پروجیکٹ":   "project",
    "ریپورٹ":    "report",
    "پریشر":     "pressure",
    "ٹائم":      "time",
    "ڈیڈ لائن":  "deadline",
    "ڈیڈ‌لائن":  "deadline",
    "شیڈول":     "schedule",
    "پلان":      "plan",
    "آئیڈیا":    "idea",
    "پرابلم":    "problem",
    "سولوشن":    "solution",
    "سروس":      "service",
    "سروسز":     "services",
    "ٹریننگ":    "training",
    "انٹرویو":   "interview",
    "جاب":       "job",
    "کمپنی":     "company",
    # ── Mathematics — operators ──────────────────────────────────────────
    "جمع":           "+",
    "جمع کریں":      "+",
    "تفریق":         "-",
    "منہا":          "-",
    "ضرب":           "×",
    "ضرب دیں":       "×",
    "تقسیم":         "÷",
    "تقسیم کریں":    "÷",
    "مساوی":         "=",
    "مساوی ہے":      "=",
    "برابر":         "=",
    "برابر ہے":      "=",
    "برابر نہیں":    "≠",
    "سے بڑا":        ">",
    "سے چھوٹا":      "<",
    "سے بڑا یا برابر": "≥",
    "سے چھوٹا یا برابر": "≤",
    "فیصد":          "%",
    "اسکوائر روٹ":   "√",
    "مربع جذر":      "√",
    "جذر":           "√",
    "پائی":          "π",
    "انفینٹی":       "∞",
    "لامتناہی":      "∞",
    # ── Mathematics — terms ─────────────────────────────────────────────
    "الجبرا":        "algebra",
    "جیومیٹری":      "geometry",
    "ٹریگنومیٹری":   "trigonometry",
    "کیلکولس":       "calculus",
    "اریتھمیٹک":     "arithmetic",
    "مثلث":          "triangle",
    "مربع":          "square",
    "مستطیل":        "rectangle",
    "دائرہ":         "circle",
    "قطر":           "diameter",
    "نصف قطر":       "radius",
    "محیط":          "perimeter",
    "رقبہ":          "area",
    "حجم":           "volume",
    "زاویہ":         "angle",
    "زاویے":         "angles",
    "قوت":           "power",
    "مربع قوت":      "squared",
    "مکعب":          "cube",
    "لوگارتھم":      "logarithm",
    "لاگ":           "log",
    "سائن":          "sin",
    "کوسائن":        "cos",
    "ٹینجنٹ":        "tan",
    "میٹرکس":        "matrix",
    "ویکٹر":         "vector",
    "انٹیگرل":       "integral",
    "ڈیریویٹو":      "derivative",
    "مشتق":          "derivative",
    "فنکشن":         "function",
    "مساوات":        "equation",
    "مساواتیں":      "equations",
    "اخراج":         "exponent",
    "متغیر":         "variable",
    "متغیرات":       "variables",
    "مستقل":         "constant",
    "گراف":          "graph",
    "محور":          "axis",
    "نقطہ":          "point",
    "لکیر":          "line",
    "ڈھلان":         "slope",
    "درمیانہ":       "mean",
    "وسطی":          "median",
    "طریقہ":         "mode",
    "معیاری انحراف": "standard deviation",
    "امکان":         "probability",
    "شماریات":       "statistics",
    # ── Numbers (Urdu names) ─────────────────────────────────────────────
    "صفر":   "0",
    "ایک":   "1",
    "دو":    "2",
    "تین":   "3",
    "چار":   "4",
    "پانچ":  "5",
    "چھ":    "6",
    "سات":   "7",
    "آٹھ":   "8",
    "نو":    "9",
    "دس":    "10",
    "گیارہ": "11",
    "بارہ":  "12",
    "تیرہ":  "13",
    "چودہ":  "14",
    "پندرہ": "15",
    "سولہ":  "16",
    "سترہ":  "17",
    "اٹھارہ":"18",
    "انیس":  "19",
    "بیس":   "20",
    "تیس":   "30",
    "چالیس": "40",
    "پچاس":  "50",
    "ساٹھ":  "60",
    "ستر":   "70",
    "اسی":   "80",
    "نوے":   "90",
    "سو":    "100",
    "ہزار":  "1000",
}


def _is_latin(word: str) -> bool:
    """Check if a word is already in Latin/English script."""
    return bool(re.match(r'^[a-zA-Z0-9\'\-\.]+$', word))


def _urdu_word_to_roman(word: str) -> str:
    """Convert a single Urdu word to Roman Urdu using char map."""
    # Check word-level override first
    if word in WORD_MAP:
        return WORD_MAP[word]

    # Character-by-character conversion
    result = ""
    i = 0
    while i < len(word):
        matched = False
        for urdu_seq, roman in _SORTED_MAP:
            if word[i:i+len(urdu_seq)] == urdu_seq:
                result += roman
                i += len(urdu_seq)
                matched = True
                break
        if not matched:
            # Keep unknown characters (numbers, punctuation, etc.)
            result += word[i]
            i += 1

    # Clean up: remove double letters from tashdid, collapse spaces
    result = re.sub(r'([a-z])\1{2,}', r'\1\1', result)  # max double
    result = result.strip()
    return result if result else word


# Words that are native Urdu — present in WORD_MAP for romanization
# but should NOT trigger English detection
_NATIVE_URDU = {
    "سوال", "جواب", "کتاب", "سبق", "نظم", "کہانی", "خط", "مضمون",
    "میں", "مجھے", "مجھ", "میرا", "میری", "میرے", "ہے", "ہیں", "ہو",
    "ہوں", "ہوگا", "ہوگی", "تھا", "تھی", "تھے", "کا", "کی", "کے",
    "کو", "کر", "کرو", "کریں", "کرنا", "کرتا", "کرتی", "کیا", "کیجیے",
    "نہیں", "نہ", "نے", "اور", "یا", "اگر", "تو", "لیکن", "مگر",
    "بھی", "سے", "پر", "آپ", "تم", "وہ", "یہ", "اس", "اُس", "ان",
    "جو", "جب", "کب", "کیسے", "کہاں", "کیوں", "کون", "دو", "دیں",
    "دے", "لو", "لیں", "آ", "جا", "جاؤ", "جائیں", "بتاؤ", "بتائیں",
    "چاہیے", "چاہتا", "چاہتی", "چاہیں", "ہاں", "ٹھیک", "اچھا", "اچھی",
    "بہت", "تھوڑا", "زیادہ", "کم", "پہلا", "پہلی", "دوسرا", "دوسری",
    "تیسرا", "چوتھا", "پانچواں", "والا", "والی", "والے", "ابھی", "پھر",
    "صرف", "سب", "کچھ", "سارا", "ساری", "ساتھ", "لیے", "وقت", "بعد",
    "پہلے", "اب", "یہاں", "وہاں",
}


# Urdu-script tokens that always signal an English word is present,
# checked as bigrams (two consecutive tokens) or single tokens.
_ENGLISH_BIGRAMS = {
    ("اے", "آئی"),              # A I → AI
    ("مشین", "لرننگ"),          # machine learning
    ("ڈیپ", "لرننگ"),           # deep learning
    ("نیورل", "نیٹ"),           # neural net
    ("ڈیٹا", "سائنس"),          # data science
    ("آرٹیفیشل", "انٹیلیجنس"),  # artificial intelligence
    ("فائن", "ٹیوننگ"),         # fine tuning
    ("چیٹ", "جی"),              # ChatGPT
    ("اوپن", "اے"),             # OpenAI
   
}

# Single-token Urdu-script words that unambiguously represent English terms
_ENGLISH_SINGLE_TRIGGERS = {
    "جنریٹیو", "جنریٹیف", "جنریٹو",
    "انٹرنشپ", "انٹرنشپس", "انٹرن",
    "آرٹیفیشل", "انٹیلیجنس",
    "مشین", "الگورتھم", "الگورتھمز",
    "پرامپٹ", "پرامپٹس", "انفرنس",
    "امبیڈنگ", "امبیڈنگز",
    "اپلیکیشن", "اپلیکیشنز",
    "موبائل", "کمپیوٹر", "انٹرنیٹ",
    "سافٹ ویئر", "ہارڈ ویئر",
    "ڈاؤن لوڈ", "اپ لوڈ",
    "پاس ورڈ", "کی بورڈ",
    "ٹیچر", "اسٹوڈنٹ", "اسٹوڈنٹس",
    "پروجیکٹ", "اسائنمنٹ", "پریزنٹیشن",
    "سلیبس", "سبجیکٹ", "لیکچر",
    "میٹنگ", "مینیجر", "ریپورٹ",
    "شیڈول", "ڈیڈ لائن", "ٹریننگ",
    "انٹرویو", "کمپنی", "سروس",
   
}


def has_english_words(text: str) -> bool:
    """
    Returns True if the text contains at least one Latin/English word
    OR one known English loanword (in Urdu script).
    """
    tokens = re.split(r'\s+', text.strip())

    for i, token in enumerate(tokens):
        # Already in Latin script
        if _is_latin(token) and len(token) > 1:
            return True
        # Single-token English loanword
        if token in _ENGLISH_SINGLE_TRIGGERS:
            return True
        # Bigram check
        if i + 1 < len(tokens):
            if (token, tokens[i + 1]) in _ENGLISH_BIGRAMS:
                return True
        # WORD_MAP loanword — exclude native Urdu Roman mappings
        if token in WORD_MAP and token not in _NATIVE_URDU:
            mapped = WORD_MAP[token]
            if re.match(r'^[a-zA-Z]', mapped) and mapped not in {
                "ka", "ki", "ke", "ko", "kar", "karo", "karein", "karna",
                "karta", "karti", "kya", "kijiye", "nahi", "na", "ne",
                "aur", "ya", "agar", "to", "lekin", "magar", "bhi", "se",
                "par", "mein", "aap", "tum", "woh", "yeh", "is", "us",
                "un", "jo", "jab", "kab", "kaise", "kahan", "kyun", "kaun",
                "do", "dein", "de", "lo", "lein", "aa", "ja", "jao",
                "jaein", "batao", "batain", "chahiye", "chahta", "chahti",
                "chahein", "haan", "theek", "acha", "achi", "bahut",
                "thora", "zyada", "kam", "pehla", "pehli", "doosra",
                "doosri", "teesra", "chautha", "paanchwan", "wala", "wali",
                "wale", "abhi", "phir", "sirf", "sab", "kuch", "sara",
                "sari", "saath", "liye", "waqt", "baad", "pehle", "ab",
                "yahan", "wahan", "mera", "meri", "mere", "hai", "hain",
                "ho", "hoon", "hoga", "hogi", "tha", "thi", "the",
                "mujhe", "mujh", "sawal", "jawab", "kitaab", "sabaq",
                "nazm", "kahani", "khat", "mazmoon", "A", "I",
            }:
                return True
    return False


def to_roman_urdu(text: str) -> str:
    """
    Convert mixed Urdu/English text to Roman Urdu.
    - If text is pure Urdu (no English words), return original Urdu script unchanged.
    - If text contains English words (in Latin or Urdu script), convert fully to Roman Urdu.

    Examples:
        "یہ کتاب بہت اچھی ہے"           → "یہ کتاب بہت اچھی ہے"  (pure Urdu, unchanged)
        "مجھے glossary چاہیے"            → "mujhe glossary chahiye"
        "آپ اپلیکیشن جمع کروائیں"       → "aap application jama karwaein"
    """
    if not text:
        return text

    # Pure Urdu — keep in Urdu script
    if not has_english_words(text):
        return text

    # Pre-substitution: replace known multi-word Urdu phrases with their mapping
    # before tokenizing, so bigrams like "مربع جذر" → "√" work correctly
    for urdu_phrase, mapped in WORD_MAP.items():
        if " " in urdu_phrase and urdu_phrase in text:
            text = text.replace(urdu_phrase, mapped)

    # Mixed — convert remaining tokens to Roman Urdu
    tokens = re.split(r'(\s+)', text)
    result_tokens = []

    for token in tokens:
        if re.match(r'^\s+$', token):
            result_tokens.append(token)
        elif _is_latin(token):
            result_tokens.append(token)  # Keep English as-is
        elif re.match(r'^[0-9]+$', token):
            result_tokens.append(token)  # Keep numbers
        else:
            result_tokens.append(_urdu_word_to_roman(token))

    result = "".join(result_tokens)
    result = re.sub(r' {2,}', ' ', result).strip()
    # Join spaced single uppercase letters that form acronyms: "A I" → "AI"
    result = re.sub(r'\b([A-Z])(?: ([A-Z]))+\b', lambda m: m.group(0).replace(' ', ''), result)
    return result


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        # Pure Urdu → should stay in Urdu script
        ("یہ کتاب بہت اچھی ہے",              "pure urdu"),
        ("مجھے سمجھ نہیں آئی",               "pure urdu"),
        ("آپ کیسے ہیں",                       "pure urdu"),
        # Mixed → should convert to Roman
        ("مجھے glossary چاہیے patriotism کی", "mixed"),
        ("آپ اپلیکیشن جمع کروائیں",           "mixed (loanword)"),
        ("پہلا paragraph دو",                  "mixed"),
        ("مجھے grammar کے rules چاہیے",        "mixed"),
    ]
    for text, label in tests:
        result = to_roman_urdu(text)
        print(f"[{label}]")
        print(f"  IN:  {text}")
        print(f"  OUT: {result}")
        print()