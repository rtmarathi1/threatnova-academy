# 🛡️ ThreatNova CyberLabs

A full **cybersecurity training & certification platform** for **ThreatNova Security / ThreatNova Academy**.
Students enroll in certification tracks, work through lessons and hands-on capture-the-flag labs, track
their progress, and earn **verifiable certificates**. Instructors and admins manage all content, users,
and credentials from a built-in admin console.

Built with a **zero-dependency stack** — only the Python standard library and SQLite. No `pip install`,
no build step. The UI is server-rendered HTML styled with Tailwind (via CDN) for a modern dark theme.

---

## ✨ Features

### Student portal
- Register / log in (secure PBKDF2-hashed passwords, server-side sessions)
- Browse the course catalogue and enroll in certification tracks
- Read structured lessons (Markdown content) and mark them complete
- Solve **flag-based labs** (CTF style) with scoring and hints
- Live **progress tracking** per course
- Personal dashboard with stats (courses, labs solved, points, certificates)
- View & print/download earned certificates

### Certification engine
- Automatically issues a certificate when a student passes a course's completion threshold
- Every certificate has a unique credential ID (e.g. `TN-A1B2-C3D4-E5F6`)
- **Public verification page** at `/verify` — anyone can confirm a credential's authenticity
- Printable certificate page (`window.print()` → save as PDF)

### Instructor / Admin panel (`/admin`)
- Dashboard with platform-wide statistics and recent activity
- Create & edit courses; toggle published/draft
- Course builder: add/remove modules, lessons, and labs inline
- Labs overview across all courses
- Certificate administration: revoke / reinstate credentials
- **User management & role assignment** (ADMIN only): STUDENT / INSTRUCTOR / ADMIN

### Security
- PBKDF2-HMAC-SHA256 password hashing with per-user salt
- Opaque server-side session tokens in HttpOnly cookies
- CSRF tokens required on all state-changing POST requests
- Role-based access control on every protected route
- Static file serving guarded against path traversal

---

## 🚀 Running the platform

**Requirements:** Python **3.12+** (uses modern f-string features). No other dependencies.

```bash
cd threatnova-cyberlabs
python3.12 run.py
```

Then open **http://localhost:8000**.

Custom host/port:

```bash
PORT=9000 HOST=127.0.0.1 python3.12 run.py
```

On first launch the app creates `data/cyberlabs.db` and seeds it with demo content
(6 certification tracks, 12 labs, and demo accounts).

### Demo accounts

| Role       | Email                      | Password    |
|------------|----------------------------|-------------|
| Admin      | `admin@threatnova.io`      | `Passw0rd!` |
| Instructor | `instructor@threatnova.io` | `Passw0rd!` |
| Student    | `student@threatnova.io`    | `Passw0rd!` |

> To reset the database, stop the server and delete the `data/` folder — it will be
> re-seeded on the next start.

---

## 📚 Seeded certification tracks

1. **Cybersecurity Fundamentals** — CIA triad, threats, controls, defense in depth
2. **Web Application Security: OWASP Top 10** — SQLi, broken access control, XSS, misconfig
3. **Network Security & Defense** — TCP/IP, segmentation, firewalls, IDS/IPS
4. **Ethical Hacking & Penetration Testing** — methodology, recon, exploitation, reporting
5. **SOC Analyst & Incident Response** — SIEM, IOCs, the NIST IR lifecycle
6. **Cryptography Essentials** — symmetric/asymmetric, hashing, key exchange

Each track ships with lessons and self-contained flag labs (solvable without external
infrastructure). Instructors can add unlimited additional content through the admin panel.

---

## 🗂️ Project structure

```
threatnova-cyberlabs/
├── run.py                  # entry point (init DB, seed, start server)
├── app/
│   ├── server.py           # HTTP framework: Request/Response, router, static files
│   ├── db.py               # SQLite connection + full schema
│   ├── auth.py             # password hashing, sessions, CSRF, role guards
│   ├── services.py         # progress tracking, scoring, certification engine
│   ├── templates.py        # layout + reusable UI components (Tailwind)
│   ├── markup.py           # minimal Markdown → HTML renderer
│   ├── seed.py             # demo users + course catalogue
│   └── routes/
│       ├── public.py       # landing, /verify
│       ├── auth_routes.py  # register, login, logout
│       ├── student.py      # dashboard, courses, lessons, labs, flag submission
│       ├── certificates.py # certificate list + printable certificate
│       └── admin.py        # instructor/admin console
└── data/                   # SQLite database (created at runtime)
```

---

## 🧱 Data model (SQLite)

`users`, `sessions`, `courses`, `modules`, `lessons`, `labs`, `enrollments`,
`lesson_progress`, `lab_submissions`, `certificates`.

Foreign keys with `ON DELETE CASCADE` keep content consistent (deleting a course removes
its modules, lessons, labs, enrollments, and certificates).

---

## 🛣️ Notes & next steps

This is a self-contained platform that runs anywhere Python does. When you're ready to
grow it, natural extensions include:

- Swapping SQLite for PostgreSQL for multi-instance deployments
- Live lab environments (per-student Docker/Kubernetes sandboxes)
- Email verification & password reset
- Leaderboards and team/cohort management
- Serving behind a production WSGI/ASGI server + reverse proxy (TLS)

---

© ThreatNova Security — CyberLabs Training Platform.
