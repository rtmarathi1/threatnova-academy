"""
Minimal Markdown-to-HTML renderer (stdlib only).

Supports the subset needed for lesson content: headings (##, ###),
bold (**text**), inline code (`code`), fenced code blocks (```),
unordered lists (-), and paragraphs. Output is escaped for safety.
"""
from __future__ import annotations

import re
import html as _html


def _inline(text: str) -> str:
    text = _html.escape(text, quote=False)
    # inline code
    text = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", text)
    # bold
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: f"<strong>{m.group(1)}</strong>", text)
    return text


def render(md: str) -> str:
    if not md:
        return ""
    lines = md.replace("\r\n", "\n").split("\n")
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # fenced code block
        if line.strip().startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(_html.escape(lines[i], quote=False))
                i += 1
            i += 1  # skip closing fence
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
            continue

        # headings
        if line.startswith("### "):
            out.append(f"<h3>{_inline(line[4:])}</h3>")
            i += 1
            continue
        if line.startswith("## "):
            out.append(f"<h2>{_inline(line[3:])}</h2>")
            i += 1
            continue

        # unordered list
        if re.match(r"^\s*-\s+", line):
            items = []
            while i < n and re.match(r"^\s*-\s+", lines[i]):
                items.append(f"<li>{_inline(re.sub(r'^\\s*-\\s+', '', lines[i]))}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # blank line
        if line.strip() == "":
            i += 1
            continue

        # paragraph (accumulate consecutive non-special lines)
        buf = [line]
        i += 1
        while i < n and lines[i].strip() != "" and not lines[i].startswith(("#", "-", "```")):
            buf.append(lines[i])
            i += 1
        out.append(f"<p>{_inline(' '.join(buf))}</p>")

    return "\n".join(out)
