from lexer import Lexer
from parser import Parser


def tokens(src, drop=("COMMENT",)):
    return [t for t in Lexer().tokenize(src) if t.type not in drop]


def parse(src):
    return Parser(tokens(src)).parse()


def parse_expr(expr):
    """The AST of a single expression statement inside a function body."""
    root = parse(f"int f() {{ {expr}; }}")
    block = root.children[0].children[1]
    return block.children[0]


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def sexpr(node):
    """Compact form for asserting tree shape: BinaryOp('+', a, b) -> (+ a b)."""
    if not node.children:
        return str(node.value)
    inner = " ".join(sexpr(c) for c in node.children)
    return f"({node.value} {inner})" if node.value is not None else f"({node.type} {inner})"
