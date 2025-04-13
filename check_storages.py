import asyncio
import aiohttp
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command

# === НАСТРОЙКИ ===
BOT_TOKEN = "7392379040:AAHCxjyeoIgbWLh-90XaN1APfvX-0Deg_54"
ADMIN_CHAT_ID = 5767985121
DEFAULT_INTERVAL = 120  # 2 минуты

# === ХРАНИЛИЩЕ ПОЛЬЗОВАТЕЛЕЙ И ИНТЕРВАЛОВ ===
user_settings = {}         # {user_id: interval}
user_check_counts = {}     # {user_id: count}

# === ИНИЦИАЛИЗАЦИЯ ===
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# === ПРОВЕРКА КЛАДОВОК НА САЙТЕ ТАЛАН ===
async def check_storages():
    url = "https://уфа.талан.рф/apartments/storages"
    found = []

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                text = await resp.text()
                soup = BeautifulSoup(text, 'html.parser')
                items = soup.find_all("div", class_="cards-item")

                for item in items:
                    status = item.get_text(strip=True).lower()
                    if "в продаже" in status and "скоро" not in status and "ожидается" not in status:
                        found.append(f"<b>Свободные кладовки есть!</b>\n<a href=\"{url}\">Перейти на сайт</a>")
                        break
        except Exception as e:
            print(f"Ошибка при проверке: {e}")

    return found

# === ПЕРИОДИЧЕСКАЯ ПРОВЕРКА ДЛЯ КАЖДОГО ПОЛЬЗОВАТЕЛЯ ===
async def user_check_loop(user_id: int):
    already_sent = set()
    while True:
        interval = user_settings.get(user_id, DEFAULT_INTERVAL)
        results = await check_storages()
        user_check_counts[user_id] = user_check_counts.get(user_id, 0) + 1
        for msg in results:
            if msg not in already_sent:
                await bot.send_message(chat_id=user_id, text=msg)
                already_sent.add(msg)
        await asyncio.sleep(interval)

# === ПРОВЕРКА АДМИНА ===
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_CHAT_ID

# === КОМАНДЫ БОТА ===
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    if user_id not in user_settings:
        user_settings[user_id] = DEFAULT_INTERVAL
        asyncio.create_task(user_check_loop(user_id))

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перейти на сайт", url="https://уфа.талан.рф/apartments/storages")]
        ]
    )

    await message.answer(
        "<b>Привет!</b>\n"
        "Я бот для отслеживания кладовок на сайте Талан.\n\n"
        "Доступные команды:\n"
        "/check — Проверка вручную\n"
        "/interval — Установить интервал\n"
        "/reset — Сброс настроек\n"
        "/about — О боте\n"
        "/help — Помощь",
        reply_markup=kb
    )

@dp.message(Command("check"))
async def cmd_check(message: Message):
    results = await check_storages()
    if results:
        for msg in results:
            await message.answer(msg)
    else:
        await message.answer("Свободных кладовок пока нет в продаже.")

@dp.message(Command("interval"))
async def cmd_interval(message: Message):
    await message.answer("Введите интервал проверки в секундах (например, 120):")

@dp.message(F.text.regexp(r"^\d+$"))
async def set_interval(message: Message):
    interval = int(message.text)
    user_id = message.from_user.id
    if 10 <= interval <= 86400:
        user_settings[user_id] = interval
        await message.answer(f"Интервал проверки обновлён: каждые {interval} сек.")
    else:
        await message.answer("Введите значение от 10 до 86400 секунд.")

@dp.message(Command("reset"))
async def cmd_reset(message: Message):
    user_id = message.from_user.id
    user_settings[user_id] = DEFAULT_INTERVAL
    user_check_counts[user_id] = 0
    await message.answer("Настройки сброшены.")
    ("Интервал установлен по умолчанию (120 сек).")

@dp.message(Command("about"))
async def cmd_about(message: Message):
    await message.answer("Я бот, который следит за кладовками на сайте Талан и уведомляет, когда они появляются в продаже.")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/check — Проверка вручную\n"
        "/interval — Установить интервал проверки\n"
        "/reset — Сброс настроек\n"
        "/about — О боте\n"
        "/help — Помощь\n"
        "/stats — Статистика (только для админа)"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Эта команда доступна только администратору.")
        return

    stats = f"<b>Статистика:</b>\nПользователей: {len(user_settings)}\n\n"
    for user_id, interval in user_settings.items():
        count = user_check_counts.get(user_id, 0)
        stats += f"• <code>{user_id}</code>: интервал {interval} сек, проверок: {count}\n"

    await message.answer(stats)

@dp.message(F.text)
async def fallback(message: Message):
    await cmd_help(message)

# === ЗАПУСК ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())