import logging
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram.ext import CommandHandler
import sqlite3 as sql
from config import BOT_TOKEN
import pec_api
import geocoder_api


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


# Сценарий диалога
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
        "В непонятной ситуации напишите команду /help\n"
        "\n"
        "⬇", reply_markup=markup)
    return 1


async def chosen_option(update, context):
    msg = update.message.text
    if msg[1:].lower() == 'сравнить варианты доставки':
        await update.message.reply_html(
            f"🌏 Напишите город, из которого вы хотите осуществить доставку.\n"
            "Пожалйуста, пишите только существующие города❗")
        return 2
    elif msg[1:].lower() == 'оценить работу бота':
        con = sql.connect('../calculator_deliver/users.db')
        cur = con.cursor()
        rate_sum = 0
        rated_users = 0
        user_db = cur.execute("SELECT * FROM users").fetchall()
        print(user_db)
        for el in user_db:
            if el[1]:
                rate_sum += el[1]
                rated_users += 1
        con.commit()
        cur.close()
        con.close()
        if rated_users == 0:
            await update.message.reply_html(f'Пожалуйста, оцените работу бота по шкале от 0 до 10')
        else:
            await update.message.reply_html(f'Нашим ботом уже воспользовалось {len(user_db)} человек! 😎\n'
                                            f'🌟 Средняя оценка наших пользователей: {round(rate_sum / rated_users, 2)}\n'
                                            f'Пожалуйста, оцените работу бота по шкале от 0 до 10')
        return 10
    else:
        reply_keyboard = [['🧮Сравнить варианты доставки', '📈Оценить работу бота']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        await update.message.reply_html('Извините, я Вас не понимаю...', reply_markup=markup)
        return 1


async def choose_city_from(update, context):
    msg = update.message.text
    city_from = geocoder_api.get_city_name(msg.lower())
    if not city_from:
        await not_understand(update, context)
    else:
        context.user_data['city_from'] = city_from
        print(city_from)
        await context.bot.send_message(chat_id=update.effective_user.id,
                                           text=f"🌏Напишите город, в который вы хотите осуществить доставку.\n"
                                            "Пожалйуста, пишите только существующие города❗")
        return 3


async def choose_city_to(update, context):

    msg = update.message.text
    try:
        city_to = geocoder_api.get_city_name(msg.lower())
        context.user_data['city_to'] = city_to
        await context.bot.send_message(chat_id=update.effective_user.id,
                                           text=f"Введите количество грузовых объектов, котрые вы хотите доставить"
                                           )
        return 4
    except geocoder_api.CityNotFoundError:
        await not_understand(update, context)


async def read_places(update, context):
    msg = update.message.text
    try:
        places = int(msg)
        context.user_data['places'] = places
        await update.message.reply_html(
            f"Введите вес в кг на одно место "
        )
        return 5

    except ValueError:
        await not_understand(update, context)


async def read_weight(update, context):
    msg = update.message.text
    try:
        weight = float(msg)
        context.user_data['weight'] = weight
        reply_keyboard = [[InlineKeyboardButton('мм', callback_data='#units_mm'),
                           InlineKeyboardButton('см', callback_data='#units_sm'),
                           InlineKeyboardButton('метр', callback_data='#units_m')]]
        markup = InlineKeyboardMarkup(reply_keyboard)
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text=f"Введите единицы измерения размеров груза (одно место)",
                                       reply_markup=markup)
        return 6
    except ValueError:
        await not_understand(update, context)


async def read_units(update, context):
    query = update.callback_query
    if query.data[7:] == 'mm':
        context.user_data['volume_coef'] = 0.001
    elif query.data[7:] == 'sm':
        context.user_data['volume_coef'] = 0.01
    elif query.data[7:] == 'm':
        context.user_data['volume_coef'] = 1
    await context.bot.send_message(chat_id=update.effective_user.id,
                                   text=f"Введите ширину, длину, высоту груза (на одно место) через пробел\n\nПример:\n20 30 50")
    return 7


async def read_sizes(update, context):
    try:
        msg = update.message.text
        width, long, height = map(lambda x: float(x) * context.user_data['volume_coef'], msg.split(' '))
        context.user_data['sizes'] = [width, height, long]
        reply_keyboard = [[InlineKeyboardButton('да', callback_data='#gabarit_yes'),
                           InlineKeyboardButton('нет', callback_data='#gabarit_no')]]
        markup = InlineKeyboardMarkup(reply_keyboard)
        await update.message.reply_html(f"Вашему грузу нужна защитная транспортная упаковка?", reply_markup=markup)
        return 8
    except Exception:
        await not_understand(update, context)


async def ztu(update, context):
    query = update.callback_query
    if query.data[9:] == 'yes':
        context.user_data['ztu'] = True
    elif query.data[9:] == 'no':
        context.user_data['ztu'] = False
    reply_keyboard = [[InlineKeyboardButton('Забрать по адресу, доставить по адресу', callback_data='#deliv_dd')],
                      [InlineKeyboardButton('Забрать из отделения, доставить в отделение', callback_data='#deliv_pp')],
                      [InlineKeyboardButton('Забрать по адресу, доставить в отделение', callback_data='#deliv_dp')],
                      [InlineKeyboardButton('Забрать из отделения, доставить по адресу', callback_data='#deliv_pd')]]
    markup = InlineKeyboardMarkup(reply_keyboard)
    await context.bot.send_message(chat_id=update.effective_user.id,
                                   text=f"Введите единицы измерения размеров груза (одно место)",
                                   reply_markup=markup)
    return 9


async def delivery(update, context):
    query = update.callback_query
    home_take = True
    home_delive = True
    if query.data[7] == 'p':
        home_take = False
    if query.data[8] == 'p':
        home_delive = False
    context.user_data['home_take'] = home_take
    context.user_data['home_delive'] = home_delive
    await calculate(update, context)


# Функция расчета доставки с использованием pec_api
async def calculate(update, context):
    city_from = ' '.join(context.user_data['city_from'].split('_'))
    city_to = ' '.join(context.user_data['city_to'].split('_'))
    places = context.user_data['places']
    weight = context.user_data['weight']
    width, long, height = context.user_data['sizes']
    ztu = context.user_data['ztu']
    home_take = context.user_data["home_take"]
    home_delive = context.user_data["home_delive"]
    text1 = f'Рассчет стоимости доставки {city_from} - {city_to}\n' \
            f'Параметры груза:\n' \
            f'Количество мест: {places}\n' \
            f'Объем на место: {round(width * long * height, 5)} м3\n' \
            f'Вес на место: {weight} кг\n' \
            f'Защитная транспортная упаковка: {"включена" if ztu else "не включена"}\n' \
            f'Забрать {"по адресу" if home_take else "из отделения"}\n' \
            f'Доставить {"по адресу" if home_delive else "в отделение"}\n' \
            f'----------------------------------------------\n'
    await context.bot.send_message(chat_id=update.effective_user.id,
                                   text=text1)
    try:
        info = pec_api.get_info_delivery(city_from=city_from, city_to=city_to,
                                         weight=weight, width=width, long=long, height=height,
                                         volume=width * long * height, is_negabarit=0, need_protected_package=ztu,
                                         places=places)
        auto_enabled = False
        auto_cost = 0
        add_list = ['ADD', 'ADD_1', 'ADD_2', 'ADD_3', 'ADD_4']
        if 'auto' in info.keys():
            auto_enabled = True
            auto_cost = int(info['auto'][2])
            if home_take:
                auto_cost += int(info['take'][2])
            if home_delive:
                auto_cost += int(info['deliver'][2])
            if 'autonegabarit' in info.keys():
                auto_cost += int(info['autonegabarit'][2])
            for i in add_list:
                if i in info.keys():
                    auto_cost += int(info[i]['3'])
        auto_time = 'неизвестен'
        if 'periods_days' in info.keys():
            auto_time = info['periods_days']
        text2 = f'Транспортная компания: ПЭК:\n' \
                f'Автоперевозка: {"недоступна" if not auto_enabled else str(auto_cost) + f"р; срок в днях:"} {auto_time}'
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text=text2)
        return ConversationHandler.END
    except pec_api.NoDeliveryToThisCity as err:
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text=f'{str(err)}')


async def stop(update, context):
    await update.message.reply_text("Всего доброго!")
    return ConversationHandler.END


# Функция для работы обратной связи с пользователем
async def feedback(update, context):
    user = update.effective_user
    con = sql.connect('../calculator_deliver/users.db')
    cur = con.cursor()
    try:
        msg = int(update.message.text)
        if msg >= 0 and msg <= 10:
            reply_keyboard = [['Сравнить варианты доставки', 'Оценить работу бота']]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            cur.execute('UPDATE users SET feadback = ? WHERE tg_id = ?', (msg, user.id))
            con.commit()
            cur.close()
            con.close()
            await update.message.reply_text("Спасибо за обратную связь!", reply_markup=markup)
            return 1
        else:

            await update.message.reply_text("Я умею считать только от 0 до 10")
    except Exception as ex:
        await not_understand(update, context)


async def help(update, context):
    await update.message.reply_text("Чтобы начать диалог, напиши /start\n"
                                    "Если что-то пошло не так, пиши /stop и /start")


async def not_understand(update, context):
    await context.bot.send_message(chat_id=update.effective_user.id,
                                   text='Извините, я не понял вашего ответа..Попробуйте еще раз\n'
                                        'Для перезапуска напишите /stop, а после /start')


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, chosen_option)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_city_from)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_city_to)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, read_places)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, read_weight)],
            6: [CallbackQueryHandler(read_units, pattern='^' + '#units_')],
            7: [MessageHandler(filters.TEXT & ~filters.COMMAND, read_sizes)],
            8: [CallbackQueryHandler(ztu, pattern='^' + '#gabarit_')],
            9: [CallbackQueryHandler(delivery, pattern='^' + '#deliv_')],
            10: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback)]
        },

        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(CommandHandler("help", help))
    application.add_handler(conv_handler)

    application.run_polling()


if __name__ == '__main__':
    main()