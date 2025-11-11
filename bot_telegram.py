# -*- coding: utf-8 -*-
import telebot
from telebot import types
import pandas as pd
from datetime import datetime, timedelta
import schedule
import time
import os

# ===== إعداد البوت =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8595026017:AAGtIq5yu8zbvTquQKx1aTzsPlzjQvuAoJo')
ADMIN_ID = ['1779449528','5738232749']
bot = telebot.TeleBot(BOT_TOKEN)

CSV_FILE = 'subscribers.csv'
DEFAULT_DURATION = 30

if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=['الاسم','تاريخ الانضمام','مدة الاشتراك','تاريخ الانتهاء','حالة الاشتراك'])
    df.to_csv(CSV_FILE, index=False)

# ===== دوال مساعدة =====
def calculate_end_date(start_date, duration_days):
    return start_date + timedelta(days=int(duration_days))

def subscription_status(end_date):
    today = datetime.now().date()
    days_left = (end_date.date() - today).days
    if days_left < 0:
        return "❌ منتهي"
    elif days_left <= 3:
        return "⚠️ قريب الانتهاء"
    else:
        return "✅ نشط"

def load_data():
    return pd.read_csv(CSV_FILE)

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

# ===== فحص الاشتراكات =====
def check_subscriptions():
    df = load_data()
    today = datetime.now().date()
    report = ""
    for index, row in df.iterrows():
        end_date = datetime.strptime(row['تاريخ الانتهاء'], "%Y-%m-%d")
        status = subscription_status(end_date)
        df.at[index, 'حالة الاشتراك'] = status
        days_left = (end_date.date() - today).days
        if 0 <= days_left <= 3:
            bot.send_message(ADMIN_ID, f"⚠️ تنبيه: اشتراك {row['الاسم']} سينتهي بعد {days_left} يوم.")
        report += f"{row['الاسم']:<10} | {row['تاريخ الانتهاء']} | {status}\n"
    save_data(df)
    bot.send_message(ADMIN_ID, f"📋 تقرير اليومي للمشتركين:\n{report}")

# ===== القائمة الاحترافية =====
def main_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🆕 إضافة مشترك", callback_data="add"),
        types.InlineKeyboardButton("📋 عرض المشتركين", callback_data="list"),
        types.InlineKeyboardButton("✏️ تحديث الاشتراك", callback_data="update"),
        types.InlineKeyboardButton("🗑 حذف مشترك", callback_data="delete"),
        types.InlineKeyboardButton("🔍 بحث عن مشترك", callback_data="search"),
        types.InlineKeyboardButton("⚠️ قريب الانتهاء", callback_data="near_end"),
        types.InlineKeyboardButton("💾 النسخ الاحتياطي", callback_data="backup"),
        types.InlineKeyboardButton("📈 تقرير اليومي", callback_data="report")
    )
    bot.send_message(chat_id, "📊 OSM Smart Subscription Bot\nمرحبًا أسامة! اختر العملية:", reply_markup=markup)

# ===== بدء البوت =====
@bot.message_handler(commands=['start'])
def send_welcome(message):
    main_menu(message.chat.id)

# ===== التعامل مع الأزرار =====
selected_for_delete = []

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global selected_for_delete
    chat_id = call.message.chat.id

    if call.data == "add":
        msg = bot.send_message(chat_id, "👤 اكتب اسم المشترك الجديد:")
        bot.register_next_step_handler(msg, add_subscriber)

    elif call.data == "list":
        df = load_data()
        if df.empty:
            bot.send_message(chat_id, "لا يوجد مشتركين حتى الآن.")
        else:
            reply = "📋 قائمة المشتركين:\n\n"
            reply += "الاسم       | انتهاء     | الحالة\n"
            reply += "-------------------------------\n"
            for i, row in df.iterrows():
                reply += f"{row['الاسم']:<10} | {row['تاريخ الانتهاء']} | {row['حالة الاشتراك']}\n"
            bot.send_message(chat_id, reply)
        main_menu(chat_id)

    elif call.data == "update":
        df = load_data()
        if df.empty:
            bot.send_message(chat_id, "لا يوجد مشتركين للتحديث.")
            main_menu(chat_id)
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        for name in df['الاسم']:
            markup.add(types.InlineKeyboardButton(name, callback_data=f"update_{name}"))
        bot.send_message(chat_id, "✏️ اختر المشترك لتحديث اشتراكه:", reply_markup=markup)

    elif call.data.startswith("update_"):
        name = call.data.replace("update_", "")
        msg = bot.send_message(chat_id,
                               f"✏️ تحديث الاشتراك للمشترك {name}\n"
                               f"إذا أردت زيادة، ضع الرقم موجبًا (+)\n"
                               f"إذا أردت نقص، ضع الرقم سالبًا (-)\n"
                               f"اكتب الرقم الآن:")
        bot.register_next_step_handler(msg, lambda m: apply_custom_update(name, m))

    elif call.data == "delete":
        df = load_data()
        if df.empty:
            bot.send_message(chat_id, "لا يوجد مشتركين للحذف.")
            main_menu(chat_id)
            return
        selected_for_delete = []
        markup = types.InlineKeyboardMarkup(row_width=1)
        for name in df['الاسم']:
            markup.add(types.InlineKeyboardButton(f"{name} ✅", callback_data=f"toggle_{name}"))
        markup.add(types.InlineKeyboardButton("حذف المحددين 🗑", callback_data="delete_selected"))
        markup.add(types.InlineKeyboardButton("🏠 العودة للقائمة الرئيسية", callback_data="cancel"))
        bot.send_message(chat_id, "🗑 اختر المشتركين للحذف (يمكن اختيار أكثر من مشترك):", reply_markup=markup)

    elif call.data.startswith("toggle_"):
        name = call.data.replace("toggle_", "")
        if name in selected_for_delete:
            selected_for_delete.remove(name)
        else:
            selected_for_delete.append(name)
        df = load_data()
        markup = types.InlineKeyboardMarkup(row_width=1)
        for n in df['الاسم']:
            mark = " ✅" if n in selected_for_delete else ""
            markup.add(types.InlineKeyboardButton(f"{n}{mark}", callback_data=f"toggle_{n}"))
        markup.add(types.InlineKeyboardButton("حذف المحددين 🗑", callback_data="delete_selected"))
        markup.add(types.InlineKeyboardButton("🏠 العودة للقائمة الرئيسية", callback_data="cancel"))
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)

    elif call.data == "delete_selected":
        if not selected_for_delete:
            bot.send_message(chat_id, "❌ لم يتم اختيار أي مشتركين للحذف.")
        else:
            msg = bot.send_message(chat_id, f"⚠️ هل أنت متأكد من حذف: {', '.join(selected_for_delete)}؟ (اكتب نعم لتأكيد)")
            bot.register_next_step_handler(msg, confirm_delete)

    elif call.data == "search":
        msg = bot.send_message(chat_id, "🔍 اكتب اسم المشترك أو جزء منه للبحث:")
        bot.register_next_step_handler(msg, search_subscriber)

    elif call.data == "near_end":
        df = load_data()
        today = datetime.now().date()
        near_end = df[df['تاريخ الانتهاء'].apply(lambda x: 0 <= (datetime.strptime(x, "%Y-%m-%d").date()-today).days <= 3)]
        if near_end.empty:
            bot.send_message(chat_id, "✅ لا يوجد مشتركين قريبين من الانتهاء.")
        else:
            reply = "⚠️ المشتركين القريبين من الانتهاء:\n\n"
            reply += "الاسم       | انتهاء     | الحالة\n"
            reply += "-------------------------------\n"
            for i, row in near_end.iterrows():
                reply += f"{row['الاسم']:<10} | {row['تاريخ الانتهاء']} | {row['حالة الاشتراك']}\n"
            bot.send_message(chat_id, reply)
        main_menu(chat_id)

    elif call.data == "backup":
        df = load_data()
        backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(backup_file, index=False)
        bot.send_message(chat_id, f"💾 تم إنشاء نسخة احتياطية: {backup_file}")
        main_menu(chat_id)

    elif call.data == "report":
        check_subscriptions()
        bot.send_message(chat_id, "✅ تم إرسال التقرير اليومي.")
        main_menu(chat_id)

    elif call.data == "cancel":
        main_menu(chat_id)

# ===== إضافة مشترك =====
def add_subscriber(message):
    try:
        name = message.text.strip()
        start_date = datetime.now().date()
        duration = DEFAULT_DURATION
        end_date = calculate_end_date(start_date, duration).strftime("%Y-%m-%d")
        status = subscription_status(datetime.strptime(end_date, "%Y-%m-%d"))

        df = load_data()
        df = pd.concat([df, pd.DataFrame([[name, start_date.strftime("%Y-%m-%d"), duration, end_date, status]],
                                         columns=df.columns)], ignore_index=True)
        save_data(df)

        bot.send_message(message.chat.id,
                         f"✅ تم إضافة المشترك {name} بنجاح!\n📅 انتهاء الاشتراك: {end_date}\nحالة الاشتراك: {status}")
        main_menu(message.chat.id)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
        main_menu(message.chat.id)

# ===== تطبيق التحديث المرن =====
def apply_custom_update(name, message):
    try:
        change = int(message.text.strip())
        df = load_data()
        found = False
        for index, row in df.iterrows():
            if row['الاسم'] == name:
                end_date = datetime.strptime(row['تاريخ الانتهاء'], "%Y-%m-%d")
                new_end = calculate_end_date(end_date, change)
                df.at[index, 'تاريخ الانتهاء'] = new_end.strftime("%Y-%m-%d")
                df.at[index, 'مدة الاشتراك'] += change
                df.at[index, 'حالة الاشتراك'] = subscription_status(new_end)
                bot.send_message(message.chat.id,
                                 f"✅ تم تعديل اشتراك {name} بمقدار {change} يوم.\n📅 انتهاء جديد: {new_end.strftime('%Y-%m-%d')}\nحالة الاشتراك: {df.at[index, 'حالة الاشتراك']}")
                found = True
                break
        if not found:
            bot.send_message(message.chat.id, "❌ لم يتم العثور على المشترك بالاسم المدخل.")
        save_data(df)
        main_menu(message.chat.id)
    except:
        bot.send_message(message.chat.id, "❌ تأكد من كتابة رقم صحيح (+ أو -).")
        main_menu(message.chat.id)

# ===== تأكيد حذف متعدد =====
def confirm_delete(message):
    global selected_for_delete
    if message.text.strip().lower() == "نعم":
        df = load_data()
        df = df[~df['الاسم'].isin(selected_for_delete)]
        save_data(df)
        bot.send_message(message.chat.id, f"🗑 تم حذف المشتركين: {', '.join(selected_for_delete)}")
    else:
        bot.send_message(message.chat.id, "❌ تم إلغاء عملية الحذف.")
    selected_for_delete = []
    main_menu(message.chat.id)

# ===== البحث عن مشترك =====
def search_subscriber(message):
    query = message.text.strip().lower()
    df = load_data()
    results = df[df['الاسم'].str.lower().str.contains(query)]
    if results.empty:
        bot.send_message(message.chat.id, "❌ لم يتم العثور على أي مشترك يطابق البحث.")
    else:
        reply = "🔍 نتائج البحث:\n\n"
        reply += "الاسم       | انتهاء     | الحالة\n"
        reply += "-------------------------------\n"
        for i, row in results.iterrows():
            reply += f"{row['الاسم']:<10} | {row['تاريخ الانتهاء']} | {row['حالة الاشتراك']}\n"
        bot.send_message(message.chat.id, reply)
    main_menu(message.chat.id)

# ===== جدولة التنبيهات =====
# schedule.every().day.at("09:00").do(check_subscriptions)
# ===== تشغيل البوت =====
if __name__ == "__main__":
    print("🚀 البوت بدأ العمل...")

    bot.infinity_polling(timeout=10, long_polling_timeout=5)
