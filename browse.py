# -*- coding: utf-8 -*-
"""
هندلر مرور پروفایل‌ها:
- حالت تصادفی (رایگان و نامحدود)
- حالت فیلترشده: فقط دختر / فقط پسر / هم‌سن (روزی محدود، بعدش سکه یا تبلیغ)
"""
import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
from config import DAILY_FREE_FILTERED_MATCHES, COIN_COST_PER_FILTERED_MATCH, ADS_REWARD_MATCHES
from handlers import chat

router = Router()


def connect_mode_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 جستجوی شانسی", callback_data="search_random")],
        [
            InlineKeyboardButton(text="👨 جستجوی پسر", callback_data="search_male"),
            InlineKeyboardButton(text="👩 جستجوی دختر", callback_data="search_female"),
        ],
        [InlineKeyboardButton(text="🛰 جستجوی اطراف", callback_data="search_nearby")],
    ])


def like_dislike_keyboard(target_id: int, mode: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❌ رد کن", callback_data=f"dislike_{mode}_{target_id}"),
            InlineKeyboardButton(text="❤️ لایک", callback_data=f"like_{mode}_{target_id}"),
        ]
    ])


def limit_reached_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 خرید سکه", callback_data="buy_coins")],
        [InlineKeyboardButton(text="🎬 دیدن تبلیغ (رایگان)", callback_data="watch_ad")],
    ])


async def send_profile(message_or_callback, profile: dict, mode: str):
    caption = (
        f"👤 {profile['name']}, {profile['age']}\n"
        f"📍 {profile['city']}\n\n"
        f"{profile['bio']}"
    )
    kb = like_dislike_keyboard(profile["user_id"], mode)

    if isinstance(message_or_callback, CallbackQuery):
        target = message_or_callback.message
    else:
        target = message_or_callback

    if profile.get("photo_id"):
        await target.answer_photo(photo=profile["photo_id"], caption=caption, reply_markup=kb)
    else:
        await target.answer(caption, reply_markup=kb)


@router.message(F.text == "/browse")
async def cmd_browse(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user.get("is_active"):
        await message.answer("اول باید ثبت‌نام کنی. دستور /start رو بزن.")
        return

    await message.answer(
        "💘 به کی وصلت کنم؟ انتخاب کن:",
        reply_markup=connect_mode_keyboard()
    )


@router.callback_query(F.data.startswith("search_"))
async def handle_search(callback: CallbackQuery):
    search_type = callback.data.split("_", 1)[1]  # random / male / female / nearby
    user_id = callback.from_user.id
    user = db.get_user(user_id)

    if not user or not user.get("is_active"):
        await callback.message.answer("اول باید ثبت‌نام کنی. دستور /start رو بزن.")
        await callback.answer()
        return

    if db.get_chat_partner(user_id):
        await callback.message.answer("تو الان وسط یه چتی. اول اونو با «🚫 پایان چت» تموم کن.")
        await callback.answer()
        return

    if search_type == "nearby" and not user.get("city"):
        await callback.message.answer("شهر تو پروفایلت ثبت نشده.")
        await callback.answer()
        return

    # برای جستجوی پسر/دختر، سهمیه رایگان و سکه رو از قبل چک می‌کنیم
    will_use_coin = False
    if search_type in ("male", "female"):
        db.reset_daily_limit_if_needed(user_id)
        user = db.get_user(user_id)
        if user["filtered_used_today"] >= DAILY_FREE_FILTERED_MATCHES:
            if user["coins"] >= COIN_COST_PER_FILTERED_MATCH:
                will_use_coin = True
            else:
                await callback.message.answer(
                    f"سهمیه رایگان امروزت (روزی {DAILY_FREE_FILTERED_MATCHES} بار) تموم شد و سکه‌ی کافی هم نداری! 😔\n"
                    f"هر مچ‌شدن بیشتر {COIN_COST_PER_FILTERED_MATCH} سکه هزینه داره.\n"
                    f"برای ادامه، یا سکه بخر یا یه تبلیغ کوتاه ببین:",
                    reply_markup=limit_reached_keyboard()
                )
                await callback.answer()
                return

    await callback.message.answer("🔍 در حال جستجو... لطفاً ۱۰ ثانیه صبر کنید")
    await callback.answer()
    await asyncio.sleep(10)

    partner_id = db.find_match_or_queue(user_id, search_type)

    if not partner_id:
        await callback.message.answer(
            "فعلاً کسی با این فیلتر آنلاین نیست 😔\nتو صف انتظار قرارت دادم؛ به محض پیدا شدن یه نفر مناسب، خودکار بهش وصلت می‌کنم 🔔"
        )
        return

    # مچ پیدا شد - فقط حالا سهمیه/سکه رو مصرف کن
    if search_type in ("male", "female"):
        if will_use_coin:
            db.spend_coins(user_id, COIN_COST_PER_FILTERED_MATCH)
        else:
            db.increment_filtered_usage(user_id)

    db.start_chat(user_id, partner_id)
    hello_text = (
        "💬 یه نفر پیدا شد و بهش وصل شدی!\n"
        "به مخاطبت سلام کن و شروع کن به صحبت 👋\n\n"
        "🔒 چت کاملاً خصوصیه - فوروارد و سیو کردن عکس‌ها غیرفعاله.\n"
        "هر وقت خواستی می‌تونی پروفایل طرفت رو ببینی، چت رو تموم کنی یا در صورت رفتار نامناسب بلاکش کنی."
    )
    await callback.message.answer(hello_text, reply_markup=chat.chat_controls_kb)
    try:
        await callback.bot.send_message(partner_id, hello_text, reply_markup=chat.chat_controls_kb)
    except Exception:
        pass


@router.callback_query(F.data.startswith("like_") | F.data.startswith("dislike_"))
async def process_like_dislike(callback: CallbackQuery):
    parts = callback.data.split("_")
    action = parts[0]          # like / dislike
    mode = parts[1]            # random / filtered
    target_id = int(parts[2])

    if action == "like":
        is_match = db.register_like(callback.from_user.id, target_id, mode)
        if is_match:
            user = db.get_user(callback.from_user.id)
            target = db.get_user(target_id)

            # چت رو همون لحظه برای هر دو طرف فعال می‌کنیم، بدون نیاز به زدن دکمه
            db.start_chat(callback.from_user.id, target_id)

            await callback.message.answer(
                f"🎉 مبارکه! تو و {target['name']} همدیگه رو لایک کردید و مچ شدید!\n"
                f"چت فعال شد 💬 هر پیامی بفرستی مستقیم براش میره.",
                reply_markup=chat.chat_controls_kb
            )
            try:
                await callback.bot.send_message(
                    target_id,
                    f"🎉 مبارکه! تو و {user['name']} همدیگه رو لایک کردید و مچ شدید!\n"
                    f"چت فعال شد 💬 هر پیامی بفرستی مستقیم براش میره.",
                    reply_markup=chat.chat_controls_kb
                )
            except Exception:
                pass
        else:
            await callback.message.answer("لایک ثبت شد ❤️")
    else:
        db.register_like(callback.from_user.id, target_id, mode)  # ثبت میشه که دوباره نشونش نده

    await callback.answer()

    # پروفایل بعدی رو نشون بده
    if mode == "random":
        profile = db.get_random_profile(callback.from_user.id, mode="random")
        if profile:
            await send_profile(callback, profile, mode="random")
        else:
            await callback.message.answer("فعلاً پروفایل جدیدی نیست. بعداً بیا سر بزن.")
    else:
        await callback.message.answer(
            "برای ادامه فیلترشده، دوباره از منو انتخاب کن یا /browse رو بزن."
        )
