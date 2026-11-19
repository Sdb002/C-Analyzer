import pytest

from complexity import big_o_from_depth, estimate_big_o, max_loop_depth
from helpers import parse


@pytest.mark.parametrize("body, expected", [
    ("x = 1;", "O(1)"),
    ("for (int i = 0; i < n; i++) s = s + i;", "O(n)"),
    ("while (n > 0) n = n - 1;", "O(n)"),
    ("for (int i = 0; i < n; i++) for (int j = 0; j < n; j++) s = s + 1;", "O(n^2)"),
    ("for (int i = 0; i < n; i++) { while (j < n) { for (k = 0; k < n; k++) s++; } }", "O(n^3)"),
])
def test_big_o_by_loop_nesting(body, expected):
    assert estimate_big_o(parse(f"int f() {{ {body} }}")) == expected


def test_sequential_loops_do_not_add_up():
    src = "int f() { for (i = 0; i < n; i++) a++; for (j = 0; j < n; j++) b++; }"
    assert max_loop_depth(parse(src)) == 1


def test_empty_tree():
    assert max_loop_depth(None) == 0
    assert big_o_from_depth(0) == "O(1)"
