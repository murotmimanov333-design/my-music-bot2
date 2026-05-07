import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from datetime import datetime

# --- ОРНОТУУЛАР ---
API_TOKEN = '8563734263:AAHxdMk8LxWFc3rs-Zuui-uYuleUMBWRong'
ADMIN_ID = 123456789  # Өзүңүздүн IDңизди жазыңыз

bot = Bot(token=API_TOKEN, parse_mode="Markdown")
dp = Dispatcher(bot)

# --- БАЗА МЕНЕН ИШТӨӨ ---
conn = sqlite3.connect("group_bot.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, invited_count INTEGER DEFAULT 0, join_date TIMESTAMP)")
cursor.execute("CREATE TABLE IF NOT EXISTS groups (group_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (group_id INTEGER PRIMARY KEY, limit_count INTEGER DEFAULT 5, is_active INTEGER DEFAULT 1)")
conn.commit()

# 1. РЕКЛАМА ТАРАТУУ (Рассылка)
@dp.message_handler(commands=['send_all'])
async def send_all(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    ad_text = message.get_args()
    if not ad_text:
        return await message.reply("⚠️ Использование: `/send_all Текст вашей рекламы`")

    cursor.execute("SELECT group_id FROM groups")
    groups = cursor.fetchall()
    
    success = 0
    for group in groups:
        try:
            await bot.send_message(group[0], ad_text)
            success += 1
            await asyncio.sleep(0.1)
        except: continue
    await message.answer(f"✅ Реклама успешно отправлена в {success} групп.")

# 2. РЕЖИМДИ БАШКАРУУ (ВКЛ/ВЫКЛ)
@dp.message_handler(commands=['mode_on'])
async def mode_on(message: types.Message):
    member = await message.chat.get_member(message.from_user.id)
    if not member.is_chat_admin(): return
    cursor.execute("INSERT OR REPLACE INTO settings (group_id, limit_count, is_active) VALUES (?, (SELECT limit_count FROM settings WHERE group_id = ?), 1)", (message.chat.id, message.chat.id))
    conn.commit()
    await message.answer("🔒 **Ограничение включено!** Теперь новые участники должны приглашать друзей, чтобы писать сообщения.")

@dp.message_handler(commands=['mode_off'])
async def mode_off(message: types.Message):
    member = await message.chat.get_member(message.from_user.id)
    if not member.is_chat_admin(): return
    cursor.execute("UPDATE settings SET is_active = 0 WHERE group_id = ?", (message.chat.id,))
    conn.commit()
    await message.answer("🔓 **Ограничение отключено!** Группа переведена в свободный режим.")

# 3. ЛИМИТ КОЮУ
@dp.message_handler(commands=['limit'])
async def set_limit(message: types.Message):
    member = await message.chat.get_member(message.from_user.id)
    if not member.is_chat_admin(): return
    args = message.get_args()
    if args.isdigit():
        cursor.execute("INSERT OR REPLACE INTO settings (group_id, limit_count, is_active) VALUES (?, ?, 1)", (message.chat.id, int(args)))
        conn.commit()
        await message.answer(f"⚙️ Установлен новый лимит: **{args}** чел.")

# 4. СТАТИСТИКА (/my, /top)
@dp.message_handler(commands=['my'])
async def my_stats(message: types.Message):
    cursor.execute("SELECT invited_count FROM users WHERE user_id = ?", (message.from_user.id,))
    count = (cursor.fetchone() or (0,))[0]
    await message.reply(f"📊 Вы пригласили: **{count}** чел.")

@dp.message_handler(commands=['top'])
async def top_users(message: types.Message):
    cursor.execute("SELECT user_id, invited_count FROM users ORDER BY invited_count DESC LIMIT 10")
    rows = cursor.fetchall()
    text = "🏆 **Топ участников по приглашениям:**\n\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. ID: `{row[0]}` — **{row[1]}** чел.\n"
    await message.answer(text)

# 5. КОНТРОЛЬ СООБЩЕНИЙ
@dp.message_handler(content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
async def on_user_joined(message: types.Message):
    cursor.execute("INSERT OR IGNORE INTO groups (group_id) VALUES (?)", (message.chat.id,))
    inviter_id = message.from_user.id
    for m in message.new_chat_members:
        if not m.is_bot:
            cursor.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)", (m.id, datetime.now()))
    
    added = len([m for m in message.new_chat_members if not m.is_bot])
    if added > 0:
        cursor.execute("UPDATE users SET invited_count = invited_count + ? WHERE user_id = ?", (added, inviter_id))
    conn.commit()

@dp.message_handler(chat_type=[types.ChatType.GROUP, types.ChatType.SUPERGROUP])
async def check_permissions(message: types.Message):
    if message.from_user.is_bot: return
    
    cursor.execute("SELECT is_active, limit_count FROM settings WHERE group_id = ?", (message.chat.id,))
    settings = cursor.fetchone()
    if settings and settings[0] == 0: return # Если режим выключен

    member = await message.chat.get_member(message.from_user.id)
    if member.is_chat_admin(): return

    cursor.execute("SELECT invited_count, join_date FROM users WHERE user_id = ?", (message.from_user.id,))
    user_data = cursor.fetchone()
    if not user_data or user_data[1] is None: return # Старые участники

    limit = settings[1] if settings else 5
    if user_data[0] < limit:
        await message.delete()
        await message.answer(f"⚠️ {message.from_user.first_name}, чтобы писать в группе, вам нужно пригласить еще {limit - user_data[0]} чел.!", delete_after=7)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
          
