import pytest

from helpers import tokens
from lexer import Lexer


def kinds(src):
    return [(t.type, t.value) for t in tokens(src)]


def test_keywords_and_identifiers():
    assert kinds("int count") == [("KEYWORD", "int"), ("IDENTIFIER", "count")]
    # a keyword prefix inside an identifier stays an identifier
    assert kinds("integer") == [("IDENTIFIER", "integer")]


@pytest.mark.parametrize("src", ["42", "0x1F", "3.14", "2.", ".5"])
def test_numbers(src):
    assert kinds(src) == [("NUMBER", src)]


def test_multichar_operators_win_over_single():
    assert [v for _, v in kinds("a <<= b >= c && d++")] == ["a", "<<=", "b", ">=", "c", "&&", "d", "++"]


def test_strings_and_chars_with_escapes():
    assert kinds(r'"say \"hi\"\n"') == [("STRING", r'"say \"hi\"\n"')]
    assert kinds(r"'\n'") == [("CHAR", r"'\n'")]


def test_comments_and_preprocessor():
    toks = Lexer().tokenize("#include <stdio.h>\n// note\n/* a\nb */ int x;")
    assert [t.type for t in toks][:3] == ["PREPROCESSOR", "COMMENT", "COMMENT"]


def test_line_and_column_tracking():
    toks = tokens("int a;\n  /* two\nlines */ float b;")
    b = next(t for t in toks if t.value == "b")
    assert (b.line, b.column) == (3, 16)


def test_unknown_characters_are_reported_not_dropped():
    assert ("UNKNOWN", "@") in kinds("int @x;")
