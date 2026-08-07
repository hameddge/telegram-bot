# -*- coding: utf-8 -*-
"""
منوی اصلی پایین صفحه و هندلر دکمه‌هاش:
- به یه ناشناس وصلم کن! / جستجوی کاربران / افراد نزدیک من / پروفایل
- راهنما / لینک ناشناس من / انتقادات و پیشنهادات / معرفی به دوستان
"""
import asyncio

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import ADMIN_IDS, REFERRAL_REWARD_COINS
from handlers import browse, profile

router = Router()


class MenuStates(StatesGroup):
    waiting_search_name = State()
    waiting_feedback = State()


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="به یه ناشناس وصلم کن! 🤝")],
            [KeyboardButton(text="جستجوی کاربران 🔍"), KeyboardButton(text="افراد نزدیک من 📍")],
            [KeyboardButton(text="پروفایل 👤"), KeyboardButton(text="راهنما ❓")],
            [KeyboardButton(text="لینک ناشناس من ✉️"), KeyboardButton(text="انتقادات و پیشنهادات 📮")],
            [KeyboardButton(text="معرفی به دوستان 📎")],
        ],
        resize_keyboard=True
    )


def _is_registered(message: Message):
    user = db.get_user(message.from_user.id)
    return user if (user and user.get("is_active")) else None


@router.message(F.text.contains("وصلم کن"))
async def menu_connect_stranger(message: Message):
    if not _is_registered(message):
        await message.answer("اول باید ثبت‌نام کنی. دستور /start رو بزن.")
        return

    await message.answer(
        "💘 به کی وصلت کنم؟ انتخاب کن:",
        reply_markup=browse.connect_mode_keyboard()
    )


@router.message(F.text.contains("جستجوی کاربران"))
async def menu_search_start(message: Message, state: FSMContext):
    if not _is_registered(message):
        await message.answer("اول باید ثبت‌نام کنی. دستور /start رو بزن.")
        return
    await message.answer("اسم یا بخشی از اسم کاربری که دنبالش می‌گردی رو بنویس:")
    await state.set_state(MenuStates.waiting_search_name)


@router.message(MenuStates.waiting_search_name)
async def menu_search_process(message: Message, state: FSMContext):
    await state.clear()
    query = (message.text or "").strip()
    if not query:
        await message.answer("یه اسم بنویس.")
        return

    results = db.search_users_by_name(query, message.from_user.id)
    if not results:
        await message.answer("کسی با این اسم پیدا نشد.")
        return

    await message.answer(f"{len(results)} نفر پیدا شد:")
    for profile_row in results:
        await browse.send_profile(message, profile_row, mode="random")


@router.message(F.text.contains("افراد نزدیک"))
async def menu_nearby(message: Message):
    user = _is_registered(message)
    if not user:
        await message.answer("اول باید ثبت‌نام کنی. دستور /start رو بزن.")
        return
    if not user.get("city"):
        await message.answer("شهر تو پروفایلت ثبت نشده.")
        return

    await message.answer(f"🔍 در حال جستجوی افراد نزدیک تو ({user['city']})... لطفاً ۱۰ ثانیه صبر کنید")
    await asyncio.sleep(10)

    profile_row = db.get_profile_by_city(message.from_user.id, user["city"])
    if not profile_row:
        await message.answer("فعلاً کسی تو شهر خودت پیدا نشد.")
        return

    await browse.send_profile(message, profile_row, mode="random")


@router.message(F.text.contains("پروفایل"))
async def menu_profile(message: Message):
    await profile.cmd_profile(message)


@router.message(F.text.contains("راهنما"))
async def menu_help(message: Message):
    await message.answer(
        "📖 راهنمای ربات:\n\n"
        "🤝 به یه ناشناس وصلم کن! - یه پروفایل تصادفی نشونت می‌ده\n"
        "🔍 جستجوی کاربران - با اسم دنبال کسی بگرد\n"
        "📍 افراد نزدیک من - افراد هم‌شهری خودت رو ببین\n"
        "👤 پروفایل - مشاهده و ویرایش پروفایلت\n"
        "✉️ لینک ناشناس من - لینکی بساز که بقیه بتونن برات پیام ناشناس بفرستن\n"
        "📮 انتقادات و پیشنهادات - نظرت رو برای مدیر ربات بفرست\n"
        "📎 معرفی به دوستان - با دعوت دوستات سکه جایزه بگیر\n\n"
        "برای مرور پروفایل‌ها با فیلتر جنسیت یا هم‌سن هم دستور /browse رو بزن."
    )


@router.message(F.text.contains("لینک ناشناس"))
async def menu_anon_link(message: Message):
    if not _is_registered(message):
        await message.answer("اول باید ثبت‌نام کنی. دستور /start رو بزن.")
        return

    me = await message.bot.get_me()
    link = f"https://t.me/{me.username}?start=msg_{message.from_user.id}"
    await message.answer(
        f"✉️ لینک پیام ناشناس تو:\n{link}\n\n"
        f"هرکی رو این لینک بزنه می‌تونه بدون اینکه هویتش برات مشخص بشه، پیام برات بفرسته."
    )


@router.message(F.text.contains("انتقادات"))
async def menu_feedback_start(message: Message, state: FSMContext):
    await message.answer("نظر، انتقاد یا پیشنهادت رو بنویس، مستقیم برای مدیر ربات ارسال میشه:")
    await state.set_state(MenuStates.waiting_feedback)


@router.message(MenuStates.waiting_feedback)
async def menu_feedback_process(message: Message, state: FSMContext):
    await state.clear()
    username = f"@{message.from_user.username}" if message.from_user.username else "بدون یوزرنیم"
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"📮 پیام جدید از کاربر {message.from_user.id} ({username}):\n\n{message.text}"
            )
        except Exception:
            pass
    await message.answer("ممنون از نظرت! برای مدیر ربات ارسال شد ✅")


@router.message(F.text.contains("معرفی به دوستان"))
async def menu_referral(message: Message):
    if not _is_registered(message):
        await message.answer("اول باید ثبت‌نام کنی. دستور /start رو بزن.")
        return

    me = await message.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{message.from_user.id}"
    await message.answer(
        f"📎 لینک دعوت تو:\n{link}\n\n"
        f"به ازای هر دوستی که با این لینک ثبت‌نام رو کامل کنه، {REFERRAL_REWARD_COINS} سکه جایزه می‌گیری 🪙"
    )
