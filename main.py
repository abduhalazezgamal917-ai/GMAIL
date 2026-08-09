import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import time
import os
import re
import html
from keep_alive import keep_alive

# ================= الإعدادات =================
BOT_TOKEN = os.getenv("BOT_TOKEN") 
bot = telebot.TeleBot(BOT_TOKEN)
CHANNEL_USERNAME = "@ZenoX_Tools"
ADMIN_ID = 6043858925

# ================= قواعد البيانات =================
user_sessions = {} # تخزين الجلسات (Sessions)
user_emails = {}
user_last_action = {}

# ================= الدوال المساعدة =================
def is_rate_limited(user_id):
    current_time = time.time()
    if user_id in user_last_action and current_time - user_last_action[user_id] < 3:
        return True
    user_last_action[user_id] = current_time
    return False

# ================= واجهة البوت =================
def email_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🔄 فحص صندوق الوارد"), KeyboardButton("🗑️ تغيير البريد"))
    markup.add(KeyboardButton("👨‍💻 المطور"))
    return markup

# ================= أوامر البوت =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "👋 أهلاً بك! استخدم الأزرار للبدء.", reply_markup=email_menu())

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text

    if is_rate_limited(user_id):
        return

    # 1. إنشاء بريد
    if text in ["📨 إنشاء بريد عشوائي", "🗑️ تغيير البريد"]:
        bot.send_message(user_id, "⏳ جاري الاتصال بخادم البريد...")
        try:
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'})
            
            # جلب البريد
            res = session.get("https://api.guerrillamail.com/ajax.php?f=get_email_address", timeout=15)
            data = res.json()
            email = data.get('email_addr')
            
            user_sessions[user_id] = session
            user_emails[user_id] = email
            
            bot.send_message(user_id, f"✅ تم إنشاء بريدك:\n\n`{email}`", reply_markup=email_menu(), parse_mode="Markdown")
        except:
            bot.send_message(user_id, "⚠️ فشل الاتصال، حاول مجدداً.")

    # 2. فحص البريد
    elif text == "🔄 فحص صندوق الوارد":
        if user_id not in user_sessions:
            bot.send_message(user_id, "⚠️ أنشئ بريداً أولاً!")
            return
            
        try:
            session = user_sessions[user_id]
            res = session.get("https://api.guerrillamail.com/ajax.php?f=get_message_list&offset=0", timeout=15)
            mails = res.json().get('list', [])
            
            if not mails:
                bot.send_message(user_id, "📭 صندوق الوارد فارغ.")
            else:
                for mail in mails:
                    # جلب نص الرسالة
                    mail_id = mail.get('mail_id')
                    read_res = session.get(f"https://api.guerrillamail.com/ajax.php?f=fetch_email&email_id={mail_id}", timeout=15)
                    body = read_res.json().get('mail_body', 'لا يوجد محتوى')
                    
                    # تنظيف
                    clean_body = re.sub(r'<[^>]+>', '', body)
                    bot.send_message(user_id, f"📨 **رسالة جديدة:**\n\n{clean_body}", parse_mode="Markdown")
        except:
            bot.send_message(user_id, "⚠️ خطأ في جلب الرسائل. تأكد من أن الموقع يعمل.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
