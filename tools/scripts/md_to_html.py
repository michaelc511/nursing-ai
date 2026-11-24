"""Regenerate docs/*.html from docs/*.md (the .md files are the source of truth).

Usage: python tools/scripts/md_to_html.py
"""
import html
import pathlib
import re

DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"
FILES = ["requirements", "architecture", "features", "governance", "production-ops", "demo/4-demo-script", "demo/1-short_script", "demo/2-talk-notes", "blog/blog", "blog/nurseops-now-evals", "blog/war-stories", "blog/war-stories-platform", "eval-qa-plan"]

CSS = """
:root{--bg:#fff;--fg:#1c1f23;--muted:#5b6470;--line:#dde1e6;--code:#f3f5f7;--accent:#0b6e8a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#15181c;--fg:#e6e8eb;--muted:#9aa3ad;--line:#2c3238;--code:#1e2328;--accent:#5cc3df}}
:root[data-theme="dark"]{--bg:#15181c;--fg:#e6e8eb;--muted:#9aa3ad;--line:#2c3238;--code:#1e2328;--accent:#5cc3df}
body{background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,system-ui,sans-serif;margin:0;padding:24px 16px}
main{max-width:860px;margin:0 auto}h1,h2{line-height:1.25}h2{border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:2em}
a{color:var(--accent)}code,pre{background:var(--code);border-radius:4px;font-size:.9em}code{padding:1px 4px}
pre{padding:12px;overflow-x:auto}table{border-collapse:collapse;width:100%;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;display:block;margin:8px 0}blockquote{border-left:3px solid var(--accent);margin:0;padding-left:12px;color:var(--muted)}
:root{--hl-bg:#fff6c2;--hl-line:#e3c400}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--hl-bg:#3d3508;--hl-line:#b39a00}}
:root[data-theme="dark"]{--hl-bg:#3d3508;--hl-line:#b39a00}
.hl{background:var(--hl-bg);border:2px solid var(--hl-line);border-radius:8px;padding:4px 16px 12px;margin:16px 0}
.hl pre,.hl code{background:rgba(255,255,255,.55)}.hl h2{margin-top:.6em}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .hl pre,:root:not([data-theme="light"]) .hl code{background:rgba(0,0,0,.35)}}
:root[data-theme="dark"] .hl pre,:root[data-theme="dark"] .hl code{background:rgba(0,0,0,.35)}
"""

# features page only: green = Y, yellow = To Do, red = N/A
STATUS_CSS = """
:root{--y-bg:#d6f3df;--y-fg:#125c2c;--todo-bg:#fff0b3;--todo-fg:#634b00;--na-bg:#fddcd9;--na-fg:#951b1b}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--y-bg:#14432a;--y-fg:#8fe8ad;--todo-bg:#4a3a08;--todo-fg:#f7d96b;--na-bg:#521d1d;--na-fg:#ffb0aa}}
:root[data-theme="dark"]{--y-bg:#14432a;--y-fg:#8fe8ad;--todo-bg:#4a3a08;--todo-fg:#f7d96b;--na-bg:#521d1d;--na-fg:#ffb0aa}
.st{border-radius:4px;padding:1px 7px;font-weight:600;font-size:.9em}
.st-y{background:var(--y-bg);color:var(--y-fg)}.st-todo{background:var(--todo-bg);color:var(--todo-fg)}.st-na{background:var(--na-bg);color:var(--na-fg)}
"""
STATUS = re.compile(r"^(.*?: )(Y|To Do When LLM is ready|N/A - Optional)(?=$| )(.*)$")
STATUS_CLASS = {"Y": "st-y", "To Do When LLM is ready": "st-todo", "N/A - Optional": "st-na"}


def inline(text: str) -> str:
    t = html.escape(text)
    t = re.sub(r"\{#([a-z0-9-]+)\}", r'<span id="\1"></span>', t)  # {#id}: an anchor inside a table cell or line
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<em>\1</em>", t)
    t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1" loading="lazy">', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def status_item(text: str) -> str:
    """A features.md line: color its status word."""
    m = STATUS.match(text)
    if not m:
        return inline(text)
    return f'{inline(m[1])}<span class="st {STATUS_CLASS[m[2]]}">{html.escape(m[2])}</span>{inline(m[3])}'


def convert(md: str, bullet=inline) -> tuple[str, str]:
    out, title, lines, i = [], "", md.splitlines(), 0
    # Heading anchors: a repeated heading name gets its parent section's anchor as a prefix.
    slugify = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    counts: dict[str, int] = {}
    for ln in lines:
        if h := re.match(r"^#{1,3} (.*)", ln):
            counts[slugify(h.group(1))] = counts.get(slugify(h.group(1)), 0) + 1
    parent = ""
    while i < len(lines):
        line = lines[i]
        if line.strip() == ":::html":                     # ":::html" ... ":::" = raw HTML, passed through as is
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                out.append(lines[i])
                i += 1
        elif line.startswith(":::"):                     # ":::highlight" ... ":::" = yellow box
            out.append('<div class="hl">' if line.strip() == ":::highlight" else "</div>")
        elif line.startswith("```"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(html.escape(lines[i]))
                i += 1
            out.append("<pre>" + "\n".join(block) + "</pre>")
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            i -= 1
            head = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
            out.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{bullet(lines[i][2:])}</li>")
                i += 1
            i -= 1
            out.append("<ul>" + "".join(items) + "</ul>")
        elif re.match(r"^\d+\. ", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\. ", lines[i]):
                text = re.sub(r"^\d+\. ", "", lines[i])
                items.append(f"<li>{inline(text)}</li>")
                i += 1
            i -= 1
            out.append("<ol>" + "".join(items) + "</ol>")
        elif m := re.match(r"^(#{1,3}) (.*)", line):
            level = len(m.group(1))
            title = title or m.group(2)
            slug = slugify(m.group(2))
            if level <= 2:
                parent = slug
            elif counts.get(slug, 0) > 1 and parent:
                slug = f"{parent}--{slug}"
            out.append(f'<h{level} id="{slug}">{inline(m.group(2))}</h{level}>')
        elif line.startswith("> "):
            out.append(f"<blockquote>{inline(line[2:])}</blockquote>")
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
        i += 1
    return title, "\n".join(out)


def page(title: str, body: str, css: str = CSS, head: str = "", tail: str = "") -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(title)}</title>{head}<style>{css}</style></head>"
            f"<body><main>{body}</main>{tail}</body></html>\n")


TERM_FILES = {"blog/nurseops-now-evals", "blog/war-stories", "blog/war-stories-platform"}  # pages with hover definitions + ?defs=1 (tools/scripts/blog_terms.py)
NAV_FILES = {"demo/4-demo-script", "demo/1-short_script", "blog/blog"}  # pages that get a contents list + "Top" links
NAV_CSS = """
#top{scroll-margin-top:0}h2,h3{scroll-margin-top:12px}
.toc{border:1px solid var(--line);border-radius:6px;padding:8px 16px;margin:12px 0}
.toc ul{margin:4px 0;padding-left:20px}.toc li{margin:2px 0}.toc .sub{padding-left:16px;font-size:.95em}
.top{font-size:.8em;font-weight:400;margin-left:8px;text-decoration:none}
"""


def add_nav(body: str) -> str:
    """Contents list after the first heading's intro, and a 'Top' link on every h2/h3."""
    heads = re.findall(r'<h([23]) id="([^"]+)">(.*?)</h\1>', body)
    sub = ' class="sub"'
    items = "".join(f'<li{sub if lvl == "3" else ""}><a href="#{sid}">{text}</a></li>'
                    for lvl, sid, text in heads)
    toc = f'<nav class="toc" aria-label="Contents"><b>Contents</b><ul>{items}</ul></nav>'
    body = re.sub(r'(<h([23]) id="[^"]+">.*?)(</h\2>)', r'\1<a class="top" href="#top">↑ Top</a>\3', body)
    first_h2 = min((i for i in (body.find("<h2 "), body.find('<div class="hl">')) if i >= 0), default=-1)
    return '<a id="top"></a>' + (body[:first_h2] + toc + body[first_h2:] if first_h2 >= 0 else toc + body)


def build_retros() -> None:
    """All retros on one page, newest first (file names start with YYYY-MM-DD-HHMM)."""
    files = sorted((DOCS / "retro").glob("*.md"), key=lambda f: f.name, reverse=True)
    if not files:
        return
    body = "\n<hr>\n".join(convert(f.read_text())[1] for f in files)
    (DOCS / "retros.html").write_text(page("Project retros", "<h1>Project retros</h1>\n" + body))
    print(f"wrote docs/retros.html ({len(files)} retro(s))")


def main() -> None:
    for name in FILES:
        src = DOCS / f"{name}.md"
        if not src.exists():
            continue
        features = name == "features"
        title, body = convert(src.read_text(), status_item if features else inline)
        css = CSS + STATUS_CSS if features else CSS
        head = tail = ""
        if name in TERM_FILES:
            import blog_terms
            body, css, head, tail = blog_terms.apply(body, css)
        if name in NAV_FILES:
            body, css = add_nav(body), css + NAV_CSS
        (DOCS / f"{name}.html").write_text(page(title, body, css, head, tail))
        print(f"wrote docs/{name}.html")
    build_retros()


if __name__ == "__main__":
    main()
