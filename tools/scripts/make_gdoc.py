"""Build docs/demo/3-nurseops-now-talk-gdocs.html: a white, link-free copy of the talk for Google Docs.

Part 1 = docs/blog/blog.md (intro), Part 2 = the yellow core demo from docs/demo/1-short_script.md,
Part 3 = its #7 Close. Images are embedded (data URIs) and styles are inline, so the file can be
uploaded to Google Drive and opened with Google Docs, or opened in a browser and copy-pasted.

Usage: python tools/scripts/make_gdoc.py
"""
import base64
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from md_to_html import DOCS, convert  # noqa: E402

OUT = DOCS / "demo" / "3-nurseops-now-talk-gdocs.html"


def section(md: str, start: str, end: str | None) -> str:
    a = md.index(start)
    b = md.index(end, a + len(start)) if end else len(md)
    return md[a:b]


def build_md() -> str:
    blog = (DOCS / "blog" / "blog.md").read_text()
    short = (DOCS / "demo" / "1-short_script.md").read_text()
    intro = blog.split("\n", 1)[1]                                    # drop the blog's own title
    intro = re.sub(r"^How the app works.*\n", "", intro, count=1, flags=re.M)  # its links line
    core = section(short, ":::highlight", "\n:::\n") + "\n:::\n"
    close = section(short, "## #7 Close", None).replace("## #7 Close", "## Part 3: Close", 1)
    return ("# NurseOps Now: AI for Faster Prior Authorization\n\n"
            "Intro from the plain-terms blog, then the core demo (yellow), then the close. "
            "Live site: https://nurseops-now.fly.dev\n\n"
            "## Part 1: Intro\n" + intro + "\n## Part 2: Core demo\n\n" + core + "\n" + close)


def strip_links(html: str) -> str:
    html = re.sub(r'<a href="(?!https?://)[^"]*">(.*?)</a>', r"\1", html)     # internal links -> text
    html = re.sub(r'<a href="(https?://[^"]+)">(.*?)</a>', r"\2 (\1)", html)  # external -> text + URL
    html = re.sub(r'<a class="top"[^>]*>.*?</a>', "", html)
    return re.sub(r' id="[^"]*"', "", html)                                   # no anchors


def embed_images(html: str) -> str:
    def data_uri(m):
        p = (DOCS / "demo" / m.group(1)).resolve()  # "demo-images/.." and "../demo/demo-images/.."
        b64 = base64.b64encode(p.read_bytes()).decode()
        return f'<img src="data:image/png;base64,{b64}" alt="{m.group(2)}" style="max-width:100%;width:620px;border:1px solid #dde1e6">'
    return re.sub(r'<img src="([^"]+)" alt="([^"]*)" loading="lazy">', data_uri, html)


def inline_styles(html: str) -> str:
    """Google Docs keeps inline styles, not stylesheet classes."""
    rules = {
        "<table>": '<table style="border-collapse:collapse;width:100%">',
        "<th>": '<th style="border:1px solid #c9ced4;padding:6px 8px;background:#f3f5f7;text-align:left">',
        "<td>": '<td style="border:1px solid #c9ced4;padding:6px 8px;vertical-align:top">',
        "<pre>": '<pre style="background:#f3f5f7;padding:10px;font-family:Menlo,Consolas,monospace;font-size:12px;white-space:pre-wrap">',
        "<blockquote>": '<blockquote style="border-left:3px solid #0b6e8a;margin:6px 0;padding-left:12px;color:#3d444d">',
        "<code>": '<code style="font-family:Menlo,Consolas,monospace;background:#f3f5f7">',
    }
    for k, v in rules.items():
        html = html.replace(k, v)
    # Yellow box: a one-cell table, which Google Docs keeps with its background color.
    html = html.replace('<div class="hl">',
                        '<table style="border-collapse:collapse;width:100%"><tr>'
                        '<td style="background:#fff6c2;border:2px solid #e3c400;padding:10px 16px">')
    return html.replace("</div>", "</td></tr></table>")


def main() -> None:
    title, body = convert(build_md())
    body = inline_styles(embed_images(strip_links(body)))
    OUT.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{title}</title></head>"
        '<body style="background:#ffffff;color:#1c1f23;font-family:Arial,Helvetica,sans-serif;'
        'font-size:11pt;line-height:1.5;max-width:860px;margin:24px auto;padding:0 16px">'
        f"{body}</body></html>\n")
    print(f"wrote {OUT.relative_to(DOCS.parent)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
