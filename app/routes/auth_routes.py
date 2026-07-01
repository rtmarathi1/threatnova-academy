"""Authentication routes: register, login, logout."""
from __future__ import annotations

import sqlite3
from urllib.parse import quote

from . import app
from .. import auth
from ..server import html, redirect
from ..templates import layout, esc, card


def _auth_shell(title, inner):
    return f'''
    <div class="min-h-[70vh] flex items-center justify-center">
      <div class="w-full max-w-md">
        <div class="text-center mb-6">
          <div class="text-3xl">🛡️</div>
          <h1 class="mt-2 text-2xl font-bold text-white">{esc(title)}</h1>
        </div>
        {card(inner)}
      </div>
    </div>'''


def _field(label, name, type_="text", value="", placeholder="", required=True):
    req_attr = "required" if required else ""
    return f'''
      <label class="block mb-4">
        <span class="text-sm text-slate-300">{esc(label)}</span>
        <input type="{type_}" name="{name}" value="{esc(value)}" placeholder="{esc(placeholder)}" {req_attr}
               class="mt-1 w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2.5 text-white
                      placeholder-slate-600 focus:border-cyan-500 focus:outline-none">
      </label>'''


@app.get("/register")
def register_form(req, error=None, values=None):
    if req.user:
        return redirect("/dashboard")
    values = values or {}
    err_html = f'<div class="mb-4 rounded-lg bg-rose-500/10 border border-rose-500/30 px-3 py-2 text-sm text-rose-200">{esc(error)}</div>' if error else ""
    inner = f'''
      {err_html}
      <form method="post" action="/register">
        {_field("Full name", "name", value=values.get("name",""), placeholder="Alex Rivera")}
        {_field("Email", "email", "email", values.get("email",""), "you@company.com")}
        {_field("Password", "password", "password", placeholder="At least 8 characters")}
        <button class="w-full rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 py-2.5 font-semibold text-slate-900">Create account</button>
      </form>
      <p class="mt-4 text-center text-sm text-slate-400">Already have an account?
        <a href="/login" class="text-cyan-400 hover:text-cyan-300">Log in</a></p>'''
    return html(layout("Create your account", _auth_shell("Create your account", inner), req))


@app.post("/register")
def register_submit(req):
    name = (req.form.get("name") or "").strip()
    email = (req.form.get("email") or "").strip().lower()
    password = req.form.get("password") or ""
    values = {"name": name, "email": email}

    if len(name) < 2:
        return register_form(req, "Please enter your full name.", values)
    if "@" not in email or "." not in email:
        return register_form(req, "Please enter a valid email address.", values)
    if len(password) < 8:
        return register_form(req, "Password must be at least 8 characters.", values)

    try:
        uid = auth.create_user(name, email, password, role="STUDENT")
    except sqlite3.IntegrityError:
        return register_form(req, "An account with that email already exists.", values)

    token = auth.create_session(uid)
    res = redirect("/dashboard?msg=" + quote("Welcome to ThreatNova CyberLabs!"))
    res.set_cookie(auth.SESSION_COOKIE, token, max_age=auth.SESSION_DAYS * 86400)
    return res


@app.get("/login")
def login_form(req, error=None, values=None):
    if req.user:
        return redirect("/dashboard")
    values = values or {}
    next_url = req.query.get("next", "/dashboard")
    err_html = f'<div class="mb-4 rounded-lg bg-rose-500/10 border border-rose-500/30 px-3 py-2 text-sm text-rose-200">{esc(error)}</div>' if error else ""
    inner = f'''
      {err_html}
      <form method="post" action="/login">
        <input type="hidden" name="next" value="{esc(next_url)}">
        {_field("Email", "email", "email", values.get("email",""), "you@company.com")}
        {_field("Password", "password", "password")}
        <button class="w-full rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 py-2.5 font-semibold text-slate-900">Log in</button>
      </form>
      <p class="mt-4 text-center text-sm text-slate-400">New to ThreatNova?
        <a href="/register" class="text-cyan-400 hover:text-cyan-300">Create an account</a></p>
      <div class="mt-4 rounded-lg bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-slate-500">
        <div class="font-medium text-slate-400 mb-1">Demo accounts</div>
        admin@threatnova.io · instructor@threatnova.io · student@threatnova.io<br>
        password for all: <span class="font-mono text-slate-300">Passw0rd!</span>
      </div>'''
    return html(layout("Log in", _auth_shell("Welcome back", inner), req))


@app.post("/login")
def login_submit(req):
    email = (req.form.get("email") or "").strip().lower()
    password = req.form.get("password") or ""
    next_url = req.form.get("next") or "/dashboard"

    user = auth.authenticate(email, password)
    if not user:
        return login_form(req, "Invalid email or password.", {"email": email})

    token = auth.create_session(user["id"])
    if not next_url.startswith("/"):
        next_url = "/dashboard"
    res = redirect(next_url)
    res.set_cookie(auth.SESSION_COOKIE, token, max_age=auth.SESSION_DAYS * 86400)
    return res


@app.get("/logout")
def logout(req):
    if req.session:
        auth.destroy_session(req.session["token"])
    res = redirect("/?msg=" + quote("You have been logged out."))
    res.delete_cookie(auth.SESSION_COOKIE)
    return res
