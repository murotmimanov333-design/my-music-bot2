import os
import sys
import subprocess

# --- КИТЕПКАНАЛАРДЫ АВТОМАТТЫК ОРНОТУУ ---
# Бул бөлүм Render'дагы "Read-only" катасын айланып өтөт
path = os.path.join(os.getcwd(), "libs")
if not os.path.exists(path):
    os.makedirs(path)

sys.path.insert(0, path)

try:
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command
    from aiogram.utils.keyboard import InlineKeyboardBuilder
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--target", path, "aiogram==3.10.0", "pydantic==2.8.2"])
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command
    from aiogram.utils.keyboard import InlineKeyboardBuilder

import asyncio
import random
import re
import sqlite3
from datetime import datetime, timedelta

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8546503087:AAFbcV2S9zhAaX6O9pfZPAIq5ImVGwjAmqg" 
ADMIN_ID = 5906354673  
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
DB_PATH = 'rdno_bot.db'

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

# Оюндар
game_history = []
bandit_symbols = ["♣️", "♥️", "♠️", "♦️", "🧧"]
red_numbers = [1, 3, 5, 7, 9, 11]

# --- КОМАНДАЛАР (ОРУС ТИЛИНДЕ) ---
@dp.message(Command("id"))
async def cmd_id(message: types.Message):
    await message.answer(f"Ваш ID: <code>{message.from_user.id}</code>", parse_mode="HTML")

@dp.message(F.text.lower() == "б")
async def check_balance(message: types.Message):
    user = get_user(message.from_user.id)
    name = message.from_user.first_name.upper()
    await message.answer(f"{name}\nМонеты: {user['balance']}🌑")

@dp.message(F.text.contains("Донат"))
async def show_donate(message: types.Message):
    text = (
        "Монеты🌑\n200.000 - 100 сом\n500.000 - 230 сом\n1.000.000 - 450 сом\n"
        "2.000.000 - 845 сом\n5.000.000 - 2.000 сом\n10.000.000 - 4.000 сом\n"
        "50.000.000 - 20.000 сом\n100.000.000 - 40.000 сом\n\n"
        "Telegram не сможет помочь с покупками...\nОбратиться к: @Argen_70_kassa"
    )
    builder = InlineKeyboardBuilder()
    for b in ["200.000", "500.000", "1.000.000", "2.000.000", "5.000.000", "10.000.000", "50.000.000", "100.000.000"]:
        builder.button(text=b, url="https://t.me/Argen_70_kassa")
    builder.button(text="✳️ Вор в законе - 4.000 сом 30 дней", url="https://t.me/Argen_70_kassa")
    builder.button(text="👮 Полицейский - 2.000 сом 30 дней", url="https://t.me/Argen_70_kassa")
    builder.adjust(2, 2, 2, 2, 1, 1)
    await message.answer(text, reply_markup=builder.as_markup())

@dp.message(F.text.lower().startswith("бандит"))
async def bandit(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = message.from_user.first_name.upper()
    match = re.search(r"\d+", message.text)
    bet = int(match.group()) if match else 1000
    if user['balance'] < bet: return
    update_user(user_id, balance=user['balance'] - bet)
    slots = ["⬜"] * 5
    msg = await message.answer(f"{name}\n\n" + "".join(slots))
    res = [random.choice(bandit_symbols) for _ in range(5)]
    for i in range(5):
        await asyncio.sleep(0.7)
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

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
