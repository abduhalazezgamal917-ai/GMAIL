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
        # السماح بطلب كل 3 ثوانٍ
        if current_time - user_last_action[user_id] < 3:
            return True
    user_last_action[user_id] = current_time
    return False

# ================= تصميم الأزرار الصلبة (أسفل الشاشة) =================
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
        # ملاحظة: أزرار الروابط الإجبارية يجب أن تكون شفافة لأن الأزرار الصلبة لا تفتح روابط
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🌟 اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        bot.send_message(user_id, "⚠️ **عذراً عزيزي!**\n\nيجب عليك الاشتراك في القناة لتتمكن من استخدام البوت.\nبعد الاشتراك، أرسل /start مجدداً.", reply_markup=markup, parse_mode="Markdown")
        return

    welcome_text = (
        "👋 **أهلاً بك في بوت البريد المؤقت الذكي!**\n\n"
        "أنا هنا لمساعدتك في إنشاء عناوين بريد إلكتروني وهمية بضغطة زر لحماية بريدك الأساسي.\n\n"
        "👇 استخدم الأزرار التي ظهرت بالأسفل للبدء."
    )
    # إرسال الرسالة مع الأزرار الصلبة
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

    # التفاعل مع الأزرار الصلبة
    if text in ["📨 إنشاء بريد عشوائي", "🗑️ تغيير البريد"]:
        msg = bot.send_message(user_id, "⏳ جاري إنشاء بريد جديد وتجهيزه لك...")
        try:
            req = requests.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1", timeout=10).json()
            email = req[0]
            user_emails[user_id] = email 
            
            text_msg = f"✅ **تم إنشاء بريدك بنجاح:**\n\n`{email}`\n\n(اضغط على البريد لنسخه)\nاستخدم هذا البريد للتسجيل، ثم اضغط على زر فحص صندوق الوارد."
            bot.edit_message_text(chat_id=user_id, message_id=msg.message_id, text=text_msg, parse_mode="Markdown")
            
            # تغيير شكل الكيبورد لإظهار زر الفحص
            bot.send_message(user_id, "الخيارات المتاحة لك الآن:", reply_markup=email_menu())
            
        except requests.exceptions.RequestException:
            bot.edit_message_text(chat_id=user_id, message_id=msg.message_id, text="⚠️ **عذراً!** خادم الإيميلات الخارجي يواجه ضغطاً أو يرفض الاتصال حالياً. جرب مرة أخرى.")

    elif text == "🔄 فحص صندوق الوارد":
        if user_id not in user_emails:
            bot.send_message(user_id, "⚠️ لم تقم بإنشاء بريد بعد! اضغط على زر الإنشاء أولاً.")
            return
            
        msg = bot.send_message(user_id, "⏳ جاري الاتصال بالخادم لفحص الرسائل...")
        email = user_emails[user_id]
        login, domain = email.split("@")
        
        try:
            req = requests.get(f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}", timeout=10).json()
            
            if len(req) == 0:
                bot.edit_message_text(chat_id=user_id, message_id=msg.message_id, text="📭 صندوق الوارد فارغ. لم تصل أي رسائل حتى الآن.")
            else:
                bot.edit_message_text(chat_id=user_id, message_id=msg.message_id, text="📬 توجد رسائل جديدة، جاري جلبها لك...")
                for m in req:
                    msg_id = m['id']
                    read_msg = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}", timeout=10).json()
                    
                    sender = read_msg.get('from', 'غير معروف')
                    subject = read_msg.get('subject', 'بدون عنوان')
                    body = read_msg.get('textBody', 'لا يوجد نص')
                    
                    msg_text = f"📨 **رسالة جديدة!**\n\n**من:** `{sender}`\n**الموضوع:** {subject}\n\n**المحتوى:**\n{body}"
                    bot.send_message(user_id, msg_text, parse_mode="Markdown")
        
        except requests.exceptions.RequestException:
            bot.edit_message_text(chat_id=user_id, message_id=msg.message_id, text="⚠️ **حدث خطأ!** فشل الاتصال بخادم الرسائل.")

    elif text == "👨‍💻 المطور":
        bot.send_message(user_id, f"هذا البوت من تطوير قناتنا: {CHANNEL_USERNAME}\nللتواصل المباشر مع المطور: tg://user?id={ADMIN_ID}")

# ================= تشغيل البوت والخادم =================
if __name__ == "__main__":
    keep_alive()
    print("Bot is running with Reply Keyboards...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)



