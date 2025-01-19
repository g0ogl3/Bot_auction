from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import *
import schedule
import threading
import time
from config import *
import os

bot = TeleBot(TOKEN)

def gen_markup(id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Получить!", callback_data=id))
    return markup

@bot.message_handler(commands=['resend_images'])
def resend_images(message):
    user_id = message.chat.id
    missed_images = manager.get_missed_images(user_id)
    if missed_images:
        for img in missed_images:
            with open(f'img/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Ты получил пропущенную картинку!")
    else:
        bot.send_message(user_id, "У тебя нет пропущенных картинок.")


@bot.message_handler(commands=['get_my_id'])
def get_my_id(message):
    user_id = message.chat.id
    bot.send_message(user_id, f"Your User ID is: {user_id}")


@bot.message_handler(commands=['rating'])
def handle_rating(message):
    res = manager.get_rating()
    
    if not res:
        bot.send_message(message.chat.id, "Рейтинг пока пуст!")
        return
    
    res = [f'| @{x[0]:<11} | {x[1]:<11}|\n{"_"*26}' for x in res]
    res = '\n'.join(res)
    res = f'|USER_NAME    |COUNT_PRIZE|\n{"_"*26}\n' + res
    
    bot.send_message(message.chat.id, res)

@bot.message_handler(commands=['my_score'])
def get_my_score(message):
    user_id = message.chat.id

    
    prizes = manager.get_winners_img(user_id)
    prizes = [x[0] for x in prizes]  

    
    all_images = os.listdir('img')
    image_paths = [f'img/{img}' if img in prizes else f'hidden_img/{img}' for img in all_images]

    prizes_img = os.listdir('img')
    paths = ['img/' + img for img in prizes_img]
    collage = create_collage(paths)
    if collage is not None:
        collage_path = f'collages/{user_id}_collage.jpg'
        cv2.imwrite(collage_path, collage)

        
        with open(collage_path, 'rb') as photo:
            bot.send_photo(user_id, photo, caption="Вот твой коллаж с достижениями!")
    else:
        bot.send_message(user_id, "У тебя пока нет картинок.")

@bot.message_handler(commands=['bonus_score'])
def handle_bonus_score(message):
    user_id = message.chat.id
    score = manager.get_user_score(user_id)
    bot.send_message(user_id, f'Твой текущий счет бонусов: {score}')


@bot.message_handler(commands=['redeem_bonus'])
def handle_redeem_bonus(message):
    user_id = message.chat.id
    score = manager.get_user_score(user_id)
    if score >= 10:
        manager.update_user_score(user_id, -10)
        bot.send_message(user_id, "Ты использовал 10 бонусов для дополнительного приза!")
    else:
        bot.send_message(user_id, "Недостаточно бонусов для получения приза.")



@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    prize_id = call.data
    user_id = call.message.chat.id

    winners_count = manager.get_winners_count(prize_id)

    if winners_count < 3:
        res = manager.add_winner(user_id, prize_id)
        if res:
            img = manager.get_prize_img(prize_id)
            with open(f'img/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Поздравляем! Ты получил картинку!")
        else:
            bot.send_message(user_id, 'Ты уже получил этот приз!')
    else:
        bot.send_message(user_id, "К сожалению, ты не успел получить картинку! Попробуй в следующий раз!)")

@bot.message_handler(commands=['add_image'])
def handle_add_image(message):
    if message.chat.id == ADMIN_USER_ID:
        bot.send_message(message.chat.id, "Отправь изображение для добавления")
        bot.register_next_step_handler(message, save_image)
    else:
        bot.send_message(message.chat.id, "У тебя нет прав администратора.")
        
def save_image(message):
    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        img_path = f'img/{file_info.file_id}.jpg'
        
        with open(img_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        bot.send_message(message.chat.id, "Изображение успешно добавлено!")


@bot.message_handler(commands=['set_frequency'])
def set_frequency(message):
    if message.chat.id == ADMIN_USER_ID:
        bot.send_message(message.chat.id, "Укажи новую частоту отправки (в минутах):")
        bot.register_next_step_handler(message, update_frequency)
        
def update_frequency(message):
    try:
        new_frequency = int(message.text)
        schedule.clear()
        schedule.every(new_frequency).minutes.do(send_message)
        bot.send_message(message.chat.id, f"Частота отправки изменена на {new_frequency} минут.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введи правильное число.")



def send_message():
    prize_id, img = manager.get_random_prize()[:2]
    manager.mark_prize_used(prize_id)
    hide_img(img)
    for user in manager.get_users():
        with open(f'hidden_img/{img}', 'rb') as photo:
            bot.send_photo(user, photo, reply_markup=gen_markup(id=prize_id))

def schedule_thread():
    schedule.every().minute.do(send_message)
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    if user_id in manager.get_users():
        bot.reply_to(message, "Ты уже зарегистрирован!")
    else:
        manager.add_user(user_id, message.from_user.username)
        bot.reply_to(message, """Привет! Добро пожаловать! 
Тебя успешно зарегистрировали!
Каждый час тебе будут приходить новые картинки, и у тебя будет шанс их получить!
Для этого нужно быстрее всех нажать на кнопку 'Получить!'

Только три первых пользователя получат картинку!""")

def polling_thread():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()

    polling_thread = threading.Thread(target=polling_thread)
    polling_schedule = threading.Thread(target=schedule_thread)

    polling_thread.start()
    polling_schedule.start()
