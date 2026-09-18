import pytest
from word_frequency import word_frequency


def test_basic_counting():
    assert word_frequency("hello world hello") == {"hello": 2, "world": 1}


def test_case_insensitive():
    assert word_frequency("Hello HELLO hello") == {"hello": 3}


def test_punctuation_ignored():
    assert word_frequency("hello, world! how; are: you?") == {
        "hello": 1,
        "world": 1,
        "how": 1,
        "are": 1,
        "you": 1,
    }


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


def test_only_whitespace():
    assert word_frequency("   \n\t  ") == {}


def test_only_numbers():
    assert word_frequency("123 456") == {"123": 1, "456": 1}


def test_mixed_case_with_numbers():
    assert word_frequency("Hello123 WORLD456") == {"hello123": 1, "world456": 1}


def test_type_error_on_non_string_input():
    with pytest.raises(TypeError):
        word_frequency(123)


def test_unicode_letters_stripped():
    assert word_frequency("café naïve") == {"caf": 1, "na": 1, "ve": 1}


def test_multiple_internal_apostrophes():
    assert word_frequency("rock'n'roll") == {"rock'n'roll": 1}


def test_apostrophe_prefix_and_suffix_on_word():
    assert word_frequency("'don't'") == {"don't": 1}
