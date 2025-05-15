#!/usr/bin/env python3
import logging
import sqlite3
import re # For SNILS validation
from datetime import datetime # For date validation
from functools import wraps # For admin decorator

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
import os

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DATABASE_NAME = "olympiad_bot/olympiad_portal.db"  # Changed from database_setup.py to olympiad.db
TELEGRAM_BOT_TOKEN = "xxxxxxxxxxx"  # Placeholder

# Define the image paths
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")
RESULTS_IMAGE = os.path.join(IMAGES_DIR, "results.png")
PROFILE_IMAGE = os.path.join(IMAGES_DIR, "profile.png")
OLYMPIADS_IMAGE = os.path.join(IMAGES_DIR, "olympiads.png")

# Conversation states
# /mydata
ASK_SNILS = 0
# /admin_add_olympiad
OLYMPIAD_NAME, OLYMPIAD_DATE, OLYMPIAD_SUBJECT, OLYMPIAD_DESCRIPTION = range(1, 5)
# /admin_add_results
SELECT_OLYMPIAD_FOR_RESULTS, RESULT_FULL_NAME, RESULT_SNILS, RESULT_SCORE, RESULT_PLACE, RESULT_DIPLOMA_LINK = range(5, 11)
# /admin_edit_result
EDIT_SELECT_RESULT_ID_OR_SNILS, EDIT_RESULT_SNILS_FOR_SEARCH, EDIT_RESULT_OLYMPIAD_ID_FOR_SEARCH, EDIT_SELECT_FIELD, EDIT_NEW_VALUE = range(11, 16)

# --- Database Helper Functions ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def add_user_if_not_exists(telegram_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO Users (telegram_id, is_admin) VALUES (?, ?)", (telegram_id, 0))
        conn.commit()
        logger.info(f"New user {telegram_id} added to database.")
    conn.close()

def get_user_snils(telegram_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT snils FROM Users WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result["snils"] if result and result["snils"] else None

def update_user_snils(telegram_id: int, snils: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT telegram_id FROM Users WHERE snils = ? AND telegram_id != ?", (snils, telegram_id))
        existing_user = cursor.fetchone()
        if existing_user:
            return False, "Этот СНИЛС уже привязан к другому аккаунту."
        cursor.execute("UPDATE Users SET snils = ? WHERE telegram_id = ?", (snils, telegram_id))
        conn.commit()
        return True, "Ваш СНИЛС успешно сохранен/обновлен."
    except sqlite3.Error as e:
        logger.error(f"Database error updating SNILS for {telegram_id}: {e}")
        return False, "Произошла ошибка при обновлении СНИЛС. Попробуйте позже."
    finally:
        conn.close()

def is_admin(telegram_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM Users WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return bool(result["is_admin"]) if result and result["is_admin"] == 1 else False

# --- Input Validation ---
def validate_snils_format(snils: str) -> bool:
    return bool(re.fullmatch(r"\d{3}-\d{3}-\d{3} \d{2}", snils))

def validate_date_format(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

# --- Decorator for Admin Commands ---
def admin_required(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text("У вас нет прав для выполнения этой команды.")
            return ConversationHandler.END # Or just return if not in a conversation
        return await func(update, context, *args, **kwargs)
    return wrapper

# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    add_user_if_not_exists(user_id)
    
    # Remove any existing keyboard
    reply_markup = ReplyKeyboardRemove()
    
    # Check if user is admin
    is_user_admin = is_admin(user_id)
    
    # Welcome message with all available commands
    base_message = (
        "👋 *Добро пожаловать в Олимпиадный Портал!*\n\n"
        "*Доступные команды:*\n"
        "• /start - Начало работы\n"
        "• /help - Показать эту помощь\n"
        "• /mydata - Привязать или изменить ваш СНИЛС\n"
        "• /myresults - Посмотреть ваши результаты олимпиад\n"
        "• /listolympiads - Посмотреть список всех олимпиад\n\n"
        "Чтобы просматривать свои результаты, пожалуйста, привяжите ваш СНИЛС с помощью команды /mydata."
    )
    
    admin_message = (
        "\n\n*Команды администратора:*\n"
        "• /admin_add_olympiad - Добавить новую олимпиаду\n"
        "• /admin_add_results - Добавить результаты олимпиады\n"
        "• /admin_edit_result - Редактировать результат олимпиады"
    )
    
    # Add admin commands if user is admin
    full_message = base_message + (admin_message if is_user_admin else "")
    
    # Send message with markdown formatting
    await update.message.reply_text(
        full_message,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    base_help_text = (
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/help - Эта помощь\n"
        "/mydata - Привязать или изменить ваш СНИЛС\n"
        "/myresults - Посмотреть ваши результаты олимпиад\n"
        "/listolympiads - Посмотреть список всех олимпиад"
    )
    admin_help_text = (
        "\n\nКоманды администратора:\n"
        "/admin_add_olympiad - Добавить новую олимпиаду\n"
        "/admin_add_results - Добавить результаты олимпиады\n"
        "/admin_edit_result - Редактировать результат олимпиады"
    )
    if is_admin(user_id):
        await update.message.reply_text(base_help_text + admin_help_text)
    else:
        await update.message.reply_text(base_help_text)

# --- /mydata Conversation --- 
async def mydata_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # First send the profile image
    if os.path.exists(PROFILE_IMAGE):
        await update.message.reply_photo(photo=open(PROFILE_IMAGE, 'rb'))
    
    # Then continue with the existing functionality
    await update.message.reply_text(
        "Пожалуйста, введите ваш СНИЛС в формате XXX-XXX-XXX XX.\n"
        "Этот СНИЛС будет использоваться для поиска ваших результатов.\n"
        "Для отмены введите /cancel."
    )
    return ASK_SNILS

async def mydata_ask_snils(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_snils_input = update.message.text
    if not validate_snils_format(user_snils_input):
        await update.message.reply_text(
            "Неверный формат СНИЛС. Пожалуйста, введите в формате XXX-XXX-XXX XX.\n"
            "Для отмены введите /cancel."
        )
        return ASK_SNILS
    user_id = update.effective_user.id
    success, message = update_user_snils(user_id, user_snils_input)
    await update.message.reply_text(message)
    return ConversationHandler.END

async def mydata_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция привязки СНИЛС отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- /myresults Command ---
async def myresults_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # First send the results image
    if os.path.exists(RESULTS_IMAGE):
        await update.message.reply_photo(photo=open(RESULTS_IMAGE, 'rb'))
    
    # Then continue with the existing functionality
    user_id = update.effective_user.id
    user_snils = get_user_snils(user_id)
    if not user_snils:
        await update.message.reply_text("Сначала привяжите ваш СНИЛС с помощью команды /mydata.")
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.name, o.date, o.subject, r.full_name, r.score, r.place, r.diploma_link
        FROM Results r
        JOIN Olympiads o ON r.olympiad_id = o.id
        WHERE r.user_snils = ?
        ORDER BY o.date DESC, o.name
    """, (user_snils,))
    results = cursor.fetchall()
    conn.close()
    if not results:
        await update.message.reply_text(f"Результаты для СНИЛС {user_snils} не найдены.")
        return
    response_text = f"Ваши результаты (СНИЛС: {user_snils}):\n\n"
    for row in results:
        response_text += (
            f"Олимпиада: {row['name']} ({row['date']})\n"
            f"Предмет: {row['subject'] if row['subject'] else '-'}\n"
            f"ФИО: {row['full_name']}\n"
            f"Баллы: {row['score'] if row['score'] is not None else '-'}\n"
            f"Место: {row['place'] if row['place'] is not None else '-'}\n"
            f"Диплом: {row['diploma_link'] if row['diploma_link'] else 'Нет'}\n"
            f"--------------------\n"
        )
    await update.message.reply_text(response_text)

# --- /listolympiads Command ---
async def listolympiads_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # First send the olympiads image
    if os.path.exists(OLYMPIADS_IMAGE):
        await update.message.reply_photo(photo=open(OLYMPIADS_IMAGE, 'rb'))
    
    # Then continue with the existing functionality
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, date, subject, description FROM Olympiads ORDER BY date DESC, name")
    olympiads = cursor.fetchall()
    conn.close()
    if not olympiads:
        await update.message.reply_text("Пока нет доступных олимпиад.")
        return
    response_text = "Список доступных олимпиад:\n\n"
    for i, row in enumerate(olympiads):
        response_text += (
            f"{i+1}. Название: {row['name']} (ID: {row['id']})\n"
            f"   Дата: {row['date']}\n"
            f"   Предмет: {row['subject'] if row['subject'] else '-'}\n"
            f"   Описание: {row['description'] if row['description'] else '-'}\n"
            f"--------------------\n"
        )
    await update.message.reply_text(response_text)

# --- Admin Commands --- 
# --- /admin_add_olympiad Conversation ---
@admin_required
async def admin_add_olympiad_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите название олимпиады (для отмены /cancel_admin_op):")
    context.user_data["new_olympiad"] = {}
    return OLYMPIAD_NAME

async def admin_olympiad_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_olympiad"]["name"] = update.message.text
    await update.message.reply_text("Введите дату проведения (ГГГГ-ММ-ДД):")
    return OLYMPIAD_DATE

async def admin_olympiad_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    date_input = update.message.text
    if not validate_date_format(date_input):
        await update.message.reply_text("Неверный формат даты. Введите дату проведения (ГГГГ-ММ-ДД):")
        return OLYMPIAD_DATE
    context.user_data["new_olympiad"]["date"] = date_input
    await update.message.reply_text("Введите предмет олимпиады (или '-' если нет):")
    return OLYMPIAD_SUBJECT

async def admin_olympiad_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_olympiad"]["subject"] = update.message.text
    await update.message.reply_text("Введите краткое описание олимпиады (или '-' если нет):")
    return OLYMPIAD_DESCRIPTION

async def admin_olympiad_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_olympiad"]["description"] = update.message.text
    olympiad_data = context.user_data["new_olympiad"]
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Olympiads (name, date, subject, description) VALUES (?, ?, ?, ?)",
                       (olympiad_data["name"], olympiad_data["date"], 
                        olympiad_data["subject"] if olympiad_data["subject"] != '-' else None, 
                        olympiad_data["description"] if olympiad_data["description"] != '-' else None))
        conn.commit()
        await update.message.reply_text(f"Олимпиада '{olympiad_data['name']}' успешно добавлена.")
    except sqlite3.Error as e:
        logger.error(f"DB error adding olympiad: {e}")
        await update.message.reply_text("Произошла ошибка при добавлении олимпиады.")
    finally:
        conn.close()
        del context.user_data["new_olympiad"]
    return ConversationHandler.END

async def admin_op_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if "new_olympiad" in context.user_data: del context.user_data["new_olympiad"]
    if "new_result" in context.user_data: del context.user_data["new_result"]
    if "edit_result" in context.user_data: del context.user_data["edit_result"]
    await update.message.reply_text("Административная операция отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- /admin_add_results Conversation (Simplified for now, full FSM is complex) ---
@admin_required
async def admin_add_results_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # In a real scenario, you'd list olympiads and ask to select one.
    # For simplicity, we'll ask for Olympiad ID directly.
    await update.message.reply_text(
        "Введите ID олимпиады для добавления результатов.\n"
        "Вы можете посмотреть ID с помощью /listolympiads.\n"
        "Для отмены введите /cancel_admin_op."
    )
    context.user_data["new_result"] = {}
    return SELECT_OLYMPIAD_FOR_RESULTS

async def admin_select_olympiad_for_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        olympiad_id = int(update.message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Olympiads WHERE id = ?", (olympiad_id,))
        olympiad = cursor.fetchone()
        conn.close()
        if not olympiad:
            await update.message.reply_text("Олимпиада с таким ID не найдена. Попробуйте снова или /cancel_admin_op.")
            return SELECT_OLYMPIAD_FOR_RESULTS
        context.user_data["new_result"]["olympiad_id"] = olympiad_id
        context.user_data["new_result"]["olympiad_name"] = olympiad["name"]
        await update.message.reply_text(f"Добавление результатов для олимпиады: {olympiad['name']}.\nВведите ФИО участника (или 'стоп' для завершения ввода для этой олимпиады):")
        return RESULT_FULL_NAME
    except ValueError:
        await update.message.reply_text("ID олимпиады должен быть числом. Попробуйте снова или /cancel_admin_op.")
        return SELECT_OLYMPIAD_FOR_RESULTS

async def admin_result_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    full_name = update.message.text
    if full_name.lower() == 'стоп':
        await update.message.reply_text("Ввод результатов для этой олимпиады завершен.")
        if "new_result" in context.user_data: del context.user_data["new_result"]
        return ConversationHandler.END
    context.user_data["new_result"]["full_name"] = full_name
    await update.message.reply_text("Введите СНИЛС участника (XXX-XXX-XXX XX):")
    return RESULT_SNILS

async def admin_result_snils(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    snils = update.message.text
    if not validate_snils_format(snils):
        await update.message.reply_text("Неверный формат СНИЛС. Введите СНИЛС (XXX-XXX-XXX XX):")
        return RESULT_SNILS
    context.user_data["new_result"]["snils"] = snils
    await update.message.reply_text("Введите набранные баллы (число):")
    return RESULT_SCORE

async def admin_result_score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        score = int(update.message.text)
        context.user_data["new_result"]["score"] = score
        await update.message.reply_text("Введите занятое место (число):")
        return RESULT_PLACE
    except ValueError:
        await update.message.reply_text("Баллы должны быть числом. Введите набранные баллы:")
        return RESULT_SCORE

async def admin_result_place(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        place = int(update.message.text)
        context.user_data["new_result"]["place"] = place
        await update.message.reply_text("Введите ссылку на диплом (или '-' если нет):")
        return RESULT_DIPLOMA_LINK
    except ValueError:
        await update.message.reply_text("Место должно быть числом. Введите занятое место:")
        return RESULT_PLACE

async def admin_result_diploma_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_result"]["diploma_link"] = update.message.text
    result_data = context.user_data["new_result"]
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""INSERT INTO Results (olympiad_id, user_snils, full_name, score, place, diploma_link)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                       (result_data["olympiad_id"], result_data["snils"], result_data["full_name"],
                        result_data["score"], result_data["place"], 
                        result_data["diploma_link"] if result_data["diploma_link"] != '-' else None))
        conn.commit()
        await update.message.reply_text(f"Результат для {result_data['full_name']} ({result_data['snils']}) добавлен.\nВведите ФИО следующего участника (или 'стоп'):")
    except sqlite3.Error as e:
        logger.error(f"DB error adding result: {e}")
        await update.message.reply_text("Произошла ошибка при добавлении результата. Попробуйте снова для этого участника или введите 'стоп'.")
    finally:
        conn.close()
    # Reset for next participant, keeping olympiad_id and name
    current_olympiad_id = result_data["olympiad_id"]
    current_olympiad_name = result_data["olympiad_name"]
    context.user_data["new_result"] = {"olympiad_id": current_olympiad_id, "olympiad_name": current_olympiad_name}
    return RESULT_FULL_NAME # Loop back to ask for next participant

# --- /admin_edit_result (Placeholder - very complex FSM) ---
@admin_required
async def admin_edit_result_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Редактирование результатов пока не полностью реализовано в этом примере.\n"
        "Для отмены введите /cancel_admin_op."
    )
    # This would be a complex conversation handler similar to add_results but with more steps
    # 1. Ask for result ID or SNILS+Olympiad_ID
    # 2. Fetch and display result
    # 3. Ask which field to edit
    # 4. Ask for new value
    # 5. Validate and update
    return ConversationHandler.END # Placeholder

# --- Main Bot Logic ---
def main() -> None:
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or not TELEGRAM_BOT_TOKEN:
        logger.error("Telegram Bot Token is not configured. Please set it in main_bot.py")
        print("Telegram Bot Token is not configured. Please set it in main_bot.py")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    mydata_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("mydata", mydata_start)],
        states={ASK_SNILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, mydata_ask_snils)]},
        fallbacks=[CommandHandler("cancel", mydata_cancel)],
    )
    application.add_handler(mydata_conv_handler)
    application.add_handler(CommandHandler("myresults", myresults_command))
    application.add_handler(CommandHandler("listolympiads", listolympiads_command))

    # Admin Add Olympiad
    add_olympiad_conv = ConversationHandler(
        entry_points=[CommandHandler("admin_add_olympiad", admin_add_olympiad_start)],
        states={
            OLYMPIAD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_olympiad_name)],
            OLYMPIAD_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_olympiad_date)],
            OLYMPIAD_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_olympiad_subject)],
            OLYMPIAD_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_olympiad_description)],
        },
        fallbacks=[CommandHandler("cancel_admin_op", admin_op_cancel)],
    )
    application.add_handler(add_olympiad_conv)

    # Admin Add Results
    add_results_conv = ConversationHandler(
        entry_points=[CommandHandler("admin_add_results", admin_add_results_start)],
        states={
            SELECT_OLYMPIAD_FOR_RESULTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_select_olympiad_for_results)],
            RESULT_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_result_full_name)],
            RESULT_SNILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_result_snils)],
            RESULT_SCORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_result_score)],
            RESULT_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_result_place)],
            RESULT_DIPLOMA_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_result_diploma_link)],
        },
        fallbacks=[CommandHandler("cancel_admin_op", admin_op_cancel)],
    )
    application.add_handler(add_results_conv)
    
    # Admin Edit Result (Placeholder)
    application.add_handler(CommandHandler("admin_edit_result", admin_edit_result_start))

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    print("main_bot.py updated with admin commands. It will not run automatically in this environment yet.")
    print("You will need to provide a TELEGRAM_BOT_TOKEN and potentially run database_setup.py if not done yet.")
    print("To make a user an admin, you'll need to manually update the 'Users' table in the database, e.g., SET is_admin = 1 WHERE telegram_id = YOUR_ADMIN_TELEGRAM_ID.")
    main()
