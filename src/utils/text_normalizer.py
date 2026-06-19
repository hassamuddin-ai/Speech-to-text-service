"""
src/utils/text_normalizer.py
Post-processes Whisper output to restore mathematical, code, and symbolic notation.
Converts spoken forms → symbolic forms: "x equals 2 plus 1" → "x = 2 + 1"
"""
import re


# ── Operator & symbol maps ─────────────────────────────────────────────────────

MATH_OPERATORS = [
    # Comparison (order matters — longer phrases first)
    (r"\bis greater than or equal to\b",    ">="),
    (r"\bis less than or equal to\b",       "<="),
    (r"\bis not equal to\b",                "!="),
    (r"\bdoes not equal\b",                 "!="),
    (r"\bis greater than\b",                ">"),
    (r"\bis less than\b",                   "<"),
    (r"\bgreater than or equal to\b",       ">="),
    (r"\bless than or equal to\b",          "<="),
    (r"\bgreater than\b",                   ">"),
    (r"\bless than\b",                      "<"),
    (r"\bnot equal to\b",                   "!="),
    (r"\bequals\b",                         "="),
    (r"\bis equal to\b",                    "="),
    (r"\bequal to\b",                       "="),

    # Arithmetic
    (r"\bplus\b",                           "+"),
    (r"\bminus\b",                          "-"),
    (r"\btimes\b",                          "*"),
    (r"\bmultiplied by\b",                  "*"),
    (r"\bdivided by\b",                     "/"),
    (r"\bover\b",                           "/"),
    (r"\bmod\b",                            "%"),
    (r"\bmodulo\b",                         "%"),
    (r"\bto the power of\b",               "^"),
    (r"\bto the power\b",                   "^"),
    (r"\bsquared\b",                        "^ 2"),
    (r"\bx square\b",                       "x ^ 2"),
    (r"\bsquare\b",                         "^ 2"),
    (r"\bcubed\b",                          "^ 3"),
    (r"\bx cube\b",                       "x ^ 3"),
    (r"\bcube\b",                         "^ 3"),
    (r"\bsquare root of\b",                 "sqrt("),
    (r"\bsquare root\b",                    "sqrt("),

    # Assignment / programming
    (r"\bis assigned\b",                    "="),
    (r"\bassign\b",                         "="),
    (r"\bgets\b",                           "="),
    (r"\bplusplus\b",                       "++"),
    (r"\bplus plus\b",                      "++"),
    (r"\bminusminus\b",                     "--"),
    (r"\bminus minus\b",                    "--"),
    (r"\bplus equals\b",                    "+="),
    (r"\bminus equals\b",                   "-="),
    (r"\btimes equals\b",                   "*="),
    (r"\bdivided equals\b",                 "/="),
]

LOGIC_OPERATORS = [
    (r"\band\b",                            "&&"),
    (r"\bor\b",                             "||"),
    (r"\bnot\b",                            "!"),
    (r"\bbitwise and\b",                    "&"),
    (r"\bbitwise or\b",                     "|"),
    (r"\bbitwise xor\b",                    "^"),
]

BRACKETS = [
    (r"\bopen paren(?:thesis|theses)?\b",   "("),
    (r"\bclose paren(?:thesis|theses)?\b",  ")"),
    (r"\bleft paren\b",                     "("),
    (r"\bright paren\b",                    ")"),
    (r"\bopen bracket\b",                   "["),
    (r"\bclose bracket\b",                  "]"),
    (r"\bopen brace\b",                     "{"),
    (r"\bclose brace\b",                    "}"),
    (r"\bopen curly\b",                     "{"),
    (r"\bclose curly\b",                    "}"),
    (r"\bopen angle\b",                     "<"),
    (r"\bclose angle\b",                    ">"),
]

PUNCTUATION = [
    (r"\bsemicolon\b",                      ";"),
    (r"\bcolon\b",                          ":"),
    (r"\bcomma\b",                          ","),
    (r"\bdot\b",                            "."),
    (r"\bperiod\b",                         "."),
    (r"\bunderscore\b",                     "_"),
    (r"\bhash\b",                           "#"),
    (r"\bat sign\b",                        "@"),
    (r"\bbackslash\b",                      r"\\"),
    (r"\bforward slash\b",                  "/"),
    (r"\bpipe\b",                           "|"),
    (r"\bampersand\b",                      "&"),
    (r"\bpercent\b",                        "%"),
    (r"\bdollar\b",                         "$"),
    (r"\bcaret\b",                          "^"),
    (r"\btilde\b",                          "~"),
    (r"\bbacktick\b",                       "`"),
    (r"\bdouble quote\b",                   '"'),
    (r"\bsingle quote\b",                   "'"),
    (r"\bnewline\b",                        "\n"),
    (r"\btab\b",                            "\t"),
    (r"\bspace\b",                          " "),
    (r"\barrow\b",                          "->"),
    (r"\bdouble arrow\b",                   "=>"),
    (r"\bfat arrow\b",                      "=>"),
]

NUMBER_WORDS = [
    (r"\bzero\b",   "0"), (r"\bone\b",   "1"), (r"\btwo\b",   "2"),
    (r"\bthree\b",  "3"), (r"\bfour\b",  "4"), (r"\bfive\b",  "5"),
    (r"\bsix\b",    "6"), (r"\bseven\b", "7"), (r"\beight\b", "8"),
    (r"\bnine\b",   "9"), (r"\bten\b",  "10"),
]

# Keywords that signal math/code context — trigger full normalization
MATH_TRIGGERS = re.compile(
    r"\b(equals|plus|minus|times|divided|squared|cubed|square|cube|sqrt|power|"
    r"open paren|close paren|semicolon|underscore|backslash|"
    r"assign|gets|modulo|bitwise)\b",
    re.IGNORECASE,
)


# ── Main normalizer ────────────────────────────────────────────────────────────

class TextNormalizer:
    """
    Converts spoken math/code phrasing to symbolic notation.

    Usage:
        normalizer = TextNormalizer(mode="auto")
        clean = normalizer.normalize("x equals two plus one")
        # → "x = 2 + 1"
    """

    def __init__(self, mode: str = "auto"):
        """
        mode:
            "auto"   — only normalize if math/code keywords detected
            "always" — always normalize
            "off"    — passthrough, no normalization
        """
        self._mode = mode

        # Pre-compile all patterns for speed
        self._math_ops   = [(re.compile(p, re.IGNORECASE), r) for p, r in MATH_OPERATORS]
        self._logic_ops  = [(re.compile(p, re.IGNORECASE), r) for p, r in LOGIC_OPERATORS]
        self._brackets   = [(re.compile(p, re.IGNORECASE), r) for p, r in BRACKETS]
        self._punct      = [(re.compile(p, re.IGNORECASE), r) for p, r in PUNCTUATION]
        self._numbers    = [(re.compile(p, re.IGNORECASE), r) for p, r in NUMBER_WORDS]

    def normalize(self, text: str) -> str:
        if self._mode == "off":
            return text
        if self._mode == "auto" and not MATH_TRIGGERS.search(text):
            return text  # No math keywords — skip processing
        return self._apply(text)

    def _apply(self, text: str) -> str:
        # Strip leading punctuation/symbols Whisper sometimes adds
        text = re.sub(r"^[^\w\s]+", "", text).strip()
    

        def sub(pattern, repl, s):
            return pattern.sub(lambda m: repl, s)

        for pattern, replacement in self._brackets:
            text = sub(pattern, replacement, text)
        for pattern, replacement in self._math_ops:
            text = sub(pattern, replacement, text)
        for pattern, replacement in self._logic_ops:
            text = sub(pattern, replacement, text)
        for pattern, replacement in self._punct:
            text = sub(pattern, replacement, text)
        for pattern, replacement in self._numbers:
            text = sub(pattern, replacement, text)

        # Collapse compound operators split by spaces
        text = re.sub(r"\+\s+\+",  "++",  text)
        text = re.sub(r"-\s+-",      "--",  text)
        text = re.sub(r"\+\s+=",    "+=",  text)
        text = re.sub(r"-\s+=",      "-=",  text)
        text = re.sub(r"\*\s+=",    "*=",  text)
        text = re.sub(r"/\s+=",      "/=",  text)
        text = re.sub(r"!\s+=",      "!=",  text)
        text = re.sub(r">\s+=",      ">=",  text)
        text = re.sub(r"<\s+=",      "<=",  text)
        text = re.sub(r"\*\s+\*",  "**",  text)
        # Remove spaces around underscore: my _ function → my_function
        text = re.sub(r"\s*_\s*",   "_",   text)
        # Clean up double spaces
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()


# ── Quick test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    n = TextNormalizer(mode="always")
    tests = [
        "x equals two plus one",
        "if x is greater than or equal to ten",
        "y equals x squared minus three times x plus one",
        "open paren x plus y close paren divided by two",
        "i plus plus",
        "x plus equals five",
        "while x is not equal to zero",
        "def my underscore function open paren a comma b close paren colon",
    ]
    for t in tests:
        print(f"IN : {t}")
        print(f"OUT: {n.normalize(t)}\n")