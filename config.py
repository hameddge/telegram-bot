# -*- coding: utf-8 -*-
"""
تنظیمات اصلی ربات
"""
import os

# توکن ربات دیگه اینجا نوشته نمیشه (امن نیست)!
# به‌جاش، قبل از اجرا یه متغیر محیطی به اسم BOT_TOKEN ست کن.
# لینوکس/مک: export BOT_TOKEN="توکن_جدیدت"
# ویندوز (PowerShell): $env:BOT_TOKEN="توکن_جدیدت"
# روی هاست (Railway/Render و ...): تو بخش Environment Variables اضافه‌اش کن.
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "متغیر محیطی BOT_TOKEN ست نشده! توکن ربات رو به‌عنوان Environment Variable اضافه کن."
    )

# مسیر فایل دیتابیس (خودش ساخته میشه، نیازی به کاری نیست)
DB_PATH = "dating_bot.db"

# چند بار در روز کاربر میتونه از فیلتر جنسیتی/هم‌سن رایگان استفاده کنه
DAILY_FREE_FILTERED_MATCHES = 10

# هر بار مچ‌شدن اضافه (بعد از تموم شدن سهمیه رایگان)، چند سکه کم میشه
COIN_COST_PER_FILTERED_MATCH = 1

# با هر بار دیدن تبلیغ، چند تا "مچ فیلتر شده" اضافه به کاربر داده میشه
ADS_REWARD_MATCHES = 3

# به ازای هر دوستی که با لینک دعوت کاربر ثبت‌نام کنه، چند سکه جایزه می‌گیره
REFERRAL_REWARD_COINS = 1

# پاداش سکه‌ای که با تکمیل کامل پروفایل به کاربر تعلق می‌گیره
PROFILE_COMPLETE_REWARD_COINS = 10

# حداقل و حداکثر سن قابل قبول برای ثبت‌نام
MIN_AGE = 18
MAX_AGE = 99

# آیدی عددی تلگرام مدیر ربات (خودت) - فقط همین آیدی به دستور /admin دسترسی داره
# این همون user_id ای هست که تو دیتابیس زیر ستون user_id خودت دیدی
ADMIN_IDS = [7076369116]
