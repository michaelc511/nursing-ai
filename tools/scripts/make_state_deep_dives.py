"""Build the 27 state-management solution deep dives from state_solutions.py.

For each solution: RUN its ServiceApps sketch (made-up data) to capture real output, write
docs/blog/deep-dives/state-NN-<slug>.md, build all pages with the blog kit, then link each one from its
yellow book row in docs/blog/nurseops-now-state.md (Deep dive column) and rebuild that page.

Usage (from the repo root):  python3 tools/scripts/make_state_deep_dives.py
Needs backend/venv (pydantic) for the sketches.
"""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BLOG = ROOT / "docs" / "blog"
OUT = BLOG / "deep-dives"
PARENT = BLOG / "nurseops-now-state.md"
KIT = pathlib.Path("/Users/mike/projects/claude-config/blog-format/kit/build_blog.py")
PY = ROOT / "backend" / "venv" / "bin" / "python"
DATE = "Nov 19, 2026"

sys.path.insert(0, str(HERE))
from state_solutions import SCENARIO, SECTIONS, SOLUTIONS  # noqa: E402


def fname(i: int, s: dict) -> str:
    return f"state-{i:02d}-{s['slug']}"


def run_sketch(code: str) -> str:
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "sketch.py"
        f.write_text(code.strip() + "\n")
        r = subprocess.run([str(PY), "-I", str(f)], capture_output=True, text=True, timeout=60, cwd=d)
    if r.returncode != 0:
        raise SystemExit(f"sketch failed:\n{r.stderr}")
    return r.stdout.rstrip()


def page(i: int, s: dict, output: str) -> str:
    n = len(SOLUTIONS)
    sec_title, sec_anchor = SECTIONS[s["sec"]]
    prev = f"[← {SOLUTIONS[i - 2]['title']}]({fname(i - 1, SOLUTIONS[i - 2])}.html)" if i > 1 else ""
    nxt = f"[{SOLUTIONS[i]['title']} →]({fname(i + 1, SOLUTIONS[i])}.html)" if i < n else ""
    nav = " · ".join(x for x in (prev, nxt) if x)
    steps = "\n".join(f"{k}. {t}" for k, t in enumerate(s["steps"], 1))
    watch = "\n".join(f"- {w}" for w in s["watch"])
    trade = "\n".join(f"- {t}" for t in s["tradeoffs"])
    return f"""# Deep dive {i} of {n}: {s['title']}

{DATE} · Michael Chang · Status in NurseOps Now: {s['status']}

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [{sec_title}](../nurseops-now-state.html#{sec_anchor}) · [All {n} solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · {nav}

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the book's problem, and its idea in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

{s['plain']}

**In plain terms:** {s['plain_terms']}

## The problem it solves

{s['problem']}

**What the book proposes** (in my words): {s['book']}

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on {DATE}, and the output below is from that run._

**The setting.** {SCENARIO}

**The scenario.** {s['scenario']}

**Steps.**

{steps}

**The code** (Python):

```python
{s['code'].strip()}
```

**Output** (from running the code above):

```
{output}
```

**What to watch for.**

{watch}

**In plain terms:** {s['sa_plain']}
:::

## In NurseOps Now

{s['nurseops']}

## Trade-offs

{trade}

## Interview answer

"{s['interview']}"

All data in this post is made up. No real people, tickets or patient data.

[← Back to all {n} solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
"""


def link_parent() -> int:
    md = PARENT.read_text()
    a = md.index("## How a chat turn flows")
    b = md.index("**About the examples below:**", a)
    lines = md[a:b].split("\n")
    linked = 0
    for k, line in enumerate(lines):
        if not line.startswith("| ") or "|---" in line:
            continue
        cells = line.split(" | ")
        if line.startswith("| **"):
            hit = [(i, s) for i, s in enumerate(SOLUTIONS, 1) if line.startswith(f"| **{s['title']}**")]
            if hit and cells[-1].strip() in ("To come |", "To come"):
                i, s = hit[0]
                cells[-1] = f"[Deep dive](deep-dives/{fname(i, s)}.html) |"
                linked += 1
        elif "_(ours)_" in line and cells[-1].strip() in ("To come |", "To come"):
            cells[-1] = "— |"
        lines[k] = " | ".join(cells)
    PARENT.write_text(md[:a] + "\n".join(lines) + md[b:])
    return linked


def main() -> None:
    assert len(SOLUTIONS) == 27, len(SOLUTIONS)
    parent = PARENT.read_text()
    missing = [s["title"] for s in SOLUTIONS if f"| **{s['title']}**" not in parent]
    assert not missing, f"titles not in the parent's flow tables: {missing}"
    files = []
    for i, s in enumerate(SOLUTIONS, 1):
        out = run_sketch(s["code"])
        p = OUT / f"{fname(i, s)}.md"
        p.write_text(page(i, s, out))
        files.append(str(p))
        print(f"{i:2d} {s['title'][:60]:60s} sketch ok ({len(out.splitlines())} lines)")
    n = link_parent()
    print("parent rows linked:", n)
    subprocess.run([sys.executable, str(KIT), *files, str(PARENT), "--terms", str(BLOG / "terms.py")], check=True,
                   stdout=subprocess.DEVNULL)
    print("built", len(files), "deep dives + parent")


if __name__ == "__main__":
    main()
