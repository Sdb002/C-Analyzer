

from PySide6 import QtCore, QtGui, QtWidgets
import sys, os, threading, queue, tempfile, time, traceback

# matplotlib for AST rendering (worker uses Agg backend)
import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

# Optional imaging
try:
    from PIL import Image
    from PIL.ImageQt import ImageQt
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

# Optional pygments for nicer token display (not required)
try:
    from pygments import lex
    from pygments.lexers import CLexer
    HAVE_PYGMENTS = True
except Exception:
    HAVE_PYGMENTS = False

# Optional psutil for memory usage
try:
    import psutil
    HAVE_PSUTIL = True
except Exception:
    HAVE_PSUTIL = False

# Try to import user modules (non-fatal if missing)
from complexity import big_o_from_depth, max_loop_depth

try:
    from lexer import Lexer
except Exception:
    Lexer = None
try:
    from parser import Parser
except Exception:
    Parser = None
try:
    from symbol_table import SymbolTable
except Exception:
    SymbolTable = None
try:
    from ast_visual_c import ASTVisualizerC
except Exception:
    ASTVisualizerC = None

# Report generator (must exist and implement create_report)
try:
    from report_generator import create_report
except Exception:
    create_report = None

# ---------------- theme ----------------
PALETTE = {
    'background': '#282a36',
    'surface': '#1e1f29',
    'panel': '#21222c',
    'accent': '#6272a4',
    'text': '#f8f8f2',
    'muted': '#b6b6b6',
}
FONT_MONO = "JetBrains Mono, Consolas, monospace"

DEBOUNCE_MS = 300
METRICS_UPDATE_MS = 600

# ---------------- worker ----------------
class AnalyzerWorker(threading.Thread):
    def __init__(self, job_q, res_q, stop_event):
        super().__init__(daemon=True)
        self.job_q = job_q
        self.res_q = res_q
        self.stop_event = stop_event
        # wrappers will be attached by main window
        self.lexer = None
        self.parser = None
        self.symbol_table = None
        self.visualizer = None

    def safe_save_fig(self, fig):
        """Save matplotlib figure to a temp PNG and return path or None."""
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            fig.savefig(tmp.name, dpi=140, bbox_inches='tight')
            tmp.close()
            return tmp.name
        except Exception:
            return None

    def run(self):
        while not self.stop_event.is_set():
            try:
                job = self.job_q.get(timeout=0.2)
            except Exception:
                continue
            code = job.get('code', '')
            out = {'tokens': [], 'symbols': [], 'ast_png': None, 'ast_root': None}
            try:
                # tokenize
                if self.lexer:
                    try:
                        tokens = self.lexer.tokenize(code)
                    except Exception:
                        tokens = []
                    out['tokens'] = tokens
                # parse
                if self.parser:
                    try:
                        parser = self.parser(tokens)
                        ast_root = parser.parse()
                        out['ast_root'] = ast_root
                    except Exception:
                        out['ast_root'] = None
                # symbols
                if self.symbol_table and out['ast_root']:
                    try:
                        self.symbol_table.clear()
                        def walk(node):
                            if not node:
                                return
                            if getattr(node, 'type', None) == 'Function':
                                fname = (node.value or '').split()[-1]
                                try:
                                    self.symbol_table.add_symbol(fname, 'function', getattr(node, 'line', 0))
                                except Exception:
                                    pass
                            for c in getattr(node, 'children', []) or []:
                                walk(c)
                        walk(out['ast_root'])
                        try:
                            syms = self.symbol_table.get_all()
                            out['symbols'] = syms
                        except Exception:
                            out['symbols'] = []
                    except Exception:
                        out['symbols'] = []
                # render AST to PNG using visualizer (if available)
                if self.visualizer and out['ast_root']:
                    try:
                        fig = self.visualizer.render_ast(out['ast_root'], figsize=(6,6))
                        png = self.safe_save_fig(fig)
                        out['ast_png'] = png
                    except Exception:
                        out['ast_png'] = None
            except Exception:
                pass
            # push result (non-blocking UI)
            self.res_q.put(out)
            time.sleep(0.01)

# ---------------- code editor (QPlainTextEdit with line numbers) ----------------
class LineNumberArea(QtWidgets.QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QtCore.QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

class CodeEditor(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QtGui.QFont(FONT_MONO, 11))
        self.setStyleSheet(f"background:{PALETTE['surface']}; color:{PALETTE['text']};")
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QtCore.QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QtGui.QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QtGui.QColor(PALETTE['panel']))
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QtGui.QColor(PALETTE['muted']))
                painter.drawText(0, top, self.lineNumberArea.width()-4, self.fontMetrics().height(), QtCore.Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def highlight_current_line(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QtWidgets.QTextEdit.ExtraSelection()
            lineColor = QtGui.QColor(40,44,52)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def fold_current_block(self):
        # simple placeholder: find nearest braces and collapse by selecting (visual only)
        try:
            txt = self.toPlainText()
            cursor = self.textCursor()
            pos = cursor.position()
            # find open brace before pos
            open_idx = txt.rfind('{', 0, pos)
            if open_idx == -1:
                return
            # find matching close
            depth = 0
            close_idx = -1
            for i in range(open_idx, len(txt)):
                if txt[i] == '{': depth += 1
                elif txt[i] == '}':
                    depth -= 1
                    if depth == 0:
                        close_idx = i
                        break
            if close_idx == -1:
                return
            # select the block to indicate folding (visual only)
            cursor.setPosition(open_idx+1)
            cursor.setPosition(close_idx, QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)
        except Exception:
            pass

# ---------------- Main Window ----------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('C Analyzer — Revamped')
        self.resize(1400, 860)
        # queues and worker
        self.job_q = queue.Queue()
        self.res_q = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = AnalyzerWorker(self.job_q, self.res_q, self.stop_event)
        # attach simple wrappers if modules present
        self.worker.lexer = Lexer() if Lexer else None
        self.worker.parser = Parser if Parser else None
        self.worker.symbol_table = SymbolTable() if SymbolTable else None
        self.worker.visualizer = ASTVisualizerC() if ASTVisualizerC else None

        # build UI
        self._build_ui()
        # start worker and timer
        self.worker.start()
        self.timer = QtCore.QTimer()
        self.timer.setInterval(120)
        self.timer.timeout.connect(self._poll_results)
        self.timer.start()

        # metrics timer
        self.metrics_timer = QtCore.QTimer()
        self.metrics_timer.setInterval(METRICS_UPDATE_MS)
        self.metrics_timer.timeout.connect(self._update_metrics_display)
        self.metrics_timer.start()

        # store last results
        self._last_tokens = []
        self._last_ast_root = None
        self._last_symbols = []
        self._last_ast_png = None

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        h = QtWidgets.QHBoxLayout(central)
        h.setContentsMargins(0,0,0,0)

        # sidebar
        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet(f"background:{PALETTE['panel']};")
        sv = QtWidgets.QVBoxLayout(sidebar)
        sv.setContentsMargins(12,12,12,12)
        title = QtWidgets.QLabel('C Analyzer')
        title.setStyleSheet(f"color:{PALETTE['text']}; font-weight:600;")
        sv.addWidget(title)
        sv.addSpacing(8)

        # icons for buttons using standard icons
        style = self.style()
        icon_open = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton)
        icon_save = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton)
        icon_run = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload)
        icon_pdf = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton)
        icon_fold = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView)

        btn_open = QtWidgets.QPushButton(icon_open, ' Open')
        btn_save = QtWidgets.QPushButton(icon_save, ' Save')
        btn_run = QtWidgets.QPushButton(icon_run, ' Analyze')
        btn_pdf = QtWidgets.QPushButton(icon_pdf, ' Export PDF')
        btn_fold = QtWidgets.QPushButton(icon_fold, ' Fold Block')
        for b in (btn_open, btn_save, btn_run, btn_pdf, btn_fold):
            b.setStyleSheet(f"background:{PALETTE['accent']}; color:{PALETTE['text']}; padding:8px; border:none; text-align:left;")
            b.setIconSize(QtCore.QSize(18,18))
            sv.addWidget(b)
        sv.addStretch()
        h.addWidget(sidebar)

        # main area: vertical layout with editor on top and performance+tokens below
        main_v = QtWidgets.QVBoxLayout()
        main_v.setContentsMargins(0,0,0,0)

        # editor area
        editor_frame = QtWidgets.QFrame()
        editor_layout = QtWidgets.QVBoxLayout(editor_frame)
        editor_layout.setContentsMargins(8,8,8,4)
        self.editor = CodeEditor()
        editor_layout.addWidget(self.editor)
        main_v.addWidget(editor_frame, stretch=3)

        # Performance panel below editor
        perf = QtWidgets.QFrame()
        perf.setFixedHeight(36)
        perf.setStyleSheet(f"background:{PALETTE['panel']};")
        perf_layout = QtWidgets.QHBoxLayout(perf)
        perf_layout.setContentsMargins(8,4,8,4)
        self.lbl_tokens = QtWidgets.QLabel('Tokens: 0')
        self.lbl_ast_nodes = QtWidgets.QLabel('AST Nodes: 0')
        self.lbl_functions = QtWidgets.QLabel('Functions: 0')
        self.lbl_complexity = QtWidgets.QLabel('Complexity: O(1)')
        self.lbl_memory = QtWidgets.QLabel('Memory: ? MB')
        for w in (self.lbl_tokens, self.lbl_ast_nodes, self.lbl_functions, self.lbl_complexity, self.lbl_memory):
            w.setStyleSheet(f"color:{PALETTE['muted']}; padding:4px;")
            perf_layout.addWidget(w)
        perf_layout.addStretch()
        main_v.addWidget(perf, stretch=0)

        # add main_v to layout
        container = QtWidgets.QFrame()
        container.setLayout(main_v)
        h.addWidget(container, stretch=1)

        # Right dock: TabWidget for Tokens / Symbols / AST
        dock = QtWidgets.QDockWidget('Inspector', self)
        dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)
        dock.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFloatable)
        inspector_tabs = QtWidgets.QTabWidget()
        inspector_tabs.setTabPosition(QtWidgets.QTabWidget.North)
        # tokens table inside a widget (with scroll)
        tokens_widget = QtWidgets.QWidget()
        tokens_layout = QtWidgets.QVBoxLayout(tokens_widget)
        tokens_layout.setContentsMargins(6,6,6,6)
        self.tokens_table = QtWidgets.QTableWidget(0,4)
        self.tokens_table.setHorizontalHeaderLabels(['Type','Value','Line','Col'])
        self.tokens_table.horizontalHeader().setStretchLastSection(True)
        self.tokens_table.setStyleSheet(f"background:{PALETTE['surface']}; color:{PALETTE['text']};")
        tokens_layout.addWidget(self.tokens_table)
        # symbols table
        symbols_widget = QtWidgets.QWidget()
        symbols_layout = QtWidgets.QVBoxLayout(symbols_widget)
        symbols_layout.setContentsMargins(6,6,6,6)
        self.symbols_table = QtWidgets.QTableWidget(0,5)
        self.symbols_table.setHorizontalHeaderLabels(['Name','Type','Scope','Line','Value'])
        self.symbols_table.horizontalHeader().setStretchLastSection(True)
        self.symbols_table.setStyleSheet(f"background:{PALETTE['surface']}; color:{PALETTE['text']};")
        symbols_layout.addWidget(self.symbols_table)
        # AST inside a scroll area (we'll set QLabel pixmap)
        ast_widget = QtWidgets.QWidget()
        ast_layout = QtWidgets.QVBoxLayout(ast_widget)
        ast_layout.setContentsMargins(6,6,6,6)
        self.ast_view = QtWidgets.QLabel('AST will appear here')
        self.ast_view.setAlignment(QtCore.Qt.AlignCenter)
        ast_layout.addWidget(self.ast_view)

        # Add tabs with icons
        tab_icon_tokens = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
        tab_icon_symbols = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)
        tab_icon_ast = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DesktopIcon)

        inspector_tabs.addTab(tokens_widget, tab_icon_tokens, "Tokens")
        inspector_tabs.addTab(symbols_widget, tab_icon_symbols, "Symbols")
        inspector_tabs.addTab(ast_widget, tab_icon_ast, "AST")

        dock.setWidget(inspector_tabs)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        # connect buttons
        btn_open.clicked.connect(self.open_file)
        btn_save.clicked.connect(self.save_file)
        btn_run.clicked.connect(lambda: self.schedule_analysis(force=True))
        btn_pdf.clicked.connect(self.export_pdf)
        btn_fold.clicked.connect(self.editor.fold_current_block)

        # editor change detection (debounced)
        self._debounce_timer = QtCore.QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(lambda: self.schedule_analysis())
        self.editor.textChanged.connect(self._on_editor_text_changed)

        # keyboard shortcuts (fixed for PySide6)
        sc_save = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        sc_save.activated.connect(self.save_file)
        sc_open = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
        sc_open.activated.connect(self.open_file)
        sc_run = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+R"), self)
        sc_run.activated.connect(lambda: self.schedule_analysis(force=True))
        sc_pdf = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+E"), self)
        sc_pdf.activated.connect(self.export_pdf)

        # create a scroll area wrapper for AST tab (replace ast_widget content)
        self.ast_scroll = QtWidgets.QScrollArea()
        self.ast_scroll.setWidgetResizable(True)
        ast_container = QtWidgets.QWidget()
        ac_layout = QtWidgets.QVBoxLayout(ast_container)
        ac_layout.setContentsMargins(6,6,6,6)
        ac_layout.addWidget(self.ast_view)
        self.ast_scroll.setWidget(ast_container)
        inspector_tabs.removeTab(2)
        inspector_tabs.addTab(self.ast_scroll, tab_icon_ast, "AST")

        # connect resize to rescale function
        self.ast_scroll.viewport().installEventFilter(self)
        self._ast_pixmap = None

    def eventFilter(self, obj, event):
        # listen for resize on ast_scroll viewport
        if obj is self.ast_scroll.viewport() and event.type() == QtCore.QEvent.Resize:
            QtCore.QTimer.singleShot(10, self._rescale_ast)
        return super().eventFilter(obj, event)

    def _rescale_ast(self):
        # rescale current AST pixmap to fit viewport while keeping aspect ratio
        try:
            if not self._ast_pixmap:
                return
            vp_w = self.ast_scroll.viewport().width()
            vp_h = self.ast_scroll.viewport().height()
            scaled = self._ast_pixmap.scaled(vp_w, vp_h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.ast_view.setPixmap(scaled)
            self.ast_view.adjustSize()
        except Exception:
            pass

    def _on_editor_text_changed(self):
        # restart debounce
        self._debounce_timer.start()

    def open_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open C file', '', 'C Files (*.c);;All Files (*)')
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                txt = f.read()
            self.editor.setPlainText(txt)
            self.schedule_analysis(force=True)

    def save_file(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save C file', '', 'C Files (*.c);;All Files (*)')
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())

    def schedule_analysis(self, force=False):
        # clear previous jobs
        try:
            while True:
                self.job_q.get_nowait()
        except Exception:
            pass
        self.job_q.put({'code': self.editor.toPlainText(), 'force': force})

    def _poll_results(self):
        try:
            while True:
                res = self.res_q.get_nowait()
                self._apply_results(res)
        except Exception:
            pass

    def _apply_results(self, res):
        # store last
        self._last_tokens = res.get('tokens', [])
        self._last_ast_root = res.get('ast_root', None)
        self._last_symbols = res.get('symbols', []) or []
        self._last_ast_png = res.get('ast_png', None)

        # tokens
        toks = res.get('tokens', [])
        try:
            self.tokens_table.setRowCount(0)
            for t in toks:
                r = self.tokens_table.rowCount()
                self.tokens_table.insertRow(r)
                self.tokens_table.setItem(r,0, QtWidgets.QTableWidgetItem(str(getattr(t,'type', ''))))
                self.tokens_table.setItem(r,1, QtWidgets.QTableWidgetItem(str(getattr(t,'value', ''))))
                self.tokens_table.setItem(r,2, QtWidgets.QTableWidgetItem(str(getattr(t,'line', ''))))
                self.tokens_table.setItem(r,3, QtWidgets.QTableWidgetItem(str(getattr(t,'column', ''))))
        except Exception:
            pass
        # symbols
        syms = res.get('symbols', []) or []
        try:
            self.symbols_table.setRowCount(0)
            for s in syms:
                r = self.symbols_table.rowCount()
                self.symbols_table.insertRow(r)
                name = str(getattr(s,'name', getattr(s,'identifier', '')))
                self.symbols_table.setItem(r,0, QtWidgets.QTableWidgetItem(name))
                self.symbols_table.setItem(r,1, QtWidgets.QTableWidgetItem(str(getattr(s,'type', ''))))
                self.symbols_table.setItem(r,2, QtWidgets.QTableWidgetItem(str(getattr(s,'scope', ''))))
                self.symbols_table.setItem(r,3, QtWidgets.QTableWidgetItem(str(getattr(s,'line_number', ''))))
                self.symbols_table.setItem(r,4, QtWidgets.QTableWidgetItem(str(getattr(s,'value', ''))))
        except Exception:
            pass
        # AST image (right dock) — scale down to fit dock using QPixmap.scaled
        png = res.get('ast_png', None)
        if png and HAVE_PIL:
            try:
                img = Image.open(png)
                qim = ImageQt(img)
                pix = QtGui.QPixmap.fromImage(qim)
                # store original pixmap for future resizes
                self._ast_pixmap = pix
                # initial scale to viewport size
                vp_w = self.ast_scroll.viewport().width()
                vp_h = self.ast_scroll.viewport().height()
                if vp_w <= 0 or vp_h <= 0:
                    # fallback scale
                    vp_w = int(self.width() * 0.35)
                    vp_h = int(self.height() * 0.6)
                scaled = pix.scaled(vp_w, vp_h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.ast_view.setPixmap(scaled)
                self.ast_view.setAlignment(QtCore.Qt.AlignCenter)
                self.ast_view.adjustSize()
                # remove temp file — keep it only if other parts need it (report)
                try:
                    os.unlink(png)
                except Exception:
                    pass
            except Exception:
                self.ast_view.setText('AST rendering failed')
        else:
            self.ast_view.setText('AST not available')
            self._ast_pixmap = None
        # update metrics immediately
        self._update_metrics()

    # ---------------- Complexity estimator (corrected -> Big-O via loop nesting) ----------------
    def _max_loop_depth(self, node, current=0):
        return max_loop_depth(node, current)

    def _big_o_from_depth(self, depth):
        return big_o_from_depth(depth)

    def _update_metrics(self):
        toks = getattr(self, '_last_tokens', []) or []
        ast_root = getattr(self, '_last_ast_root', None)
        token_count = len(toks)
        ast_nodes = 0
        functions = 0

        def walk(n):
            nonlocal ast_nodes, functions
            if not n:
                return
            ast_nodes += 1
            t = getattr(n, 'type', '').lower()
            if t == 'function':
                functions += 1
            for c in getattr(n, 'children', []) or []:
                walk(c)
        walk(ast_root)

        # complexity: compute max loop depth then map to Big-O
        depth = self._max_loop_depth(ast_root, 0)
        bigo = self._big_o_from_depth(depth)

        # memory
        mem_mb = '?'
        if HAVE_PSUTIL:
            try:
                proc = psutil.Process(os.getpid())
                mem_mb = f"{proc.memory_info().rss // 1024 // 1024} MB"
            except Exception:
                mem_mb = '?'
        else:
            mem_mb = 'install psutil'
        # update labels
        self.lbl_tokens.setText(f"Tokens: {token_count}")
        self.lbl_ast_nodes.setText(f"AST Nodes: {ast_nodes}")
        self.lbl_functions.setText(f"Functions: {functions}")
        self.lbl_complexity.setText(f"Complexity: {bigo}")
        self.lbl_memory.setText(f"Memory: {mem_mb}")

    def _update_metrics_display(self):
        # called by timer to refresh metrics even if no new result
        self._update_metrics()

    def export_pdf(self):
        # Real PDF export implementation using report_generator.create_report
        if create_report is None:
            QtWidgets.QMessageBox.critical(self, 'Export', 'report_generator not found. Make sure report_generator.py is present and has create_report().')
            return

        if not self._last_tokens:
            QtWidgets.QMessageBox.warning(self, 'Export', 'No analysis results available. Run Analyze first.')
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Export PDF', '', 'PDF Files (*.pdf)')
        if not path:
            return

        try:
            # compute Big-O string from AST
            depth = self._max_loop_depth(self._last_ast_root, 0)
            big_o = self._big_o_from_depth(depth)
            # call generator
            create_report(
                filepath=path,
                code_text=self.editor.toPlainText(),
                tokens=self._last_tokens,
                symbols=self._last_symbols,
                ast_fig=None  # report_generator in this code expects ast_png; many implementations accept fig or png; using png fallback below
            )
            # If the report_generator supports ast_png path variant, you could pass that instead.
            # For safety, also try the newer API if available:
            try:
                # some versions expose create_report(path, code, tokens, symbols, big_o, ast_png)
                create_report(path, self.editor.toPlainText(), self._last_tokens, self._last_symbols, big_o, self._last_ast_png)
            except Exception:
                # ignore if not available
                pass

            QtWidgets.QMessageBox.information(self, 'Export', f'PDF exported to:\n{path}')
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Export', f'PDF export failed:\n{e}')

    def closeEvent(self, event):
        # stop worker gracefully
        try:
            self.stop_event.set()
        except Exception:
            pass
        try:
            if self.worker.is_alive():
                self.worker.join(timeout=0.2)
        except Exception:
            pass
        event.accept()

# ---------------- run ----------------
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    palette = app.palette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(PALETTE['background']))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(PALETTE['surface']))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(PALETTE['text']))
    app.setPalette(palette)
    win = MainWindow()
    # link queues (worker already has them but ensure)
    win.worker.job_q = win.job_q
    win.worker.res_q = win.res_q
    win.show()
    sys.exit(app.exec())
