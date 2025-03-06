import json
import asyncio
import os
from config import logger, USERS_FILE

class UserManager:
    def __init__(self):
        self.registered_users = set()  # Sử dụng set để tránh trùng lặp và tìm kiếm nhanh
        self.save_interval = 3600  # Lưu dữ liệu 1 giờ một lần
    
    async def load_users(self):
        """Tải danh sách người dùng đã đăng ký từ file"""
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r') as file:
                    users_data = json.load(file)
                    # Chuyển đổi list thành set để xử lý hiệu quả
                    self.registered_users = set(users_data)
                logger.info(f"Đã tải {len(self.registered_users)} người dùng đã đăng ký từ file")
            else:
                logger.info("Không tìm thấy file dữ liệu người dùng, tạo danh sách mới")
                self.registered_users = set()
        except Exception as e:
            logger.error(f"Lỗi khi tải danh sách người dùng: {e}")
            self.registered_users = set()
    
    async def save_users(self):
        """Lưu danh sách người dùng đã đăng ký xuống file"""
        try:
            with open(USERS_FILE, 'w') as file:
                # Chuyển set thành list để lưu vào JSON
                json.dump(list(self.registered_users), file)
            logger.info(f"Đã lưu danh sách {len(self.registered_users)} người dùng đăng ký")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu danh sách người dùng: {e}")
            return False
    
    def register_user(self, user_id):
        """Đăng ký người dùng mới"""
        self.registered_users.add(user_id)
        return True
    
    def unregister_user(self, user_id):
        """Hủy đăng ký người dùng"""
        if user_id in self.registered_users:
            self.registered_users.remove(user_id)
            return True
        return False
    
    def is_user_registered(self, user_id):
        """Kiểm tra xem người dùng đã đăng ký hay chưa"""
        return user_id in self.registered_users
    
    async def start_periodic_save(self):
        """Lưu danh sách người dùng định kỳ"""
        while True:
            await asyncio.sleep(self.save_interval)
            await self.save_users()