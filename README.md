 🔬 C Analyzer

[![tests](https://github.com/Sdb002/C-Analyzer/actions/workflows/tests.yml/badge.svg)](https://github.com/Sdb002/C-Analyzer/actions/workflows/tests.yml)

A desktop IDE-like tool for static analysis of C source code. Built with Python and PySide6, it parses your C code in real time, visualizes the Abstract Syntax Tree, extracts tokens and symbols, estimates time complexity, and exports a full PDF report — all in a clean dark-themed GUI.

---

✨ Features

- **Live Code Editor** — Syntax-aware editor with line numbers, current line highlight, and block folding
- **Real-time Analysis** — Debounced analysis triggers automatically as you type (no button needed)
- **Lexer** — Regex-based tokenizer handling keywords, identifiers, numbers (hex/float/int), strings, chars, operators, preprocessor directives, and comments
- **Parser** — Pratt-style expression parser + recursive descent for statements and declarations
- **AST Visualization** — Auto-balanced tree layout rendered with Matplotlib, displayed inline and auto-scales with the dock
- **Symbol Table** — Nested scope tracking with scope chain resolution (global → function → block)
- **Big-O Complexity Estimator** — Heuristic analysis via AST loop-nesting depth (O(1), O(n), O(n²), ...)
- **Live Metrics Bar** — Token count, AST node count, function count, complexity, and memory usage
- **PDF Export** — Full report with source code, token table, symbol table, Big-O estimate, and AST image
- **Threaded Worker** — Analysis runs on a background thread; UI never freezes

---

---

 🗂️ Project Structure

```
c-analyzer/
├── gui.py               # Main window, editor, worker, UI layout
├── lexer.py             # Regex-based C lexer
├── parser.py            # Pratt parser + recursive descent, produces ASTNode tree
├── symbol_table.py      # Scoped symbol table with scope stack
├── complexity.py        # Big-O estimate from loop nesting (no GUI imports)
├── ast_visual_c.py      # AST renderer using Matplotlib
├── report_generator.py  # PDF report generator using ReportLab
├── sample.c             # Sample C file for testing
└── tests/               # pytest suite: lexer, parser, symbol table, complexity
```

---

 🧪 Tests

The analysis core (lexer, parser, symbol table, complexity estimator) is pure Python and has a pytest suite, run on every push by GitHub Actions on Python 3.10–3.13:

```bash
pip install -r requirements-dev.txt
pytest
```

The suite covers operator precedence and associativity, assignments, prefix/postfix `++`/`--`, arrays, line numbers on AST nodes, scope resolution, Big-O by loop nesting, and that `sample.c` parses with no unknown nodes.

---

 ⚙️ Installation

**Requirements:** Python 3.10+

```bash
# Clone the repo
git clone https://github.com/Sdb002/c-analyzer.git
cd c-analyzer

# Install dependencies
pip install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `PySide6` | GUI framework |
| `matplotlib` | AST visualization |
| `reportlab` | PDF report generation |
| `pillow` | AST image rendering in GUI |
| `psutil` | Live memory usage in metrics bar |
| `pygments` | Enhanced token display |

---

 🚀 Usage

```bash
python gui.py
```

Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open a `.c` file |
| `Ctrl+S` | Save current file |
| `Ctrl+R` | Force re-analyze |
| `Ctrl+E` | Export PDF report |

 Workflow

1. Open a `.c` file or type directly in the editor
2. Analysis triggers automatically after you stop typing
3. Switch between **Tokens**, **Symbols**, and **AST** tabs in the right inspector
4. Check the metrics bar at the bottom for live stats
5. Export a full PDF report with `Ctrl+E`

---

 🧠 How It Works

```
Source Code
    │
    ▼
  Lexer  ──────────────────► Token List
    │
    ▼
  Parser (Pratt + Recursive Descent)
    │
    ▼
  ASTNode Tree
    ├──► Symbol Table Builder  ──► Scoped Symbol List
    ├──► AST Visualizer        ──► Matplotlib Figure → PNG
    ├──► Big-O Estimator       ──► Loop Nesting Depth → O(nᵏ)
    └──► Report Generator      ──► PDF
```

---

 📄 PDF Report Contents

Each exported report includes:

1. Cover page with date
2. Full source code listing
3. Complete token table (type, value, line, column)
4. Symbol table (name, type, scope, line, value)
5. Big-O time complexity estimate with explanation
6. AST diagram image

---

 ⚠️ Known Limitations

- Big-O estimation is heuristic (loop nesting depth only) — does not account for recursion or data structure complexity
- Symbol table currently extracts function names from AST; variable-level scope analysis is partial
- Block folding in the editor is visual only (selects the block range)
- Parser handles a subset of C — no `do-while`, `goto`, `#define` macros, or pointer arithmetic edge cases

---

 🛠️ Built With

- [PySide6](https://doc.qt.io/qtforpython/) — Qt6 bindings for Python
- [Matplotlib](https://matplotlib.org/) — AST tree visualization
- [ReportLab](https://www.reportlab.com/) — PDF generation
- [Pillow](https://python-pillow.org/) — Image handling

---



 👤 Author

**Shuvrodev**
- GitHub: [@Sdb002](https://github.com/Sdb002)

---

 📜 License

MIT License — feel free to use, modify, and distribute.
