

import matplotlib.pyplot as plt
import matplotlib.patches as patches

class ASTVisualizerC:
    def __init__(self, node_radius=0.45, x_sep=2.2, y_sep=1.4):
        self.node_positions = {}
        self.node_radius = node_radius
        self.x_sep = x_sep
        self.y_sep = y_sep
        self._order = []

    def _assign_levels(self, root):
        levels = {}
        def dfs(node, depth=0):
            levels.setdefault(depth, []).append(node)
            for ch in getattr(node, "children", []):
                dfs(ch, depth+1)
        dfs(root, 0)
        return levels

    def _compute_positions(self, root):
        levels = self._assign_levels(root)
        positions = {}
        for depth, nodes in levels.items():
            x = depth * self.x_sep
            count = len(nodes)
            # center vertically
            total = (count - 1) * self.y_sep
            start = total / 2.0
            for i, n in enumerate(nodes):
                y = start - i * self.y_sep
                positions[id(n)] = (x, y)
        self.node_positions = positions

    def _collect_preorder(self, root):
        self._order = []
        def dfs(n):
            self._order.append(n)
            for c in getattr(n, "children", []):
                dfs(c)
        dfs(root)

    def render_ast(self, root, figsize=(10,6)):
        if root is None:
            return None
        self._compute_positions(root)
        self._collect_preorder(root)

        fig, ax = plt.subplots(figsize=figsize)
        # edges
        for node in self._order:
            p = self.node_positions.get(id(node))
            if not p:
                continue
            x1, y1 = p
            for child in getattr(node, "children", []):
                pc = self.node_positions.get(id(child))
                if not pc:
                    continue
                x2, y2 = pc
                ax.plot([x1, x2], [y1, y2], linewidth=0.9, color='black', zorder=1)

        # nodes
        for node in self._order:
            p = self.node_positions.get(id(node))
            if not p:
                continue
            x, y = p
            # draw rounded rectangle-like patch for readability
            rect = patches.FancyBboxPatch((x-0.8, y-0.35), 1.6, 0.7,
                                          boxstyle="round,pad=0.1", linewidth=0.8,
                                          facecolor="#f2f7ff", edgecolor="#1f3a93", zorder=3)
            ax.add_patch(rect)
            label = node.type if node.value is None else f"{node.type}: {str(node.value)}"
            # wrap if long
            if len(label) > 28:
                label = label[:25] + "..."
            ax.text(x, y, label, ha='center', va='center', fontsize=8, zorder=4)

        # adjust limits
        xs = [p[0] for p in self.node_positions.values()]
        ys = [p[1] for p in self.node_positions.values()]
        if xs and ys:
            margin_x = 1.5
            ax.set_xlim(min(xs) - margin_x, max(xs) + margin_x)
            ax.set_ylim(min(ys) - 1.5, max(ys) + 1.5)
        ax.axis('off')
        plt.tight_layout()
        return fig
