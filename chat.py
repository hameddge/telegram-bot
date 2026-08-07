# -*- coding: utf-8 -*-
"""
چت خصوصی بین دو نفر مچ‌شده:
- پیام‌ها از طریق ربات رد و بدل می‌شه (نه مستقیم)، با غیرفعال بودن فوروارد/سیو
- امکان پایان دادن به چت (رد کردن و رفتن سراغ نفر بعدی)
- امکان بلاک کردن کامل طرف مقابل
- همه پیام‌ها برای بازبینی مدیر تو دیتابیس ثبت می‌شه
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import database as db

router = Router()

chat_controls_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 پروفایل طرف مقابل")],
        [KeyboardButton(text="🚫 پایان چت"), KeyboardButton(text="⛔ بلاک کردن")],
    ],
    resize_keyboard=True
)


def _main_menu_kb():
    # ایمپورت داخل تابع برای جلوگیری از import چرخه‌ای با menu.py
    from handlers.menu import main_menu_keyboard
    return main_menu_keyboard()


@router.callback_query(F.data.startswith("startchat_"))
async def start_chat(callback: CallbackQuery):
    partner_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    if db.is_blocked(user_id, partner_id):
        await callback.message.answer("امکان چت با این کاربر وجود نداره.")
        await callback.answer()
        return

    db.start_chat(user_id, partner_id)
    await callback.message.answer(
        "چت فعال شد 💬\n"
        "هر پیام یا عکسی بفرستی مستقیم برای طرف مقابل میره.\n"
        "🔒 چت کاملاً خصوصیه - فوروارد و سیو کردن عکس‌ها غیرفعاله.\n"
        "هر وقت خواستی می‌تونی پروفایل طرفت رو ببینی، پایان بدی، یا در صورت رفتار نامناسب بلاک کنی.",
        reply_markup=chat_controls_kb
    )
    await callback.answer()


@router.message(F.text == "👤 پروفایل طرف مقابل")
async def view_partner_profile(message: Message):
    partner_id = db.get_chat_partner(message.from_user.id)
    if not partner_id:
        await message.answer("چت فعالی نداری.")
        return

    partner = db.get_user(partner_id)
    if not partner:
        await message.answer("پروفایل طرف مقابل پیدا نشد.")
        return

    caption = (
        f"👤 {partner['name']}, {partner['age']}\n"
        f"📍 {partner['city']}\n\n"
        f"{partner['bio']}"
    )

    if partner.get("photo_id"):
        await message.answer_photo(photo=partner["photo_id"], caption=caption)
    else:
        await message.answer(caption)

    try:
        await message.bot.send_message(partner_id, "👀 طرف مقابل در حال دیدن پروفایل شماست...")
    except Exception:
        pass


@router.message(F.text == "🚫 پایان چت")
async def end_chat_handler(message: Message):
    partner_id = db.end_chat(message.from_user.id)
    await message.answer("چت پایان یافت. می‌تونی از منو دوباره یه نفر دیگه پیدا کنی.", reply_markup=_main_menu_kb())
    if partner_id:
        try:
            await message.bot.send_message(
                partner_id,
                "طرف مقابل چت رو تموم کرد.",
                reply_markup=_main_menu_kb()
            )
        except Exception:
            pass


@router.message(F.text == "⛔ بلاک کردن")
async def block_handler(message: Message):
    partner_id = db.get_chat_partner(message.from_user.id)
    if not partner_id:
        await message.answer("چت فعالی نداری.")
        return

    db.block_user(message.from_user.id, partner_id)
    db.end_chat(message.from_user.id)
    await message.answer(
        "کاربر بلاک شد. دیگه نمی‌تونه باهات چت کنه.",
        reply_markup=_main_menu_kb()
    )
    try:
        await message.bot.send_message(
            partner_id,
            "طرف مقابل چت رو بست.",
            reply_markup=_main_menu_kb()
        )
    except Exception:
        pass


@router.message(F.text)
async def relay_text(message: Message):
    partner_id = db.get_chat_partner(message.from_user.id)
    if not partner_id:
        return  # چت فعالی نداره، این پیام مال چت نیست

    db.log_message(message.from_user.id, partner_id, "text", content_text=message.text)
    try:
        await message.bot.send_message(partner_id, message.text, protect_content=True)
    except Exception:
        await message.answer("ارسال پیام ناموفق بود، احتمالاً طرف مقابل ربات رو بلاک کرده.")


@router.message(F.photo)
async def relay_photo(message: Message):
    partner_id = db.get_chat_partner(message.from_user.id)
    if not partner_id:
        return

    photo_id = message.photo[-1].file_id
    caption = message.caption or ""
    db.log_message(message.from_user.id, partner_id, "photo", content_text=caption, file_id=photo_id)
    try:
        await message.bot.send_photo(partner_id, photo_id, caption=caption, protect_content=True)
    except Exception:
        await message.answer("ارسال عکس ناموفق بود، احتمالاً طرف مقابل ربات رو بلاک کرده.")
