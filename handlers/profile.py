# -*- coding: utf-8 -*-
"""
مشاهده و ویرایش پروفایل شخصی
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import MIN_AGE, MAX_AGE

router = Router()


class EditProfile(StatesGroup):
    waiting_new_name = State()
    waiting_new_age = State()
    waiting_new_gender = State()
    waiting_new_city = State()
    waiting_new_bio = State()
    waiting_new_photo = State()


gender_edit_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="پسر 👦"), KeyboardButton(text="دختر 👧")]],
    resize_keyboard=True,
    one_time_keyboard=True
)


def gender_label(gender: str) -> str:
    if gender == "male":
        return "پسر 👦"
    if gender == "female":
        return "دختر 👧"
    return "نامشخص"


def profile_edit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ تغییر اسم", callback_data="edit_name")],
        [InlineKeyboardButton(text="🎂 تغییر سن", callback_data="edit_age")],
        [InlineKeyboardButton(text="⚧ تغییر جنسیت", callback_data="edit_gender")],
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
        f"جنسیت: {gender_label(user['gender'])}\n"
        f"شهر: {user['city']}\n"
        f"بیو: {user['bio']}\n\n"
        f"می‌خوای چی رو تغییر بدی؟"
    )
    kb = profile_edit_keyboard()

    if user.get("photo_id"):
        await message.answer_photo(photo=user["photo_id"], caption=caption, reply_markup=kb)
    else:
        await message.answer(caption, reply_markup=kb)


@router.callback_query(F.data == "edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("اسم جدیدت رو بنویس:")
    await state.set_state(EditProfile.waiting_new_name)
    await callback.answer()


@router.message(EditProfile.waiting_new_name, F.text)
async def process_new_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name or name.startswith("/"):
        await message.answer("لطفاً یه اسم معتبر بنویس (نمی‌تونه خالی باشه).")
        return
    if len(name) > 30:
        await message.answer("اسم خیلی طولانیه، لطفاً حداکثر ۳۰ حرف بنویس.")
        return
    db.create_or_update_user(message.from_user.id, name=name)
    await state.clear()
    await message.answer("✅ اسمت به‌روز شد.")


@router.message(EditProfile.waiting_new_name)
async def process_new_name_invalid(message: Message):
    await message.answer("لطفاً اسمت رو به صورت متن بنویس 📝")


@router.callback_query(F.data == "edit_age")
async def edit_age(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("سن جدیدت رو بنویس (فقط عدد):")
    await state.set_state(EditProfile.waiting_new_age)
    await callback.answer()


@router.message(EditProfile.waiting_new_age)
async def process_new_age(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("لطفاً فقط عدد بنویس.")
        return
    age = int(message.text)
    if age < MIN_AGE or age > MAX_AGE:
        await message.answer(f"سن باید بین {MIN_AGE} تا {MAX_AGE} باشه.")
        return
    db.create_or_update_user(message.from_user.id, age=age)
    await state.clear()
    await message.answer("✅ سنت به‌روز شد.")


@router.callback_query(F.data == "edit_gender")
async def edit_gender(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("جنسیت جدیدت رو انتخاب کن:", reply_markup=gender_edit_keyboard)
    await state.set_state(EditProfile.waiting_new_gender)
    await callback.answer()


@router.message(EditProfile.waiting_new_gender, F.text)
async def process_new_gender(message: Message, state: FSMContext):
    text = message.text
    if "پسر" in text:
        gender = "male"
    elif "دختر" in text:
        gender = "female"
    else:
        await message.answer("لطفاً یکی از دکمه‌ها رو انتخاب کن.", reply_markup=gender_edit_keyboard)
        return
    db.create_or_update_user(message.from_user.id, gender=gender)
    await state.clear()
    await message.answer("✅ جنسیتت به‌روز شد.", reply_markup=ReplyKeyboardRemove())


@router.callback_query(F.data == "edit_city")
async def edit_city(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("اسم شهر جدید رو بنویس:")
    await state.set_state(EditProfile.waiting_new_city)
    await callback.answer()


@router.message(EditProfile.waiting_new_city, F.text)
async def process_new_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if not city:
        await message.answer("لطفاً اسم شهرت رو بنویس.")
        return
    if len(city) > 30:
        await message.answer("اسم شهر خیلی طولانیه، لطفاً کوتاه‌تر بنویس.")
        return
    db.create_or_update_user(message.from_user.id, city=city)
    await state.clear()
    await message.answer("✅ شهرت به‌روز شد.")


@router.message(EditProfile.waiting_new_city)
async def process_new_city_invalid(message: Message):
    await message.answer("لطفاً اسم شهرت رو به صورت متن بنویس 📝")


@router.callback_query(F.data == "edit_bio")
async def edit_bio(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("بیوگرافی جدیدت رو بنویس:")
    await state.set_state(EditProfile.waiting_new_bio)
    await callback.answer()


@router.message(EditProfile.waiting_new_bio, F.text)
async def process_new_bio(message: Message, state: FSMContext):
    bio = message.text.strip()
    if not bio:
        await message.answer("لطفاً یه بیوگرافی کوتاه بنویس.")
        return
    if len(bio) > 300:
        await message.answer("بیوگرافی خیلی طولانیه، لطفاً حداکثر ۳۰۰ حرف بنویس.")
        return
    db.create_or_update_user(message.from_user.id, bio=bio)
    await state.clear()
    await message.answer("✅ بیوت به‌روز شد.")


@router.message(EditProfile.waiting_new_bio)
async def process_new_bio_invalid(message: Message):
    await message.answer("لطفاً بیوگرافیت رو به صورت متن بنویس 📝")


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
