from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import Message, CallbackQuery
from aiogram.types import LabeledPrice
from keyboards import *
from database import *
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

TOKEN = os.getenv('TOKEN')
PAYMENT = os.getenv('PAYMENT')
CHANNEL_ID = os.getenv('CHANNEL_ID')

bot = Bot(TOKEN, parse_mode='html')

dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def command_start(message: Message):
    full_name = message.from_user.full_name
    await message.answer(f'Salom <b>{full_name}</b>!\nMEGA Shaurma ga xush kelibsiz! 🌯')
    await register_user(message)


async def register_user(message: Message):
    chat_id = message.chat.id
    full_name = message.from_user.full_name
    user = first_select_user(chat_id)
    if user:
        await message.answer('Hush kelibsiz 😇')
        await show_main_menu(message)
    else:
        first_register_user(chat_id, full_name)
        await message.answer('Ro`yxatdan o`tish uchun kontaktingizni jo`nating 📞',
                             reply_markup=phone_button())


@dp.message_handler(content_types=['contact'])
async def finish_register(message: Message):
    chat_id = message.chat.id
    phone = message.contact.phone_number
    update_user_to_finish_register(chat_id, phone)  # Tel raqam qoshish uchun javobgar funksiya !
    await create_cart_for_user(message)
    await message.answer('Ro`yxatdan muvaffaqiyatli o`ttingiz!')
    await show_main_menu(message)


async def create_cart_for_user(message: Message):
    chat_id = message.chat.id
    try:
        insert_to_cart(chat_id)
    except:
        pass


async def show_main_menu(message: Message):
    await message.answer('Bo`limni tanlang 🍖', reply_markup=generate_main_menu())


@dp.message_handler(lambda message: '✅ Buyurtma qilish' in message.text)
async def mek_order(message: Message):
    await message.answer('Bo`limni tanlang', reply_markup=generate_category_menu())


@dp.callback_query_handler(lambda call: 'category' in call.data)
async def show_products(call: CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    _, category_id = call.data.split('_')
    category_id = int(category_id)
    await bot.edit_message_text('Maxsulot tanlang', chat_id, message_id, reply_markup=products_by_category(category_id))


@dp.callback_query_handler(lambda call: 'main_menu' in call.data)
async def return_to_main_menu(call: CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    await bot.edit_message_text(chat_id=chat_id,
                                message_id=message_id,
                                text='Bo`limni tanlang',
                                reply_markup=generate_category_menu())


@dp.callback_query_handler(lambda call: 'product' in call.data)
async def show_detail_product(call: CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    _, product_id = call.data.split('_')
    product_id = int(product_id)

    product = get_product_detail(product_id)
    await bot.delete_message(chat_id, message_id)
    with open(product[-1], mode='rb') as img:
        await bot.send_photo(chat_id=chat_id, photo=img, caption=f'''{product[2]}\n
Ta`rkibi: {product[4]}\n

Narxi: {product[3]}
''', reply_markup=generate_product_detail_menu(product_id=product_id, category_id=product[1]))


@dp.callback_query_handler(lambda call: 'back' in call.data)
async def return_to_category(call: CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    _, category_id = call.data.split('_')
    await bot.delete_message(chat_id, message_id)
    await bot.send_message(chat_id, 'Mahsulot tanlang', reply_markup=products_by_category(category_id))


@dp.callback_query_handler(lambda call: 'cart' in call.data)
async def add_product_cart(call: CallbackQuery):
    chat_id = call.message.chat.id
    _, product_id, quantity = call.data.split('_')
    product_id, quantity = int(product_id), int(quantity)

    cart_id = get_user_cart_id(chat_id)
    product = get_product_detail(product_id)

    final_price = quantity * product[3]

    if insert_or_update_cart_product(cart_id, product[2], quantity, final_price):
        await bot.answer_callback_query(call.id, 'Mahsulot qoshildi')
    else:
        await bot.answer_callback_query(call.id, 'Soni ozgardi')


@dp.message_handler(regexp='🛒 Savat')
async def show_cart(message: Message, edit_message: bool = False):
    chat_id = message.chat.id
    cart_id = get_user_cart_id(chat_id)

    try:
        update_total_product_total_price(cart_id)
    except Exception as e:
        print(e)
        await message.answer('Savatga qoshilmadi !')
        return

    cart_products = get_cart_products(cart_id)
    total_products, total_price = get_total_products_price(cart_id)



    if total_products and total_price:
        text = 'Sizning Savat: \n\n'
        i = 0
        for product_name, quantity, final_price in cart_products:
            i += 1
            text += f'''{i}. {product_name}
Soni: {quantity} ta
Umumiy summasi: {final_price} som\n\n'''

        text += f'''Umumiy mahsulot soni: {total_products} ta
Umumiy summasi: {total_price} som'''

        if edit_message:
            await bot.edit_message_text(text, chat_id, message.message_id, reply_markup=generate_cart_menu(cart_id))
        else:
            await bot.send_message(chat_id, text, reply_markup=generate_cart_menu(cart_id))
    else:
        await bot.delete_message(chat_id, message.message_id)
        await bot.send_message(chat_id, '🗑 Savat bosh !')


@dp.callback_query_handler(lambda call: 'delete' in call.data)
async def delete_cart_product(call: CallbackQuery):
    _, cart_product_id = call.data.split('_')
    message = call.message
    cart_product_id = int(cart_product_id)

    delete_cart_product_from_database(cart_product_id)

    await bot.answer_callback_query(call.id, 'Mahsulot ochirildi !')
    await show_cart(message, edit_message=True)


@dp.callback_query_handler(lambda call: 'order' in call.data)
async def create_order(call: CallbackQuery):
    chat_id = call.message.chat.id

    _, cart_id = call.data.split('_')
    cart_id = int(cart_id)
    time_order = datetime.now().strftime('%H:%M')
    date_order = datetime.now().strftime('%d/%m/%Y')

    cart_products = get_cart_products(cart_id)
    total_products, total_price = get_total_products_price(cart_id)

    save_order_check(cart_id, total_products, total_price, time_order, date_order)
    order_check_id = get_order_check_id(cart_id)

    if total_products and total_price:
        text = 'Sizning Savat: \n\n'
        i = 0
        for product_name, quantity, final_price in cart_products:
            i += 1
            text += f'''{i}. {product_name}
Soni: {quantity} ta
Umumiy summasi: {final_price} som\n\n'''
            save_order(order_check_id, product_name, quantity, final_price)
        text += f'''Umumiy mahsulot soni: {total_products} ta
Umumiy summasi: {total_price} som'''

        await bot.send_invoice(
            chat_id=chat_id,
            title=f'Buyurtma №{cart_id}',
            description=text,
            payload='invoice_payload',
            provider_token=PAYMENT,
            currency='UZS',
            prices=[
                LabeledPrice(label='Umumiy summa', amount=int(total_price * 100)),
                LabeledPrice(label='Yetkazib bering 🚚', amount=1500000)
            ],
            start_parameter='test'
        )


@dp.pre_checkout_query_handler(lambda query: True)
async def checkout(pre_checkout_query):
    await bot.answer_pre_checkout_query(pre_checkout_query.id,
                                        ok=True,
                                        error_message='Kartangizda mablag yetarli emas'
                                        )


@dp.message_handler(content_types=['successful_payment'])
async def get_payment(message):
    chat_id = message.chat.id
    cart_id = get_user_cart_id(chat_id)
    await bot.send_message(chat_id, 'Sizning tolovingiz amalga oshdi!')
    drop_cart_products_default(cart_id)


@dp.message_handler(regexp='📍 Manzil')
async def send_location(message: types.Message):
    await bot.send_location(
        chat_id=message.chat.id,
        latitude=41.25561356612139,
        longitude=69.17825208879218,
    )
    await message.answer("📍 Bizning manzil")



executor.start_polling(dp)
