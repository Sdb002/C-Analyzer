"""Big-O estimate from an AST: the deepest nesting of loops.

A heuristic, not a proof: it assumes every loop runs O(n) times and ignores
recursion and what called functions cost. Kept free of any GUI import so it
can be tested on its own.
"""

LOOP_TYPES = ('for', 'while', 'do')


def max_loop_depth(node, current=0):
    """Maximum loop nesting depth in the tree rooted at `node`."""
    if not node:
        return current
    kind = (getattr(node, 'type', '') or '').lower()
    depth_here = current + 1 if kind in LOOP_TYPES else current
    deepest = depth_here
    for child in getattr(node, 'children', []) or []:
        deepest = max(deepest, max_loop_depth(child, depth_here))
    return deepest


def big_o_from_depth(depth):
    if depth == 0:
        return 'O(1)'
    if depth == 1:
        return 'O(n)'
    return f'O(n^{depth})'


def estimate_big_o(root):
    """Big-O string for a whole program, e.g. \x27O(n^2)\x27."""
    return big_o_from_depth(max_loop_depth(root))
