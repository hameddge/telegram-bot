# -*- coding: utf-8 -*-
"""
هندلر مدیریت سکه‌ها:
- نمایش موجودی
- خرید سکه (فعلاً فقط ساختار، بدون درگاه واقعی)
- دیدن تبلیغ برای گرفتن مچ اضافه (فعلاً شبیه‌سازی شده)
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from config import ADS_REWARD_MATCHES, DAILY_FREE_FILTERED_MATCHES

router = Router()


def coin_shop_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 10 سکه", callback_data="shop_10")],
        [InlineKeyboardButton(text="🪙 50 سکه", callback_data="shop_50")],
        [InlineKeyboardButton(text="🪙 100 سکه", callback_data="shop_100")],
    ])


@router.message(F.text == "/coins")
async def cmd_coins(message: Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("اول باید ثبت‌نام کنی. دستور /start رو بزن.")
        return
    await message.answer(f"🪙 موجودی سکه‌ات: {user['coins']}")


@router.callback_query(F.data == "buy_coins")
async def buy_coins(callback: CallbackQuery):
    await callback.message.answer(
        "کدوم بسته سکه رو می‌خوای؟\n\n"
        "(فعلاً پرداخت واقعی وصل نشده — این فقط نمای اولیه‌ست)",
        reply_markup=coin_shop_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("shop_"))
async def process_shop_purchase(callback: CallbackQuery):
    amount = int(callback.data.split("_")[1])
    # TODO: اینجا بعداً اتصال به Telegram Stars یا درگاه پرداخت اضافه می‌شه
    # فعلاً فقط برای تست، سکه مستقیم اضافه می‌شه
    db.add_coins(callback.from_user.id, amount)
    await callback.message.answer(
        f"✅ {amount} سکه به حسابت اضافه شد (حالت تست).\n"
        f"وقتی درگاه پرداخت واقعی رو وصل کردیم، اینجا باید قبلش پرداخت انجام بشه."
    )
    await callback.answer()


@router.callback_query(F.data == "watch_ad")
async def watch_ad(callback: CallbackQuery):
    # TODO: اینجا بعداً به یک شبکه تبلیغاتی واقعی وصل می‌شه
    # فعلاً فقط شبیه‌سازی شده: انگار تبلیغ دیده شده
    user_id = callback.from_user.id
    user = db.get_user(user_id)

    # چند تا مچ اضافه به کاربر می‌دیم (با کم کردن از شمارنده امروز)
    new_used = max(0, user["filtered_used_today"] - ADS_REWARD_MATCHES)
    db.create_or_update_user(user_id, filtered_used_today=new_used)

    await callback.message.answer(
        f"🎬 (اینجا باید ویدیو تبلیغاتی نمایش داده بشه)\n\n"
        f"ممنون! {ADS_REWARD_MATCHES} تا مچ فیلترشده اضافه گرفتی. می‌تونی ادامه بدی."
    )
    await callback.answer()
