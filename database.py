# -*- coding: utf-8 -*-
"""
مدیریت دیتابیس ربات (SQLite)
"""
import sqlite3
from datetime import date
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """ساخت جدول‌ها در صورت نیاز"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER,
        gender TEXT,           -- 'male' یا 'female'
        city TEXT,
        bio TEXT,
        photo_id TEXT,
        coins INTEGER DEFAULT 0,
        filtered_used_today INTEGER DEFAULT 0,
        last_reset_date TEXT,
        is_active INTEGER DEFAULT 0,   -- آیا ثبت‌نام کامل شده
        is_banned INTEGER DEFAULT 0,   -- آیا مسدود شده توسط مدیر
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # اگه دیتابیس قدیمی‌تری از قبل بدون این ستون وجود داشت، اضافه‌اش کن
    try:
        cur.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # ستون از قبل وجود داره

    cur.execute("""
    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user INTEGER,
        to_user INTEGER,
        mode TEXT,              -- 'random' یا 'filtered'
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(from_user, to_user)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1 INTEGER,
        user2 INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS active_chats (
        user_id INTEGER PRIMARY KEY,
        partner_id INTEGER,
        started_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user INTEGER,
        to_user INTEGER,
        content_type TEXT,   -- 'text' یا 'photo' یا غیره
        content_text TEXT,   -- متن پیام یا کپشن عکس
        file_id TEXT,        -- در صورت عکس/فایل
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS blocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blocker INTEGER,
        blocked INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(blocker, blocked)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS waiting_queue (
        user_id INTEGER PRIMARY KEY,
        search_type TEXT,     -- 'random' / 'male' / 'female' / 'nearby'
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_or_update_user(user_id: int, **fields):
    user = get_user(user_id)
    conn = get_connection()
    cur = conn.cursor()
    if user is None:
        cur.execute(
            "INSERT INTO users (user_id, last_reset_date) VALUES (?, ?)",
            (user_id, str(date.today()))
        )
        conn.commit()
    if fields:
        keys = ", ".join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [user_id]
        cur.execute(f"UPDATE users SET {keys} WHERE user_id = ?", values)
        conn.commit()
    conn.close()


def reset_daily_limit_if_needed(user_id: int):
    """اگه روز عوض شده، شمارنده روزانه رو صفر می‌کنه"""
    user = get_user(user_id)
    if not user:
        return
    today = str(date.today())
    if user["last_reset_date"] != today:
        create_or_update_user(user_id, filtered_used_today=0, last_reset_date=today)


def increment_filtered_usage(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET filtered_used_today = filtered_used_today + 1 WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()


def add_coins(user_id: int, amount: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def spend_coins(user_id: int, amount: int) -> bool:
    """اگه سکه کافی بود کم می‌کنه و True برمی‌گردونه، وگرنه False"""
    user = get_user(user_id)
    if not user or user["coins"] < amount:
        return False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    return True


def start_chat(user_a: int, user_b: int):
    """چت رو برای هر دو طرف فعال می‌کنه"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO active_chats (user_id, partner_id) VALUES (?, ?)", (user_a, user_b))
    cur.execute("INSERT OR REPLACE INTO active_chats (user_id, partner_id) VALUES (?, ?)", (user_b, user_a))
    conn.commit()
    conn.close()


def get_chat_partner(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT partner_id FROM active_chats WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["partner_id"] if row else None


def end_chat(user_id: int):
    """چت رو برای کاربر و طرف مقابلش تموم می‌کنه"""
    partner_id = get_chat_partner(user_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM active_chats WHERE user_id = ?", (user_id,))
    if partner_id:
        cur.execute("DELETE FROM active_chats WHERE user_id = ?", (partner_id,))
    conn.commit()
    conn.close()
    return partner_id


def log_message(from_user: int, to_user: int, content_type: str, content_text: str = None, file_id: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_messages (from_user, to_user, content_type, content_text, file_id) VALUES (?, ?, ?, ?, ?)",
        (from_user, to_user, content_type, content_text, file_id)
    )
    conn.commit()
    conn.close()


def block_user(blocker: int, blocked: int):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO blocks (blocker, blocked) VALUES (?, ?)", (blocker, blocked))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()


def is_blocked(user_a: int, user_b: int) -> bool:
    """آیا هرکدوم از این دو نفر اون‌یکی رو بلاک کرده؟"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM blocks WHERE (blocker = ? AND blocked = ?) OR (blocker = ? AND blocked = ?)",
        (user_a, user_b, user_b, user_a)
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def get_all_users():
    """همه کاربرهای فعال (ثبت‌نام‌شده) رو برمی‌گردونه - برای پنل مدیر"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_banned(user_id: int, banned: bool):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if banned else 0, user_id))
    conn.commit()
    conn.close()


def is_user_banned(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user.get("is_banned") == 1)


def get_random_profile(user_id: int, mode: str, gender_filter: str = None, same_age: int = None):
    """
    یه پروفایل تصادفی برمی‌گردونه که:
    - خود کاربر نباشه
    - قبلاً لایک/دیسلایک نشده باشه
    - اگه فیلتر جنسیتی خواسته شده، رعایت بشه
    - اگه هم‌سن خواسته شده، رعایت بشه
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT * FROM users
        WHERE user_id != ?
          AND is_active = 1
          AND is_banned = 0
          AND user_id NOT IN (
              SELECT to_user FROM likes WHERE from_user = ?
          )
          AND user_id NOT IN (
              SELECT blocked FROM blocks WHERE blocker = ?
          )
          AND user_id NOT IN (
              SELECT blocker FROM blocks WHERE blocked = ?
          )
    """
    params = [user_id, user_id, user_id, user_id]

    if gender_filter:
        query += " AND gender = ?"
        params.append(gender_filter)

    if same_age:
        query += " AND age = ?"
        params.append(same_age)

    query += " ORDER BY RANDOM() LIMIT 1"

    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def search_users_by_name(query: str, exclude_user_id: int, limit: int = 5):
    """جستجوی کاربرها بر اساس بخشی از اسم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM users
        WHERE user_id != ?
          AND is_active = 1
          AND is_banned = 0
          AND name LIKE ?
          AND user_id NOT IN (SELECT blocked FROM blocks WHERE blocker = ?)
          AND user_id NOT IN (SELECT blocker FROM blocks WHERE blocked = ?)
        LIMIT ?
        """,
        (exclude_user_id, f"%{query}%", exclude_user_id, exclude_user_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_profile_by_city(user_id: int, city: str):
    """یه پروفایل تصادفی از همون شهر کاربر برمی‌گردونه"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM users
        WHERE user_id != ?
          AND is_active = 1
          AND is_banned = 0
          AND city = ?
          AND user_id NOT IN (SELECT to_user FROM likes WHERE from_user = ?)
          AND user_id NOT IN (SELECT blocked FROM blocks WHERE blocker = ?)
          AND user_id NOT IN (SELECT blocker FROM blocks WHERE blocked = ?)
        ORDER BY RANDOM() LIMIT 1
        """,
        (user_id, city, user_id, user_id, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def find_match_or_queue(user_id: int, search_type: str):
    """
    دنبال یه نفر سازگار تو صف انتظار می‌گرده (بر اساس جنسیت خواسته‌شده یا شهر).
    اگه پیدا شد: طرف مقابل رو از صف حذف می‌کنه و آیدیش رو برمی‌گردونه.
    اگه پیدا نشد: خود کاربر رو به صف انتظار اضافه می‌کنه و None برمی‌گردونه.
    """
    me = get_user(user_id)
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT wq.user_id AS user_id, wq.search_type AS search_type,
               u.gender AS gender, u.city AS city
        FROM waiting_queue wq
        JOIN users u ON wq.user_id = u.user_id
        WHERE wq.user_id != ?
        ORDER BY wq.created_at ASC
        """,
        (user_id,)
    )
    rows = cur.fetchall()

    for row in rows:
        cand_id = row["user_id"]
        cand_search_type = row["search_type"]
        cand_gender = row["gender"]
        cand_city = row["city"]

        if is_blocked(user_id, cand_id):
            continue

        # آیا کاندید با خواسته‌ی من جور در میاد؟
        if search_type == "male" and cand_gender != "male":
            continue
        if search_type == "female" and cand_gender != "female":
            continue
        if search_type == "nearby" and (not me["city"] or me["city"] != cand_city):
            continue

        # آیا من با خواسته‌ی کاندید جور در میام؟
        if cand_search_type == "male" and (not me or me["gender"] != "male"):
            continue
        if cand_search_type == "female" and (not me or me["gender"] != "female"):
            continue
        if cand_search_type == "nearby" and (not cand_city or cand_city != me["city"]):
            continue

        cur.execute("DELETE FROM waiting_queue WHERE user_id = ?", (cand_id,))
        cur.execute("DELETE FROM waiting_queue WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return cand_id

    # کسی پیدا نشد - خودم رو میذارم تو صف انتظار
    cur.execute(
        "INSERT OR REPLACE INTO waiting_queue (user_id, search_type, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (user_id, search_type)
    )
    conn.commit()
    conn.close()
    return None


def leave_queue(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM waiting_queue WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def register_like(from_user: int, to_user: int, mode: str) -> bool:
    """
    ثبت لایک. اگه طرف مقابل هم قبلاً این کاربر رو لایک کرده باشه، مچ اتفاق میفته.
    خروجی: True اگه مچ شد، False اگه نشد
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO likes (from_user, to_user, mode) VALUES (?, ?, ?)",
            (from_user, to_user, mode)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False

    # چک کن آیا طرف مقابل هم قبلاً لایک کرده
    cur.execute(
        "SELECT 1 FROM likes WHERE from_user = ? AND to_user = ?",
        (to_user, from_user)
    )
    mutual = cur.fetchone()

    is_match = False
    if mutual:
        cur.execute(
            "INSERT INTO matches (user1, user2) VALUES (?, ?)",
            (from_user, to_user)
        )
        conn.commit()
        is_match = True

    conn.close()
    return is_match
