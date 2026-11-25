"""
Let It Flow - data access functions.

Security rule used everywhere in this file:
    EVERY query has  WHERE user_id = %s  (or checks the owner)  so a logged-in
    user can only ever read, change or delete THEIR OWN rows, even if they
    guess another record's id in the URL.
"""
from datetime import date, datetime

from database import execute, query_all, query_one, upsert


# ------------------------------------------------------------------ users
def get_user(user_id):
    return query_one("SELECT id, name, email, age, created_at FROM users WHERE id = %s", [user_id])


def get_user_by_email(email):
    return query_one("SELECT * FROM users WHERE email = %s", [email.lower()])


def create_user(name, age, email, password_hash):
    uid = execute("INSERT INTO users (name, age, email, password_hash) VALUES (%s, %s, %s, %s)",
                  [name, age, email.lower(), password_hash])
    execute("INSERT INTO user_profiles (user_id) VALUES (%s)", [uid])
    return uid


def update_user_basic(user_id, name, age):
    execute("UPDATE users SET name = %s, age = %s WHERE id = %s", [name, age, user_id])


def update_password(user_id, password_hash):
    execute("UPDATE users SET password_hash = %s WHERE id = %s", [password_hash, user_id])


def delete_user(user_id):
    """Deletes the account and (through ON DELETE CASCADE) every related row."""
    execute("DELETE FROM users WHERE id = %s", [user_id])


# --------------------------------------------------------------- profile
def get_profile(user_id):
    row = query_one("SELECT * FROM user_profiles WHERE user_id = %s", [user_id])
    if row is None:
        execute("INSERT INTO user_profiles (user_id) VALUES (%s)", [user_id])
        row = query_one("SELECT * FROM user_profiles WHERE user_id = %s", [user_id])
    return row


def save_profile(user_id, **fields):
    allowed = {"residence", "typical_cycle_length", "period_duration", "self_regularity",
               "has_missed_periods", "attendance_impact", "sleep_routine", "onboarding_done"}
    data = {k: v for k, v in fields.items() if k in allowed}
    if not data:
        return
    get_profile(user_id)
    sets = ", ".join(f"{k} = %s" for k in data)
    execute(f"UPDATE user_profiles SET {sets} WHERE user_id = %s", list(data.values()) + [user_id])


def get_diet_pref(user_id):
    return query_one("SELECT * FROM dietary_preferences WHERE user_id = %s", [user_id]) or {}


def save_diet_pref(user_id, diet_type, dislikes, skips_meals_often):
    upsert("dietary_preferences", ["user_id"], {
        "user_id": user_id, "diet_type": diet_type, "dislikes": dislikes,
        "skips_meals_often": skips_meals_often})


def get_exercise_pref(user_id):
    return query_one("SELECT * FROM exercise_preferences WHERE user_id = %s", [user_id]) or {}


def save_exercise_pref(user_id, preferred_exercise, activity_level):
    upsert("exercise_preferences", ["user_id"], {
        "user_id": user_id, "preferred_exercise": preferred_exercise,
        "activity_level": activity_level})


# ---------------------------------------------------------------- cycles
def list_cycles(user_id):
    """All logged period starts, newest first."""
    return query_all("SELECT id, period_start, period_end, notes FROM menstrual_cycles "
                     "WHERE user_id = %s ORDER BY period_start DESC", [user_id])


def period_starts(user_id):
    return sorted(r["period_start"] for r in list_cycles(user_id))


def add_cycle(user_id, start, end=None, notes=None):
    """Returns False if that start date is already logged."""
    if query_one("SELECT id FROM menstrual_cycles WHERE user_id = %s AND period_start = %s",
                 [user_id, start]):
        return False
    execute("INSERT INTO menstrual_cycles (user_id, period_start, period_end, notes) "
            "VALUES (%s, %s, %s, %s)", [user_id, start, end, notes])
    return True


def update_cycle(user_id, cycle_id, start, end, notes):
    clash = query_one("SELECT id FROM menstrual_cycles WHERE user_id = %s AND period_start = %s "
                      "AND id <> %s", [user_id, start, cycle_id])
    if clash:
        return False
    execute("UPDATE menstrual_cycles SET period_start = %s, period_end = %s, notes = %s "
            "WHERE id = %s AND user_id = %s", [start, end, notes, cycle_id, user_id])
    return True


def delete_cycle(user_id, cycle_id):
    execute("DELETE FROM menstrual_cycles WHERE id = %s AND user_id = %s", [cycle_id, user_id])


def get_cycle(user_id, cycle_id):
    return query_one("SELECT id, period_start, period_end, notes FROM menstrual_cycles "
                     "WHERE id = %s AND user_id = %s", [cycle_id, user_id])


# ------------------------------------------------------------- daily logs
def save_daily_log(user_id, log_date, symptoms=None, lifestyle=None, flow=None):
    """
    One 'daily check-in' can hold flow + symptoms + lifestyle.  Each part is
    saved only if the user filled something in (nothing is forced).
    Saving the same date again updates it.
    """
    if flow:
        upsert("period_logs", ["user_id", "log_date"],
               {"user_id": user_id, "log_date": log_date, "flow_intensity": flow})
    if symptoms:
        upsert("symptom_logs", ["user_id", "log_date"],
               dict(user_id=user_id, log_date=log_date, **symptoms))
    if lifestyle:
        upsert("lifestyle_logs", ["user_id", "log_date"],
               dict(user_id=user_id, log_date=log_date, **lifestyle))


def get_day(user_id, log_date):
    return {
        "flow": query_one("SELECT * FROM period_logs WHERE user_id = %s AND log_date = %s",
                          [user_id, log_date]),
        "symptoms": query_one("SELECT * FROM symptom_logs WHERE user_id = %s AND log_date = %s",
                              [user_id, log_date]),
        "lifestyle": query_one("SELECT * FROM lifestyle_logs WHERE user_id = %s AND log_date = %s",
                               [user_id, log_date]),
    }


def list_symptoms(user_id, limit=None):
    sql = "SELECT * FROM symptom_logs WHERE user_id = %s ORDER BY log_date DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return query_all(sql, [user_id])


def list_lifestyle(user_id, limit=None):
    sql = "SELECT * FROM lifestyle_logs WHERE user_id = %s ORDER BY log_date DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return query_all(sql, [user_id])


def list_flow(user_id, limit=None):
    sql = "SELECT * FROM period_logs WHERE user_id = %s ORDER BY log_date DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return query_all(sql, [user_id])


def delete_day(user_id, log_date):
    for table in ("period_logs", "symptom_logs", "lifestyle_logs"):
        execute(f"DELETE FROM {table} WHERE user_id = %s AND log_date = %s", [user_id, log_date])


def delete_all_logs(user_id):
    """Wipes tracking data but keeps the account (Settings -> Delete my logs)."""
    for table in ("menstrual_cycles", "period_logs", "symptom_logs", "lifestyle_logs",
                  "cycle_analysis", "chatbot_conversations"):
        execute(f"DELETE FROM {table} WHERE user_id = %s", [user_id])


# ----------------------------------------------------------- cycle_analysis
def save_analysis_snapshot(user_id, status, n_cycles, mean_cycle, std_cycle, predicted_next, summary):
    execute("DELETE FROM cycle_analysis WHERE user_id = %s AND analysis_date = %s",
            [user_id, date.today()])
    execute("INSERT INTO cycle_analysis (user_id, analysis_date, status, n_cycles, mean_cycle, "
            "std_cycle, predicted_next, summary) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            [user_id, date.today(), status, n_cycles, mean_cycle, std_cycle, predicted_next, summary])


def list_analysis_history(user_id, limit=12):
    return query_all("SELECT analysis_date, status, n_cycles, mean_cycle, std_cycle, predicted_next "
                     "FROM cycle_analysis WHERE user_id = %s ORDER BY analysis_date DESC "
                     f"LIMIT {int(limit)}", [user_id])


# ---------------------------------------------------------------- chatbot
def create_conversation(user_id, title):
    return execute("INSERT INTO chatbot_conversations (user_id, title) VALUES (%s, %s)",
                   [user_id, title[:110]])


def list_conversations(user_id, limit=15):
    return query_all("SELECT id, title, created_at FROM chatbot_conversations WHERE user_id = %s "
                     f"ORDER BY id DESC LIMIT {int(limit)}", [user_id])


def get_conversation(user_id, conv_id):
    """Returns None when the conversation belongs to someone else."""
    return query_one("SELECT id, title FROM chatbot_conversations WHERE id = %s AND user_id = %s",
                     [conv_id, user_id])


def add_message(user_id, conv_id, role, content, intent=None):
    execute("INSERT INTO chatbot_messages (conversation_id, user_id, role, content, intent) "
            "VALUES (%s, %s, %s, %s, %s)", [conv_id, user_id, role, content, intent])


def list_messages(user_id, conv_id):
    return query_all("SELECT role, content, intent, created_at FROM chatbot_messages "
                     "WHERE conversation_id = %s AND user_id = %s ORDER BY id", [conv_id, user_id])


def recent_user_questions(user_id, limit=5, exclude_conv=None):
    sql = ("SELECT content, conversation_id FROM chatbot_messages WHERE user_id = %s AND role = 'user'")
    params = [user_id]
    if exclude_conv:
        sql += " AND conversation_id <> %s"
        params.append(exclude_conv)
    sql += f" ORDER BY id DESC LIMIT {int(limit)}"
    return query_all(sql, params)


def delete_conversation(user_id, conv_id):
    execute("DELETE FROM chatbot_conversations WHERE id = %s AND user_id = %s", [conv_id, user_id])
