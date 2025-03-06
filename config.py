import os
import logging
from logging.handlers import RotatingFileHandler
import sys

# Lấy Telegram Bot Token từ biến môi trường hoặc sử dụng giá trị mặc định
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")  # Nhớ thiết lập biến môi trường này

# Thông tin đăng nhập hệ thống TTVU từ biến môi trường
TTVU_USERNAME = os.environ.get("TTVU_USERNAME", "")  # Nhớ thiết lập biến môi trường này
TTVU_PASSWORD = os.environ.get("TTVU_PASSWORD", "")  # Nhớ thiết lập biến môi trường này

# Cài đặt thời gian làm mới token (25 phút = 1500 giây)
TOKEN_REFRESH_INTERVAL = 1500

# Chu kỳ kiểm tra thời khóa biểu để gửi thông báo (phút)
REMINDER_CHECK_INTERVAL = 300  # 5 phút

# Ánh xạ tiết học sang giờ thực
TIET_TO_HOUR_MAP = {
    1: "07:00",
    2: "07:50",
    3: "08:40",
    4: "10:30",
    5: "11:20",
    6: "13:00",
    7: "13:50",
    8: "14:40",
    9: "16:30",
    10: "17:20",
    11: "18:10",
    12: "19:00",
    13: "19:50"
}

# Đường dẫn file dữ liệu
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

# Tạo thư mục nếu chưa tồn tại
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Thiết lập logging
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_FILE = os.path.join(LOG_DIR, 'bot.log')

# Mức độ logging, đặt thành DEBUG để xem log chi tiết về quá trình đăng nhập
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Danh sách logger modules cần giảm mức độ log
REDUCED_LOGGERS = [
    'telegram.ext._application',
    'telegram.ext._updater',
    'telegram.bot',
    'httpx',
    'urllib3',
    'asyncio'
]

# Thiết lập logger chính
logger = logging.getLogger('tkb_bot')
logger.setLevel(getattr(logging, LOG_LEVEL))

# Xóa các handlers hiện có để tránh log bị trùng lặp
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Định dạng log
formatter = logging.Formatter(LOG_FORMAT)

# Handler cho file
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024*5, backupCount=3)  # 5MB mỗi file, giữ 3 file
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Handler cho console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Giảm mức độ log cho các module không cần thiết
for logger_name in REDUCED_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Kiểm tra các giá trị quan trọng
if not TELEGRAM_TOKEN:
    logger.critical("❌ TELEGRAM_TOKEN không được cung cấp. Hãy thiết lập biến môi trường TELEGRAM_TOKEN.")
    sys.exit(1)

if not TTVU_USERNAME or not TTVU_PASSWORD:
    logger.critical("❌ TTVU_USERNAME hoặc TTVU_PASSWORD không được cung cấp. Hãy thiết lập các biến môi trường này.")
    sys.exit(1)

# In thông tin cấu hình khi khởi động
logger.info(f"Mức độ log: {LOG_LEVEL}")