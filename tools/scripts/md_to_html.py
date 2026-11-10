"""Regenerate docs/*.html from docs/*.md (the .md files are the source of truth).

Usage: python tools/scripts/md_to_html.py
"""
import html
import pathlib
import re

DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"
FILES = ["requirements", "architecture", "features"]

CSS = """
:root{--bg:#fff;--fg:#1c1f23;--muted:#5b6470;--line:#dde1e6;--code:#f3f5f7;--accent:#0b6e8a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#15181c;--fg:#e6e8eb;--muted:#9aa3ad;--line:#2c3238;--code:#1e2328;--accent:#5cc3df}}
:root[data-theme="dark"]{--bg:#15181c;--fg:#e6e8eb;--muted:#9aa3ad;--line:#2c3238;--code:#1e2328;--accent:#5cc3df}
body{background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,system-ui,sans-serif;margin:0;padding:24px 16px}
main{max-width:860px;margin:0 auto}h1,h2{line-height:1.25}h2{border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:2em}
a{color:var(--accent)}code,pre{background:var(--code);border-radius:4px;font-size:.9em}code{padding:1px 4px}
pre{padding:12px;overflow-x:auto}table{border-collapse:collapse;width:100%;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}blockquote{border-left:3px solid var(--accent);margin:0;padding-left:12px;color:var(--muted)}
"""


def inline(text: str) -> str:
    t = html.escape(text)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def convert(md: str) -> tuple[str, str]:
    out, title, lines, i = [], "", md.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
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
                items.append(f"<li>{inline(lines[i][2:])}</li>")
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
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
        elif line.startswith("> "):
            out.append(f"<blockquote>{inline(line[2:])}</blockquote>")
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
        i += 1
    return title, "\n".join(out)


def main() -> None:
    for name in FILES:
        src = DOCS / f"{name}.md"
        if not src.exists():
            continue
        title, body = convert(src.read_text())
        page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width=device-width,initial-scale=1">'
                f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
                f"<body><main>{body}</main></body></html>\n")
        (DOCS / f"{name}.html").write_text(page)
        print(f"wrote docs/{name}.html")


if __name__ == "__main__":
    main()
