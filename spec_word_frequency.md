# Specificatie: `word_frequency`

## 1. Doel
Ontwerp een Python-functie `word_frequency(text: str) -> dict` die de frequentie van woorden in een gegeven tekst telt. De telling is case-insensitief en negeert leestekens, met uitzondering van interne apostrofs in woorden (bijv. "don't").

## 2. Functionele Vereisten

### 2.1 Case-insensitief
Alle letters worden geconverteerd naar lowercase voordat telling plaatsvindt. "Hello" en "hello" worden als hetzelfde woord beschouwd.

### 2.2 Leestekens negeren
- Alleen letters (a-z, A-Z), cijfers (0-9) en interne apostrofs (`'`) worden beschouwd als deel van een woord.
- Interne apostrofs: apostrofs die omringd zijn door letters/cijfers aan beide zijden behoren tot het woord (bijv. "don't", "rock'n'roll").
- Apostrofs aan het begin of einde van een token worden genegeerd (bijv. "'hello" → "hello", "world'" → "world").
- Alle andere leestekens (`.`, `,`, `!`, `?`, `;`, `:`, `"`, `` ` ``, `(`, `)`, `[`, `]`, `{`, `}`, `-`, `_`, `@`, `#`, `$`, `%`, `^`, `&`, `*`, `+`, `=`, `|`, `\`, `/`, `<`, `>`, `~`) fungeren als scheidingstekens.

### 2.3 Retourwaarde
- Type: `dict`
- Sleutels: woorden (strings, lowercase)
- Waardes: aantallen voorkomens (integers)
- Volgorde: niet gedefinieerd (dict-volgorde in Python 3.7+ is insertion-order, maar dit is geen contractuele vereiste)

### 2.4 Lege invoer
- Lege string `""` retourneert lege dict `{}`

## 3. API-contract

```python
def word_frequency(text: str) -> dict:
    """
    Tel woordfrequenties in een tekst.

    Args:
        text: Invoertekst (str). Kan leeg zijn.

    Returns:
        dict: {woord: aantal} met woorden in lowercase.
              Lege dict als text leeg is of geen geldige woorden bevat.

    Raises:
        TypeError: Als text geen str is.
    """
```

## 4. Randvoorwaarden en Edge-cases

| # | Case | Verwacht gedrag |
|---|------|-----------------|
| 1 | Lege string `""` | `{}` |
| 2 | Alleen whitespace `"   \n\t  "` | `{}` |
| 3 | Alleen leestekens `"!@#$%^&*()"` | `{}` |
| 4 | Enkel woord `"hello"` | `{"hello": 1}` |
| 5 | Case-variatie `"Hello HELLO hello"` | `{"hello": 3}` |
| 6 | Leestekens als scheiding `"hello, world! how; are: you?"` | `{"hello": 1, "world": 1, "how": 1, "are": 1, "you": 1}` |
| 7 | Interne apostrof `"don't can't it's"` | `{"don't": 1, "can't": 1, "it's": 1}` |
| 8 | Apostrof aan randen `" 'hello world' "` | `{"hello": 1, "world": 1}` |
| 9 | Cijfers in woorden `"abc123 def456"` | `{"abc123": 1, "def456": 1}` |
| 10 | Alleen cijfers `"123 456"` | `{"123": 1, "456": 1}` |
| 11 | Mixed case met cijfers `"Hello123 WORLD456"` | `{"hello123": 1, "world456": 1}` |
| 12 | Meerdere spaties/newlines `"hello\n\n  world\thello"` | `{"hello": 2, "world": 1}` |
| 13 | Unicode letters (bijv. "café", "naïve") | Beslis: behandel als niet-ASCII letters → verwijder of vervang? **Advies: strip naar ASCII-only; documenteer dat alleen [a-z0-9'] worden meegenomen.** |
| 14 | Heel lange tekst | Geen speciale limiet; werkt met willekeurige lengte |

## 5. Testvereisten (pytest, minimaal 4 cases)

De implementatie wordt voorzien van pytest-tests met minimaal de volgende cases:

```python
def test_basic_counting():
    assert word_frequency("hello world hello") == {"hello": 2, "world": 1}

def test_case_insensitive():
    assert word_frequency("Hello HELLO hello") == {"hello": 3}

def test_punctuation_ignored():
    assert word_frequency("hello, world! how; are: you?") == {"hello": 1, "world": 1, "how": 1, "are": 1, "you": 1}

def test_internal_apostrophes():
    assert word_frequency("don't can't it's") == {"don't": 1, "can't": 1, "it's": 1}

def test_apostrophe_at_edges():
    assert word_frequency("'hello world'") == {"hello": 1, "world": 1}

def test_empty_string():
    assert word_frequency("") == {}

def test_only_punctuation():
    assert word_frequency("!@#$%") == {}

def test_numbers_in_words():
    assert word_frequency("abc123 def456") == {"abc123": 1, "def456": 1}

def test_mixed_whitespace():
    assert word_frequency("hello\n\n  world\thello") == {"hello": 2, "world": 1}
```

## 6. Implementatie-aanwijzingen (voor Lead Dev)

- Gebruik `re.findall` met een passend patroon om tokens te extraheren.
- Normaliseer naar lowercase met `.lower()`.
- Voor het patroon: overweeg `r"[a-z0-9]+(?:'[a-z0-9]+)*"` na lowercase-conversie, of een alternatief dat apostrofs filtert.
- Gebruik `dict` en tel met `.get(woord, 0) + 1` of `collections.Counter`.

## 7. Niet-functionele Vereisten

- Pure Python, geen externe dependencies (standaardbibliotheek alleen).
- Werkt op Python 3.8+.
- Deterministisch: zelfde invoer geeft altijd dezelfde output.
- Efficiënt voor teksten tot ~1 MB (tijdscomplexiteit O(n) waar n = aantal tekens).

## 8. Uitgesloten (out of scope)

- Stemming/lemmatization (bijv. "running" → "run")
- Meertalige ondersteuning met Unicode-normalisatie
- Stopwoord-filtering
- Parallelle verwerking
