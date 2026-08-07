# -*- coding: utf-8 -*-
"""
پنل مدیریت (فقط برای مدیر ربات):
- مرور همه پروفایل‌های ثبت‌شده به همراه عکس
- امکان مسدود کردن کاربر متخلف
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from config import ADMIN_IDS

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_nav_keyboard(current_index: int, total: int, target_user_id: int):
    buttons = []
    nav_row = []
    if current_index > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"admin_prev_{current_index}"))
    if current_index < total - 1:
        nav_row.append(InlineKeyboardButton(text="➡️ بعدی", callback_data=f"admin_next_{current_index}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="🚫 مسدود کردن این کاربر", callback_data=f"admin_ban_{target_user_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def show_profile_by_index(message_or_callback, index: int):
    all_users = db.get_all_users()
    if not all_users:
        text = "هنوز هیچ کاربری ثبت‌نام نکرده."
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.answer(text)
        else:
            await message_or_callback.answer(text)
        return

    index = max(0, min(index, len(all_users) - 1))
    user = all_users[index]

    status = "✅ فعال" if user.get("is_banned") != 1 else "🚫 مسدود شده"
    caption = (
        f"👤 {user['name']}, {user['age']}\n"
        f"جنسیت: {user['gender']}\n"
        f"شهر: {user['city']}\n"
        f"بیو: {user['bio']}\n"
        f"آیدی عددی: {user['user_id']}\n"
        f"وضعیت: {status}\n\n"
        f"({index + 1} از {len(all_users)})"
    )
    kb = admin_nav_keyboard(index, len(all_users), user["user_id"])

    if isinstance(message_or_callback, CallbackQuery):
        target = message_or_callback.message
    else:
        target = message_or_callback

    if user.get("photo_id"):
        await target.answer_photo(photo=user["photo_id"], caption=caption, reply_markup=kb)
    else:
        await target.answer(caption, reply_markup=kb)


@router.message(F.text == "/admin")
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return  # کاربر عادی، هیچ واکنشی نشون نده

    await show_profile_by_index(message, 0)


@router.callback_query(F.data.startswith("admin_prev_"))
async def admin_prev(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    current_index = int(callback.data.split("_")[2])
    await show_profile_by_index(callback, current_index - 1)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_next_"))
async def admin_next(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    current_index = int(callback.data.split("_")[2])
    await show_profile_by_index(callback, current_index + 1)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_ban_"))
async def admin_ban(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    target_user_id = int(callback.data.split("_")[2])
    db.set_banned(target_user_id, banned=True)
    await callback.message.answer(f"کاربر {target_user_id} مسدود شد 🚫")
    await callback.answer()
