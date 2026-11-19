from pathlib import Path

import pytest

from helpers import parse, parse_expr, sexpr, walk

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("expr, tree", [
    ("a + b * c", "(+ a (* b c))"),          # * binds tighter than +
    ("a * b + c", "(+ (* a b) c)"),
    ("a - b - c", "(- (- a b) c)"),          # left-associative
    ("a < b && c == d", "(&& (< a b) (== c d))"),
    ("(a + b) * c", "(* (+ a b) c)"),
    ("-a * b", "(* (- a) b)"),               # unary binds tighter than binary
    ("a & b", "(& a b)"),                    # binary &, not address-of
])
def test_operator_precedence(expr, tree):
    assert sexpr(parse_expr(expr)) == tree


def test_assignment_is_parsed_and_right_associative():
    node = parse_expr("a = b = c + 1")
    assert node.type == "Assign"
    assert sexpr(node) == "(= a (= b (+ c 1)))"


def test_compound_assignment():
    node = parse_expr("total += x * 2")
    assert (node.type, sexpr(node)) == ("Assign", "(+= total (* x 2))")


def test_postfix_increment_does_not_swallow_next_token():
    root = parse("int f() { for (int i = 0; i < n; i++) { s = s + i; } }")
    loop = next(n for n in walk(root) if n.type == "For")
    assert [c.type for c in loop.children] == ["Init", "Condition", "Inc", "Body"]
    inc = loop.children[2].children[0]
    assert (inc.type, inc.value, inc.children[0].value) == ("PostfixOp", "++", "i")


def test_prefix_increment():
    node = parse_expr("++i")
    assert (node.type, node.value) == ("PrefixOp", "++")


def test_function_params_and_call():
    root = parse("int add(int a, int b) { return add(a, 1); }")
    fn = root.children[0]
    assert fn.value == "int add"
    assert [p.value for p in fn.children[0].children] == ["int a", "int b"]
    call = next(n for n in walk(fn) if n.type == "Call")
    assert call.value == "add" and len(call.children) == 2


def test_if_else_and_while():
    root = parse("int f() { if (x) { y = 1; } else y = 2; while (x > 0) x = x - 1; }")
    kinds = [n.type for n in walk(root)]
    for kind in ("If", "Then", "Else", "While", "Body"):
        assert kind in kinds


def test_array_declaration():
    root = parse('int f() { char msg[] = "hi"; int buf[16]; }')
    decls = [n for n in walk(root) if n.type == "Declaration"]
    assert [d.value for d in decls] == ["char[]", "int[16]"]
    assert decls[0].children[1].children[0].value == '"hi"'


def test_statement_nodes_carry_line_numbers():
    root = parse("int x = 1;\n\nint main() {\n  if (x) {\n    x = 2;\n  }\n  return x;\n}")
    lines = {n.type: n.line for n in walk(root) if n.type in ("Declaration", "Function", "If", "Assign", "Return")}
    assert lines == {"Declaration": 1, "Function": 3, "If": 4, "Assign": 5, "Return": 7}


def test_sample_file_parses_without_unknown_nodes():
    root = parse((ROOT / "sample.c").read_text())
    assert root.type == "Program"
    assert not [n for n in walk(root) if n.type in ("Unknown", "ParseError")]
    functions = [n.value for n in walk(root) if n.type == "Function"]
    assert functions == ["int calculate_sum", "int main"]


def test_garbage_input_does_not_raise():
    parse("}}} int ( ; @@ for while")
