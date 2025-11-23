import re

def _int_to_uzbek_words(n: int) -> str:
    """Converts an integer to Uzbek words in Latin script."""
    if n == 0:
        return "nol"

    digits = ["", "bir", "ikki", "uch", "to'rt", "besh", "olti", "yetti", "sakkiz", "to'qqiz"]
    tens = ["", "o'n", "yigirma", "o'ttiz", "qirq", "ellik", "oltmish", "yetmish", "sakson", "to'qson"]
    
    parts = []

    if n >= 1000:
        thousand_part = n // 1000
        parts.append(f"{_int_to_uzbek_words(thousand_part)} ming")
        n %= 1000
    
    if n >= 100:
        hundred_part = n // 100
        parts.append(f"{digits[hundred_part]} yuz")
        n %= 100
        
    if n >= 10:
        ten_part = n // 10
        parts.append(tens[ten_part])
        n %= 10
        
    if n > 0:
        parts.append(digits[n])
        
    return " ".join(parts)


def convert_numbers_to_words_in_text(text: str) -> str:
    """
    Finds all numeric values (integers and floats) in a string and converts them
    to their Uzbek Latin word representation using a custom implementation.

    Args:
        text: The input string.

    Returns:
        A new string with numbers converted to Uzbek words (Latin script).
    """
    if not text:
        return ""

    number_pattern = r'\d+\.\d+|\d+'

    def replace_with_words(match):
        number_str = match.group(0)
        try:
            if '.' in number_str:
                parts = number_str.split('.')
                integer_part_word = _int_to_uzbek_words(int(parts[0]))
                decimal_part_word = ' '.join(_int_to_uzbek_words(int(c)) for c in parts[1])
                return f"{integer_part_word} nuqta {decimal_part_word}"
            else:
                return _int_to_uzbek_words(int(number_str))
        except (ValueError, IndexError):
            return number_str

    return re.sub(number_pattern, replace_with_words, text)