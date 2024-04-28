import logging
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram.ext import CommandHandler
import sqlite3 as sql
from config import BOT_TOKEN
import geocoder_api


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update, context):
    con = sql.connect('users.db')
    cur = con.cursor()
    context.user_data.clear()
    user = update.effective_user
    user_db = cur.execute("SELECT * FROM users WHERE tg_id == ?", (user.id,)).fetchall()
    if not user_db:
        cur.execute('INSERT INTO users (tg_id, feadback) VALUES (?, ?)', (user.id, 0))
        con.commit()
        cur.close()
        con.close()
    reply_keyboard = [['🧮Сравнить варианты доставки', '📈Оценить работу бота']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        "Привет! \n"
        "\n"
        "Я помогу тебе рассчитать стоимость доставки \n"
        "различными компаниями и найти лучший вариант\n"
        "\n"
        "Для начала выберите необходимый пункт в меню\n"
        "В не понятной ситуации напишите команду /help\n"
        "\n"
        "⬇", reply_markup=markup)
    return 1


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.run_polling()


if __name__ == '__main__':
    main()