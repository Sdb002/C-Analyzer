# ast_visual_c.py
# Better AST visualization with:
# - Auto-balanced tree layout
# - Material 3 themed nodes
# - Prevents overlapping
# - Clean labeling

import matplotlib.pyplot as plt
import matplotlib.patches as patches

class ASTVisualizerC:
    def __init__(self, node_width=1.8, node_height=0.75, h_spacing=2.8, v_spacing=1.8):
        self.node_width = node_width
        self.node_height = node_height
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing
        self.positions = {}
        self._order = []

    # ----------------------------------------------------------
    # Compute layout using DFS + subtree width calculation
    # ----------------------------------------------------------
    def compute_layout(self, root):
        subtree_widths = {}

        def calc_subtree_width(node):
            """Returns required width of subtree rooted at this node."""
            if not getattr(node, "children", []):
                subtree_widths[id(node)] = self.node_width
                return self.node_width

            total = 0
            for c in node.children:
                total += calc_subtree_width(c) + self.h_spacing
            total = max(total - self.h_spacing, self.node_width)
            subtree_widths[id(node)] = total
            return total

        calc_subtree_width(root)

        def place_node(node, x, y):
            """Place node and recursively position children centered under it."""
            self.positions[id(node)] = (x, y)
            children = getattr(node, "children", [])
            if not children:
                return

            # total width of children
            total_w = sum(subtree_widths[id(c)] + self.h_spacing for c in children)
            total_w -= self.h_spacing

            start_x = x - total_w / 2
            for c in children:
                cw = subtree_widths[id(c)]
                cx = start_x + cw / 2
                cy = y - self.v_spacing
                place_node(c, cx, cy)
                start_x += cw + self.h_spacing

        place_node(root, 0, 0)

    # ----------------------------------------------------------
    # Collect nodes in preorder for drawing edges + nodes
    # ----------------------------------------------------------
    def collect_preorder(self, root):
        self._order = []

        def dfs(n):
            self._order.append(n)
            for c in getattr(n, "children", []):
                dfs(c)

        dfs(root)

    # ----------------------------------------------------------
    # Public API: Render the AST to a figure
    # ----------------------------------------------------------
    def render_ast(self, root, figsize=(14, 10)):
        if root is None:
            return None

        self.compute_layout(root)
        self.collect_preorder(root)

        fig, ax = plt.subplots(figsize=figsize)

        # --------------------------------------
        # Draw edges
        # --------------------------------------
        for node in self._order:
            x1, y1 = self.positions[id(node)]
            for child in getattr(node, "children", []):
                x2, y2 = self.positions[id(child)]
                ax.plot([x1, x2], [y1, y2],
                        color="#37474f", linewidth=1.0, zorder=1)

        # --------------------------------------
        # Draw nodes
        # --------------------------------------
        for node in self._order:
            x, y = self.positions[id(node)]

            # Material-style card node
            rect = patches.FancyBboxPatch(
                (x - self.node_width / 2, y - self.node_height / 2),
                self.node_width,
                self.node_height,
                boxstyle="round,pad=0.18,rounding_size=0.15",
                edgecolor="#1a237e",
                facecolor="#e8eaf6",
                linewidth=1.3,
                zorder=3,
                mutation_aspect=1
            )
            ax.add_patch(rect)

            # Node label text
            text = node.type
            if node.value is not None:
                text += f": {node.value}"

            # clip if too long
            if len(text) > 28:
                text = text[:25] + "..."

            ax.text(x, y, text,
                    ha='center', va='center',
                    fontsize=8.5, color="#1a237e",
                    zorder=4)

        # --------------------------------------
        # Adjust viewport
        # --------------------------------------
        xs = [p[0] for p in self.positions.values()]
        ys = [p[1] for p in self.positions.values()]

        pad_x = 2.5
        pad_y = 2.0
        ax.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
        ax.set_ylim(min(ys) - pad_y, max(ys) + pad_y)

        ax.set_axis_off()
        plt.tight_layout()

        return fig
