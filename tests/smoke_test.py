"""
Let It Flow - end-to-end smoke test.
Runs the real app against a throw-away SQLite database (no MySQL needed):

    python tests/smoke_test.py
"""
import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tmp = tempfile.mkdtemp()
os.environ["DB_BACKEND"] = "sqlite"
os.environ["SQLITE_PATH"] = os.path.join(tmp, "test.db")

import app as flow  # noqa: E402

flow.init_db(flow.app)
PASSED = []


def check(name, cond):
    PASSED.append(bool(cond))
    print(("PASS  " if cond else "FAIL  ") + name)


def token(client):
    with client.session_transaction() as s:
        s.setdefault("csrf", "test-token-" + str(id(client)))
        return s["csrf"]


def post(client, url, data=None, **kw):
    data = dict(data or {})
    data["csrf_token"] = token(client)
    return client.post(url, data=data, **kw)


def register(client, name, email):
    return post(client, "/register", {"name": name, "age": "21", "email": email,
                                     "password": "Secret123", "password2": "Secret123"})


def db(fn, *args):
    """Call a repository function inside an app context (for test assertions)."""
    with flow.app.app_context():
        return fn(*args)


A, B = flow.app.test_client(), flow.app.test_client()

# --- public pages + security basics
check("landing page loads", A.get("/").status_code == 200)
check("private page redirects when logged out", A.get("/dashboard").status_code == 302)
check("POST without CSRF token is rejected", A.post("/login", data={"email": "x", "password": "y"}).status_code == 400)
check("weak password rejected", post(A, "/register", {"name": "Z", "age": "20", "email": "z@x.com", "password": "abc", "password2": "abc"}).status_code == 400)

# --- register + onboarding
r = register(A, "Asha Verma", "asha@example.com")
check("register redirects to onboarding", r.status_code == 302 and "/onboarding" in r.headers["Location"])
check("duplicate email rejected", register(flow.app.test_client(), "Other", "asha@example.com").status_code == 400)
today = date.today()
dates = [(today - timedelta(days=d)).isoformat() for d in (6, 36, 65, 95, 124)]
post(A, "/onboarding?step=1", {"action": "save", "past_dates": dates})
post(A, "/onboarding?step=2", {"action": "save", "typical_cycle_length": "29", "period_duration": "5",
                              "self_regularity": "regular", "has_missed_periods": "no"})
post(A, "/onboarding?step=3", {"action": "save", "residence": "hostel", "diet_type": "vegetarian",
                              "skips_meals_often": "yes", "preferred_exercise": "yoga", "activity_level": "moderate"})
check("5 period dates saved", len(db(flow.repo.list_cycles, 1)) == 5)

# --- every private page renders
for url in ["/dashboard", "/tracker", "/tracker?month=2026-03", "/log", "/prediction", "/intelligence",
            "/insights", "/nutrition", "/nutrition?phase=luteal&exclude=paneer", "/assistant", "/learn",
            "/reports", "/profile", "/settings"]:
    check(f"GET {url} -> 200", A.get(url).status_code == 200)

# --- tracker CRUD
post(A, "/tracker/add", {"period_start": (today - timedelta(days=150)).isoformat()})
page = A.get("/tracker").get_data(as_text=True)
check("tracker lists added period", (today - timedelta(days=150)).strftime("%d %b %Y") in page)
check("future period date rejected", b"not in the future" in post(A, "/tracker/add", {"period_start": (today + timedelta(days=3)).isoformat()}, follow_redirects=True).data)

# --- daily log + quick log
post(A, "/log", {"date": today.isoformat(), "flow": "3", "pain_severity": "6", "fatigue": "2",
                 "sleep_hours": "5.5", "stress_level": "4", "exam_period": "1"})
check("daily log saved", "pain" in A.get("/log").get_data(as_text=True).lower())
post(A, "/quick-log", {"sym": ["bloating"], "pain": "5"})

# --- prediction / intelligence content
d = A.get("/dashboard").get_data(as_text=True)
check("dashboard shows ring + estimate", "ring-wrap" in d and "Next period" in d or "late" in d)
check("intelligence shows status", "What we noticed" in A.get("/intelligence").get_data(as_text=True))

# --- chatbot
def chat(client, msg, conv=None):
    r = client.post("/api/chat", json={"message": msg, "conversation_id": conv},
                    headers={"X-CSRF-Token": token(client)})
    return r.status_code, r.get_json()

code, j = chat(A, "When did my last period start?")
check("chat: personal fact from DB", code == 200 and (today - timedelta(days=6)).strftime("%d %b %Y") in j["reply"])
conv_a = j["conversation_id"]
code, j2 = chat(A, "Why might my period be late?", conv_a)
check("chat: knowledge-base answer", "stress" in j2["reply"].lower() and "From your logs" in j2["reply"])
code, j3 = chat(A, "Do I have PCOS?", conv_a)
check("chat: refuses to diagnose", "can't diagnose" in j3["reply"].lower())
code, j4 = chat(A, "I am soaking a pad every hour and feel faint", conv_a)
check("chat: urgent safety reply", j4["intent"] == "urgent")
code, j5 = chat(A, "what is the capital of France", conv_a)
check("chat: honest fallback", j5["intent"] == "fallback")

# --- reports
pdf = A.get("/reports/download.pdf")
check("PDF report generated", pdf.status_code == 200 and pdf.data[:4] == b"%PDF")
csvr = A.get("/reports/download.csv")
check("CSV export works", csvr.status_code == 200 and b"record_type" in csvr.data)

# --- ACCOUNT ISOLATION (second user must never see user A's data)
register(B, "Bina Rao", "bina@example.com")
post(B, "/onboarding?step=3", {"action": "skip"})
a_cycle_id = db(flow.repo.list_cycles, 1)[0]["id"]
check("B cannot delete A's period (404)", post(B, f"/tracker/{a_cycle_id}/delete").status_code == 404)
check("A's period still exists", len(db(flow.repo.list_cycles, 1)) >= 5)
check("B cannot open A's conversation", "last period" not in B.get(f"/assistant?c={conv_a}").get_data(as_text=True))
code, jb = chat(B, "When did my last period start?", conv_a)       # tries to reuse A's conversation id
check("B chat creates its own conversation", jb["conversation_id"] != conv_a)
check("B has no period data in answer", "haven't logged" in jb["reply"])
check("B sees none of A's dates", len(db(flow.repo.list_cycles, 2)) == 0)

# --- settings: wrong password does nothing; delete logs; delete account
post(A, "/settings/delete-logs", {"password": "wrong"})
check("wrong password -> logs kept", len(db(flow.repo.list_cycles, 1)) >= 5)
post(A, "/settings/delete-logs", {"password": "Secret123"})
check("logs deleted with correct password", len(db(flow.repo.list_cycles, 1)) == 0)
post(A, "/settings/delete-account", {"password": "Secret123", "confirm": "DELETE"})
check("account deleted", db(flow.repo.get_user, 1) is None)

print(f"\n{sum(PASSED)}/{len(PASSED)} checks passed")
sys.exit(0 if all(PASSED) else 1)
