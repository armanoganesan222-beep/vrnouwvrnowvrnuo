import asyncio
import html
import random
import sqlite3
import uuid

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = "8098580791:AAHBPMoOuVKU7WdPD8WYAJjU8-RHIvQwbrY"

DB_NAME = "ice_bot.db"

LOBBY_SECONDS = 30

MIN_PLAYERS = 2
MAX_PLAYERS = 8

XP_WIN = 100
XP_PARTICIPATION = 20


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()

bot_username = ""


# ============================================================
# DATABASE
# ============================================================

db = sqlite3.connect(
    DB_NAME,
    check_same_thread=False
)

db.row_factory = sqlite3.Row


def init_database():
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            xp INTEGER DEFAULT 0,
            games INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0
        )
        """
    )

    db.commit()


def register_user(user):
    username = user.username or ""
    first_name = user.first_name or "Игрок"

    db.execute(
        """
        INSERT INTO users (
            user_id,
            username,
            first_name
        )
        VALUES (?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
        """,
        (
            user.id,
            username,
            first_name
        )
    )

    db.commit()


def get_user(user_id):
    return db.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()


def add_game(user_id):
    db.execute(
        """
        UPDATE users
        SET games = games + 1
        WHERE user_id = ?
        """,
        (user_id,)
    )

    db.commit()


def add_win(user_id):
    db.execute(
        """
        UPDATE users
        SET wins = wins + 1
        WHERE user_id = ?
        """,
        (user_id,)
    )

    db.commit()


def add_xp(user_id, amount):
    db.execute(
        """
        UPDATE users
        SET xp = xp + ?
        WHERE user_id = ?
        """,
        (
            amount,
            user_id
        )
    )

    db.commit()


def get_level(xp):
    return (xp // 500) + 1


# ============================================================
# ИГРЫ
# ============================================================

games = {}


def create_game_id():
    # Только буквы и цифры.
    # Никаких "_" и ":".
    return uuid.uuid4().hex[:12]


def get_chat_game(chat_id):
    return games.get(chat_id)


def find_game_by_id(game_id):
    for game in games.values():
        if game["id"] == game_id:
            return game

    return None


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def escape_name(name):
    return html.escape(
        name or "Игрок"
    )


def get_player_name(game, user_id):
    return escape_name(
        game["names"].get(
            user_id,
            "Игрок"
        )
    )


def remaining_seconds(game):
    now = asyncio.get_running_loop().time()

    seconds = int(
        game["deadline"] - now
    )

    return max(
        0,
        seconds
    )


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

def main_menu():
    add_url = (
        f"https://t.me/"
        f"{bot_username}"
        f"?startgroup=true"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧊 Играть",
                    callback_data="menu:play"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Профиль",
                    callback_data="menu:profile"
                ),
                InlineKeyboardButton(
                    text="🏆 Топ",
                    callback_data="menu:top"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Добавить в группу",
                    url=add_url
                )
            ]
        ]
    )


def back_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="menu:back"
                )
            ]
        ]
    )


# ============================================================
# ГРУППОВОЕ МЕНЮ
# ============================================================

def group_start_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧊 Начать игру",
                    callback_data="game:create"
                )
            ]
        ]
    )


# ============================================================
# ВЫБОР РАЗМЕРА
# ============================================================

def size_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="3 × 3",
                    callback_data="size:3"
                ),
                InlineKeyboardButton(
                    text="4 × 4",
                    callback_data="size:4"
                )
            ],
            [
                InlineKeyboardButton(
                    text="5 × 5",
                    callback_data="size:5"
                ),
                InlineKeyboardButton(
                    text="6 × 6",
                    callback_data="size:6"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="game:cancel"
                )
            ]
        ]
    )


# ============================================================
# ВЫБОР МИН
# ============================================================

def mines_keyboard(size):
    total = size * size

    values = [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        10,
        12
    ]

    buttons = []

    for value in values:
        if value < total:
            buttons.append(
                InlineKeyboardButton(
                    text=f"💣 {value}",
                    callback_data=f"mines:{size}:{value}"
                )
            )

    rows = []

    for i in range(
        0,
        len(buttons),
        4
    ):
        rows.append(
            buttons[i:i + 4]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="size:back"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="game:cancel"
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# ============================================================
# ЛОББИ
# ============================================================

def lobby_keyboard(game):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧊 Участвовать",
                    callback_data=f"join:{game['id']}"
                )
            ]
        ]
    )


def lobby_text(game):
    return (
        "🧊 <b>ЛЁД</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "🎮 <b>НОВАЯ ИГРА</b>\n\n"

        f"🔲 Поле: <b>"
        f"{game['size']} × {game['size']}"
        f"</b>\n"

        f"💣 Мин: <b>"
        f"{game['mines_count']}"
        f"</b>\n"

        f"👥 Игроки: <b>"
        f"{len(game['players'])}/{MAX_PLAYERS}"
        f"</b>\n"

        f"⏳ Старт через: <b>"
        f"{remaining_seconds(game)} сек."
        f"</b>\n\n"

        f"Минимум для старта — "
        f"<b>{MIN_PLAYERS}</b> игрока.\n\n"

        "Нажми кнопку ниже, "
        "чтобы присоединиться 👇\n\n"

        "⚡ Можно начать раньше командой "
        "<b>/stop</b>"
    )


# ============================================================
# ИГРОВАЯ КЛАВИАТУРА
# ============================================================

def game_keyboard(game):
    size = game["size"]

    rows = []

    for row in range(size):
        buttons = []

        for column in range(size):

            cell = (
                row * size +
                column
            )

            if cell not in game["opened"]:
                symbol = "🧊"

            elif game["opened"][cell] == "mine":
                symbol = "💥"

            else:
                symbol = "❌"

            buttons.append(
                InlineKeyboardButton(
                    text=symbol,
                    callback_data=(
                        f"cell:"
                        f"{game['id']}:"
                        f"{cell}"
                    )
                )
            )

        rows.append(buttons)

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# ============================================================
# ТЕКСТ ИГРЫ
# ============================================================

def game_text(game):
    alive = len(
        game["alive"]
    )

    total = len(
        game["players"]
    )

    eliminated = (
        total -
        alive
    )

    if alive:
        current_id = game["alive"][
            game["current_index"]
        ]

        current_name = get_player_name(
            game,
            current_id
        )

    else:
        current_name = "—"

    return (
        "🧊 <b>ЛЁД</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "🎯 <b>СЕЙЧАС ХОДИТ</b>\n"
        f"👤 {current_name}\n\n"

        f"👥 В игре: <b>{alive}</b>\n"
        f"💀 Выбыло: <b>{eliminated}</b>\n"
        f"💣 Мин: <b>{game['mines_count']}</b>\n\n"

        "👇 <b>Выбери льдину</b>"
    )


# ============================================================
# ОБНОВЛЕНИЕ ИГРОВОГО СООБЩЕНИЯ
# ============================================================

async def update_game_message(game):
    try:
        await bot.edit_message_text(
            chat_id=game["chat_id"],
            message_id=game["message_id"],
            text=game_text(game),
            reply_markup=game_keyboard(game)
        )

    except Exception:
        pass


# ============================================================
# СТАРТ ИГРЫ
# ============================================================

async def start_game(game):
    if game["started"]:
        return

    if len(game["players"]) < MIN_PLAYERS:
        return

    game["started"] = True

    total_cells = (
        game["size"] *
        game["size"]
    )

    max_mines = total_cells - 1

    if game["mines_count"] > max_mines:
        game["mines_count"] = max_mines

    game["mine_cells"] = set(
        random.sample(
            range(total_cells),
            game["mines_count"]
        )
    )

    game["alive"] = list(
        game["players"]
    )

    random.shuffle(
        game["alive"]
    )

    game["current_index"] = 0

    game["opened"] = {}

    try:
        await bot.edit_message_text(
            chat_id=game["chat_id"],
            message_id=game["message_id"],
            text=(
                "🧊 <b>ЛЁД • ИГРА НАЧАЛАСЬ</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"

                "💣 Мины спрятаны.\n"
                "🎯 Игроки ходят по очереди.\n"
                "💥 Мина = вылет.\n"
                "👑 Последний выживший побеждает.\n\n"

                "🚀 <b>Первый ход!</b>"
            ),
            reply_markup=game_keyboard(game)
        )

    except Exception:
        pass

    await asyncio.sleep(1)

    await update_game_message(
        game
    )


# ============================================================
# ФИНАЛЬНОЕ СООБЩЕНИЕ
# ============================================================

async def finish_game(game, winner_id):
    if game.get("finished"):
        return

    game["finished"] = True

    # --------------------------------------------------------
    # НАГРАДЫ
    # --------------------------------------------------------

    for user_id in game["players"]:

        add_game(
            user_id
        )

        if user_id == winner_id:

            add_xp(
                user_id,
                XP_WIN
            )

            add_win(
                user_id
            )

        else:

            add_xp(
                user_id,
                XP_PARTICIPATION
            )

    # --------------------------------------------------------
    # ИМЯ ПОБЕДИТЕЛЯ
    # --------------------------------------------------------

    winner_name = get_player_name(
        game,
        winner_id
    )

    # --------------------------------------------------------
    # РЕЗУЛЬТАТЫ
    # --------------------------------------------------------

    result_lines = []

    for user_id in game["players"]:

        name = get_player_name(
            game,
            user_id
        )

        if user_id == winner_id:

            result_lines.append(
                f"👑 {name} — "
                f"<b>+{XP_WIN} XP</b>"
            )

        else:

            result_lines.append(
                f"👤 {name} — "
                f"<b>+{XP_PARTICIPATION} XP</b>"
            )

    results = "\n".join(
        result_lines
    )

    # --------------------------------------------------------
    # НОВОЕ ОТДЕЛЬНОЕ СООБЩЕНИЕ
    # --------------------------------------------------------

    final_text = (
        "🏆 <b>ЛЁД • ИГРА ОКОНЧЕНА</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "👑 <b>ПОБЕДИТЕЛЬ</b>\n"
        f"{winner_name}\n\n"

        "⭐ <b>РЕЗУЛЬТАТЫ</b>\n"
        f"{results}\n\n"

        "🎮 <b>Спасибо за игру!</b>\n"
        "До встречи в следующей партии 🧊\n\n"

        "⭐ Telegram Stars: "
        "<b>@armastarbot</b>"
    )

    try:
        await bot.send_message(
            chat_id=game["chat_id"],
            text=final_text
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # СТАРОЕ ИГРОВОЕ СООБЩЕНИЕ
    # --------------------------------------------------------

    try:
        await bot.edit_message_text(
            chat_id=game["chat_id"],
            message_id=game["message_id"],
            text=(
                "🧊 <b>ЛЁД • ИГРА ЗАВЕРШЕНА</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"

                "🏁 Эта партия закончена.\n\n"

                f"👑 Победитель: "
                f"<b>{winner_name}</b>\n\n"

                "👇 Подробные результаты "
                "отправлены следующим сообщением."
            )
        )

    except Exception:
        pass

    games.pop(
        game["chat_id"],
        None
    )


# ============================================================
# ТАЙМЕР ЛОББИ
# ============================================================

async def lobby_timer(game):
    await asyncio.sleep(
        LOBBY_SECONDS
    )

    current = games.get(
        game["chat_id"]
    )

    if not current:
        return

    if current["id"] != game["id"]:
        return

    if current["started"]:
        return

    # --------------------------------------------------------
    # НЕДОСТАТОЧНО ИГРОКОВ
    # --------------------------------------------------------

    if len(current["players"]) < MIN_PLAYERS:

        try:
            await bot.edit_message_text(
                chat_id=current["chat_id"],
                message_id=current["message_id"],
                text=(
                    "🧊 <b>ЛЁД • ИГРА ОТМЕНЕНА</b>\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"

                    "😕 Время ожидания закончилось.\n\n"

                    f"Нужно минимум "
                    f"<b>{MIN_PLAYERS}</b> игрока.\n\n"

                    "🎮 Попробуйте создать игру "
                    "ещё раз."
                )
            )

        except Exception:
            pass

        games.pop(
            current["chat_id"],
            None
        )

        return

    await start_game(
        current
    )


# ============================================================
# /START
# ============================================================

@dp.message(
    Command("start")
)
async def command_start(
    message: Message
):
    register_user(
        message.from_user
    )

    if message.chat.type in (
        "group",
        "supergroup"
    ):

        await message.answer(
            "🧊 <b>ЛЁД</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            "Игра на выживание "
            "прямо в этом чате.\n\n"

            "💣 Мины\n"
            "🎯 Ходы по очереди\n"
            "🏆 XP и уровни\n\n"

            "Нажми кнопку, "
            "чтобы создать игру.",
            reply_markup=group_start_keyboard()
        )

        return

    await message.answer(
        "🧊 <b>ЛЁД</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "Добро пожаловать!\n\n"

        "💣 Найди безопасную льдину.\n"
        "🎯 Ходи по очереди.\n"
        "💥 Не попади на мину.\n"
        "👑 Стань последним выжившим.\n\n"

        "Игры проходят прямо в группах.",
        reply_markup=main_menu()
    )


# ============================================================
# /ICE
# ============================================================

@dp.message(
    Command("ice")
)
async def command_ice(
    message: Message
):
    register_user(
        message.from_user
    )

    if message.chat.type not in (
        "group",
        "supergroup"
    ):

        await message.answer(
            "🧊 Команда /ice "
            "работает только в группе."
        )

        return

    if get_chat_game(
        message.chat.id
    ):

        await message.answer(
            "⚠️ В этой группе "
            "уже есть активная игра."
        )

        return

    await message.answer(
        "🧊 <b>СОЗДАНИЕ ИГРЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "🔲 Выбери размер "
        "игрового поля:",
        reply_markup=size_keyboard()
    )


# ============================================================
# /STOP
# ============================================================

@dp.message(
    Command("stop")
)
async def command_stop(
    message: Message
):
    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    game = get_chat_game(
        message.chat.id
    )

    if not game:

        await message.answer(
            "ℹ️ Сейчас нет активной игры."
        )

        return

    if game["started"]:

        await message.answer(
            "🎮 Игра уже началась."
        )

        return

    count = len(
        game["players"]
    )

    if count < MIN_PLAYERS:

        await message.answer(
            "⚠️ Недостаточно игроков.\n\n"

            f"Сейчас: <b>{count}</b>\n"
            f"Нужно: <b>{MIN_PLAYERS}</b>"
        )

        return

    await message.answer(
        "⚡ <b>НАБОР ОСТАНОВЛЕН</b>\n\n"

        f"👥 Игроков: <b>{count}</b>\n"
        "🚀 Игра начинается!"
    )

    await start_game(
        game
    )


# ============================================================
# СОЗДАНИЕ
# ============================================================

@dp.callback_query(
    F.data == "game:create"
)
async def callback_create(
    callback: CallbackQuery
):
    if callback.message.chat.type not in (
        "group",
        "supergroup"
    ):

        await callback.answer(
            "Создавать игру можно "
            "только в группе.",
            show_alert=True
        )

        return

    if get_chat_game(
        callback.message.chat.id
    ):

        await callback.answer(
            "В этой группе уже "
            "есть активная игра.",
            show_alert=True
        )

        return

    await callback.message.edit_text(
        "🧊 <b>СОЗДАНИЕ ИГРЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "🔲 Выбери размер поля:",
        reply_markup=size_keyboard()
    )

    await callback.answer()


# ============================================================
# ОТМЕНА
# ============================================================

@dp.callback_query(
    F.data == "game:cancel"
)
async def callback_cancel(
    callback: CallbackQuery
):
    await callback.message.edit_text(
        "🧊 <b>ЛЁД</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "Создание игры отменено.",
        reply_markup=group_start_keyboard()
    )

    await callback.answer()


# ============================================================
# РАЗМЕР
# ============================================================

@dp.callback_query(
    F.data.startswith("size:")
)
async def callback_size(
    callback: CallbackQuery
):
    value = callback.data[
        len("size:"):
    ]

    if value == "back":

        await callback.message.edit_text(
            "🧊 <b>СОЗДАНИЕ ИГРЫ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            "🔲 Выбери размер поля:",
            reply_markup=size_keyboard()
        )

        await callback.answer()

        return

    try:
        size = int(value)

    except ValueError:

        await callback.answer(
            "❌ Ошибка.",
            show_alert=True
        )

        return

    await callback.message.edit_text(
        "🧊 <b>СОЗДАНИЕ ИГРЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"🔲 Поле: "
        f"<b>{size} × {size}</b>\n\n"

        "💣 Выбери количество мин:",
        reply_markup=mines_keyboard(size)
    )

    await callback.answer()


# ============================================================
# МИНЫ
# ============================================================

@dp.callback_query(
    F.data.startswith("mines:")
)
async def callback_mines(
    callback: CallbackQuery
):
    parts = callback.data.split(
        ":"
    )

    if len(parts) != 3:

        await callback.answer(
            "❌ Ошибка.",
            show_alert=True
        )

        return

    try:
        size = int(parts[1])
        mines = int(parts[2])

    except ValueError:

        await callback.answer(
            "❌ Ошибка.",
            show_alert=True
        )

        return

    chat_id = callback.message.chat.id

    if get_chat_game(chat_id):

        await callback.answer(
            "В этой группе уже "
            "есть игра.",
            show_alert=True
        )

        return

    game = {
        "id": create_game_id(),

        "chat_id": chat_id,

        "message_id": (
            callback.message.message_id
        ),

        "chat_title": (
            callback.message.chat.title
            or "Группа"
        ),

        "size": size,

        "mines_count": mines,

        "players": [],

        "names": {},

        "alive": [],

        "mine_cells": set(),

        "opened": {},

        "current_index": 0,

        "started": False,

        "finished": False,

        "deadline": (
            asyncio.get_running_loop().time()
            + LOBBY_SECONDS
        )
    }

    games[chat_id] = game

    await callback.message.edit_text(
        lobby_text(game),
        reply_markup=lobby_keyboard(game)
    )

    asyncio.create_task(
        lobby_timer(game)
    )

    await callback.answer(
        "🧊 Игра создана!"
    )


# ============================================================
# JOIN
# ============================================================

@dp.callback_query(
    F.data.startswith("join:")
)
async def callback_join(
    callback: CallbackQuery
):
    game_id = callback.data[
        len("join:"):
    ]

    game = find_game_by_id(
        game_id
    )

    if not game:

        await callback.answer(
            "❌ Игра уже недоступна.",
            show_alert=True
        )

        return

    if game["started"]:

        await callback.answer(
            "🎮 Игра уже началась.",
            show_alert=True
        )

        return

    user_id = callback.from_user.id

    register_user(
        callback.from_user
    )

    if user_id in game["players"]:

        await callback.answer(
            "✅ Ты уже в игре!",
            show_alert=True
        )

        return

    if len(game["players"]) >= MAX_PLAYERS:

        await callback.answer(
            "🚫 Максимум игроков — 8.",
            show_alert=True
        )

        return

    game["players"].append(
        user_id
    )

    game["names"][user_id] = (
        callback.from_user.full_name
        or "Игрок"
    )

    await callback.message.edit_text(
        lobby_text(game),
        reply_markup=lobby_keyboard(game)
    )

    await callback.answer(
        "🧊 Ты присоединился!"
    )


# ============================================================
# ЛЬДИНА
# ============================================================

@dp.callback_query(
    F.data.startswith("cell:")
)
async def callback_cell(
    callback: CallbackQuery
):
    parts = callback.data.split(
        ":"
    )

    if len(parts) != 3:

        await callback.answer(
            "❌ Ошибка кнопки.",
            show_alert=True
        )

        return

    game_id = parts[1]

    try:
        cell = int(parts[2])

    except ValueError:

        await callback.answer(
            "❌ Неверная льдина.",
            show_alert=True
        )

        return

    game = find_game_by_id(
        game_id
    )

    if not game:

        await callback.answer(
            "❌ Игра уже закончилась.",
            show_alert=True
        )

        return

    if not game["started"]:

        await callback.answer(
            "⏳ Игра ещё не началась.",
            show_alert=True
        )

        return

    if game["finished"]:

        await callback.answer(
            "🏁 Игра закончилась.",
            show_alert=True
        )

        return

    total_cells = (
        game["size"] *
        game["size"]
    )

    if cell < 0 or cell >= total_cells:

        await callback.answer(
            "❌ Такой льдины нет.",
            show_alert=True
        )

        return

    if not game["alive"]:

        await callback.answer(
            "🏁 Игра закончилась.",
            show_alert=True
        )

        return

    current_id = game["alive"][
        game["current_index"]
    ]

    if callback.from_user.id != current_id:

        current_name = game["names"].get(
            current_id,
            "Игрок"
        )

        await callback.answer(
            f"🚫 Сейчас ходит: {current_name}",
            show_alert=True
        )

        return

    if cell in game["opened"]:

        await callback.answer(
            "🧊 Эта льдина уже открыта!",
            show_alert=True
        )

        return

    # ========================================================
    # МИНА
    # ========================================================

    if cell in game["mine_cells"]:

        game["opened"][cell] = "mine"

        eliminated_name = game["names"].get(
            current_id,
            "Игрок"
        )

        game["alive"].pop(
            game["current_index"]
        )

        # ----------------------------------------------------
        # ОСТАЛСЯ ПОБЕДИТЕЛЬ
        # ----------------------------------------------------

        if len(game["alive"]) == 1:

            winner_id = game["alive"][0]

            await callback.answer(
                "💥 МИНА! Ты выбыл!",
                show_alert=True
            )

            await finish_game(
                game,
                winner_id
            )

            return

        # ----------------------------------------------------
        # НИКТО НЕ ОСТАЛСЯ
        # ----------------------------------------------------

        if len(game["alive"]) == 0:

            game["finished"] = True

            try:
                await callback.message.edit_text(
                    "🧊 <b>ЛЁД • ИГРА ЗАВЕРШЕНА</b>\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"

                    "💥 Все игроки попали "
                    "на мины.\n\n"

                    "😶 Победителя нет.\n\n"

                    "🎮 Спасибо за игру!"
                )

            except Exception:
                pass

            games.pop(
                game["chat_id"],
                None
            )

            await callback.answer(
                "💥 Ты выбыл!",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # ИНДЕКС
        # ----------------------------------------------------

        if (
            game["current_index"]
            >= len(game["alive"])
        ):
            game["current_index"] = 0

        await update_game_message(
            game
        )

        await callback.answer(
            f"💥 {eliminated_name} выбыл!",
            show_alert=True
        )

        return

    # ========================================================
    # БЕЗОПАСНО
    # ========================================================

    game["opened"][cell] = "safe"

    game["current_index"] += 1

    if (
        game["current_index"]
        >= len(game["alive"])
    ):
        game["current_index"] = 0

    await update_game_message(
        game
    )

    await callback.answer(
        "❌ Безопасно! "
        "Ход следующего игрока."
    )


# ============================================================
# ПРОФИЛЬ
# ============================================================

@dp.callback_query(
    F.data == "menu:profile"
)
async def callback_profile(
    callback: CallbackQuery
):
    register_user(
        callback.from_user
    )

    user = get_user(
        callback.from_user.id
    )

    if not user:

        await callback.answer(
            "❌ Профиль не найден.",
            show_alert=True
        )

        return

    xp = user["xp"]

    level = get_level(
        xp
    )

    await callback.message.edit_text(
        "👤 <b>ПРОФИЛЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 Игрок: "
        f"<b>{escape_name(user['first_name'])}</b>\n\n"

        f"⭐ XP: <b>{xp}</b>\n"
        f"🎖 Уровень: <b>{level}</b>\n"
        f"🎮 Игр: <b>{user['games']}</b>\n"
        f"🏆 Побед: <b>{user['wins']}</b>\n\n"

        f"📈 Следующий уровень: "
        f"<b>{level * 500} XP</b>",
        reply_markup=back_main_keyboard()
    )

    await callback.answer()


# ============================================================
# ТОП
# ============================================================

@dp.callback_query(
    F.data == "menu:top"
)
async def callback_top(
    callback: CallbackQuery
):
    users = db.execute(
        """
        SELECT *
        FROM users
        ORDER BY xp DESC, wins DESC
        LIMIT 10
        """
    ).fetchall()

    if not users:

        text = (
            "🏆 <b>ТОП ИГРОКОВ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Пока здесь никого нет."
        )

    else:

        lines = []

        for index, user in enumerate(
            users,
            start=1
        ):

            name = escape_name(
                user["first_name"]
                or "Игрок"
            )

            if index == 1:
                icon = "🥇"

            elif index == 2:
                icon = "🥈"

            elif index == 3:
                icon = "🥉"

            else:
                icon = "▫️"

            lines.append(
                f"{icon} <b>{index}.</b> "
                f"{name} — "
                f"<b>{user['xp']} XP</b>"
            )

        text = (
            "🏆 <b>ТОП ИГРОКОВ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            + "\n".join(lines)
        )

    await callback.message.edit_text(
        text,
        reply_markup=back_main_keyboard()
    )

    await callback.answer()


# ============================================================
# КАК ИГРАТЬ
# ============================================================

@dp.callback_query(
    F.data == "menu:play"
)
async def callback_play(
    callback: CallbackQuery
):
    await callback.message.edit_text(
        "🧊 <b>КАК ИГРАТЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "1️⃣ Добавь бота в группу.\n\n"

        "2️⃣ Напиши <b>/ice</b>.\n\n"

        "3️⃣ Выбери поле.\n\n"

        "4️⃣ Выбери количество мин.\n\n"

        "5️⃣ Игроки нажимают "
        "<b>«🧊 Участвовать»</b>.\n\n"

        "6️⃣ Через 30 секунд игра начинается.\n\n"

        "7️⃣ Игроки ходят по очереди.\n\n"

        "💥 Мина = вылет.\n"
        "❌ Безопасная льдина = следующий ход.\n"
        "👑 Последний игрок = победитель.\n\n"

        "🏆 Победитель: "
        f"<b>+{XP_WIN} XP</b>\n"

        "👥 Остальные: "
        f"<b>+{XP_PARTICIPATION} XP</b>",
        reply_markup=back_main_keyboard()
    )

    await callback.answer()


# ============================================================
# НАЗАД
# ============================================================

@dp.callback_query(
    F.data == "menu:back"
)
async def callback_back(
    callback: CallbackQuery
):
    await callback.message.edit_text(
        "🧊 <b>ЛЁД</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "Игра на выживание "
        "прямо в Telegram.\n\n"

        "💣 Мины\n"
        "🎯 Ходы по очереди\n"
        "🏆 XP и уровни\n\n"

        "Выбери действие:",
        reply_markup=main_menu()
    )

    await callback.answer()


# ============================================================
# БОТ ДОБАВИЛИ В ГРУППУ
# ============================================================

@dp.my_chat_member()
async def bot_added_to_group(
    event
):
    if event.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    await bot.send_message(
        event.chat.id,

        "🧊 <b>ЛЁД</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "Игра на выживание "
        "прямо в этом чате.\n\n"

        "💣 Среди льдин спрятаны мины.\n"
        "🎯 Игроки ходят по очереди.\n"
        "💥 Мина выбивает игрока.\n"
        "👑 Последний выживший побеждает.\n\n"

        "Нажми кнопку ниже, "
        "чтобы создать игру.",

        reply_markup=group_start_keyboard()
    )


# ============================================================
# ЗАПУСК
# ============================================================

async def run_bot():
    global bot_username

    init_database()

    me = await bot.get_me()

    bot_username = me.username or ""

    print(
        f"🤖 Бот: @{bot_username}"
    )

    print(
        "🧊 ЛЁД запущен!"
    )

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )


asyncio.run(run_bot())