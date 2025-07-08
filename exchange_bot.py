import os
from dotenv import load_dotenv
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import datetime

load_dotenv()  # Загружаем переменные окружения из файла .env

# Получаем актуальные курсы валют
def get_currency_rate(currency):
    today = datetime.datetime.now().strftime('%d/%m/%Y')
    response = requests.get(f'https://www.cbr-xml-daily.ru/daily_json.js')
    data = response.json()
    
    if currency == 'USD':
        return float(data['Valute']['USD']['Value'])
    elif currency == 'EUR':
        return float(data['Valute']['EUR']['Value'])
    else:
        # Для рубля возвращаем единицу
        return 1.0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Рубль", callback_data='RUB')],
        [InlineKeyboardButton("Доллар", callback_data='USD')],
        [InlineKeyboardButton("Евро", callback_data='EUR')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите валюту:', reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_choice = query.data
    context.user_data['source_currency'] = user_choice
    
    # Меняем клавиатуру на выбор итоговой валюты
    new_keyboard = [
        [InlineKeyboardButton("В доллар", callback_data=f'TO_USD')],
        [InlineKeyboardButton("В рубль", callback_data=f'TO_RUB')],
        [InlineKeyboardButton("В евро", callback_data=f'TO_EUR')]
    ]
    reply_markup = InlineKeyboardMarkup(new_keyboard)
    await query.edit_message_text(text="Теперь выберите валюту, в которую перевести:", reply_markup=reply_markup)

async def convert_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    target_currency = query.data.split('_')[1]
    source_currency = context.user_data['source_currency']
    
    if source_currency == target_currency:
        await query.edit_message_text(text="Валюта должна быть разной, выберите, пожалуйста, другую.")
        return
    
    # Запрашиваем ввод суммы
    await query.edit_message_text(text="Введите сумму:")
    context.user_data['target_currency'] = target_currency

async def process_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_str = update.message.text.replace(',', '.').strip()  # Обрабатываем число с точкой или запятой
    try:
        amount = float(amount_str)
        
        source_currency = context.user_data['source_currency']
        target_currency = context.user_data['target_currency']
        
        rate_source = get_currency_rate(source_currency)
        rate_target = get_currency_rate(target_currency)
        
        # Логика правильной обработки конверсий:
        if source_currency == 'RUB':  # Из рублей в другую валюту
            converted_amount = round(amount / rate_target, 2)
        elif target_currency == 'RUB':  # Из другой валюты в рубли
            converted_amount = round(amount * rate_source, 2)
        else:  # Прямая конвертация между двумя иностранными валютами
            converted_amount = round((amount * rate_source) / rate_target, 2)
        
        await update.message.reply_text(
            f"{amount:.2f} {source_currency} равно примерно {converted_amount:.2f} {target_currency}.",
            parse_mode=None
        )
    except ValueError:
        await update.message.reply_text("Некорректная сумма. Попробуйте снова ввести число.")

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')  # Берём токен из переменной окружения
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_callback, pattern=r'^RUB|USD|EUR$'))
    application.add_handler(CallbackQueryHandler(convert_currency, pattern=r'^TO_(RUB|USD|EUR)$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_amount))

    print("Бот запущен...")
    application.run_polling()