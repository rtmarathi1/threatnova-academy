"""
Server-side HTML rendering: shared layout, navigation, and UI components.

Styling uses Tailwind CSS via CDN (loaded by the visitor's browser) plus a
small custom theme. No build step required.
"""
from __future__ import annotations

import html as _html
from urllib.parse import quote


def esc(value) -> str:
    return _html.escape("" if value is None else str(value), quote=True)


BADGE_COLORS = {
    "Beginner": "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
    "Intermediate": "bg-amber-500/15 text-amber-300 ring-amber-500/30",
    "Advanced": "bg-rose-500/15 text-rose-300 ring-rose-500/30",
    "STUDENT": "bg-sky-500/15 text-sky-300 ring-sky-500/30",
    "INSTRUCTOR": "bg-violet-500/15 text-violet-300 ring-violet-500/30",
    "ADMIN": "bg-cyan-500/15 text-cyan-300 ring-cyan-500/30",
}


def badge(text, kind=None):
    cls = BADGE_COLORS.get(kind or text, "bg-slate-500/15 text-slate-300 ring-slate-500/30")
    return (f'<span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs '
            f'font-medium ring-1 ring-inset {cls}">{esc(text)}</span>')


def progress_bar(pct):
    pct = max(0, min(100, int(pct)))
    return f'''<div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
      <div class="bg-gradient-to-r from-cyan-400 to-emerald-400 h-2 rounded-full transition-all"
           style="width:{pct}%"></div>
    </div>'''


def flash(req):
    out = []
    msg = req.query.get("msg")
    err = req.query.get("err")
    if msg:
        out.append(f'''<div class="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10
             px-4 py-3 text-sm text-emerald-200">{esc(msg)}</div>''')
    if err:
        out.append(f'''<div class="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/10
             px-4 py-3 text-sm text-rose-200">{esc(err)}</div>''')
    return "".join(out)


def _nav(req):
    user = req.user
    links = []
    if user:
        links.append(('/dashboard', 'Dashboard'))
        links.append(('/courses', 'Courses'))
        links.append(('/labs', 'Labs'))
        links.append(('/certificates', 'My Certificates'))
        if user["role"] in ("INSTRUCTOR", "ADMIN"):
            links.append(('/admin', 'Admin'))
    else:
        links.append(('/courses', 'Courses'))
        links.append(('/verify', 'Verify Certificate'))

    link_html = "".join(
        f'<a href="{href}" class="text-sm text-slate-300 hover:text-white transition">{esc(label)}</a>'
        for href, label in links
    )

    if user:
        right = f'''
          <div class="flex items-center gap-3">
            <span class="hidden sm:inline text-xs text-slate-400">{esc(user["name"])}</span>
            {badge(user["role"], user["role"])}
            <a href="/logout" class="text-sm rounded-lg bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-slate-200">Log out</a>
          </div>'''
    else:
        right = '''
          <div class="flex items-center gap-2">
            <a href="/login" class="text-sm text-slate-300 hover:text-white px-3 py-1.5">Log in</a>
            <a href="/register" class="text-sm rounded-lg bg-cyan-500 hover:bg-cyan-400 px-3 py-1.5 font-medium text-slate-900">Get started</a>
          </div>'''

    return f'''
    <header class="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
      <nav class="mx-auto max-w-7xl px-4 sm:px-6 h-16 flex items-center justify-between">
        <a href="/" class="flex items-center gap-2 font-semibold text-white">
          <span class="text-xl">🛡️</span>
          <span>ThreatNova <span class="text-cyan-400">CyberLabs</span></span>
        </a>
        <div class="hidden md:flex items-center gap-6">{link_html}</div>
        {right}
      </nav>
    </header>'''


def layout(title, body, req=None, full_width=False):
    nav = _nav(req) if req is not None else ""
    container = "max-w-full" if full_width else "max-w-7xl"
    return f'''<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} · ThreatNova CyberLabs</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{ theme: {{ extend: {{
      fontFamily: {{ sans: ['Inter','ui-sans-serif','system-ui','sans-serif'],
                     mono: ['JetBrains Mono','ui-monospace','monospace'] }}
    }}}}}}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Inter', system-ui, sans-serif; }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
    .grid-glow {{ background-image: radial-gradient(circle at 30% 10%, rgba(34,211,238,0.10), transparent 40%),
                                     radial-gradient(circle at 80% 0%, rgba(16,185,129,0.08), transparent 35%); }}
    .prose-tn h2 {{ font-size:1.25rem; font-weight:700; color:#f1f5f9; margin:1.4rem 0 .6rem; }}
    .prose-tn h3 {{ font-size:1.05rem; font-weight:600; color:#e2e8f0; margin:1.1rem 0 .5rem; }}
    .prose-tn p  {{ color:#cbd5e1; line-height:1.7; margin:.6rem 0; }}
    .prose-tn ul {{ list-style:disc; margin:.6rem 0 .6rem 1.4rem; color:#cbd5e1; }}
    .prose-tn li {{ margin:.25rem 0; }}
    .prose-tn code {{ background:#1e293b; color:#67e8f9; padding:.1rem .35rem; border-radius:.3rem; font-family:'JetBrains Mono',monospace; font-size:.85em; }}
    .prose-tn pre {{ background:#0b1220; border:1px solid #1e293b; border-radius:.6rem; padding:1rem; overflow-x:auto; margin:.8rem 0; }}
    .prose-tn pre code {{ background:none; color:#e2e8f0; padding:0; }}
    .prose-tn strong {{ color:#f1f5f9; }}
    @media print {{
      header, footer, .no-print {{ display: none !important; }}
      body {{ background: #fff !important; }}
      main {{ padding: 0 !important; max-width: none !important; }}
      #cert {{ box-shadow: none !important; border-color: #94a3b8 !important; }}
    }}
  </style>
</head>
<body class="h-full bg-slate-950 text-slate-200 grid-glow">
  {nav}
  <main class="mx-auto {container} px-4 sm:px-6 py-8">{body}</main>
  <footer class="border-t border-slate-800/80 mt-16">
    <div class="mx-auto max-w-7xl px-4 sm:px-6 py-8 text-sm text-slate-500 flex flex-col sm:flex-row justify-between gap-2">
      <span>© ThreatNova Security · CyberLabs Training Platform</span>
      <span>Built for hands-on cybersecurity certification</span>
    </div>
  </footer>
</body>
</html>'''


def page_header(title, subtitle=None, actions=""):
    sub = f'<p class="mt-1 text-slate-400">{esc(subtitle)}</p>' if subtitle else ""
    return f'''
    <div class="flex flex-wrap items-end justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-white">{esc(title)}</h1>
        {sub}
      </div>
      <div class="flex items-center gap-2">{actions}</div>
    </div>'''


def card(inner, extra=""):
    return f'''<div class="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 {extra}">{inner}</div>'''
