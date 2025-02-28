import telebot
import subprocess
import threading
import psutil
import time
import os
from datetime import datetime, timedelta

TOKEN = "7656031517:AAFSYcm8x17xafPqA1d9Gl0u-znGVnjkkFU"
ADMIN_ID = 7088683094  # Thay bằng ID admin của bạn
USER_FILE = "users.txt"
GROUP_FILE = "groups.txt"

bot = telebot.TeleBot(TOKEN)

running_attacks = {}
allowed_users = {}  # {user_id: expiry_date}
allowed_groups = {}  # {group_id: expiry_date}
last_attack_time = {}  # {user_id: last_attack_time}
ATTACK_COOLDOWN = 120  # Giới hạn 2 phút (120 giây) / lần attack
DEFAULT_THREADS = "100"  # Số luồng mặc định

# 📌 Load dữ liệu từ file khi bot khởi động
def load_data():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            for line in f:
                user_id, expiry_date = line.strip().split(",")
                allowed_users[int(user_id)] = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")

    if os.path.exists(GROUP_FILE):
        with open(GROUP_FILE, "r") as f:
            for line in f:
                group_id, expiry_date = line.strip().split(",")
                allowed_groups[int(group_id)] = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")

# 📌 Lưu dữ liệu vào file
def save_data():
    with open(USER_FILE, "w") as f:
        for user_id, expiry_date in allowed_users.items():
            f.write(f"{user_id},{expiry_date.strftime('%Y-%m-%d %H:%M:%S')}\n")

    with open(GROUP_FILE, "w") as f:
        for group_id, expiry_date in allowed_groups.items():
            f.write(f"{group_id},{expiry_date.strftime('%Y-%m-%d %H:%M:%S')}\n")

# 📌 Xóa user/group hết hạn
def check_expired_access():
    current_time = datetime.now()
    expired_users = [user for user, exp in allowed_users.items() if exp < current_time]
    expired_groups = [group for group, exp in allowed_groups.items() if exp < current_time]

    for user in expired_users:
        del allowed_users[user]
    
    for group in expired_groups:
        del allowed_groups[group]

    save_data()  # Cập nhật file

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
        save_data()
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
            save_data()
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
        save_data()
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
            save_data()
            bot.send_message(message.chat.id, f"✅ Nhóm `{group_id}` đã bị xóa khỏi danh sách sử dụng bot.", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Nhóm này không có trong danh sách.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Lỗi! Hãy nhập đúng định dạng.")

# 🚀 Chạy bot
def main():
    load_data()  # Load dữ liệu khi khởi động bot
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
                
