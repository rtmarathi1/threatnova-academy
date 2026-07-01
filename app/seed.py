"""
Seed data for ThreatNova CyberLabs.

Creates demo accounts and a catalogue of real cybersecurity certification
tracks with modules, lessons, and self-contained flag-based labs.

The seed is idempotent-ish: it only runs when the database has no courses.
"""
from __future__ import annotations

from . import db, auth
from .services import hash_flag


# --------------------------------------------------------------------------- #
# Course catalogue definition
# --------------------------------------------------------------------------- #
COURSES = [
    {
        "slug": "cybersecurity-fundamentals",
        "title": "Cybersecurity Fundamentals",
        "category": "Foundations",
        "difficulty": "Beginner",
        "icon": "🛡️",
        "duration_hours": 6,
        "pass_threshold": 70,
        "summary": "Build a rock-solid foundation: the CIA triad, threats, controls, and core defensive thinking.",
        "description": (
            "## Why this track\n"
            "Every security career starts with the fundamentals. This track gives you the vocabulary, "
            "mental models, and core concepts you will use every day as a security professional.\n\n"
            "## What you will learn\n"
            "- The **CIA triad** and how it drives every security decision\n"
            "- Common **threats, threat actors, and attack vectors**\n"
            "- **Security controls**: preventive, detective, and corrective\n"
            "- How to think like a defender **and** an attacker\n"
        ),
        "modules": [
            {
                "title": "Core Concepts",
                "lessons": [
                    {
                        "title": "The CIA Triad",
                        "content": (
                            "## The foundation of security\n"
                            "The **CIA triad** describes the three goals of every security program:\n\n"
                            "- **Confidentiality** — only authorized parties can read data (encryption, access control).\n"
                            "- **Integrity** — data cannot be altered without detection (hashing, digital signatures).\n"
                            "- **Availability** — systems and data are accessible when needed (redundancy, DDoS protection).\n\n"
                            "### Applying it\n"
                            "When you assess any system, ask: *how is each pillar protected, and what happens if it fails?* "
                            "A ransomware attack, for example, primarily breaks **availability** (and often confidentiality).\n\n"
                            "### Key terms\n"
                            "- **Vulnerability** — a weakness.\n"
                            "- **Threat** — something that can exploit a weakness.\n"
                            "- **Risk** — the likelihood and impact of a threat exploiting a vulnerability.\n"
                        ),
                    },
                    {
                        "title": "Threats, Actors & Attack Vectors",
                        "content": (
                            "## Who attacks, and how\n"
                            "**Threat actors** range from opportunistic script kiddies to organized crime and "
                            "nation-state groups (APTs). Their motivations differ: money, espionage, disruption, or ideology.\n\n"
                            "## Common attack vectors\n"
                            "- **Phishing** — the #1 initial access method.\n"
                            "- **Malware** — viruses, worms, trojans, ransomware.\n"
                            "- **Credential attacks** — brute force, password spraying, credential stuffing.\n"
                            "- **Exploiting vulnerabilities** — unpatched software, misconfigurations.\n\n"
                            "### The attack lifecycle\n"
                            "Recon → Initial access → Execution → Persistence → Privilege escalation → "
                            "Lateral movement → Exfiltration. Frameworks like **MITRE ATT&CK** map these stages in detail.\n"
                        ),
                    },
                    {
                        "title": "Security Controls & Defense in Depth",
                        "content": (
                            "## Layering your defenses\n"
                            "**Defense in depth** means no single control is your only protection. Controls are grouped as:\n\n"
                            "- **Preventive** — stop incidents (firewalls, MFA, patching).\n"
                            "- **Detective** — spot incidents (IDS, logging, SIEM).\n"
                            "- **Corrective** — recover from incidents (backups, incident response).\n\n"
                            "## Least privilege & zero trust\n"
                            "Give users and systems the **minimum access** they need. Modern architectures assume "
                            "breach and verify every request — the core idea behind **zero trust**.\n"
                        ),
                    },
                ],
            },
        ],
        "labs": [
            {
                "title": "Decode the Intercepted Message",
                "difficulty": "Beginner",
                "points": 100,
                "scenario": (
                    "Your SOC intercepted a suspicious string being exfiltrated from a workstation. "
                    "It looks Base64-encoded:\n\n"
                    "```\nZmxhZ3tiYXNlNjRfaXNfbm90X2VuY3J5cHRpb259\n```\n"
                ),
                "instructions": (
                    "Base64 is an **encoding**, not encryption — anyone can reverse it. "
                    "Decode the string to reveal the flag and submit it.\n\n"
                    "Tip: try `echo '<string>' | base64 -d` in a terminal, or an online decoder."
                ),
                "hint": "The flag format is flag{...}. Decode the Base64 to get plaintext.",
                "flag": "flag{base64_is_not_encryption}",
            },
            {
                "title": "Classify the Risk",
                "difficulty": "Beginner",
                "points": 80,
                "scenario": (
                    "A web server runs an outdated library with a publicly known remote code execution bug. "
                    "The server is internet-facing and processes customer payments.\n"
                ),
                "instructions": (
                    "In risk terms, the outdated library is the **vulnerability** and an attacker exploiting it is the "
                    "**threat**. What single word describes *the likelihood and impact of that threat exploiting the "
                    "vulnerability*?\n\n"
                    "Submit your answer wrapped as `flag{word}` (lowercase)."
                ),
                "hint": "Vulnerability + Threat + Impact = this concept. It rhymes with 'brisk'.",
                "flag": "flag{risk}",
            },
        ],
    },
    {
        "slug": "web-application-security",
        "title": "Web Application Security: OWASP Top 10",
        "category": "Web Security",
        "difficulty": "Intermediate",
        "icon": "🕸️",
        "duration_hours": 10,
        "pass_threshold": 75,
        "summary": "Attack and defend modern web apps. Master injection, broken access control, XSS, and more.",
        "description": (
            "## Hack the web, then fix it\n"
            "The **OWASP Top 10** is the industry-standard list of the most critical web application security risks. "
            "In this track you will understand each risk, see how it is exploited, and learn how to remediate it.\n\n"
            "## Highlights\n"
            "- Injection (SQLi) and how parameterized queries stop it\n"
            "- Broken access control (IDOR, privilege escalation)\n"
            "- Cross-site scripting (XSS) and output encoding\n"
            "- Security misconfiguration and secure headers\n"
        ),
        "modules": [
            {
                "title": "Injection & Access Control",
                "lessons": [
                    {
                        "title": "SQL Injection",
                        "content": (
                            "## What is SQL injection?\n"
                            "**SQL injection (SQLi)** happens when untrusted input is concatenated directly into a SQL "
                            "query. An attacker can then change the query's logic.\n\n"
                            "### Vulnerable code\n"
                            "```\nquery = \"SELECT * FROM users WHERE name = '\" + username + \"'\"\n```\n"
                            "If `username` is `' OR '1'='1`, the query returns **all** users.\n\n"
                            "## The fix: parameterized queries\n"
                            "```\ncur.execute(\"SELECT * FROM users WHERE name = ?\", (username,))\n```\n"
                            "The database treats input strictly as **data**, never as code. Also apply least-privilege "
                            "DB accounts and input validation as defense in depth.\n"
                        ),
                    },
                    {
                        "title": "Broken Access Control & IDOR",
                        "content": (
                            "## Broken access control\n"
                            "Ranked **#1** in the OWASP Top 10. It occurs when users can act outside their intended "
                            "permissions.\n\n"
                            "### IDOR (Insecure Direct Object Reference)\n"
                            "If `/invoice?id=1001` shows your invoice, what happens when you change it to `1002`? "
                            "If the app does not verify ownership, you just read someone else's data.\n\n"
                            "## Defenses\n"
                            "- Enforce authorization checks **server-side** on every request.\n"
                            "- Deny by default; grant access explicitly.\n"
                            "- Use unpredictable identifiers where appropriate, but never rely on them alone.\n"
                        ),
                    },
                ],
            },
            {
                "title": "Client-Side & Configuration Risks",
                "lessons": [
                    {
                        "title": "Cross-Site Scripting (XSS)",
                        "content": (
                            "## XSS in a nutshell\n"
                            "**XSS** lets an attacker run JavaScript in a victim's browser by injecting script into "
                            "pages the victim trusts.\n\n"
                            "- **Stored XSS** — payload saved on the server (e.g., a comment).\n"
                            "- **Reflected XSS** — payload echoed from the request.\n"
                            "- **DOM XSS** — client-side JS writes untrusted data to the DOM.\n\n"
                            "## Defenses\n"
                            "- **Output-encode** data for the context (HTML, attribute, JS).\n"
                            "- Use a **Content Security Policy (CSP)**.\n"
                            "- Treat all user input as untrusted.\n"
                        ),
                    },
                    {
                        "title": "Security Misconfiguration",
                        "content": (
                            "## Misconfiguration\n"
                            "Default credentials, verbose error messages, open cloud buckets, and missing security "
                            "headers all fall here.\n\n"
                            "## Hardening checklist\n"
                            "- Remove defaults and sample apps.\n"
                            "- Set headers: `Content-Security-Policy`, `X-Content-Type-Options`, `Strict-Transport-Security`.\n"
                            "- Disable directory listing and detailed stack traces in production.\n"
                            "- Automate configuration with infrastructure-as-code and scan for drift.\n"
                        ),
                    },
                ],
            },
        ],
        "labs": [
            {
                "title": "Bypass the Login (SQLi)",
                "difficulty": "Intermediate",
                "points": 150,
                "scenario": (
                    "A legacy admin panel builds its login query like this:\n\n"
                    "```\nSELECT * FROM users WHERE user='<input>' AND pass='<input>'\n```\n"
                    "There is no input sanitization."
                ),
                "instructions": (
                    "Craft a classic SQL injection payload for the **username** field that always evaluates true and "
                    "comments out the password check. A canonical answer is the tautology payload.\n\n"
                    "Submit the payload as `flag{PAYLOAD}` where PAYLOAD is exactly: `' OR '1'='1`\n"
                    "So the flag is `flag{' OR '1'='1}`."
                ),
                "hint": "The classic tautology: ' OR '1'='1",
                "flag": "flag{' OR '1'='1}",
            },
            {
                "title": "Spot the IDOR",
                "difficulty": "Intermediate",
                "points": 120,
                "scenario": (
                    "You are logged in as user 57. Your profile loads from `/api/users/57/profile`. "
                    "Out of curiosity you change the number and the server happily returns another user's data.\n"
                ),
                "instructions": (
                    "This vulnerability class — accessing objects by manipulating identifiers without an authorization "
                    "check — has a well-known 4-letter acronym. Submit it lowercase as `flag{acronym}`."
                ),
                "hint": "Insecure Direct Object Reference.",
                "flag": "flag{idor}",
            },
        ],
    },
    {
        "slug": "network-security-defense",
        "title": "Network Security & Defense",
        "category": "Blue Team",
        "difficulty": "Intermediate",
        "icon": "🌐",
        "duration_hours": 8,
        "pass_threshold": 70,
        "summary": "Understand protocols, segmentation, firewalls, and how to detect malicious traffic.",
        "description": (
            "## Defend the network\n"
            "Networks are where attacks travel. This track covers the protocols attackers abuse, how to segment and "
            "firewall your environment, and how to read traffic to catch intrusions.\n"
        ),
        "modules": [
            {
                "title": "Protocols & Architecture",
                "lessons": [
                    {
                        "title": "TCP/IP & Ports You Must Know",
                        "content": (
                            "## The model\n"
                            "The **TCP/IP** stack (Link, Internet, Transport, Application) moves your data across networks. "
                            "**TCP** is reliable and connection-oriented; **UDP** is fast and connectionless.\n\n"
                            "## Common ports\n"
                            "- `22` SSH, `80` HTTP, `443` HTTPS\n"
                            "- `53` DNS, `25` SMTP, `3389` RDP\n\n"
                            "Knowing default ports helps you read scans and firewall rules quickly.\n"
                        ),
                    },
                    {
                        "title": "Segmentation & Firewalls",
                        "content": (
                            "## Segmentation\n"
                            "Divide the network into zones (e.g., DMZ, internal, management). If one zone is breached, "
                            "segmentation limits **lateral movement**.\n\n"
                            "## Firewalls\n"
                            "Firewalls enforce allow/deny rules. Prefer **default-deny**: block everything, then allow only "
                            "what is required. Next-gen firewalls add application awareness and intrusion prevention.\n"
                        ),
                    },
                ],
            },
            {
                "title": "Detection",
                "lessons": [
                    {
                        "title": "IDS/IPS & Reading Traffic",
                        "content": (
                            "## IDS vs IPS\n"
                            "- **IDS** detects and alerts.\n"
                            "- **IPS** detects and **blocks** inline.\n\n"
                            "## Signatures vs anomalies\n"
                            "Signature-based detection matches known patterns; anomaly-based detection flags deviations "
                            "from a baseline. Tools like **Wireshark** and **Zeek** let analysts inspect packets and flows "
                            "to confirm alerts.\n"
                        ),
                    },
                ],
            },
        ],
        "labs": [
            {
                "title": "Name That Port",
                "difficulty": "Beginner",
                "points": 90,
                "scenario": (
                    "An nmap scan of a server shows a single open port used for encrypted remote shell access:\n\n"
                    "```\nPORT   STATE SERVICE\n22/tcp open  ssh\n```\n"
                ),
                "instructions": (
                    "Which protocol runs on TCP port 22 by default? Submit lowercase as `flag{protocol}`."
                ),
                "hint": "Secure Shell.",
                "flag": "flag{ssh}",
            },
            {
                "title": "Default-Deny Principle",
                "difficulty": "Intermediate",
                "points": 110,
                "scenario": (
                    "You are writing firewall rules for a new DMZ. Best practice says to block all traffic first, then "
                    "explicitly permit only required flows.\n"
                ),
                "instructions": (
                    "What is the two-word name (hyphenated) for this best-practice firewall posture? "
                    "Submit as `flag{answer}` in lowercase, e.g. `flag{some-thing}`."
                ),
                "hint": "The opposite of 'default-allow'.",
                "flag": "flag{default-deny}",
            },
        ],
    },
    {
        "slug": "ethical-hacking-pentest",
        "title": "Ethical Hacking & Penetration Testing",
        "category": "Red Team",
        "difficulty": "Advanced",
        "icon": "🎯",
        "duration_hours": 12,
        "pass_threshold": 80,
        "summary": "Think like an attacker. Learn the pentest methodology, recon, exploitation, and reporting.",
        "description": (
            "## Offensive security, done ethically\n"
            "Penetration testers find weaknesses **before** criminals do — always with authorization. This advanced "
            "track walks the full engagement lifecycle and the mindset behind it.\n\n"
            "> ⚠️ Everything here is for authorized testing and education only. Never test systems you do not own or "
            "have explicit written permission to assess.\n"
        ),
        "modules": [
            {
                "title": "Methodology",
                "lessons": [
                    {
                        "title": "The Penetration Testing Lifecycle",
                        "content": (
                            "## Phases\n"
                            "1. **Scoping & rules of engagement** — authorization, targets, limits.\n"
                            "2. **Reconnaissance** — passive and active information gathering.\n"
                            "3. **Scanning & enumeration** — services, versions, users.\n"
                            "4. **Exploitation** — gain access.\n"
                            "5. **Post-exploitation** — privilege escalation, lateral movement.\n"
                            "6. **Reporting** — the deliverable that creates value.\n\n"
                            "The report is the product: clear findings, risk ratings, and actionable remediation.\n"
                        ),
                    },
                    {
                        "title": "Reconnaissance",
                        "content": (
                            "## Passive vs active\n"
                            "- **Passive recon** touches nothing owned by the target (OSINT, WHOIS, public records).\n"
                            "- **Active recon** interacts directly (port scans, banner grabbing).\n\n"
                            "## Tooling\n"
                            "`nmap` for scanning, `whois`/`dig` for infrastructure, and search engines / OSINT frameworks "
                            "for exposed data. Good recon makes every later phase easier.\n"
                        ),
                    },
                ],
            },
            {
                "title": "Exploitation",
                "lessons": [
                    {
                        "title": "From Foothold to Domain Admin",
                        "content": (
                            "## Privilege escalation\n"
                            "After initial access, attackers seek higher privileges via misconfigurations, weak service "
                            "permissions, or credential reuse.\n\n"
                            "## Lateral movement\n"
                            "Using harvested credentials or tokens to pivot across hosts. Detection relies on monitoring "
                            "authentication logs and unusual account behavior. Defenders counter with tiered admin models "
                            "and strong credential hygiene.\n"
                        ),
                    },
                ],
            },
        ],
        "labs": [
            {
                "title": "Caesar's Secret",
                "difficulty": "Intermediate",
                "points": 130,
                "scenario": (
                    "During recon you find a config comment left by a lazy developer. It is 'encrypted' with a Caesar "
                    "cipher shifted by 3:\n\n"
                    "```\niodj{fdhvdu_vkliw_wkuhh}\n```\n"
                ),
                "instructions": (
                    "Decrypt the Caesar cipher (shift each letter back by 3) to reveal the flag, then submit it.\n\n"
                    "Example: `d` shifted back by 3 is `a`."
                ),
                "hint": "Shift letters back by 3: i→f, o→l, d→a ... it starts with 'flag'.",
                "flag": "flag{caesar_shift_three}",
            },
            {
                "title": "Report or It Didn't Happen",
                "difficulty": "Beginner",
                "points": 90,
                "scenario": (
                    "A junior tester found five critical bugs but never wrote them up. The client received nothing "
                    "actionable.\n"
                ),
                "instructions": (
                    "Which final phase of the penetration testing lifecycle turns findings into client value? "
                    "Submit the single word as `flag{word}` (lowercase)."
                ),
                "hint": "It's the deliverable — the write-up.",
                "flag": "flag{reporting}",
            },
        ],
    },
    {
        "slug": "soc-analyst-incident-response",
        "title": "SOC Analyst & Incident Response",
        "category": "Blue Team",
        "difficulty": "Intermediate",
        "icon": "🚨",
        "duration_hours": 9,
        "pass_threshold": 75,
        "summary": "Triage alerts, investigate incidents, and follow the IR lifecycle like a pro analyst.",
        "description": (
            "## Life in the SOC\n"
            "Security Operations Center analysts are the front line. This track teaches alert triage, log analysis, and "
            "the incident response process used by professional teams.\n"
        ),
        "modules": [
            {
                "title": "Detection & Triage",
                "lessons": [
                    {
                        "title": "SIEM, Logs & Alert Triage",
                        "content": (
                            "## The SIEM\n"
                            "A **SIEM** aggregates logs from across the environment and correlates them into alerts. "
                            "Analysts triage: is this a true positive, false positive, or benign true positive?\n\n"
                            "## Good triage\n"
                            "- Gather context (user, host, time, indicators).\n"
                            "- Compare against baselines and threat intel.\n"
                            "- Escalate real incidents quickly with clear notes.\n"
                        ),
                    },
                    {
                        "title": "Indicators of Compromise",
                        "content": (
                            "## IOCs\n"
                            "**Indicators of Compromise** are artifacts that suggest a breach: malicious IPs, file hashes, "
                            "domains, or unusual registry keys.\n\n"
                            "## Pyramid of Pain\n"
                            "Blocking hashes is easy for attackers to bypass; disrupting their **TTPs** (tactics, "
                            "techniques, procedures) causes the most pain. Focus detection higher up the pyramid.\n"
                        ),
                    },
                ],
            },
            {
                "title": "Response",
                "lessons": [
                    {
                        "title": "The Incident Response Lifecycle",
                        "content": (
                            "## NIST IR phases\n"
                            "1. **Preparation**\n2. **Detection & Analysis**\n3. **Containment**\n"
                            "4. **Eradication**\n5. **Recovery**\n6. **Lessons Learned**\n\n"
                            "Containment often splits into short-term (isolate the host) and long-term (patch, rebuild). "
                            "The final phase feeds improvements back into preparation.\n"
                        ),
                    },
                ],
            },
        ],
        "labs": [
            {
                "title": "First Move After Detection",
                "difficulty": "Intermediate",
                "points": 120,
                "scenario": (
                    "Malware is confirmed active on a finance workstation and beaconing to a C2 server. You must stop it "
                    "spreading before eradicating it.\n"
                ),
                "instructions": (
                    "Which NIST IR phase focuses on **limiting the damage and stopping the spread** immediately after "
                    "analysis? Submit the single word as `flag{word}` (lowercase)."
                ),
                "hint": "It comes right after Detection & Analysis, before Eradication.",
                "flag": "flag{containment}",
            },
            {
                "title": "Hash the Evidence",
                "difficulty": "Intermediate",
                "points": 130,
                "scenario": (
                    "To preserve integrity of a collected malware sample, analysts compute a cryptographic hash. The team "
                    "standard is the 256-bit member of the SHA-2 family.\n"
                ),
                "instructions": (
                    "Name the specific hashing algorithm (letters + number, no spaces or hyphen) used to fingerprint the "
                    "evidence. Submit lowercase as `flag{algorithm}`, e.g. `flag{md5}`."
                ),
                "hint": "SHA-2 family, 256-bit output.",
                "flag": "flag{sha256}",
            },
        ],
    },
    {
        "slug": "cryptography-essentials",
        "title": "Cryptography Essentials",
        "category": "Core",
        "difficulty": "Intermediate",
        "icon": "🔐",
        "duration_hours": 7,
        "pass_threshold": 75,
        "summary": "Symmetric vs asymmetric crypto, hashing, TLS, and how to avoid crypto mistakes.",
        "description": (
            "## The math that protects data\n"
            "Cryptography underpins confidentiality and integrity everywhere. This track demystifies the building "
            "blocks and, crucially, how they are misused.\n"
        ),
        "modules": [
            {
                "title": "Primitives",
                "lessons": [
                    {
                        "title": "Symmetric vs Asymmetric",
                        "content": (
                            "## Symmetric\n"
                            "One shared secret key encrypts and decrypts (e.g., **AES**). Fast, but key distribution is hard.\n\n"
                            "## Asymmetric\n"
                            "A **public/private key pair** (e.g., **RSA**, **ECC**). Encrypt with the public key, decrypt with "
                            "the private key — solving key distribution and enabling digital signatures.\n\n"
                            "## In practice\n"
                            "TLS uses asymmetric crypto to exchange a symmetric session key, then switches to fast "
                            "symmetric encryption for the data.\n"
                        ),
                    },
                    {
                        "title": "Hashing & Integrity",
                        "content": (
                            "## Hash functions\n"
                            "A hash is a one-way function producing a fixed-length digest. Good hashes (**SHA-256**) are "
                            "collision-resistant. **MD5** and **SHA-1** are broken — do not use them for security.\n\n"
                            "## Passwords\n"
                            "Never store plaintext. Use a **slow, salted** password hash like **bcrypt**, **scrypt**, or "
                            "**PBKDF2** to resist brute force.\n"
                        ),
                    },
                ],
            },
        ],
        "labs": [
            {
                "title": "Pick the Right Password Hash",
                "difficulty": "Intermediate",
                "points": 120,
                "scenario": (
                    "A developer stored passwords as unsalted MD5. You must recommend a modern, deliberately slow, "
                    "salted password-hashing function whose name starts with 'b'.\n"
                ),
                "instructions": (
                    "Name the recommended algorithm and submit lowercase as `flag{name}`."
                ),
                "hint": "Blowfish-based, adaptive, widely recommended: b_____.",
                "flag": "flag{bcrypt}",
            },
            {
                "title": "Key Exchange Logic",
                "difficulty": "Advanced",
                "points": 150,
                "scenario": (
                    "During a TLS handshake, the parties must agree on a shared symmetric key without ever sending it in "
                    "the clear. They use a famous algorithm for this key exchange.\n"
                ),
                "instructions": (
                    "Name the classic key-exchange algorithm (two surnames joined by a hyphen). Submit lowercase as "
                    "`flag{name}`, e.g. `flag{rivest-shamir}`."
                ),
                "hint": "Two cryptographers, 1976, foundational key exchange: ______-______.",
                "flag": "flag{diffie-hellman}",
            },
        ],
    },
]


DEMO_USERS = [
    ("Nova Admin", "admin@threatnova.io", "Passw0rd!", "ADMIN"),
    ("Ivy Instructor", "instructor@threatnova.io", "Passw0rd!", "INSTRUCTOR"),
    ("Sam Student", "student@threatnova.io", "Passw0rd!", "STUDENT"),
]


def seed():
    """Populate the database if it is empty."""
    existing = db.query_one("SELECT COUNT(*) c FROM courses")["c"]
    if existing:
        return False

    # users
    user_ids = {}
    for name, email, pw, role in DEMO_USERS:
        if not auth.get_user_by_email(email):
            uid = auth.create_user(name, email, pw, role)
        else:
            uid = auth.get_user_by_email(email)["id"]
        user_ids[role] = uid

    author = user_ids.get("INSTRUCTOR") or user_ids.get("ADMIN")

    for c in COURSES:
        cid = db.execute(
            """INSERT INTO courses (slug,title,summary,description,category,difficulty,
               duration_hours,pass_threshold,icon,published,created_by)
               VALUES (?,?,?,?,?,?,?,?,?,1,?)""",
            (c["slug"], c["title"], c["summary"], c["description"], c["category"],
             c["difficulty"], c["duration_hours"], c["pass_threshold"], c["icon"], author))

        for mpos, m in enumerate(c["modules"], start=1):
            mid = db.execute(
                "INSERT INTO modules (course_id,title,position) VALUES (?,?,?)",
                (cid, m["title"], mpos))
            for lpos, l in enumerate(m["lessons"], start=1):
                db.execute(
                    "INSERT INTO lessons (module_id,title,content,position) VALUES (?,?,?,?)",
                    (mid, l["title"], l["content"], lpos))

        for lpos, lab in enumerate(c["labs"], start=1):
            slug = c["slug"] + "-lab-" + str(lpos)
            db.execute(
                """INSERT INTO labs (course_id,title,slug,scenario,instructions,difficulty,
                   points,flag_hash,hint,position) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (cid, lab["title"], slug, lab["scenario"], lab["instructions"],
                 lab["difficulty"], lab["points"], hash_flag(lab["flag"]),
                 lab.get("hint", ""), lpos))

    print(f"Seeded {len(COURSES)} courses and {len(DEMO_USERS)} demo users.")
    return True
