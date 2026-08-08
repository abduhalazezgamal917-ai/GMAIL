import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import time
import os
from keep_alive import keep_alive

# ================= الإعدادات الأساسية =================
BOT_TOKEN = os.getenv("BOT_TOKEN") 
bot = telebot.TeleBot(BOT_TOKEN)

CHANNEL_USERNAME = "@ZenoX_Tools"
ADMIN_ID = 6043858925

# ================= قواعد البيانات المؤقتة =================
user_emails = {} 
user_last_action = {} 

# ================= دوال مساعدة =================
def check_subscription(user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        if status in ['member', 'administrator', 'creator']:
            return True
        return False
    except:
        return False

def is_rate_limited(user_id):
    current_time = time.time()
    if user_id in user_last_action:
        if current_time - user_last_action[user_id] < 3:
            return True
    user_last_action[user_id] = current_time
    return False

# ================= تصميم الأزرار الصلبة (الثابتة أسفل الشاشة) =================
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📨 إنشاء بريد عشوائي"))
    markup.add(KeyboardButton("👨‍💻 المطور"))
    return markup

def email_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🔄 فحص صندوق الوارد"))
    markup.add(KeyboardButton("🗑️ تغيير البريد"), KeyboardButton("👨‍💻 المطور"))
    return markup

# ================= أوامر البوت =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # فحص الاشتراك الإجباري
    if not check_subscription(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🌟 اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        bot.send_message(user_id, "⚠️ **عذراً عزيزي!**\n\nيجب عليك الاشتراك في القناة لتتمكن من استخدام البوت.\nبعد الاشتراك، أرسل /start مجدداً.", reply_markup=markup, parse_mode="Markdown")
        return

    welcome_text = (
        "👋 **أهلاً بك في بوت البريد المؤقت الذكي!**\n\n"
        "أنا هنا لمساعدتك في إنشاء عناوين بريد إلكتروني وهمية بضغطة زر لحماية بريدك الأساسي.\n\n"
        "👇 استخدم الأزرار الثابتة بالأسفل للبدء."
    )
    bot.send_message(user_id, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text

    if is_rate_limited(user_id):
        bot.send_message(user_id, "⏳ يرجى الانتظار قليلاً بين الطلبات...")
        return

    if not check_subscription(user_id):
        bot.send_message(user_id, "❌ لم تشترك في القناة بعد! أرسل /start للاشتراك.")
        return

    # 1. توليد بريد جديد باستخدام Guerrilla Mail (سريع ولا يحظر السيرفرات)
    if text in ["📨 إنشاء بريد عشوائي", "🗑️ تغيير البريد"]:
        msg = bot.send_message(user_id, "⏳ جاري توليد بريد إلكتروني حقيقي...")
        try:
            # طلب بريد جديد من واجهة بديلة مستقرة
            res = requests.get("https://api.guerrillamail.com/ajax.php?f=get_email_address", timeout=10).json()
            email = res.get('email_addr')
            
            if not email:
                raise Exception("API Error")
                
            user_emails[user_id] = email 
            
            text_msg = f"✅ **تم إنشاء بريدك بنجاح:**\n\n`{email}`\n\n(اضغط على البريد لنسخه)\nاستخدم هذا البريد للتسجيل، ثم اضغط على زر فحص صندوق الوارد."
            bot.send_message(user_id, text_msg, reply_markup=email_menu(), parse_mode="Markdown")
            
        except Exception as e:
            bot.send_message(user_id, "⚠️ حدث خطأ في الاتصال بخادم الإيميلات البديل. حاول مرة أخرى.")

    # 2. فحص صندوق الوارد واستقبال الرسائل
    elif text == "🔄 فحص صندوق الوارد":
        if user_id not in user_emails:
            bot.send_message(user_id, "⚠️ لم تقم بإنشاء بريد بعد! اضغط على زر الإنشاء أولاً.")
            return
            
        msg = bot.send_message(user_id, "⏳ جاري فحص صندوق الوارد...")
        email = user_emails[user_id]
        
        try:
            # جلب قائمة الرسائل للبريد الحالي
            res = requests.get(f"https://api.guerrillamail.com/ajax.php?f=get_message_list&offset=0", timeout=10).json()
            list_mails = res.get('list', [])
            
            if not list_mails:
                bot.send_message(user_id, "📭 صندوق الوارد فارغ. لم تصل أي رسائل حتى الآن.")
            else:
                for mail in list_mails:
                    mail_id = mail.get('mail_id')
                    sender = mail.get('mail_from', 'غير معروف')
                    subject = mail.get('mail_subject', 'بدون عنوان')
                    
                    # جلب نص الرسالة بالتفصيل
                    read_res = requests.get(f"https://api.guerrillamail.com/ajax.php?f=fetch_email&email_id={mail_id}", timeout=10).json()
                    body = read_res.get('mail_body', 'لا يوجد نص')
                    
                    msg_text = f"📨 **رسالة جديدة واردة!**\n\n**من:** `{sender}`\n**الموضوع:** {subject}\n\n**المحتوى:**\n{body}"
                    bot.send_message(user_id, msg_text, parse_mode="Markdown")
        
        except Exception as e:
            bot.send_message(user_id, "⚠️ حدث خطأ أثناء جلب الرسائل. حاول مجدداً.")

    elif text == "👨‍💻 المطور":
        bot.send_message(user_id, f"هذا البوت من تطوير قناتنا: {CHANNEL_USERNAME}\nللتواصل مع المطور: tg://user?id={ADMIN_ID}")

# ================= تشغيل البوت والخادم =================
if __name__ == "__main__":
    keep_alive()
    print("Bot is running with Guerrilla API & Reply Keyboards...")
    bot.infinity_polling(timeout=20, long_polling_timeout=5)





