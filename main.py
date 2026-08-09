import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from guerrillamail import GuerrillaMail
import time
import os
import re
import html
from keep_alive import keep_alive

# ================= الإعدادات الأساسية =================
BOT_TOKEN = os.getenv("BOT_TOKEN") 
bot = telebot.TeleBot(BOT_TOKEN)

CHANNEL_USERNAME = "@ZenoX_Tools"
ADMIN_ID = 6043858925

# ================= قواعد البيانات المؤقتة =================
gm_instances = {} # حفظ كائن البريد لكل مستخدم
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

# ================= تصميم الأزرار الصلبة =================
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

    # 1. توليد بريد جديد باستخدام المكتبة الموثوقة
    if text in ["📨 إنشاء بريد عشوائي", "🗑️ تغيير البريد"]:
        bot.send_message(user_id, "⏳ جاري توليد بريد إلكتروني حقيقي...")
        try:
            # إنشاء كائن اتصال مستقل لكل مستخدم
            gm = GuerrillaMail()
            email = gm.get_email_address()
            
            if not email:
                raise Exception("API Error")
                
            gm_instances[user_id] = gm # حفظ كائن البريد للتحقق لاحقاً
            
            text_msg = f"✅ **تم إنشاء بريدك بنجاح:**\n\n`{email}`\n\n(اضغط على البريد لنسخه)\nاستخدم هذا البريد للتسجيل، ثم اضغط على زر فحص صندوق الوارد."
            bot.send_message(user_id, text_msg, reply_markup=email_menu(), parse_mode="Markdown")
            
        except Exception as e:
            bot.send_message(user_id, "⚠️ حدث خطأ في الاتصال بخادم الإيميلات. حاول مرة أخرى.")

    # 2. فحص صندوق الوارد واستقبال الرسائل
    elif text == "🔄 فحص صندوق الوارد":
        if user_id not in gm_instances:
            bot.send_message(user_id, "⚠️ لم تقم بإنشاء بريد بعد! اضغط على زر الإنشاء أولاً.")
            return
            
        bot.send_message(user_id, "⏳ جاري فحص صندوق الوارد...")
        gm = gm_instances[user_id]
        
        try:
            # جلب الرسائل مباشرة عبر المكتبة الرسمية
            emails = gm.get_inbox()
            
            if not emails:
                bot.send_message(user_id, "📭 صندوق الوارد فارغ. لم تصل أي رسائل حتى الآن.")
            else:
                for mail in emails:
                    sender = getattr(mail, 'sender', 'غير معروف')
                    subject = getattr(mail, 'subject', 'بدون عنوان')
                    body = getattr(mail, 'body', 'لا يوجد نص')
                    
                    # تنظيف وتنسيق المحتوى
                    clean_body = re.sub(r'<br\s*/?>', '\n', body, flags=re.IGNORECASE)
                    clean_body = re.sub(r'<[^>]+>', ' ', clean_body)
                    clean_body = html.unescape(clean_body).strip()
                    clean_body_escaped = html.escape(clean_body)
                    
                    msg_text = f"📨 <b>رسالة جديدة واردة!</b>\n\n<b>من:</b> <code>{html.escape(sender)}</code>\n<b>الموضوع:</b> {html.escape(subject)}\n\n<b>المحتوى:</b>\n{clean_body_escaped}"
                    bot.send_message(user_id, msg_text, parse_mode="HTML")
        
        except Exception as e:
            bot.send_message(user_id, "⚠️ حدث خطأ أثناء جلب الرسائل. حاول مجدداً.")

    elif text == "👨‍💻 المطور":
        bot.send_message(user_id, f"هذا البوت من تطوير قناتنا: {CHANNEL_USERNAME}\nللتواصل مع المطور: tg://user?id={ADMIN_ID}")

# ================= تشغيل البوت والخادم =================
if __name__ == "__main__":
    keep_alive()
    print("Bot is running with official GuerrillaMail library...")
    bot.infinity_polling(timeout=20, long_polling_timeout=5)





