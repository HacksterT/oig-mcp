# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx==1.2.0"]
# ///
"""Build the evaluation document DOCX from docs/submission/evaluation-document.md.

Needs pandoc on the PATH. From the repository root:
    uv run docs/submission/render/build_docx.py
Output: docs/submission/render/out/oig-mcp-evaluation-document.docx
"""

import re
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

HERE = Path(__file__).parent
REPO = HERE.parents[2]
SRC = REPO / "docs/submission/evaluation-document.md"
OUT = HERE / "out"
GH = "https://github.com/HacksterT/oig-mcp"

# Palette shared with the deck: evergreen ink, teal, amber.
INK = "14302E"
TEAL = "2A6F6A"
AMBER = "C98A1E"
TEXT = "26302F"
MUTED = "5F7371"
TINT = "EEF4F3"
RULE = "CFDAD8"

BODY_FONT = "Calibri"
HEAD_FONT = "Cambria"
CODE_FONT = "Consolas"


def rgb(h):
    return RGBColor.from_string(h)


# ---------- 1. Markdown preprocessing ----------


def github_link(rel, base):
    path, _, anchor = rel.partition("#")
    target = (base / path).resolve()
    repo_rel = target.relative_to(REPO).as_posix()
    kind = "tree" if target.is_dir() else "blob"
    url = f"{GH}/{kind}/main/{repo_rel}"
    return url + (f"#{anchor}" if anchor else "")


def preprocess(md):
    base = SRC.parent
    # Title block becomes pandoc metadata.
    md = md.replace("# Evaluation\n", "", 1)
    meta = (
        "---\n"
        'title: "Evaluating oig-mcp"\n'
        'subtitle: "An MCP server over VA Inspector General reports, '
        'tested with five models"\n'
        'author: "Troy Sybert, MD"\n'
        'date: "GSA MCP Server and AI Agent Government Hackathon · '
        'November 2026"\n'
        "---\n\n"
    )

    def fix(m):
        text, link = m.group(1), m.group(2)
        if link.startswith(("http", "mailto:", "#")):
            return m.group(0)
        return f"[{text}]({github_link(link, base)})"

    md = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", fix, md)

    # Figures the Markdown only describes.
    figs = [
        (
            "**The lesson:** a server that only meets the best model",
            "images/models-spread.png",
            "Same server, five models: 9 to 23 of 24 questions with the server, "
            "against 2 or 3 without it.",
        ),
        (
            "The form halved the round trips against asking in chat",
            "images/elicitation-savings.png",
            "What the facility form saves: five runs per arm, Claude Opus 5.5, "
            "one ambiguous facility name.",
        ),
        (
            "- **It confirms the main result with a judge",
            "images/phoenix-experiments.png",
            "Phoenix experiments on the gold dataset, "
            "with the five watsonx.ai evaluators across runs.",
        ),
    ]
    for anchor, img, cap in figs:
        i = md.find(anchor)
        assert i >= 0, anchor
        # A list item gets the figure before it; a paragraph, after it.
        if anchor.startswith("- "):
            md = md[:i] + f"![{cap}]({img}){{width=6.3in}}\n\n" + md[i:]
        else:
            j = md.find("\n\n", i)
            md = md[:j] + f"\n\n![{cap}]({img}){{width=6.3in}}" + md[j:]
    return meta + md


# ---------- 2. Reference document (styles) ----------


def set_font(style, name, size=None, color=None, bold=None, italic=None):
    f = style.font
    f.name = name
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), name)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rfonts.get(qn(a)) is not None:
            del rfonts.attrib[qn(a)]
    if size:
        f.size = Pt(size)
    if color:
        f.color.rgb = rgb(color)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic


def build_reference(path):
    subprocess.run(
        ["pandoc", "-o", str(path), "--print-default-data-file", "reference.docx"],
        check=True,
    )
    doc = Document(path)
    st = doc.styles

    def get(name, kind=WD_STYLE_TYPE.PARAGRAPH):
        try:
            return st[name]
        except KeyError:
            return st.add_style(name, kind)

    for name in ("Normal", "Body Text", "First Paragraph", "Compact"):
        s = get(name)
        set_font(s, BODY_FONT, 10.5, TEXT)
        pf = s.paragraph_format
        pf.space_after = Pt(6)
        pf.line_spacing = 1.12
    get("Compact").paragraph_format.space_after = Pt(2)

    t = get("Title")
    set_font(t, HEAD_FONT, 30, INK, bold=True)
    t.paragraph_format.space_before = Pt(20)
    t.paragraph_format.space_after = Pt(8)
    t.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    s = get("Subtitle")
    set_font(s, HEAD_FONT, 15, TEAL, bold=False, italic=True)
    s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    s.paragraph_format.space_after = Pt(10)
    for name in ("Author", "Date"):
        s = get(name)
        set_font(s, BODY_FONT, 11, MUTED)
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        s.paragraph_format.space_after = Pt(2)
    get("Date").paragraph_format.space_after = Pt(24)

    h1 = get("Heading 1")
    set_font(h1, HEAD_FONT, 19, INK, bold=True)
    h1.paragraph_format.space_before = Pt(26)
    h1.paragraph_format.space_after = Pt(8)
    h1.paragraph_format.page_break_before = True
    h1.paragraph_format.keep_with_next = True
    h2 = get("Heading 2")
    set_font(h2, HEAD_FONT, 13.5, TEAL, bold=True)
    h2.paragraph_format.space_before = Pt(16)
    h2.paragraph_format.space_after = Pt(4)
    h2.paragraph_format.keep_with_next = True
    h3 = get("Heading 3")
    set_font(h3, BODY_FONT, 11, AMBER, bold=True)
    h3.paragraph_format.space_before = Pt(10)
    h3.paragraph_format.keep_with_next = True

    for name in ("Source Code",):
        s = get(name)
        set_font(s, CODE_FONT, 8.5, INK)
    vs = get("Verbatim Char", WD_STYLE_TYPE.CHARACTER)
    set_font(vs, CODE_FONT, 9, TEAL)
    hl = get("Hyperlink", WD_STYLE_TYPE.CHARACTER)
    hl.font.color.rgb = rgb(TEAL)
    hl.font.underline = False
    cap = get("Image Caption")
    set_font(cap, BODY_FONT, 9, MUTED, italic=True)
    cap.paragraph_format.space_after = Pt(12)
    for name in ("Table Caption",):
        set_font(get(name), BODY_FONT, 9, MUTED, italic=True)
    doc.save(path)


# ---------- 3. Post-processing ----------


def shade(cell, fill):
    tcpr = cell._tc.get_or_add_tcPr()
    for old in tcpr.findall(qn("w:shd")):
        tcpr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def cell_margins(table, top=50, bottom=50, left=90, right=90):
    tblpr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    for old in tblpr.findall(qn("w:tblCellMar")):
        tblpr.remove(old)
    tblpr.append(mar)


def borders(table):
    tblpr = table._tbl.tblPr
    for old in tblpr.findall(qn("w:tblBorders")):
        tblpr.remove(old)
    b = OxmlElement("w:tblBorders")
    for side in ("top", "bottom", "insideH"):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), RULE)
        b.append(e)
    for side in ("left", "right", "insideV"):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "nil")
        b.append(e)
    tblpr.append(b)


def style_runs(cell, color=None, bold=None, size=9.5):
    for p in cell.paragraphs:
        p.paragraph_format.space_after = Pt(0)
        for r in p.runs:
            r.font.size = Pt(size)
            if color:
                r.font.color.rgb = rgb(color)
            if bold is not None:
                r.font.bold = bold


def postprocess(path):
    doc = Document(path)
    for i, table in enumerate(doc.tables):
        rows = table.rows
        for row in rows:
            trpr = row._tr.get_or_add_trPr()
            trpr.append(OxmlElement("w:cantSplit"))
        header_empty = all(not c.text.strip() for c in rows[0].cells)
        if i == 0 or header_empty:
            # Key-value summary table: no header row, tint the key column.
            if header_empty:
                table._tbl.remove(rows[0]._tr)
            widths = (2600, 6760)  # twips: key column narrow
            grid = table._tbl.tblGrid
            for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
                gc.set(qn("w:w"), str(w))
            for row in table.rows:
                for c, w in zip(row.cells, widths):
                    tcpr = c._tc.get_or_add_tcPr()
                    for old in tcpr.findall(qn("w:tcW")):
                        tcpr.remove(old)
                    tcw = OxmlElement("w:tcW")
                    tcw.set(qn("w:w"), str(w))
                    tcw.set(qn("w:type"), "dxa")
                    tcpr.insert(0, tcw)
            for row in table.rows:
                k, v = row.cells[0], row.cells[-1]
                shade(k, TINT)
                style_runs(k, INK, True, 9.5)
                style_runs(v, TEXT, None, 9.5)
        else:
            rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
            for c in rows[0].cells:
                shade(c, INK)
                style_runs(c, "FFFFFF", True, 9.5)
            for n, row in enumerate(list(table.rows)[1:]):
                for c in row.cells:
                    if n % 2 == 1:
                        shade(c, "F6F9F8")
                    style_runs(c, None, None, 9.5)
        borders(table)
        cell_margins(table)

    # Kicker above the title.
    title = next(p for p in doc.paragraphs if p.style.name == "Title")
    kicker = title.insert_paragraph_before()
    run = kicker.add_run("EVALUATION DOCUMENTATION  ·  DATASET ACCESS TRACK")
    run.font.size = Pt(9.5)
    run.font.bold = True
    run.font.color.rgb = rgb(AMBER)
    rpr = run._r.get_or_add_rPr()
    sp = OxmlElement("w:spacing")
    sp.set(qn("w:val"), "40")
    rpr.append(sp)
    kicker.paragraph_format.space_before = Pt(36)

    # The summary stays on page 1; Heading 1 starts each numbered section on a new page.

    # Footer: project and page number.
    for section in doc.sections:
        section.page_width, section.page_height = Pt(612), Pt(792)
        section.left_margin = section.right_margin = Pt(72)
        section.top_margin = Pt(64)
        section.bottom_margin = Pt(64)
        footer = section.footer
        p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p.text = ""
        r = p.add_run("oig-mcp  ·  Evaluation  ·  github.com/HacksterT/oig-mcp")
        r.font.size = Pt(8.5)
        r.font.color.rgb = rgb(MUTED)
        p.add_run("\t")
        fld_r = p.add_run()
        field = (("w:fldChar", "begin"), ("w:instrText", None), ("w:fldChar", "end"))
        for tag, attr in field:
            e = OxmlElement(tag)
            if attr:
                e.set(qn("w:fldCharType"), attr)
            else:
                e.set(qn("xml:space"), "preserve")
                e.text = " PAGE "
            fld_r._r.append(e)
        fld_r.font.size = Pt(8.5)
        fld_r.font.color.rgb = rgb(MUTED)
        # Right tab at the text width.
        ppr = p._p.get_or_add_pPr()
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "right")
        text_width = section.page_width - section.left_margin - section.right_margin
        tab.set(qn("w:pos"), str(int(text_width / 635)))  # EMU to twips
        tabs.append(tab)
        ppr.append(tabs)

    doc.core_properties.title = "Evaluating oig-mcp"
    doc.core_properties.author = "Troy Sybert"
    doc.core_properties.subject = (
        "GSA MCP Server and AI Agent Government Hackathon: evaluation documentation"
    )
    doc.save(path)


def main():
    OUT.mkdir(exist_ok=True)
    md = preprocess(SRC.read_text())
    tmp_md = OUT / "evaluation-document.pre.md"
    tmp_md.write_text(md)
    ref = OUT / "reference.docx"
    build_reference(ref)
    out = OUT / "oig-mcp-evaluation-document.docx"
    subprocess.run(
        [
            "pandoc",
            str(tmp_md),
            "-o",
            str(out),
            "--from",
            "markdown+pipe_tables+link_attributes+implicit_figures",
            "--reference-doc",
            str(ref),
            "--resource-path",
            str(SRC.parent),
            "--syntax-highlighting=none",
            "--shift-heading-level-by=-1",
        ],
        check=True,
    )
    postprocess(out)
    print(out)


if __name__ == "__main__":
    main()
