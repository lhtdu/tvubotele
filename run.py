#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import asyncio

# Tải biến môi trường từ file .env
load_dotenv()

# Kiểm tra xem các biến cần thiết đã được thiết lập chưa
required_vars = ["TELEGRAM_TOKEN", "TTVU_USERNAME", "TTVU_PASSWORD"]
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    print(f"❌ Thiếu các biến môi trường sau: {', '.join(missing_vars)}")
    print("Hãy thiết lập các biến này trong file .env hoặc biến môi trường hệ thống.")
    exit(1)

# Nhập và chạy file main
from main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot đã dừng.")