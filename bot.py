# -*- coding: utf-8 -*-
"""
فایل اصلی اجرای ربات
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db

from handlers import registration, browse, coins, admin, profile, menu, chat


async def main():
    logging.basicConfig(level=logging.INFO)

    # ساخت جدول‌های دیتابیس (اگه وجود نداشته باشن)
    db.init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # ثبت هندلرها
    dp.include_router(admin.router)
    dp.include_router(registration.router)
    dp.include_router(browse.router)
    dp.include_router(coins.router)
    dp.include_router(profile.router)
    dp.include_router(menu.router)
    dp.include_router(chat.router)

    print("ربات روشن شد و در حال اجراست... (برای توقف Ctrl+C بزن)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
