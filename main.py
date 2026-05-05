import asyncio
import random
import re
import sqlite3
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8546503087:AAFbcV2S9zhAaX6O9pfZPAIq5ImVGwjAmqg" 
ADMIN_ID = 5906354673  
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
DB_PATH = '/data/rdno_bot.db' if os.path.exists('/data') else 'rdno_bot.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, balance INTEGER, 
                       limit_expires TEXT, max_limit INTEGER)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, limit_expires, max_limit FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        # ЖАҢЫ ОЮНЧУГА 5000 МОНЕТА БЕРИЛЕТ
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, 5000, None, 10000))
        conn.commit()
        row = (5000, None, 10000)
    conn.close()
    return {"balance": row[0], "limit_expires": row[1], "max_limit": row[2]}

def update_user(user_id, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for key, value in kwargs.items():
        cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

# Переменные
game_history = []
bandit_symbols = ["♣️", "♥️", "♠️", "♦️", "🧧"]
red_numbers = [1, 3, 5, 7, 9, 11]

# --- КОМАНДЫ ---

@dp.message(Command("id"))
async def cmd_id(message: types.Message):
    await message.answer(f"Ваш ID: <code>{message.from_user.id}</code>", parse_mode="HTML")

@dp.message(F.text.lower() == "б")
async def check_balance(message: types.Message):
    user = get_user(message.from_user.id)
    name = message.from_user.first_name.upper()
    await message.answer(f"{name}\nМонеты: {user['balance']}🌑")

@dp.message(F.text.lower() == "лог")
async def show_log(message: types.Message):
    if not game_history:
        await message.answer("Лог пуст.")
    else:
        await message.answer("\n".join(game_history[-11:]))

# --- ДОНАТ МЕНЮ ---
@dp.message(F.text.contains("Донат"))
async def show_donate(message: types.Message):
    text = (
        "Монеты🌑\n200.000 - 100 сом\n500.000 - 230 сом\n1.000.000 - 450 сом\n"
        "2.000.000 - 845 сом\n5.000.000 - 2.000 сом\n10.000.000 - 4.000 сом\n"
        "50.000.000 - 20.000 сом\n100.000.000 - 40.000 сом\n\n"
        "Telegram не сможет помочь с покупками, сделанными через нашего бота.\n"
        "Если возникнут вопросы, Вы можете обратиться к: @Argen_70_kassa"
    )
    builder = InlineKeyboardBuilder()
    btns = ["200.000", "500.000", "1.000.000", "2.000.000", "5.000.000", "10.000.000", "50.000.000", "100.000.000"]
    for b in btns: builder.button(text=b, url="https://t.me/Argen_70_kassa")
    builder.button(text="✳️ Вор в законе - 4.000 сом 30 дней", url="https://t.me/Argen_70_kassa")
    builder.button(text="👮 Полицейский - 2.000 сом 30 дней", url="https://t.me/Argen_70_kassa")
    builder.adjust(2, 2, 2, 2, 1, 1)
    await message.answer(text, reply_markup=builder.as_markup())

# --- АДМИН: ВЫДАЧА ---
@dp.message(lambda m: m.from_user.id == ADMIN_ID and m.text.startswith("+"))
async def admin_give(message: types.Message):
    try:
        parts = message.text.split()
        t_id, amount = int(parts[1]), int(parts[2])
        user = get_user(t_id)
        expiry = (datetime.now() + timedelta(days=7)).isoformat()
        update_user(t_id, balance=user['balance'] + amount, limit_expires=expiry, max_limit=5000000)
        await message.answer(f"✅ Для ID {t_id} открыт лимит 5 млн на 7 дней.\nДобавлено: {amount} 🌑")
    except: pass

# --- ПЕРЕВОД ---
@dp.message(F.text.startswith("+"))
async def transfer(message: types.Message):
    if not message.reply_to_message: return
    s_id, t_id = message.from_user.id, message.reply_to_message.from_user.id
    if s_id == t_id: return
    try:
        amount = int(message.text.replace("+", "").strip())
        s_user = get_user(s_id)
        limit = 10000
        if s_user['limit_expires'] and datetime.now() < datetime.fromisoformat(s_user['limit_expires']):
            limit = s_user['max_limit']
        if amount > limit: return await message.answer(f"❌ Лимит! Ваш текущий лимит: {limit} 🌑")
        if s_user['balance'] < amount: return await message.answer("Недостаточно средств!")
        update_user(s_id, balance=s_user['balance'] - amount)
        update_user(t_id, balance=get_user(t_id)['balance'] + amount)
        await message.answer(f"✅ Переведено: {amount} 🌑")
    except: pass

# --- БАНДИТ ---
@dp.message(F.text.lower().startswith("бандит"))
async def bandit(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = message.from_user.first_name.upper()
    match = re.search(r"\d+", message.text)
    bet = int(match.group()) if match else 1000
    if user['balance'] < bet: return await message.answer("Недостаточно средств!")

    update_user(user_id, balance=user['balance'] - bet)
    slots = ["⬜"] * 5
    msg = await message.answer(f"{name}\n\n" + "".join(slots))
    res = [random.choice(bandit_symbols) for _ in range(5)]
    for i in range(5):
        await asyncio.sleep(1)
        slots[i] = res[i]
        await msg.edit_text(f"{name}\n\n" + "".join(slots))
    win = 0
    if res.count("♦️") == 5: win = 70000
    elif res.count("♠️") == 5: win = 40000
    elif res.count("♥️") == 3: win = 15000
    elif res.count("♣️") == 3: win = 10000
    elif any(res.count(s) == 3 for s in ["♦️", "🧧"]): win = random.choice([3000, 4000, 5000])
    if win > 0:
        update_user(user_id, balance=get_user(user_id)['balance'] + win)
        await msg.edit_text(f"{name}\n\n{''.join(slots)}\n\nВыигрыш: {win} 🌑")
    else: await msg.edit_text(f"{name}\n\n{''.join(slots)}\n\nПроигрыш: {bet} 🌑")

# --- РУЛЕТКА ---
@dp.message(F.text.regexp(r'^(\d+)\s*([кчз])$'))
async def roulette(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    match = re.match(r'^(\d+)\s*([кчз])$', message.text.lower())
    bet, col = int(match.group(1)), match.group(2)
    if user['balance'] < bet: return
    update_user(user_id, balance=user['balance'] - bet)
    colors = {'к': 'красное', 'ч': 'черное', 'з': 'зеро'}
    name = message.from_user.first_name.upper()
    await message.answer(f"Ставка принята: {name} {bet} на {colors[col]}")
    msg = await message.answer(f"{name}\nКрутит (3 сек.)")
    await asyncio.sleep(3)
    num = random.randint(0, 12)
    if num == 0: d, c = "0💚", "зеро"
    elif num in red_numbers: d, c = f"{num}🔴", "красное"
    else: d, c = f"{num}⚫", "черное"
    game_history.append(d)
    if colors[col] == c:
        win = bet * 14 if c == "зеро" else bet * 2
        update_user(user_id, balance=get_user(user_id)['balance'] + win)
        res_t = f"выиграл {win}"
    else: res_t = f"проиграл {bet}"
    await msg.edit_text(f"Рулетка: {d}\n{name} {bet} на {colors[col]}\n{name} {res_t}")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
