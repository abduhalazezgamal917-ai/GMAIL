import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import time
import os
import threading
from keep_alive import keep_alive


# ================= الإعدادات الأساسية =================
# سيقوم Render بقراءة التوكن من المتغيرات البيئية
BOT_TOKEN = os.getenv("BOT_TOKEN") 
bot = telebot.TeleBot(BOT_TOKEN)

CHANNEL_USERNAME = "@ZenoX_Tools"
ADMIN_ID = 6043858925

# ================= خادم Flask لبقاء البوت يعمل على Render =================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================= قواعد البيانات المؤقتة =================
user_emails = {} # لتخزين البريد النشط لكل مستخدم
user_last_action = {} # للحد من الطلبات (Rate Limiting)

# ================= دوال مساعدة =================

# 1. التحقق من الاشتراك الإجباري
def check_subscription(user_id):
    if user_id == ADMIN_ID: # تجاوز الأدمن من الفحص
        return True
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        if status in ['member', 'administrator', 'creator']:
            return True
        return False
    except:
        # في حال لم يكن البوت مشرفاً في القناة
        return False

# 2. نظام الحد من الطلبات (Rate Limit)
def is_rate_limited(user_id):
    current_time = time.time()
    if user_id in user_last_action:
        # السماح بطلب واحد كل 3 ثوانٍ لحماية السيرفر
        if current_time - user_last_action[user_id] < 3:
            return True
    user_last_action[user_id] = current_time
    return False

# ================= أوامر البوت =================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # فحص الاشتراك
    if not check_subscription(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🌟 اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
        bot.send_message(user_id, "⚠️ **عذراً عزيزي!**\n\nيجب عليك الاشتراك في قناة البوت الرسمية لتتمكن من استخدامه.\nاشترك ثم اضغط على زر التحقق.", reply_markup=markup, parse_mode="Markdown")
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📨 إنشاء بريد عشوائي", callback_data="generate_email"))
    markup.add(InlineKeyboardButton("👨‍💻 المطور", url="tg://user?id=6043858925"))
    
    welcome_text = (
        "👋 **أهلاً بك في بوت البريد المؤقت الذكي!**\n\n"
        "أنا هنا لمساعدتك في إنشاء عناوين بريد إلكتروني وهمية بضغطة زر لحماية بريدك الأساسي من الرسائل المزعجة (Spam).\n\n"
        "👇 اضغط على الزر بالأسفل للبدء."
    )
    bot.reply_to(message, welcome_text, reply_markup=markup, parse_mode="Markdown")

# ================= التعامل مع الأزرار =================

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id

    # نظام الحماية من الضغط المستمر
    if is_rate_limited(user_id):
        bot.answer_callback_query(call.id, "⏳ يرجى الانتظار قليلاً بين الطلبات!", show_alert=True)
        return

    if call.data == "check_sub":
        if check_subscription(user_id):
            bot.answer_callback_query(call.id, "✅ تم التحقق بنجاح! يمكنك الآن استخدام البوت.", show_alert=True)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ لم تشترك في القناة بعد!", show_alert=True)

    elif call.data == "generate_email":
        # طلب بريد جديد من واجهة 1secmail
        req = requests.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1").json()
        email = req[0]
        user_emails[user_id] = email # حفظ البريد للمستخدم
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 فحص صندوق الوارد", callback_data="check_inbox"))
        markup.add(InlineKeyboardButton("🗑️ تغيير البريد", callback_data="generate_email"))
        
        text = f"✅ **تم إنشاء بريدك بنجاح:**\n\n`{email}`\n\n(اضغط على البريد لنسخه)\nاستخدم هذا البريد للتسجيل، ثم اضغط على فحص صندوق الوارد."
        
        # تعديل الرسالة السابقة بدلاً من إرسال رسالة جديدة لتجربة مستخدم أفضل
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "check_inbox":
        if user_id not in user_emails:
            bot.answer_callback_query(call.id, "⚠️ لم تقم بإنشاء بريد بعد!", show_alert=True)
            return
            
        email = user_emails[user_id]
        login, domain = email.split("@")
        
        # فحص الرسائل
        req = requests.get(f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}").json()
        
        if len(req) == 0:
            bot.answer_callback_query(call.id, "📭 صندوق الوارد فارغ. لم تصل أي رسائل بعد.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "📬 توجد رسائل جديدة!", show_alert=False)
            for msg in req:
                msg_id = msg['id']
                # جلب محتوى الرسالة
                read_msg = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}").json()
                
                sender = read_msg.get('from', 'غير معروف')
                subject = read_msg.get('subject', 'بدون عنوان')
                body = read_msg.get('textBody', 'لا يوجد نص')
                
                msg_text = f"📨 **رسالة جديدة!**\n\n**من:** `{sender}`\n**الموضوع:** {subject}\n\n**المحتوى:**\n{body}"
                bot.send_message(user_id, msg_text, parse_mode="Markdown")

# ================= تشغيل البوت والخادم =================
if __name__ == "__main__":
    # استدعاء السيرفر الوهمي لاستقبال النقرات
    keep_alive()
    
    print("Bot is running...")
    # تشغيل البوت
    bot.infinity_polling(timeout=10, long_polling_timeout=5)




