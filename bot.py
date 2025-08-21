import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from datetime import datetime, date
from collections import Counter

# 🔑 Config
API_TOKEN = "8265201585:AAGhmbqqlJRN6wAB7M472rWAQ4CFPjPPVL8"
SUPER_ADMIN_ID = 6969913541   # bu yerga SuperAdmin ID yozasiz

logging.basicConfig(level=logging.INFO)

# 🔧 Bot setup
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# 👥 Foydalanuvchilar
admins = set()
ofitsants = set()

# 🍽 Stollar
stollar = {}

# 📊 Statistikaga saqlanadigan ma’lumotlar
statistika = {
    "orders": [],   # (sana, ofitsant_id, stol, mahsulot, narx)
    "totals": []    # (sana, stol, summa, ofitsant_id)
}

# --- STATES ---
class StolStates(StatesGroup):
    waiting_for_stol_number = State()
    waiting_for_stol_price = State()
    waiting_for_meal_name = State()
    waiting_for_meal_price = State()

# --- START ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if message.from_user.id == SUPER_ADMIN_ID:
        await message.answer("👑 Salom, SuperAdmin!\n/admin_add ID\n/ofitsant_add ID\n/statistika")
    elif message.from_user.id in admins:
        await message.answer("📊 Salom, Admin!\n/statistika — umumiy hisobot")
    elif message.from_user.id in ofitsants:
        await message.answer("🧑‍🍳 Salom, Ofitsant!\n/stol_och — yangi stol ochish")
    else:
        await message.answer("❌ Sizni SuperAdmin hali qo‘shmagan.")

# --- SuperAdmin komandalar ---
@dp.message_handler(commands=['admin_add'])
async def add_admin(message: types.Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    try:
        user_id = int(message.get_args())
        admins.add(user_id)
        await message.answer(f"✅ {user_id} Admin qo‘shildi")
    except:
        await message.answer("❌ To‘g‘ri ID kiriting")

@dp.message_handler(commands=['ofitsant_add'])
async def add_ofitsant(message: types.Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    try:
        user_id = int(message.get_args())
        ofitsants.add(user_id)
        await message.answer(f"✅ {user_id} Ofitsant qo‘shildi")
    except:
        await message.answer("❌ To‘g‘ri ID kiriting")

# --- Ofitsant: Stol ochish ---
@dp.message_handler(commands=['stol_och'])
async def stol_och(message: types.Message):
    if message.from_user.id not in ofitsants and message.from_user.id != SUPER_ADMIN_ID:
        return
    await message.answer("➡️ Stol raqamini kiriting:")
    await StolStates.waiting_for_stol_number.set()

@dp.message_handler(state=StolStates.waiting_for_stol_number)
async def stol_number(message: types.Message, state: FSMContext):
    stol = message.text
    await state.update_data(stol=stol)
    await message.answer(f"➡️ Stol {stol} uchun boshlang‘ich narxni kiriting:")
    await StolStates.waiting_for_stol_price.set()

@dp.message_handler(state=StolStates.waiting_for_stol_price)
async def stol_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
    except:
        return await message.answer("❌ Faqat son kiriting.")
    data = await state.get_data()
    stol = data['stol']
    stollar[stol] = {"summa": price, "buyurtmalar": [], "ofitsant": message.from_user.id}
    await message.answer(f"✅ {stol}-stol ochildi.\nBuyurtma qo‘shish uchun /zakaz")
    await state.finish()

# --- Ofitsant: Zakaz qo‘shish ---
@dp.message_handler(commands=['zakaz'])
async def zakaz_start(message: types.Message):
    if message.from_user.id not in ofitsants and message.from_user.id != SUPER_ADMIN_ID:
        return
    if not stollar:
        return await message.answer("❌ Hali stol ochilmagan.")
    await message.answer("🍽 Ovqat nomini kiriting:")
    await StolStates.waiting_for_meal_name.set()
@dp.message_handler(state=StolStates.waiting_for_meal_name)
async def zakaz_meal(message: types.Message, state: FSMContext):
    await state.update_data(meal=message.text)
    await message.answer("💰 Narxini kiriting:")
    await StolStates.waiting_for_meal_price.set()

@dp.message_handler(state=StolStates.waiting_for_meal_price)
async def zakaz_meal_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
    except:
        return await message.answer("❌ Faqat son kiriting.")
    data = await state.get_data()
    meal = data['meal']
    stol = list(stollar.keys())[-1]
    stollar[stol]['buyurtmalar'].append((meal, price))
    stollar[stol]['summa'] += price
    # statistikaga yozib qo'yish
    statistika["orders"].append((date.today(), message.from_user.id, stol, meal, price))
    await message.answer(f"✅ {meal} ({price} so‘m) qo‘shildi.\n/stol_yop — stolni yopish")
    await state.finish()

# --- Ofitsant: Stol yopish ---
@dp.message_handler(commands=['stol_yop'])
async def stol_yop(message: types.Message):
    if message.from_user.id not in ofitsants and message.from_user.id != SUPER_ADMIN_ID:
        return
    if not stollar:
        return await message.answer("❌ Hali stol ochilmagan.")
    stol = list(stollar.keys())[-1]
    summa = stollar[stol]['summa']
    ofitsant_id = stollar[stol]['ofitsant']
    await message.answer(f"🧾 {stol}-stol yopildi.\nYakuniy summa: {summa} so‘m")
    statistika["totals"].append((date.today(), stol, summa, ofitsant_id))
    del stollar[stol]

# --- Statistika ---
@dp.message_handler(commands=['statistika'])
async def statistikani_korish(message: types.Message):
    if message.from_user.id not in admins and message.from_user.id != SUPER_ADMIN_ID:
        return

    bugun = date.today()
    bugungi_orders = [o for o in statistika["orders"] if o[0] == bugun]
    bugungi_totals = [t for t in statistika["totals"] if t[0] == bugun]

    jami_summa = sum(t[2] for t in bugungi_totals)
    jami_stol = len(bugungi_totals)

    mahsulotlar = Counter([o[3] for o in bugungi_orders])
    top_meals = mahsulotlar.most_common(3)

    ofitsantlar = Counter([o[1] for o in bugungi_orders])
    top_ofitsantlar = ofitsantlar.most_common(3)

    msg = f"📊 Bugungi Statistika ({bugun}):\n"
    msg += f"💰 Jami tushum: {jami_summa} so‘m\n"
    msg += f"🍽 Ochildi: {jami_stol} ta stol\n\n"

    msg += "🥇 Eng ko‘p sotilganlar:\n"
    for meal, soni in top_meals:
        msg += f"- {meal}: {soni} marta\n"

    msg += "\n🧑‍🍳 Eng faol ofitsantlar:\n"
    for ofitsant_id, soni in top_ofitsantlar:
        msg += f"- ID {ofitsant_id}: {soni} ta zakaz\n"

    await message.answer(msg)

# --- Run ---
if name == 'main':
    executor.start_polling(dp, skip_updates=True)
