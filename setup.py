import os
import subprocess

def run_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"Executed: {command}")
    except subprocess.CalledProcessError as e:
        print(f"Error executing {command}: {e}")

if __name__ == "__main__":
    # Cài đặt thư viện telebot
    run_command("pip install telebot")

    run_command("pip install psutil")
    
    # Biên dịch file C++
    run_command("g++ -std=c++14 soul.cpp -o soul -pthread")
