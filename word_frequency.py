import re


def word_frequency(text: str) -> dict:
    if not isinstance(text, str):
        raise TypeError("Input must be a string")

    words = re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)*", text.lower())
    result = {}
    for word in words:
        result[word] = result.get(word, 0) + 1
    return result
