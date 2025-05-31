import sqlite3
from openpyxl import Workbook
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Этапы диалога
NAME, DATE, SERVICE, COST, PAID, EXPORT = range(6)

# Список услуг
SERVICES = [
    "Лечение кариеса",
    "Отбеливание",
    "Виниры",
    "Профилактика",
    "Удаление зуба"
]

# Клавиатуры
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("Добавить пациента")],
    [KeyboardButton("Помощь")]
], one_time_keyboard=False)

SERVICE_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton(service)] for service in SERVICES],
    one_time_keyboard=True
)

FINAL_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("Экспортировать данные")],
    [KeyboardButton("Добавить нового пациента")]
], one_time_keyboard=False)

# === Работа с SQLite ===
DB_NAME = 'patients.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                date TEXT,
                service TEXT,
                cost REAL,
                paid TEXT
            )
        ''')
        conn.commit()

def add_patient_to_db(data):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO patients (name, date, service, cost, paid)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['name'], data['date'], data['service'], data['cost'], data['paid']))
        conn.commit()

def export_patients_to_excel(filename='patients_export.xlsx'):
# def export_patients_to_csv(filename='patients_export.csv'):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM patients")
        rows = cur.fetchall()


        # Создаём Excel-файл
        wb = Workbook()
        ws = wb.active
        ws.title = "Пациенты"

        # Заголовки
        headers = ['id', 'Имя', 'Дата', 'Услуга', 'Стоимость', 'Оплачено']
        ws.append(headers)

        # Данные
        for row in rows:
            ws.append(row)

        # Сохраняем файл
        wb.save(filename)
        
    return filename



# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите действие:", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END

async def add_patient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите имя пациента:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Введите дату приёма (например, 01.05.2025):")
    return DATE

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date'] = update.message.text
    await update.message.reply_text("Выберите услугу:", reply_markup=SERVICE_KEYBOARD)
    return SERVICE

async def get_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['service'] = update.message.text
    await update.message.reply_text("Введите стоимость услуги:")
    return COST

async def get_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cost'] = update.message.text
    await update.message.reply_text("Оплачено? (да/нет)")
    return PAID

async def get_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['paid'] = update.message.text
    add_patient_to_db(context.user_data)

    await update.message.reply_text("✅ Данные успешно сохранены!")
    await update.message.reply_text("Выберите действие:", reply_markup=FINAL_KEYBOARD)
    return EXPORT

async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Экспортировать данные":
        # file_path = export_patients_to_csv()
        file_path = export_patients_to_excel()
        await update.message.reply_document(document=open(file_path, 'rb'))
        await update.message.reply_text("Выберите действие:", reply_markup=FINAL_KEYBOARD)
    elif update.message.text == "Добавить нового пациента":
        await update.message.reply_text("Введите имя пациента:")
        return NAME
    return EXPORT

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Бот для учёта пациентов стоматологического кабинета.\n"
        "Используйте кнопки для добавления данных.\n"
        "Доступные услуги:\n" + "\n".join(SERVICES)
    )
    return ConversationHandler.END

# === Запуск бота ===
if __name__ == '__main__':
    init_db()  # Создаём БД, если не существует

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^Добавить пациента$"), add_patient)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_service)],
            COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cost)],
            PAID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_paid)],
            EXPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_export)]
        },
        fallbacks=[CommandHandler('cancel', start)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Помощь$"), help_command))

    print("Бот запущен...")
    app.run_polling()

