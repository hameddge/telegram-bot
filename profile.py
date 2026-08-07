# -*- coding: utf-8 -*-
"""
مشاهده و ویرایش پروفایل شخصی
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import MIN_AGE, MAX_AGE

router = Router()


class EditProfile(StatesGroup):
    waiting_new_age = State()
    waiting_new_city = State()
    waiting_new_bio = State()
    waiting_new_photo = State()


def profile_edit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎂 تغییر سن", callback_data="edit_age")],
        [InlineKeyboardButton(text="📍 تغییر شهر", callback_data="edit_city")],
        [InlineKeyboardButton(text="📝 تغییر بیو", callback_data="edit_bio")],
        [InlineKeyboardButton(text="📸 تغییر عکس", callback_data="edit_photo")],
    ])


@router.message(F.text == "/profile")
async def cmd_profile(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user.get("is_active"):
        await message.answer("هنوز ثبت‌نام نکردی. دستور /start رو بزن.")
        return

    caption = (
        f"👤 پروفایل تو:\n\n"
        f"اسم: {user['name']}\n"
        f"سن: {user['age']}\n"
        f"شهر: {user['city']}\n"
        f"بیو: {user['bio']}\n\n"
        f"می‌خوای چی رو تغییر بدی؟"
    )
    kb = profile_edit_keyboard()

    if user.get("photo_id"):
        await message.answer_photo(photo=user["photo_id"], caption=caption, reply_markup=kb)
    else:
        await message.answer(caption, reply_markup=kb)


@router.callback_query(F.data == "edit_age")
async def edit_age(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("سن جدیدت رو بنویس (فقط عدد):")
    await state.set_state(EditProfile.waiting_new_age)
    await callback.answer()


@router.message(EditProfile.waiting_new_age)
async def process_new_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط عدد بنویس.")
        return
    age = int(message.text)
    if age < MIN_AGE or age > MAX_AGE:
        await message.answer(f"سن باید بین {MIN_AGE} تا {MAX_AGE} باشه.")
        return
    db.create_or_update_user(message.from_user.id, age=age)
    await state.clear()
    await message.answer("✅ سنت به‌روز شد.")


@router.callback_query(F.data == "edit_city")
async def edit_city(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("اسم شهر جدید رو بنویس:")
    await state.set_state(EditProfile.waiting_new_city)
    await callback.answer()


@router.message(EditProfile.waiting_new_city)
async def process_new_city(message: Message, state: FSMContext):
    db.create_or_update_user(message.from_user.id, city=message.text)
    await state.clear()
    await message.answer("✅ شهرت به‌روز شد.")


@router.callback_query(F.data == "edit_bio")
async def edit_bio(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("بیوگرافی جدیدت رو بنویس:")
    await state.set_state(EditProfile.waiting_new_bio)
    await callback.answer()


@router.message(EditProfile.waiting_new_bio)
async def process_new_bio(message: Message, state: FSMContext):
    db.create_or_update_user(message.from_user.id, bio=message.text)
    await state.clear()
    await message.answer("✅ بیوت به‌روز شد.")


@router.callback_query(F.data == "edit_photo")
async def edit_photo(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("عکس جدیدت رو بفرست 📸")
    await state.set_state(EditProfile.waiting_new_photo)
    await callback.answer()


@router.message(EditProfile.waiting_new_photo, F.photo)
async def process_new_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    db.create_or_update_user(message.from_user.id, photo_id=photo_id)
    await state.clear()
    await message.answer("✅ عکست به‌روز شد.")


@router.message(EditProfile.waiting_new_photo)
async def process_new_photo_invalid(message: Message):
    await message.answer("لطفاً یه عکس بفرست 📸")
