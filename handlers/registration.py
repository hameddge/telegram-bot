# -*- coding: utf-8 -*-
"""
هندلر ثبت‌نام و ساخت پروفایل
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import database as db
from config import MIN_AGE, MAX_AGE, REFERRAL_REWARD_COINS, PROFILE_COMPLETE_REWARD_COINS
from handlers import menu as menu_module

router = Router()


class Registration(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_gender = State()
    waiting_city = State()
    waiting_bio = State()
    waiting_photo = State()


class AnonymousMessage(StatesGroup):
    waiting_text = State()


gender_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="پسر 👦"), KeyboardButton(text="دختر 👧")]],
    resize_keyboard=True,
    one_time_keyboard=True
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject):
    args = command.args

    # لینک "پیام ناشناس" - کار می‌کنه چه کاربر ثبت‌نام کرده باشه چه نه
    if args and args.startswith("msg_"):
        try:
            target_id = int(args[4:])
        except ValueError:
            target_id = None
        if target_id and target_id != message.from_user.id:
            await state.update_data(anon_target=target_id)
            await state.set_state(AnonymousMessage.waiting_text)
            await message.answer("پیامت رو بنویس، به صورت کاملاً ناشناس براش ارسال میشه 🤫")
            return

    user = db.get_user(message.from_user.id)

    if user and user.get("is_active"):
        await message.answer(
            f"سلام {user['name']} 👋\nخوش برگشتی! از منو یکی از گزینه‌ها رو انتخاب کن.",
            reply_markup=menu_module.main_menu_keyboard()
        )
        return

    referred_by = None
    if args and args.startswith("ref_"):
        try:
            referred_by = int(args[4:])
        except ValueError:
            referred_by = None
        if referred_by == message.from_user.id:
            referred_by = None

    db.create_or_update_user(message.from_user.id)
    if referred_by:
        await state.update_data(referred_by=referred_by)

    await message.answer(
        "سلام! خوش اومدی 🌸\nبیا اول یه پروفایل کوچیک بسازیم.\n\nاسمت چیه؟"
    )
    await state.set_state(Registration.waiting_name)


@router.message(AnonymousMessage.waiting_text, F.text)
async def process_anonymous_message(message: Message, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("anon_target")
    await state.clear()

    if not target_id:
        await message.answer("مشکلی پیش اومد، دوباره امتحان کن.")
        return

    try:
        await message.bot.send_message(
            target_id,
            f"📩 یک پیام ناشناس برات اومد:\n\n{message.text}"
        )
        await message.answer("پیامت به صورت ناشناس ارسال شد ✅")
    except Exception:
        await message.answer("ارسال پیام ناموفق بود، احتمالاً طرف مقابل ربات رو استارت نکرده یا بلاکش کرده.")


@router.message(Registration.waiting_name, F.text)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name or name.startswith("/"):
        await message.answer("لطفاً یه اسم معتبر بنویس (نمی‌تونه خالی باشه).")
        return
    if len(name) > 30:
        await message.answer("اسم خیلی طولانیه، لطفاً حداکثر ۳۰ حرف بنویس.")
        return

    await state.update_data(name=name)
    await message.answer("چند سالته؟ (فقط عدد بنویس)")
    await state.set_state(Registration.waiting_age)


@router.message(Registration.waiting_name)
async def process_name_invalid(message: Message):
    await message.answer("لطفاً اسمت رو به صورت متن بنویس 📝")


@router.message(Registration.waiting_age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط عدد بنویس. مثلاً: 22")
        return

    age = int(message.text)
    if age < MIN_AGE or age > MAX_AGE:
        await message.answer(f"سن باید بین {MIN_AGE} تا {MAX_AGE} باشه.")
        return

    await state.update_data(age=age)
    await message.answer("جنسیتت چیه؟", reply_markup=gender_keyboard)
    await state.set_state(Registration.waiting_gender)


@router.message(Registration.waiting_gender)
async def process_gender(message: Message, state: FSMContext):
    text = message.text
    if "پسر" in text:
        gender = "male"
    elif "دختر" in text:
        gender = "female"
    else:
        await message.answer("لطفاً یکی از دکمه‌ها رو انتخاب کن.")
        return

    await state.update_data(gender=gender)
    await message.answer("اهل کجایی؟ (اسم شهر)", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.waiting_city)


@router.message(Registration.waiting_city, F.text)
async def process_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if not city:
        await message.answer("لطفاً اسم شهرت رو بنویس.")
        return
    if len(city) > 30:
        await message.answer("اسم شهر خیلی طولانیه، لطفاً کوتاه‌تر بنویس.")
        return

    await state.update_data(city=city)
    await message.answer("یه بیوگرافی کوتاه درباره خودت بنویس (چند جمله کافیه)")
    await state.set_state(Registration.waiting_bio)


@router.message(Registration.waiting_city)
async def process_city_invalid(message: Message):
    await message.answer("لطفاً اسم شهرت رو به صورت متن بنویس 📝")


@router.message(Registration.waiting_bio, F.text)
async def process_bio(message: Message, state: FSMContext):
    bio = message.text.strip()
    if not bio:
        await message.answer("لطفاً یه بیوگرافی کوتاه بنویس.")
        return
    if len(bio) > 300:
        await message.answer("بیوگرافی خیلی طولانیه، لطفاً حداکثر ۳۰۰ حرف بنویس.")
        return

    await state.update_data(bio=bio)
    await message.answer("حالا یه عکس پروفایل بفرست 📸")
    await state.set_state(Registration.waiting_photo)


@router.message(Registration.waiting_bio)
async def process_bio_invalid(message: Message):
    await message.answer("لطفاً بیوگرافیت رو به صورت متن بنویس 📝")


@router.message(Registration.waiting_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()

    db.create_or_update_user(
        message.from_user.id,
        name=data["name"],
        age=data["age"],
        gender=data["gender"],
        city=data["city"],
        bio=data["bio"],
        photo_id=photo_id,
        is_active=1
    )
    db.add_coins(message.from_user.id, PROFILE_COMPLETE_REWARD_COINS)

    referred_by = data.get("referred_by")
    if referred_by:
        db.add_coins(referred_by, REFERRAL_REWARD_COINS)
        try:
            await message.bot.send_message(
                referred_by,
                f"🎉 یکی از دوستات با لینک دعوت تو ثبت‌نام کرد! {REFERRAL_REWARD_COINS} سکه بهت اضافه شد 🪙"
            )
        except Exception:
            pass

    await state.clear()
    await message.answer(
        "پروفایلت با موفقیت ساخته شد! 🎉\n"
        f"🪙 {PROFILE_COMPLETE_REWARD_COINS} سکه برای تکمیل پروفایل بهت داده شد.\n\n"
        "از منوی پایین یکی از گزینه‌ها رو انتخاب کن، یا با /browse بریم سراغ دوستیابی.",
        reply_markup=menu_module.main_menu_keyboard()
    )


@router.message(Registration.waiting_photo)
async def process_photo_invalid(message: Message):
    await message.answer("لطفاً یه عکس بفرست 📸 (نه متن)")
