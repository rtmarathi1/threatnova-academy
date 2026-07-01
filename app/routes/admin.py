"""
Instructor/Admin panel.

INSTRUCTOR and ADMIN can manage course content (courses, modules, lessons, labs)
and certificates. Only ADMIN can manage users and roles.
"""
from __future__ import annotations

import re
import sqlite3
from urllib.parse import quote

from . import app
from .. import db, auth, services
from ..server import html, redirect, Response
from ..templates import layout, esc, card, page_header, badge, flash


def _slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "item"


def _staff(req):
    return auth.require_role(req, "INSTRUCTOR", "ADMIN")


def _admin_only(req):
    return auth.require_role(req, "ADMIN")


def _csrf(req):
    return req.session["csrf"] if req.session else ""


def _tab_nav(active):
    tabs = [("/admin", "Overview"), ("/admin/courses", "Courses"),
            ("/admin/labs", "Labs"), ("/admin/certificates", "Certificates"),
            ("/admin/users", "Users")]
    out = []
    for href, label in tabs:
        is_active = (href == active)
        cls = "bg-slate-800 text-white" if is_active else "text-slate-400 hover:text-white hover:bg-slate-800/60"
        out.append(f'<a href="{href}" class="rounded-lg px-3 py-1.5 text-sm {cls}">{esc(label)}</a>')
    return f'<div class="flex flex-wrap gap-1 mb-6 border-b border-slate-800 pb-3">{"".join(out)}</div>'


# --------------------------------------------------------------------------- #
# Overview
# --------------------------------------------------------------------------- #
@app.get("/admin")
def admin_home(req):
    guard = _staff(req)
    if guard:
        return guard
    s = lambda q: db.query_one(q)["c"]
    stats = {
        "users": s("SELECT COUNT(*) c FROM users"),
        "students": s("SELECT COUNT(*) c FROM users WHERE role='STUDENT'"),
        "courses": s("SELECT COUNT(*) c FROM courses"),
        "labs": s("SELECT COUNT(*) c FROM labs"),
        "enrollments": s("SELECT COUNT(*) c FROM enrollments"),
        "certs": s("SELECT COUNT(*) c FROM certificates WHERE revoked=0"),
    }
    recent_enroll = db.query(
        """SELECT u.name, c.title, e.enrolled_at FROM enrollments e
           JOIN users u ON u.id=e.user_id JOIN courses c ON c.id=e.course_id
           ORDER BY e.enrolled_at DESC LIMIT 8""")
    recent_certs = db.query(
        """SELECT u.name, c.title, ce.code, ce.issued_at FROM certificates ce
           JOIN users u ON u.id=ce.user_id JOIN courses c ON c.id=ce.course_id
           ORDER BY ce.issued_at DESC LIMIT 8""")

    stat = lambda label, val, icon: f'''<div class="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <div class="text-2xl">{icon}</div><div class="mt-1 text-2xl font-bold text-white">{val}</div>
        <div class="text-xs text-slate-500">{label}</div></div>'''

    enroll_rows = "".join(
        f'<tr class="border-t border-slate-800"><td class="py-2 pr-4 text-slate-200">{esc(r["name"])}</td>'
        f'<td class="py-2 pr-4 text-slate-400">{esc(r["title"])}</td>'
        f'<td class="py-2 text-slate-500 text-xs">{esc(r["enrolled_at"])}</td></tr>'
        for r in recent_enroll) or '<tr><td class="py-2 text-slate-500 text-sm">No enrollments yet.</td></tr>'
    cert_rows = "".join(
        f'<tr class="border-t border-slate-800"><td class="py-2 pr-4 text-slate-200">{esc(r["name"])}</td>'
        f'<td class="py-2 pr-4 text-slate-400">{esc(r["title"])}</td>'
        f'<td class="py-2 font-mono text-xs text-cyan-300">{esc(r["code"])}</td></tr>'
        for r in recent_certs) or '<tr><td class="py-2 text-slate-500 text-sm">No certificates issued yet.</td></tr>'

    body = f'''
    {page_header("Admin console", f"Signed in as {esc(req.user['name'])} ({esc(req.user['role'])})")}
    {_tab_nav("/admin")}
    {flash(req)}
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
      {stat("Users", stats["users"], "👥")}
      {stat("Students", stats["students"], "🎓")}
      {stat("Courses", stats["courses"], "📚")}
      {stat("Labs", stats["labs"], "🧪")}
      {stat("Enrollments", stats["enrollments"], "📝")}
      {stat("Certificates", stats["certs"], "🏅")}
    </div>
    <div class="grid lg:grid-cols-2 gap-6">
      {card(f'<h3 class="font-semibold text-white mb-3">Recent enrollments</h3><table class="w-full text-sm"><tbody>{enroll_rows}</tbody></table>')}
      {card(f'<h3 class="font-semibold text-white mb-3">Recent certificates</h3><table class="w-full text-sm"><tbody>{cert_rows}</tbody></table>')}
    </div>'''
    return html(layout("Admin", body, req))


# --------------------------------------------------------------------------- #
# Courses list + create
# --------------------------------------------------------------------------- #
@app.get("/admin/courses")
def admin_courses(req):
    guard = _staff(req)
    if guard:
        return guard
    courses = db.query("SELECT * FROM courses ORDER BY id DESC")
    rows = ""
    for c in courses:
        n_lessons = db.query_one(
            "SELECT COUNT(*) c FROM lessons l JOIN modules m ON m.id=l.module_id WHERE m.course_id=?", (c["id"],))["c"]
        n_labs = db.query_one("SELECT COUNT(*) c FROM labs WHERE course_id=?", (c["id"],))["c"]
        pub = '<span class="text-emerald-300 text-xs">Published</span>' if c["published"] else '<span class="text-slate-500 text-xs">Draft</span>'
        rows += f'''<tr class="border-t border-slate-800">
          <td class="py-3 pr-4">{esc(c["icon"])}</td>
          <td class="py-3 pr-4"><div class="text-slate-100 font-medium">{esc(c["title"])}</div>
            <div class="text-xs text-slate-500">{esc(c["category"])} · {esc(c["difficulty"])}</div></td>
          <td class="py-3 pr-4 text-slate-400 text-sm">{n_lessons} lessons · {n_labs} labs</td>
          <td class="py-3 pr-4">{pub}</td>
          <td class="py-3 text-right"><a href="/admin/courses/{c["id"]}" class="text-cyan-400 hover:text-cyan-300 text-sm">Manage →</a></td>
        </tr>'''

    create_form = card(f'''
      <h3 class="font-semibold text-white mb-3">Create a course</h3>
      <form method="post" action="/admin/courses" class="grid sm:grid-cols-2 gap-3">
        <input type="hidden" name="csrf" value="{esc(_csrf(req))}">
        <input name="title" placeholder="Course title" required class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white placeholder-slate-600">
        <input name="category" placeholder="Category (e.g. Web Security)" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white placeholder-slate-600">
        <input name="icon" placeholder="Icon emoji (e.g. 🕸️)" maxlength="4" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white placeholder-slate-600">
        <select name="difficulty" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white">
          <option>Beginner</option><option>Intermediate</option><option>Advanced</option></select>
        <input name="duration_hours" type="number" value="8" min="1" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white">
        <input name="pass_threshold" type="number" value="70" min="1" max="100" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white">
        <input name="summary" placeholder="Short summary" class="sm:col-span-2 rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white placeholder-slate-600">
        <textarea name="description" placeholder="Full description (Markdown supported)" rows="3" class="sm:col-span-2 rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white placeholder-slate-600"></textarea>
        <button class="sm:col-span-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 py-2 font-semibold text-slate-900">Create course</button>
      </form>''')

    rows_html = rows or '<tr><td class="py-3 text-slate-500">No courses yet.</td></tr>'
    body = f'''
    {page_header("Courses")}{_tab_nav("/admin/courses")}{flash(req)}
    {card(f'<table class="w-full text-sm"><tbody>{rows_html}</tbody></table>')}
    <div class="mt-6">{create_form}</div>'''
    return html(layout("Manage Courses", body, req))


@app.post("/admin/courses")
def admin_course_create(req):
    guard = _staff(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    f = req.form
    title = (f.get("title") or "").strip()
    if not title:
        return redirect("/admin/courses?err=" + quote("Title is required."))
    slug = _slugify(title)
    # ensure unique slug
    base, n = slug, 2
    while db.query_one("SELECT 1 FROM courses WHERE slug=?", (slug,)):
        slug = f"{base}-{n}"; n += 1
    try:
        cid = db.execute(
            """INSERT INTO courses (slug,title,summary,description,category,difficulty,duration_hours,pass_threshold,icon,created_by)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (slug, title, f.get("summary","").strip(), f.get("description","").strip(),
             f.get("category","General").strip() or "General", f.get("difficulty","Beginner"),
             int(f.get("duration_hours") or 8), int(f.get("pass_threshold") or 70),
             (f.get("icon") or "🛡️").strip() or "🛡️", req.user["id"]))
    except (sqlite3.IntegrityError, ValueError):
        return redirect("/admin/courses?err=" + quote("Could not create course."))
    return redirect(f"/admin/courses/{cid}?msg=" + quote("Course created. Add modules, lessons and labs."))


# --------------------------------------------------------------------------- #
# Course builder (edit + modules/lessons/labs)
# --------------------------------------------------------------------------- #
@app.get("/admin/courses/<cid>")
def admin_course_edit(req):
    guard = _staff(req)
    if guard:
        return guard
    cid = int(req.params["cid"])
    course = db.query_one("SELECT * FROM courses WHERE id=?", (cid,))
    if not course:
        return redirect("/admin/courses")
    csrf = _csrf(req)

    # settings form
    def opt(v, cur):
        return f'<option {"selected" if v==cur else ""}>{v}</option>'
    settings = card(f'''
      <h3 class="font-semibold text-white mb-3">Course settings</h3>
      <form method="post" action="/admin/courses/{cid}" class="grid sm:grid-cols-2 gap-3">
        <input type="hidden" name="csrf" value="{esc(csrf)}">
        <input name="title" value="{esc(course["title"])}" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white">
        <input name="category" value="{esc(course["category"])}" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white">
        <input name="icon" value="{esc(course["icon"])}" maxlength="4" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white">
        <select name="difficulty" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white">
          {opt("Beginner",course["difficulty"])}{opt("Intermediate",course["difficulty"])}{opt("Advanced",course["difficulty"])}</select>
        <input name="duration_hours" type="number" value="{course["duration_hours"]}" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white">
        <input name="pass_threshold" type="number" value="{course["pass_threshold"]}" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white">
        <label class="sm:col-span-2 flex items-center gap-2 text-sm text-slate-300">
          <input type="checkbox" name="published" {"checked" if course["published"] else ""}> Published (visible to students)</label>
        <input name="summary" value="{esc(course["summary"])}" class="sm:col-span-2 rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white">
        <textarea name="description" rows="4" class="sm:col-span-2 rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white">{esc(course["description"])}</textarea>
        <button class="rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 py-2 font-semibold text-slate-900">Save settings</button>
      </form>''')

    # modules & lessons
    blocks = services.course_modules_with_lessons(cid)
    mod_html = ""
    for b in blocks:
        m = b["module"]
        lessons = "".join(f'''<div class="flex items-center justify-between rounded-lg bg-slate-950 px-3 py-2">
            <span class="text-sm text-slate-200">{esc(l["title"])}</span>
            <form method="post" action="/admin/lessons/{l["id"]}/delete" onsubmit="return confirm('Delete lesson?')">
              <input type="hidden" name="csrf" value="{esc(csrf)}"><input type="hidden" name="cid" value="{cid}">
              <button class="text-xs text-rose-400 hover:text-rose-300">Delete</button></form></div>'''
            for l in b["lessons"]) or '<div class="text-xs text-slate-500 px-1">No lessons yet.</div>'
        mod_html += f'''
          <div class="rounded-xl border border-slate-800 p-4">
            <div class="flex items-center justify-between">
              <h4 class="font-medium text-white">{esc(m["title"])}</h4>
              <form method="post" action="/admin/modules/{m["id"]}/delete" onsubmit="return confirm('Delete module and its lessons?')">
                <input type="hidden" name="csrf" value="{esc(csrf)}"><input type="hidden" name="cid" value="{cid}">
                <button class="text-xs text-rose-400 hover:text-rose-300">Delete module</button></form>
            </div>
            <div class="mt-3 space-y-2">{lessons}</div>
            <form method="post" action="/admin/modules/{m["id"]}/lessons" class="mt-3 space-y-2">
              <input type="hidden" name="csrf" value="{esc(csrf)}"><input type="hidden" name="cid" value="{cid}">
              <input name="title" placeholder="New lesson title" required class="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-600">
              <textarea name="content" placeholder="Lesson content (Markdown)" rows="3" class="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-600"></textarea>
              <button class="rounded-lg bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-sm text-slate-100">+ Add lesson</button>
            </form>
          </div>'''

    curriculum = card(f'''
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold text-white">Curriculum</h3>
      </div>
      <div class="space-y-4">{mod_html or '<div class="text-sm text-slate-500">No modules yet.</div>'}</div>
      <form method="post" action="/admin/courses/{cid}/modules" class="mt-4 flex gap-2">
        <input type="hidden" name="csrf" value="{esc(csrf)}">
        <input name="title" placeholder="New module title" required class="flex-1 rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-600">
        <button class="rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 text-sm font-semibold text-slate-900">+ Module</button>
      </form>''')

    # labs
    labs = services.course_labs(cid)
    lab_rows = "".join(f'''<div class="flex items-center justify-between rounded-lg bg-slate-950 px-3 py-2">
        <div><span class="text-sm text-slate-200">{esc(lb["title"])}</span>
        <span class="ml-2 text-xs text-slate-500">{lb["points"]} pts · {esc(lb["difficulty"])}</span></div>
        <form method="post" action="/admin/labs/{lb["id"]}/delete" onsubmit="return confirm('Delete lab?')">
          <input type="hidden" name="csrf" value="{esc(csrf)}"><input type="hidden" name="cid" value="{cid}">
          <button class="text-xs text-rose-400 hover:text-rose-300">Delete</button></form></div>'''
        for lb in labs) or '<div class="text-sm text-slate-500">No labs yet.</div>'
    labs_card = card(f'''
      <h3 class="font-semibold text-white mb-3">Labs</h3>
      <div class="space-y-2">{lab_rows}</div>
      <form method="post" action="/admin/courses/{cid}/labs" class="mt-4 grid gap-2">
        <input type="hidden" name="csrf" value="{esc(csrf)}">
        <input name="title" placeholder="Lab title" required class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-600">
        <textarea name="scenario" placeholder="Scenario (Markdown)" rows="2" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-600"></textarea>
        <textarea name="instructions" placeholder="Task / instructions (Markdown)" rows="2" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-600"></textarea>
        <div class="grid grid-cols-3 gap-2">
          <select name="difficulty" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm text-white"><option>Beginner</option><option>Intermediate</option><option>Advanced</option></select>
          <input name="points" type="number" value="100" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm text-white">
          <input name="flag" placeholder="flag{{...}}" required class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm font-mono text-white placeholder-slate-600">
        </div>
        <input name="hint" placeholder="Optional hint" class="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-600">
        <button class="rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-900">+ Add lab</button>
      </form>''')

    danger = card(f'''<div class="flex items-center justify-between">
        <div><h3 class="font-semibold text-white">Delete course</h3><p class="text-sm text-slate-500">Removes the course and all its content.</p></div>
        <form method="post" action="/admin/courses/{cid}/delete" onsubmit="return confirm('Delete this course and ALL its content?')">
          <input type="hidden" name="csrf" value="{esc(csrf)}">
          <button class="rounded-lg border border-rose-500/40 text-rose-300 hover:bg-rose-500/10 px-4 py-2 text-sm">Delete course</button></form>
      </div>''', extra="border-rose-500/20")

    body = f'''
    {page_header(f"Manage: {esc(course['title'])}", actions=f'<a href="/courses/{esc(course["slug"])}" class="rounded-lg border border-slate-700 hover:border-slate-500 px-4 py-2 text-sm text-slate-200">View public page →</a>')}
    {_tab_nav("/admin/courses")}{flash(req)}
    <div class="grid lg:grid-cols-2 gap-6">
      <div class="space-y-6">{settings}{labs_card}</div>
      <div class="space-y-6">{curriculum}{danger}</div>
    </div>'''
    return html(layout("Edit Course", body, req))


@app.post("/admin/courses/<cid>")
def admin_course_update(req):
    guard = _staff(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    cid = int(req.params["cid"])
    f = req.form
    db.execute(
        """UPDATE courses SET title=?, summary=?, description=?, category=?, difficulty=?,
           duration_hours=?, pass_threshold=?, icon=?, published=? WHERE id=?""",
        (f.get("title","").strip(), f.get("summary","").strip(), f.get("description","").strip(),
         f.get("category","General").strip() or "General", f.get("difficulty","Beginner"),
         int(f.get("duration_hours") or 8), int(f.get("pass_threshold") or 70),
         (f.get("icon") or "🛡️").strip() or "🛡️", 1 if f.get("published") else 0, cid))
    return redirect(f"/admin/courses/{cid}?msg=" + quote("Settings saved."))


@app.post("/admin/courses/<cid>/delete")
def admin_course_delete(req):
    guard = _staff(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    db.execute("DELETE FROM courses WHERE id=?", (int(req.params["cid"]),))
    return redirect("/admin/courses?msg=" + quote("Course deleted."))


@app.post("/admin/courses/<cid>/modules")
def admin_module_create(req):
    guard = _staff(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    cid = int(req.params["cid"])
    title = (req.form.get("title") or "").strip()
    if title:
        pos = db.query_one("SELECT COALESCE(MAX(position),0)+1 p FROM modules WHERE course_id=?", (cid,))["p"]
        db.execute("INSERT INTO modules (course_id,title,position) VALUES (?,?,?)", (cid, title, pos))
    return redirect(f"/admin/courses/{cid}?msg=" + quote("Module added."))


@app.post("/admin/modules/<mid>/delete")
def admin_module_delete(req):
    guard = _staff(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    cid = req.form.get("cid", "")
    db.execute("DELETE FROM modules WHERE id=?", (int(req.params["mid"]),))
    return redirect(f"/admin/courses/{cid}?msg=" + quote("Module deleted."))


@app.post("/admin/modules/<mid>/lessons")
def admin_lesson_create(req):
    guard = _staff(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    mid = int(req.params["mid"])
    cid = req.form.get("cid", "")
    title = (req.form.get("title") or "").strip()
    if title:
        pos = db.query_one("SELECT COALESCE(MAX(position),0)+1 p FROM lessons WHERE module_id=?", (mid,))["p"]
        db.execute("INSERT INTO lessons (module_id,title,content,position) VALUES (?,?,?,?)",
                   (mid, title, req.form.get("content","").strip(), pos))
    return redirect(f"/admin/courses/{cid}?msg=" + quote("Lesson added."))


@app.post("/admin/lessons/<lid>/delete")
def admin_lesson_delete(req):
    guard = _staff(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    cid = req.form.get("cid", "")
    db.execute("DELETE FROM lessons WHERE id=?", (int(req.params["lid"]),))
    return redirect(f"/admin/courses/{cid}?msg=" + quote("Lesson deleted."))


@app.post("/admin/courses/<cid>/labs")
def admin_lab_create(req):
    guard = _staff(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    cid = int(req.params["cid"])
    f = req.form
    title = (f.get("title") or "").strip()
    flag = (f.get("flag") or "").strip()
    if not title or not flag:
        return redirect(f"/admin/courses/{cid}?err=" + quote("Lab title and flag are required."))
    slug = _slugify(title)
    base, n = slug, 2
    while db.query_one("SELECT 1 FROM labs WHERE slug=?", (slug,)):
        slug = f"{base}-{n}"; n += 1
    pos = db.query_one("SELECT COALESCE(MAX(position),0)+1 p FROM labs WHERE course_id=?", (cid,))["p"]
    db.execute(
        """INSERT INTO labs (course_id,title,slug,scenario,instructions,difficulty,points,flag_hash,hint,position)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (cid, title, slug, f.get("scenario","").strip(), f.get("instructions","").strip(),
         f.get("difficulty","Beginner"), int(f.get("points") or 100),
         services.hash_flag(flag), f.get("hint","").strip(), pos))
    return redirect(f"/admin/courses/{cid}?msg=" + quote("Lab added."))


@app.post("/admin/labs/<lid>/delete")
def admin_lab_delete(req):
    guard = _staff(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    cid = req.form.get("cid", "")
    db.execute("DELETE FROM labs WHERE id=?", (int(req.params["lid"]),))
    return redirect(f"/admin/courses/{cid}?msg=" + quote("Lab deleted."))


# --------------------------------------------------------------------------- #
# Labs overview
# --------------------------------------------------------------------------- #
@app.get("/admin/labs")
def admin_labs(req):
    guard = _staff(req)
    if guard:
        return guard
    labs = db.query(
        """SELECT lb.*, c.title AS course_title FROM labs lb
           JOIN courses c ON c.id=lb.course_id ORDER BY c.title, lb.position""")
    rows = "".join(f'''<tr class="border-t border-slate-800">
        <td class="py-3 pr-4 text-slate-100">{esc(lb["title"])}</td>
        <td class="py-3 pr-4 text-slate-400 text-sm">{esc(lb["course_title"])}</td>
        <td class="py-3 pr-4">{badge(lb["difficulty"], lb["difficulty"])}</td>
        <td class="py-3 pr-4 text-slate-400 text-sm">{lb["points"]} pts</td>
        <td class="py-3 text-right"><a href="/admin/courses/{lb["course_id"]}" class="text-cyan-400 hover:text-cyan-300 text-sm">Manage →</a></td>
      </tr>''' for lb in labs) or '<tr><td class="py-3 text-slate-500">No labs yet.</td></tr>'
    body = f'''{page_header("Labs")}{_tab_nav("/admin/labs")}{flash(req)}
      {card(f'<table class="w-full text-sm"><thead><tr class="text-slate-500 text-xs text-left"><th class="pb-2">Lab</th><th>Course</th><th>Difficulty</th><th>Points</th><th></th></tr></thead><tbody>{rows}</tbody></table>')}'''
    return html(layout("Labs", body, req))


# --------------------------------------------------------------------------- #
# Certificates admin
# --------------------------------------------------------------------------- #
@app.get("/admin/certificates")
def admin_certs(req):
    guard = _staff(req)
    if guard:
        return guard
    certs = db.query(
        """SELECT ce.*, u.name AS student, c.title AS course FROM certificates ce
           JOIN users u ON u.id=ce.user_id JOIN courses c ON c.id=ce.course_id
           ORDER BY ce.issued_at DESC""")
    csrf = _csrf(req)
    rows = ""
    for c in certs:
        if c["revoked"]:
            action = f'''<form method="post" action="/admin/certificates/{c["id"]}/reinstate"><input type="hidden" name="csrf" value="{esc(csrf)}">
              <button class="text-xs text-emerald-400 hover:text-emerald-300">Reinstate</button></form>'''
            status = '<span class="text-xs text-rose-300">Revoked</span>'
        else:
            action = f'''<form method="post" action="/admin/certificates/{c["id"]}/revoke"><input type="hidden" name="csrf" value="{esc(csrf)}">
              <button class="text-xs text-rose-400 hover:text-rose-300">Revoke</button></form>'''
            status = '<span class="text-xs text-emerald-300">Valid</span>'
        rows += f'''<tr class="border-t border-slate-800">
          <td class="py-3 pr-4 text-slate-100">{esc(c["student"])}</td>
          <td class="py-3 pr-4 text-slate-400 text-sm">{esc(c["course"])}</td>
          <td class="py-3 pr-4 font-mono text-xs text-cyan-300">{esc(c["code"])}</td>
          <td class="py-3 pr-4">{status}</td>
          <td class="py-3 text-right">{action}</td></tr>'''
    rows_html = rows or '<tr><td class="py-3 text-slate-500">No certificates.</td></tr>'
    body = f'''{page_header("Certificates")}{_tab_nav("/admin/certificates")}{flash(req)}
      {card(f'<table class="w-full text-sm"><thead><tr class="text-slate-500 text-xs text-left"><th class="pb-2">Student</th><th>Course</th><th>Credential</th><th>Status</th><th></th></tr></thead><tbody>{rows_html}</tbody></table>')}'''
    return html(layout("Certificates", body, req))


@app.post("/admin/certificates/<cid>/revoke")
def admin_cert_revoke(req):
    guard = _staff(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    db.execute("UPDATE certificates SET revoked=1 WHERE id=?", (int(req.params["cid"]),))
    return redirect("/admin/certificates?msg=" + quote("Certificate revoked."))


@app.post("/admin/certificates/<cid>/reinstate")
def admin_cert_reinstate(req):
    guard = _staff(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    db.execute("UPDATE certificates SET revoked=0 WHERE id=?", (int(req.params["cid"]),))
    return redirect("/admin/certificates?msg=" + quote("Certificate reinstated."))


# --------------------------------------------------------------------------- #
# Users (ADMIN only)
# --------------------------------------------------------------------------- #
@app.get("/admin/users")
def admin_users(req):
    guard = _admin_only(req)
    if guard:
        return guard
    users = db.query("SELECT * FROM users ORDER BY id")
    csrf = _csrf(req)
    rows = ""
    for u in users:
        opts = "".join(
            f'<option value="{r}" {"selected" if u["role"]==r else ""}>{r}</option>'
            for r in ("STUDENT", "INSTRUCTOR", "ADMIN"))
        rows += f'''<tr class="border-t border-slate-800">
          <td class="py-3 pr-4 text-slate-100">{esc(u["name"])}</td>
          <td class="py-3 pr-4 text-slate-400 text-sm">{esc(u["email"])}</td>
          <td class="py-3 pr-4">
            <form method="post" action="/admin/users/{u["id"]}/role" class="flex items-center gap-2">
              <input type="hidden" name="csrf" value="{esc(csrf)}">
              <select name="role" class="rounded-lg bg-slate-950 border border-slate-700 px-2 py-1 text-sm text-white">{opts}</select>
              <button class="text-xs text-cyan-400 hover:text-cyan-300">Update</button>
            </form></td>
          <td class="py-3 text-slate-500 text-xs">{esc(u["created_at"])}</td></tr>'''
    body = f'''{page_header("Users", "Manage roles and access.")}{_tab_nav("/admin/users")}{flash(req)}
      {card(f'<table class="w-full text-sm"><thead><tr class="text-slate-500 text-xs text-left"><th class="pb-2">Name</th><th>Email</th><th>Role</th><th>Joined</th></tr></thead><tbody>{rows}</tbody></table>')}'''
    return html(layout("Users", body, req))


@app.post("/admin/users/<uid>/role")
def admin_user_role(req):
    guard = _admin_only(req)
    if guard:
        return guard
    e = auth.check_csrf(req)
    if e:
        return e
    role = req.form.get("role", "STUDENT")
    if role not in ("STUDENT", "INSTRUCTOR", "ADMIN"):
        role = "STUDENT"
    db.execute("UPDATE users SET role=? WHERE id=?", (role, int(req.params["uid"])))
    return redirect("/admin/users?msg=" + quote("Role updated."))
