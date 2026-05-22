

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak, Image, Preformatted
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import mm
from datetime import datetime
import tempfile, os

class ReportGenerator:
    def __init__(self):
        styles = getSampleStyleSheet()

        self.title = ParagraphStyle(
            "title", parent=styles["Title"],
            alignment=TA_CENTER, fontSize=26
        )
        self.subtitle = ParagraphStyle(
            "subtitle", parent=styles["Heading2"],
            alignment=TA_CENTER, textColor=colors.grey
        )
        self.h = ParagraphStyle(
            "h", parent=styles["Heading2"], spaceAfter=8
        )
        self.body = ParagraphStyle(
            "body", parent=styles["BodyText"], fontSize=10
        )
        self.code = ParagraphStyle(
            "code", fontName="Courier", fontSize=8
        )

    def table(self, rows, widths):
        t = Table(rows, widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
        ]))
        return t

    def create(self, path, code, tokens, symbols, big_o, ast_png=None):
        if not path.endswith(".pdf"):
            path += ".pdf"

        doc = SimpleDocTemplate(
            path, pagesize=A4,
            leftMargin=18*mm, rightMargin=18*mm,
            topMargin=18*mm, bottomMargin=18*mm
        )

        story = []

        #COVER
        story.append(Spacer(1, 100))
        story.append(Paragraph("C SOURCE CODE ANALYSIS REPORT", self.title))
        story.append(Spacer(1, 20))
        story.append(Paragraph("Static Analysis & Complexity Estimation", self.subtitle))
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            f"""
            <b>Date:</b> {datetime.now().strftime('%d %B %Y')}<br/>
            <b>Includes:</b> Tokens, Symbols, AST, Big-O Complexity
            """,
            self.body
        ))
        story.append(PageBreak())

        # SOURCE 
        story.append(Paragraph("1. Source Code", self.h))
        story.append(Preformatted(code, self.code))
        story.append(PageBreak())

        # ---------- TOKENS ----------
        story.append(Paragraph("2. Token Table", self.h))
        rows = [["Type", "Value", "Line", "Column"]]
        for t in tokens:
            rows.append([t.type, t.value, t.line, t.column])
        story.append(self.table(rows, [80, 240, 60, 60]))
        story.append(PageBreak())

        # ---------- SYMBOLS ----------
        story.append(Paragraph("3. Symbol Table", self.h))
        rows = [["Name", "Type", "Scope", "Line", "Value"]]
        for s in symbols:
            rows.append([
                s.name, s.type, s.scope,
                s.line_number, s.value or ""
            ])
        story.append(self.table(rows, [100, 80, 80, 50, 120]))
        story.append(PageBreak())

        # ---------- BIG-O ----------
        story.append(Paragraph("4. Time Complexity (Big-O)", self.h))
        story.append(Paragraph(
            f"""
            The estimated time complexity of the program is:<br/><br/>
            <b>{big_o}</b><br/><br/>
            This estimate is derived heuristically from loop nesting
            and control flow structures in the Abstract Syntax Tree.
            """,
            self.body
        ))
        story.append(PageBreak())

        # AST
        story.append(Paragraph("5. Abstract Syntax Tree", self.h))
        if ast_png and os.path.exists(ast_png):
            story.append(Image(ast_png, width=500, height=350))
        else:
            story.append(Paragraph("AST not available.", self.body))

        doc.build(story)
        return path


def create_report(path, code, tokens, symbols, big_o, ast_png=None):
    return ReportGenerator().create(path, code, tokens, symbols, big_o, ast_png)
