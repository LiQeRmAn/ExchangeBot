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
    
    rates = {
        'USD': float(data['Valute']['USD']['Value']),  # Доллар США
        'EUR': float(data['Valute']['EUR']['Value']),  # Евро
        'BYN': float(data['Valute']['BYN']['Value']),  # Белорусский рубль
        'CNY': float(data['Valute']['CNY']['Value'])   # Китайский Юань
    }
    
    # Возвращаем 1 для российского рубля, так как он является базовой валютой
    if currency == 'RUB':
        return 1.0
    else:
        return rates[currency]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Конвертация валюты", callback_data='CURRENCY')],
        [InlineKeyboardButton("Конвертация температуры", callback_data='TEMPERATURE')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Привет! Что хотите конвертировать?', reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    
    if choice == 'CURRENCY':
        # Кнопки выбора начальной валюты
        currency_keyboard = [
            [InlineKeyboardButton("Рубль", callback_data='RUB')],
            [InlineKeyboardButton("Доллар", callback_data='USD')],
            [InlineKeyboardButton("Евро", callback_data='EUR')],
            [InlineKeyboardButton("Бел. Рубль", callback_data='BYN')],
            [InlineKeyboardButton("Кит. Юань", callback_data='CNY')]
        ]
        reply_markup = InlineKeyboardMarkup(currency_keyboard)
        await query.edit_message_text(text="Выберите начальную валюту:", reply_markup=reply_markup)
    elif choice == 'TEMPERATURE':
        temp_keyboard = [
            [InlineKeyboardButton("Цельсий", callback_data='CELSIUS')],
            [InlineKeyboardButton("Фаренгейт", callback_data='FAHRENHEIT')],
            [InlineKeyboardButton("Кельвин", callback_data='KELVIN')]
        ]
        reply_markup = InlineKeyboardMarkup(temp_keyboard)
        await query.edit_message_text(text="Выберите температуру для конвертации:", reply_markup=reply_markup)
    else:
        # Сохранение выбранной валюты или единицы температуры
        context.user_data['source_unit'] = choice
        
        # Далее идет логика вывода следующего шага
        if choice in ['RUB', 'USD', 'EUR', 'BYN', 'CNY']:
            new_keyboard = [
                [InlineKeyboardButton("В Доллар", callback_data=f'TO_USD')],
                [InlineKeyboardButton("В Рубль", callback_data=f'TO_RUB')],
                [InlineKeyboardButton("В Евро", callback_data=f'TO_EUR')],
                [InlineKeyboardButton("В Бел. Рубль", callback_data=f'TO_BYN')],
                [InlineKeyboardButton("В Кит. Юань", callback_data=f'TO_CNY')]
            ]
            reply_markup = InlineKeyboardMarkup(new_keyboard)
            await query.edit_message_text(text="Теперь выберите валюту, в которую перевести:", reply_markup=reply_markup)
        elif choice in ['CELSIUS', 'FAHRENHEIT', 'KELVIN']:
            temp_convert_keyboard = [
                [InlineKeyboardButton("В Цельсий", callback_data=f'TEMP_TO_CELSIUS')],
                [InlineKeyboardButton("В Фаренгейт", callback_data=f'TEMP_TO_FAHRENHEIT')],
                [InlineKeyboardButton("В Кельвин", callback_data=f'TEMP_TO_KELVIN')]
            ]
            reply_markup = InlineKeyboardMarkup(temp_convert_keyboard)
            await query.edit_message_text(text="Теперь выберите единицу измерения, в которую перевести:", reply_markup=reply_markup)

async def convert_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    target_currency = query.data.split('_')[1]
    source_currency = context.user_data['source_unit']
    
    if source_currency == target_currency:
        await query.edit_message_text(text="Валюта должна быть разной, выберите, пожалуйста, другую.")
        return
    
    # Запрашиваем ввод суммы
    await query.edit_message_text(text="Введите число:")
    context.user_data['target_currency'] = target_currency

async def convert_temperature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    target_temp = query.data.split('_')[2].lower()
    source_temp = context.user_data['source_unit'].lower()
    
    if source_temp == target_temp:
        await query.edit_message_text(text="Единица измерения должна быть разной, выберите, пожалуйста, другую.")
        return
    
    # Запрашиваем ввод значения температуры
    await query.edit_message_text(text="Введите значение температуры:")
    context.user_data['target_temp'] = target_temp

async def process_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_str = update.message.text.replace(',', '.').strip()  # Обрабатываем число с точкой или запятой
    try:
        amount = float(amount_str)
        
        if 'target_currency' in context.user_data:
            # Конвертируем валюту
            source_currency = context.user_data['source_unit']
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
        elif 'target_temp' in context.user_data:
            # Конвертируем температуру
            source_temp = context.user_data['source_unit'].lower()
            target_temp = context.user_data['target_temp'].lower()
            
            if source_temp == 'celsius':
                celsius_value = amount
            elif source_temp == 'fahrenheit':
                celsius_value = (amount - 32) * 5/9
            elif source_temp == 'kelvin':
                celsius_value = amount - 273.15
            
            if target_temp == 'celsius':
                result = celsius_value
            elif target_temp == 'fahrenheit':
                result = celsius_value * 9/5 + 32
            elif target_temp == 'kelvin':
                result = celsius_value + 273.15
            
            await update.message.reply_text(
                f"{amount:.2f}° {context.user_data['source_unit']} равно примерно {result:.2f}° {context.user_data['target_temp'].capitalize()}."
            )
    except ValueError:
        await update.message.reply_text("Некорректная сумма. Попробуйте снова ввести число.")

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')  # Берём токен из переменной окружения
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_callback, pattern=r'^CURRENCY|TEMPERATURE|RUB|USD|EUR|BYN|CNY|CELSIUS|FAHRENHEIT|KELVIN$'))
    application.add_handler(CallbackQueryHandler(convert_currency, pattern=r'^TO_(RUB|USD|EUR|BYN|CNY)$'))
    application.add_handler(CallbackQueryHandler(convert_temperature, pattern=r'^TEMP_TO_(CELSIUS|FAHRENHEIT|KELVIN)$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_amount))

    print("Бот запущен...")
    application.run_polling()