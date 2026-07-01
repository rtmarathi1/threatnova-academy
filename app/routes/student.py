"""Student portal: dashboard, course catalog, course/lesson viewer, labs, flag submission."""
from __future__ import annotations

from urllib.parse import quote

from . import app
from .. import db, auth, services
from ..server import html, redirect
from ..markup import render as md
from ..templates import layout, esc, badge, card, progress_bar, page_header, flash


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
@app.get("/dashboard")
def dashboard(req):
    guard = auth.login_required(req)
    if guard:
        return guard
    uid = req.user["id"]

    enrollments = db.query(
        """SELECT c.* FROM enrollments e JOIN courses c ON c.id = e.course_id
           WHERE e.user_id = ? ORDER BY e.enrolled_at DESC""",
        (uid,),
    )

    enrolled_cards = []
    for c in enrollments:
        prog = services.course_progress(uid, c["id"])
        cert = services.get_certificate(uid, c["id"])
        cert_badge = ('<span class="text-xs text-emerald-300">🏅 Certified</span>' if cert
                      else f'<span class="text-xs text-slate-500">{prog["percent"]}% complete</span>')
        enrolled_cards.append(card(f'''
          <div class="flex items-start justify-between">
            <div class="text-2xl">{esc(c["icon"])}</div>{badge(c["difficulty"], c["difficulty"])}
          </div>
          <h3 class="mt-2 font-semibold text-white">{esc(c["title"])}</h3>
          <div class="mt-3">{progress_bar(prog["percent"])}</div>
          <div class="mt-2 flex items-center justify-between">{cert_badge}
            <a href="/courses/{esc(c["slug"])}" class="text-sm text-cyan-400 hover:text-cyan-300">Continue →</a>
          </div>'''))

    if not enrolled_cards:
        enrolled_html = card('''<div class="text-center py-6">
          <div class="text-3xl">🚀</div>
          <p class="mt-2 text-slate-300">You have not enrolled in any courses yet.</p>
          <a href="/courses" class="mt-3 inline-block rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-900">Browse courses</a>
        </div>''')
    else:
        enrolled_html = f'<div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">{"".join(enrolled_cards)}</div>'

    total_points = db.query_one(
        "SELECT COALESCE(SUM(points_awarded),0) p FROM lab_submissions WHERE user_id=? AND correct=1", (uid,)
    )["p"]
    n_certs = db.query_one(
        "SELECT COUNT(*) c FROM certificates WHERE user_id=? AND revoked=0", (uid,)
    )["c"]
    n_labs = db.query_one(
        "SELECT COUNT(DISTINCT lab_id) c FROM lab_submissions WHERE user_id=? AND correct=1", (uid,)
    )["c"]

    stat = lambda label, val, icon: f'''
      <div class="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <div class="text-2xl">{icon}</div>
        <div class="mt-1 text-2xl font-bold text-white">{val}</div>
        <div class="text-xs text-slate-500">{label}</div>
      </div>'''

    body = f'''
    {flash(req)}
    {page_header(f"Welcome back, {esc(req.user['name'].split()[0])}", "Pick up where you left off.")}
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
      {stat("Courses enrolled", len(enrollments), "📚")}
      {stat("Labs solved", n_labs, "🧪")}
      {stat("Points earned", total_points, "⚡")}
      {stat("Certificates", n_certs, "🏅")}
    </div>
    <h2 class="text-lg font-semibold text-white mb-3">Your courses</h2>
    {enrolled_html}'''
    return html(layout("Dashboard", body, req))


# --------------------------------------------------------------------------- #
# Course catalog
# --------------------------------------------------------------------------- #
@app.get("/courses")
def catalog(req):
    courses = db.query("SELECT * FROM courses WHERE published = 1 ORDER BY category, id")
    cards = []
    for c in courses:
        enrolled = req.user and services.is_enrolled(req.user["id"], c["id"])
        tag = '<span class="text-xs text-emerald-300">Enrolled</span>' if enrolled else \
              f'<span class="text-xs text-slate-500">⏱ {c["duration_hours"]}h</span>'
        cards.append(card(f'''
          <div class="flex items-start justify-between">
            <div class="text-3xl">{esc(c["icon"])}</div>{badge(c["difficulty"], c["difficulty"])}
          </div>
          <h3 class="mt-3 font-semibold text-white">{esc(c["title"])}</h3>
          <p class="mt-1 text-sm text-slate-400">{esc(c["summary"])}</p>
          <div class="mt-4 flex items-center justify-between">
            <span class="text-xs text-slate-500">📚 {esc(c["category"])}</span>{tag}
          </div>
          <a href="/courses/{esc(c["slug"])}" class="mt-4 inline-block text-sm font-medium text-cyan-400 hover:text-cyan-300">View course →</a>
        ''', extra="hover:border-cyan-500/40 transition"))

    body = f'''
    {page_header("Certification tracks", "Structured, hands-on paths across offensive and defensive security.")}
    <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">{"".join(cards)}</div>'''
    return html(layout("Courses", body, req))


# --------------------------------------------------------------------------- #
# Course detail
# --------------------------------------------------------------------------- #
@app.get("/courses/<slug>")
def course_detail(req):
    slug = req.params["slug"]
    course = services.course_by_slug(slug)
    if not course:
        return html(layout("Not found", page_header("Course not found"), req), status=404)

    enrolled = req.user and services.is_enrolled(req.user["id"], course["id"])
    prog = services.course_progress(req.user["id"], course["id"]) if enrolled else None
    done_lessons = prog["done_lesson_ids"] if prog else set()
    done_labs = prog["done_lab_ids"] if prog else set()

    # curriculum
    modules = services.course_modules_with_lessons(course["id"])
    mod_html = []
    for block in modules:
        m = block["module"]
        items = []
        for l in block["lessons"]:
            check = "✅" if l["id"] in done_lessons else "○"
            link = f'/courses/{esc(slug)}/lessons/{l["id"]}' if enrolled else "/login"
            items.append(f'''<a href="{link}" class="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-slate-800/60">
              <span class="text-sm">{check}</span>
              <span class="text-sm text-slate-200">{esc(l["title"])}</span></a>''')
        mod_html.append(f'''
          <div class="rounded-xl border border-slate-800 overflow-hidden">
            <div class="bg-slate-900/70 px-4 py-3 font-medium text-white">{esc(m["title"])}</div>
            <div class="p-2 divide-y divide-slate-800/50">{"".join(items) or '<div class="px-3 py-2 text-sm text-slate-500">No lessons yet.</div>'}</div>
          </div>''')

    # labs
    labs = services.course_labs(course["id"])
    lab_html = []
    for lb in labs:
        solved = lb["id"] in done_labs
        state = '<span class="text-xs text-emerald-300">Solved ✅</span>' if solved else f'<span class="text-xs text-slate-500">{lb["points"]} pts</span>'
        link = f'/labs/{esc(lb["slug"])}' if enrolled else "/login"
        lab_html.append(f'''<a href="{link}" class="flex items-center justify-between rounded-lg border border-slate-800 px-4 py-3 hover:border-cyan-500/40">
          <div><div class="text-sm font-medium text-slate-100">{esc(lb["title"])}</div>
          <div class="text-xs text-slate-500">{badge(lb["difficulty"], lb["difficulty"])}</div></div>
          {state}</a>''')
    labs_section = f'<div class="grid sm:grid-cols-2 gap-3">{"".join(lab_html)}</div>' if labs else '<p class="text-sm text-slate-500">No labs in this course yet.</p>'

    # sidebar / enroll box
    if enrolled:
        cert = services.get_certificate(req.user["id"], course["id"])
        if cert:
            cta = f'''<a href="/certificates/{esc(cert["code"])}" class="block text-center rounded-lg bg-emerald-500 hover:bg-emerald-400 px-4 py-2.5 font-semibold text-slate-900">🏅 View your certificate</a>'''
        else:
            cta = f'''<div class="text-sm text-slate-400 mb-2">Reach {course["pass_threshold"]}% to earn your certificate.</div>'''
        side = card(f'''
          <div class="text-sm text-slate-400">Your progress</div>
          <div class="mt-2 text-3xl font-bold text-white">{prog["percent"]}%</div>
          <div class="mt-3">{progress_bar(prog["percent"])}</div>
          <div class="mt-3 text-xs text-slate-500">Lessons {prog["lessons_done"]}/{prog["lessons_total"]} · Labs {prog["labs_done"]}/{prog["labs_total"]}</div>
          <div class="mt-4">{cta}</div>''')
    else:
        csrf = req.session["csrf"] if req.session else ""
        if req.user:
            enroll_btn = f'''<form method="post" action="/courses/{esc(slug)}/enroll">
              <input type="hidden" name="csrf" value="{esc(csrf)}">
              <button class="w-full rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 py-2.5 font-semibold text-slate-900">Enroll now — free</button></form>'''
        else:
            enroll_btn = '<a href="/register" class="block text-center rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 py-2.5 font-semibold text-slate-900">Sign up to enroll</a>'
        side = card(f'''
          <div class="text-sm text-slate-400">This track includes</div>
          <ul class="mt-2 space-y-1 text-sm text-slate-300">
            <li>📖 {len(services.course_lessons(course["id"]))} lessons</li>
            <li>🧪 {len(labs)} hands-on labs</li>
            <li>🏅 Verifiable certificate</li>
            <li>⏱ ~{course["duration_hours"]} hours</li>
          </ul>
          <div class="mt-4">{enroll_btn}</div>''')

    body = f'''
    {flash(req)}
    <div class="flex items-center gap-2 text-sm text-slate-500 mb-4">
      <a href="/courses" class="hover:text-slate-300">Courses</a><span>/</span><span class="text-slate-300">{esc(course["title"])}</span>
    </div>
    <div class="grid lg:grid-cols-3 gap-8">
      <div class="lg:col-span-2">
        <div class="flex items-start gap-4">
          <div class="text-5xl">{esc(course["icon"])}</div>
          <div>
            <div class="flex items-center gap-2">{badge(course["difficulty"], course["difficulty"])}{badge(course["category"])}</div>
            <h1 class="mt-2 text-3xl font-bold text-white">{esc(course["title"])}</h1>
          </div>
        </div>
        <div class="prose-tn mt-6 max-w-none">{md(course["description"] or course["summary"])}</div>

        <h2 class="mt-10 text-xl font-semibold text-white mb-3">Curriculum</h2>
        <div class="space-y-3">{"".join(mod_html) or '<p class="text-sm text-slate-500">No modules yet.</p>'}</div>

        <h2 class="mt-10 text-xl font-semibold text-white mb-3">Hands-on labs</h2>
        {labs_section}
      </div>
      <div class="lg:col-span-1"><div class="lg:sticky lg:top-24">{side}</div></div>
    </div>'''
    return html(layout(course["title"], body, req))


@app.post("/courses/<slug>/enroll")
def enroll(req):
    guard = auth.login_required(req)
    if guard:
        return guard
    csrf_err = auth.check_csrf(req)
    if csrf_err:
        return csrf_err
    course = services.course_by_slug(req.params["slug"])
    if not course:
        return redirect("/courses")
    services.enroll(req.user["id"], course["id"])
    return redirect(f'/courses/{req.params["slug"]}?msg=' + quote("You are enrolled! Start learning below."))


# --------------------------------------------------------------------------- #
# Lesson viewer
# --------------------------------------------------------------------------- #
@app.get("/courses/<slug>/lessons/<lesson_id>")
def lesson_view(req):
    guard = auth.login_required(req)
    if guard:
        return guard
    slug = req.params["slug"]
    course = services.course_by_slug(slug)
    if not course or not services.is_enrolled(req.user["id"], course["id"]):
        return redirect(f"/courses/{slug}")

    lessons = services.course_lessons(course["id"])
    ids = [l["id"] for l in lessons]
    try:
        lesson_id = int(req.params["lesson_id"])
    except ValueError:
        return redirect(f"/courses/{slug}")
    if lesson_id not in ids:
        return redirect(f"/courses/{slug}")

    lesson = next(l for l in lessons if l["id"] == lesson_id)
    idx = ids.index(lesson_id)
    prev_id = ids[idx - 1] if idx > 0 else None
    next_id = ids[idx + 1] if idx < len(ids) - 1 else None
    done = lesson_id in services.completed_lesson_ids(req.user["id"], course["id"])
    csrf = req.session["csrf"] if req.session else ""

    # lesson list sidebar
    done_set = services.completed_lesson_ids(req.user["id"], course["id"])
    side_items = "".join(
        f'''<a href="/courses/{esc(slug)}/lessons/{l["id"]}"
             class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm {'bg-slate-800 text-white' if l["id"]==lesson_id else 'text-slate-300 hover:bg-slate-800/60'}">
             <span>{'✅' if l["id"] in done_set else '○'}</span><span>{esc(l["title"])}</span></a>'''
        for l in lessons
    )

    complete_btn = ('<span class="inline-flex items-center gap-2 text-emerald-300 text-sm">✅ Completed</span>' if done else
        f'''<form method="post" action="/lessons/{lesson_id}/complete">
          <input type="hidden" name="csrf" value="{esc(csrf)}">
          <input type="hidden" name="slug" value="{esc(slug)}">
          <input type="hidden" name="next" value="{next_id or ''}">
          <button class="rounded-lg bg-emerald-500 hover:bg-emerald-400 px-4 py-2 text-sm font-semibold text-slate-900">Mark complete {'& continue →' if next_id else ''}</button>
        </form>''')

    nav_links = []
    if prev_id:
        nav_links.append(f'<a href="/courses/{esc(slug)}/lessons/{prev_id}" class="text-sm text-slate-400 hover:text-white">← Previous</a>')
    else:
        nav_links.append("<span></span>")
    if next_id:
        nav_links.append(f'<a href="/courses/{esc(slug)}/lessons/{next_id}" class="text-sm text-slate-400 hover:text-white">Next →</a>')

    body = f'''
    {flash(req)}
    <div class="flex items-center gap-2 text-sm text-slate-500 mb-4">
      <a href="/courses/{esc(slug)}" class="hover:text-slate-300">{esc(course["title"])}</a><span>/</span><span class="text-slate-300">Lesson {idx+1}</span>
    </div>
    <div class="grid lg:grid-cols-4 gap-8">
      <aside class="lg:col-span-1 order-2 lg:order-1">
        <div class="lg:sticky lg:top-24 rounded-xl border border-slate-800 p-2">{side_items}</div>
      </aside>
      <div class="lg:col-span-3 order-1 lg:order-2">
        <h1 class="text-2xl font-bold text-white">{esc(lesson["title"])}</h1>
        <article class="prose-tn mt-5 max-w-none">{md(lesson["content"])}</article>
        <div class="mt-8 flex items-center justify-between border-t border-slate-800 pt-5">
          {nav_links[0]}
          <div>{complete_btn}</div>
          {nav_links[1] if len(nav_links)>1 else ''}
        </div>
      </div>
    </div>'''
    return html(layout(lesson["title"], body, req))


@app.post("/lessons/<lesson_id>/complete")
def lesson_complete(req):
    guard = auth.login_required(req)
    if guard:
        return guard
    csrf_err = auth.check_csrf(req)
    if csrf_err:
        return csrf_err
    lesson_id = int(req.params["lesson_id"])
    slug = req.form.get("slug", "")
    next_id = req.form.get("next", "")
    services.mark_lesson_complete(req.user["id"], lesson_id)

    course = services.course_by_slug(slug)
    cert_msg = ""
    if course:
        cert = services.evaluate_and_issue(req.user["id"], course["id"])
        if cert:
            return redirect(f'/certificates/{cert["code"]}?msg=' + quote("Congratulations! You earned a certificate."))
    if next_id:
        return redirect(f"/courses/{slug}/lessons/{next_id}")
    return redirect(f"/courses/{slug}?msg=" + quote("Lesson completed."))


# --------------------------------------------------------------------------- #
# Labs
# --------------------------------------------------------------------------- #
@app.get("/labs")
def labs_index(req):
    guard = auth.login_required(req)
    if guard:
        return guard
    uid = req.user["id"]
    labs = db.query(
        """SELECT lb.*, c.title AS course_title, c.slug AS course_slug
           FROM labs lb JOIN courses c ON c.id = lb.course_id
           ORDER BY lb.difficulty, lb.id"""
    )
    solved = {r["lab_id"] for r in db.query(
        "SELECT DISTINCT lab_id FROM lab_submissions WHERE user_id=? AND correct=1", (uid,))}

    cards = []
    for lb in labs:
        is_solved = lb["id"] in solved
        enrolled = services.is_enrolled(uid, lb["course_id"])
        state = '<span class="text-xs text-emerald-300">Solved ✅</span>' if is_solved else f'<span class="text-xs text-slate-500">{lb["points"]} pts</span>'
        cards.append(card(f'''
          <div class="flex items-start justify-between">{badge(lb["difficulty"], lb["difficulty"])}{state}</div>
          <h3 class="mt-2 font-semibold text-white">{esc(lb["title"])}</h3>
          <p class="mt-1 text-sm text-slate-400 line-clamp-2">{esc(lb["scenario"])}</p>
          <div class="mt-3 text-xs text-slate-500">from {esc(lb["course_title"])}</div>
          <a href="/labs/{esc(lb["slug"])}" class="mt-3 inline-block text-sm text-cyan-400 hover:text-cyan-300">
            {"Open lab →" if enrolled else "Enroll to access →"}</a>'''))

    body = f'''{page_header("Hands-on labs", "Capture-the-flag challenges. Submit the flag to score points.")}
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">{"".join(cards)}</div>'''
    return html(layout("Labs", body, req))


@app.get("/labs/<slug>")
def lab_view(req, error=None, solved_now=False):
    guard = auth.login_required(req)
    if guard:
        return guard
    lab = db.query_one("SELECT * FROM labs WHERE slug = ?", (req.params["slug"],))
    if not lab:
        return html(layout("Not found", page_header("Lab not found"), req), status=404)
    course = db.query_one("SELECT * FROM courses WHERE id = ?", (lab["course_id"],))
    if not services.is_enrolled(req.user["id"], course["id"]):
        return redirect(f'/courses/{course["slug"]}?err=' + quote("Enroll in the course to access this lab."))

    already = db.query_one(
        "SELECT 1 FROM lab_submissions WHERE user_id=? AND lab_id=? AND correct=1",
        (req.user["id"], lab["id"]))
    solved = bool(already) or solved_now
    csrf = req.session["csrf"] if req.session else ""

    if solved:
        panel = card('''<div class="flex items-center gap-3"><div class="text-3xl">🎉</div>
          <div><div class="font-semibold text-emerald-300">Flag captured!</div>
          <div class="text-sm text-slate-400">You earned this lab's points.</div></div></div>''',
          extra="border-emerald-500/30")
    else:
        err_html = f'<div class="mb-3 rounded-lg bg-rose-500/10 border border-rose-500/30 px-3 py-2 text-sm text-rose-200">{esc(error)}</div>' if error else ""
        hint_html = f'''<details class="mt-4"><summary class="cursor-pointer text-sm text-slate-400 hover:text-slate-200">💡 Need a hint?</summary>
          <div class="mt-2 text-sm text-slate-400 rounded-lg bg-slate-950 border border-slate-800 p-3">{esc(lab["hint"])}</div></details>''' if lab["hint"] else ""
        panel = card(f'''
          {err_html}
          <form method="post" action="/labs/{esc(lab["slug"])}/submit">
            <input type="hidden" name="csrf" value="{esc(csrf)}">
            <label class="text-sm text-slate-300">Submit flag</label>
            <div class="mt-1 flex gap-2">
              <input name="flag" placeholder="flag{{...}}" autocomplete="off"
                     class="flex-1 rounded-lg bg-slate-950 border border-slate-700 px-3 py-2.5 font-mono text-white placeholder-slate-600 focus:border-cyan-500 focus:outline-none">
              <button class="rounded-lg bg-cyan-500 hover:bg-cyan-400 px-5 font-semibold text-slate-900">Submit</button>
            </div>
          </form>{hint_html}''')

    body = f'''
    {flash(req)}
    <div class="flex items-center gap-2 text-sm text-slate-500 mb-4">
      <a href="/courses/{esc(course["slug"])}" class="hover:text-slate-300">{esc(course["title"])}</a><span>/</span><span class="text-slate-300">Lab</span>
    </div>
    <div class="grid lg:grid-cols-3 gap-8">
      <div class="lg:col-span-2">
        <div class="flex items-center gap-2">{badge(lab["difficulty"], lab["difficulty"])}<span class="text-sm text-slate-500">{lab["points"]} points</span></div>
        <h1 class="mt-2 text-3xl font-bold text-white">{esc(lab["title"])}</h1>
        <h2 class="mt-6 text-lg font-semibold text-white">Scenario</h2>
        <div class="prose-tn max-w-none">{md(lab["scenario"])}</div>
        <h2 class="mt-6 text-lg font-semibold text-white">Your task</h2>
        <div class="prose-tn max-w-none">{md(lab["instructions"])}</div>
      </div>
      <div class="lg:col-span-1"><div class="lg:sticky lg:top-24">{panel}</div></div>
    </div>'''
    return html(layout(lab["title"], body, req))


@app.post("/labs/<slug>/submit")
def lab_submit(req):
    guard = auth.login_required(req)
    if guard:
        return guard
    csrf_err = auth.check_csrf(req)
    if csrf_err:
        return csrf_err
    lab = db.query_one("SELECT * FROM labs WHERE slug = ?", (req.params["slug"],))
    if not lab:
        return redirect("/labs")
    if not services.is_enrolled(req.user["id"], lab["course_id"]):
        return redirect(f"/labs/{lab['slug']}")

    submitted = req.form.get("flag", "")
    correct = services.check_flag(lab, submitted)
    already = db.query_one(
        "SELECT 1 FROM lab_submissions WHERE user_id=? AND lab_id=? AND correct=1",
        (req.user["id"], lab["id"]))
    points = lab["points"] if (correct and not already) else 0

    db.execute(
        "INSERT INTO lab_submissions (user_id, lab_id, submitted_flag, correct, points_awarded) VALUES (?,?,?,?,?)",
        (req.user["id"], lab["id"], submitted[:200], 1 if correct else 0, points))

    if correct:
        cert = services.evaluate_and_issue(req.user["id"], lab["course_id"])
        if cert:
            return redirect(f'/certificates/{cert["code"]}?msg=' + quote("Flag captured — and you earned a certificate!"))
        return lab_view(req, solved_now=True)
    return lab_view(req, error="Incorrect flag. Review the scenario and try again.")
