"""Public pages: landing page, public course catalog, and certificate verification."""
from __future__ import annotations

from . import app
from .. import db
from ..server import html, redirect
from ..services import verify_certificate
from ..templates import layout, esc, badge, card, page_header


@app.get("/")
def landing(req):
    if req.user:
        return redirect("/dashboard")

    courses = db.query(
        "SELECT * FROM courses WHERE published = 1 ORDER BY id LIMIT 6"
    )
    stats = {
        "courses": db.query_one("SELECT COUNT(*) c FROM courses WHERE published=1")["c"],
        "labs": db.query_one("SELECT COUNT(*) c FROM labs")["c"],
        "certs": db.query_one("SELECT COUNT(*) c FROM certificates WHERE revoked=0")["c"],
        "students": db.query_one("SELECT COUNT(*) c FROM users WHERE role='STUDENT'")["c"],
    }

    course_cards = "".join(
        card(f'''
          <div class="flex items-start justify-between">
            <div class="text-3xl">{esc(c["icon"])}</div>
            {badge(c["difficulty"], c["difficulty"])}
          </div>
          <h3 class="mt-3 font-semibold text-white">{esc(c["title"])}</h3>
          <p class="mt-1 text-sm text-slate-400 line-clamp-3">{esc(c["summary"])}</p>
          <div class="mt-4 flex items-center gap-3 text-xs text-slate-500">
            <span>📚 {esc(c["category"])}</span><span>⏱ {c["duration_hours"]}h</span>
          </div>
          <a href="/courses/{esc(c["slug"])}" class="mt-4 inline-block text-sm font-medium text-cyan-400 hover:text-cyan-300">Explore course →</a>
        ''', extra="hover:border-cyan-500/40 transition")
        for c in courses
    )

    feature = lambda icon, t, d: f'''
      <div class="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <div class="text-2xl">{icon}</div>
        <h3 class="mt-2 font-semibold text-white">{t}</h3>
        <p class="mt-1 text-sm text-slate-400">{d}</p>
      </div>'''

    body = f'''
    <section class="py-12 sm:py-20 text-center">
      <div class="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs text-cyan-300">
        <span class="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
        ThreatNova Security · Training & Certification
      </div>
      <h1 class="mt-6 text-4xl sm:text-6xl font-extrabold tracking-tight text-white">
        Master cybersecurity through <span class="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400">hands-on labs</span>
      </h1>
      <p class="mx-auto mt-5 max-w-2xl text-lg text-slate-400">
        Learn offensive and defensive security in a safe, guided environment. Complete real challenges,
        capture flags, and earn verifiable ThreatNova certifications.
      </p>
      <div class="mt-8 flex items-center justify-center gap-3">
        <a href="/register" class="rounded-xl bg-cyan-500 hover:bg-cyan-400 px-6 py-3 font-semibold text-slate-900">Start training free</a>
        <a href="/courses" class="rounded-xl border border-slate-700 hover:border-slate-500 px-6 py-3 font-semibold text-slate-200">Browse courses</a>
      </div>
      <div class="mt-14 grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl mx-auto">
        <div><div class="text-3xl font-bold text-white">{stats["courses"]}</div><div class="text-xs text-slate-500 mt-1">Courses</div></div>
        <div><div class="text-3xl font-bold text-white">{stats["labs"]}</div><div class="text-xs text-slate-500 mt-1">Hands-on labs</div></div>
        <div><div class="text-3xl font-bold text-white">{stats["students"]}</div><div class="text-xs text-slate-500 mt-1">Students</div></div>
        <div><div class="text-3xl font-bold text-white">{stats["certs"]}</div><div class="text-xs text-slate-500 mt-1">Certificates issued</div></div>
      </div>
    </section>

    <section class="py-8">
      <div class="grid sm:grid-cols-3 gap-4">
        {feature("🎯", "Real-world labs", "Capture-the-flag style challenges built from actual attack and defense scenarios.")}
        {feature("📈", "Track your progress", "Every lesson and lab is scored. Watch your mastery grow across each track.")}
        {feature("🏅", "Verifiable certificates", "Earn a unique certificate ID that anyone can verify on our public portal.")}
      </div>
    </section>

    <section class="py-10">
      {page_header("Featured certification tracks", "Start with fundamentals or dive into specialized paths.")}
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">{course_cards}</div>
    </section>
    '''
    return html(layout("Train. Hack. Defend. Get certified.", body, req))


@app.get("/verify")
def verify_form(req):
    code = req.query.get("code", "").strip()
    result_html = ""
    if code:
        cert = verify_certificate(code)
        if cert and not cert["revoked"]:
            result_html = card(f'''
              <div class="flex items-center gap-3">
                <div class="text-3xl">✅</div>
                <div>
                  <div class="text-lg font-semibold text-emerald-300">Valid certificate</div>
                  <div class="text-sm text-slate-400">Issued by ThreatNova Security</div>
                </div>
              </div>
              <dl class="mt-5 grid sm:grid-cols-2 gap-4 text-sm">
                <div><dt class="text-slate-500">Recipient</dt><dd class="text-white font-medium">{esc(cert["student_name"])}</dd></div>
                <div><dt class="text-slate-500">Certification</dt><dd class="text-white font-medium">{esc(cert["course_title"])}</dd></div>
                <div><dt class="text-slate-500">Category</dt><dd class="text-white">{esc(cert["category"])} · {esc(cert["difficulty"])}</dd></div>
                <div><dt class="text-slate-500">Score</dt><dd class="text-white">{cert["score"]}%</dd></div>
                <div><dt class="text-slate-500">Issued</dt><dd class="text-white">{esc(cert["issued_at"])}</dd></div>
                <div><dt class="text-slate-500">Credential ID</dt><dd class="text-cyan-300 font-mono">{esc(cert["code"])}</dd></div>
              </dl>
            ''', extra="border-emerald-500/30")
        elif cert and cert["revoked"]:
            result_html = card('''<div class="text-rose-300"><span class="text-2xl">⛔</span>
              <div class="mt-2 font-semibold">This certificate has been revoked.</div></div>''',
              extra="border-rose-500/30")
        else:
            result_html = card('''<div class="text-slate-300"><span class="text-2xl">❓</span>
              <div class="mt-2 font-semibold">No certificate found for that credential ID.</div>
              <div class="text-sm text-slate-500 mt-1">Check the code and try again.</div></div>''')

    body = f'''
    {page_header("Verify a certificate", "Enter a ThreatNova credential ID to confirm its authenticity.")}
    <div class="max-w-xl">
      <form method="get" action="/verify" class="flex gap-2">
        <input name="code" value="{esc(code)}" placeholder="TN-XXXX-XXXX-XXXX"
               class="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 font-mono text-white placeholder-slate-600 focus:border-cyan-500 focus:outline-none">
        <button class="rounded-lg bg-cyan-500 hover:bg-cyan-400 px-5 py-2.5 font-semibold text-slate-900">Verify</button>
      </form>
      <div class="mt-6">{result_html}</div>
    </div>'''
    return html(layout("Verify Certificate", body, req))
