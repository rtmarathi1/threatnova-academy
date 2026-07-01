"""Certificate routes: student's certificate list and the printable certificate page."""
from __future__ import annotations

from . import app
from .. import db, auth
from ..server import html
from ..templates import layout, esc, card, page_header, badge


@app.get("/certificates")
def my_certificates(req):
    guard = auth.login_required(req)
    if guard:
        return guard
    certs = db.query(
        """SELECT c.*, co.category, co.difficulty, co.slug AS course_slug
           FROM certificates c JOIN courses co ON co.id = c.course_id
           WHERE c.user_id = ? ORDER BY c.issued_at DESC""",
        (req.user["id"],),
    )
    if not certs:
        body = f'''{page_header("My certificates")}
          {card('<div class="text-center py-8"><div class="text-3xl">🏅</div><p class="mt-2 text-slate-300">No certificates yet. Complete a course to earn one!</p><a href="/courses" class="mt-3 inline-block rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-900">Browse courses</a></div>')}'''
        return html(layout("My Certificates", body, req))

    cards = []
    for c in certs:
        status = ('<span class="text-xs text-rose-300">Revoked</span>' if c["revoked"]
                  else '<span class="text-xs text-emerald-300">Valid</span>')
        cards.append(card(f'''
          <div class="flex items-start justify-between">
            <div class="text-3xl">🏅</div>{status}
          </div>
          <h3 class="mt-2 font-semibold text-white">{esc(c["title"])}</h3>
          <div class="mt-1 text-sm text-slate-400">{esc(c["category"])} · Score {c["score"]}%</div>
          <div class="mt-2 font-mono text-xs text-cyan-300">{esc(c["code"])}</div>
          <div class="mt-4 flex gap-3">
            <a href="/certificates/{esc(c["code"])}" class="text-sm text-cyan-400 hover:text-cyan-300">View & print →</a>
          </div>'''))
    body = f'''{page_header("My certificates", "Your verifiable ThreatNova credentials.")}
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">{"".join(cards)}</div>'''
    return html(layout("My Certificates", body, req))


@app.get("/certificates/<code>")
def certificate_view(req):
    code = req.params["code"].upper()
    cert = db.query_one(
        """SELECT c.*, u.name AS student_name, co.title AS course_title,
                  co.category, co.difficulty
           FROM certificates c JOIN users u ON u.id = c.user_id
           JOIN courses co ON co.id = c.course_id WHERE c.code = ?""",
        (code,),
    )
    if not cert:
        return html(layout("Not found", page_header("Certificate not found"), req), status=404)

    revoked_banner = ('<div class="mb-4 rounded-lg bg-rose-500/10 border border-rose-500/30 px-4 py-3 text-rose-200 text-sm">This certificate has been revoked and is no longer valid.</div>'
                      if cert["revoked"] else "")

    verify_url = f'/verify?code={esc(cert["code"])}'
    certificate = f'''
    <div id="cert" class="relative mx-auto max-w-3xl rounded-2xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-950 p-10 shadow-2xl">
      <div class="absolute inset-0 rounded-2xl ring-1 ring-cyan-500/20 pointer-events-none"></div>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2 text-white font-semibold text-lg">🛡️ ThreatNova <span class="text-cyan-400">Security</span></div>
        <div class="text-xs text-slate-500 uppercase tracking-widest">Certificate of Completion</div>
      </div>
      <div class="mt-10 text-center">
        <div class="text-sm text-slate-400">This certifies that</div>
        <div class="mt-2 text-3xl font-extrabold text-white">{esc(cert["student_name"])}</div>
        <div class="mt-3 text-sm text-slate-400">has successfully completed the certification track</div>
        <div class="mt-2 text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400">{esc(cert["course_title"])}</div>
        <div class="mt-3 flex items-center justify-center gap-2">{badge(cert["difficulty"], cert["difficulty"])}{badge(cert["category"])}
          <span class="text-sm text-slate-400">· Score {cert["score"]}%</span></div>
      </div>
      <div class="mt-10 flex items-end justify-between">
        <div>
          <div class="text-xs text-slate-500">Issued</div>
          <div class="text-sm text-slate-200">{esc(cert["issued_at"][:10])}</div>
        </div>
        <div class="text-center">
          <div class="text-xs text-slate-500">Credential ID</div>
          <div class="font-mono text-sm text-cyan-300">{esc(cert["code"])}</div>
        </div>
        <div class="text-right">
          <div class="text-xs text-slate-500">Verify at</div>
          <div class="text-sm text-slate-200">/verify</div>
        </div>
      </div>
    </div>'''

    body = f'''
    {revoked_banner}
    <div class="flex items-center justify-between mb-4 no-print">
      <h1 class="text-xl font-semibold text-white">Certificate</h1>
      <div class="flex gap-2">
        <a href="{verify_url}" class="rounded-lg border border-slate-700 hover:border-slate-500 px-4 py-2 text-sm text-slate-200">Public verify page</a>
        <button onclick="window.print()" class="rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-900">🖨 Print / Save PDF</button>
      </div>
    </div>
    {certificate}
    <p class="mt-4 text-center text-sm text-slate-500">Anyone can confirm this credential at
      <span class="font-mono text-slate-300">/verify</span> using ID <span class="font-mono text-cyan-300">{esc(cert["code"])}</span>.</p>
    '''
    return html(layout("Certificate", body, req))
