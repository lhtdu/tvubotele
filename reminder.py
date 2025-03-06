import asyncio
from datetime import datetime, timedelta
from config import logger, REMINDER_CHECK_INTERVAL
from utils import tiet_to_hour, get_vietnam_datetime, get_vietnam_date

class ReminderService:
    def __init__(self, ttvu_client, user_manager):
        self.ttvu_client = ttvu_client
        self.user_manager = user_manager
        self.application = None
        self.last_reminder_check = None
        self.last_reminder_sent = {}
    
    def set_application(self, application):
        """Thiết lập đối tượng application của bot"""
        self.application = application
    
    async def check_and_send_reminders(self):
        """Kiểm tra và gửi thông báo nhắc nhở"""
        # Đợi một chút để đảm bảo khởi động ổn định
        await asyncio.sleep(10)
        
        while True:
            try:
                # Nếu không có người dùng đăng ký, bỏ qua
                if not self.user_manager.registered_users:
                    await asyncio.sleep(60)  # Đợi 1 phút và kiểm tra lại
                    continue

                # Lấy thời gian hiện tại theo múi giờ Việt Nam
                current_time = get_vietnam_datetime()
                
                # Tránh kiểm tra quá thường xuyên 
                if self.last_reminder_check and (current_time - self.last_reminder_check).total_seconds() < 60:
                    await asyncio.sleep(60)
                    continue
                    
                self.last_reminder_check = current_time
                logger.info(f"Đang kiểm tra thời khóa biểu để gửi thông báo... (Thời gian VN: {current_time.strftime('%d/%m/%Y %H:%M:%S')})")
                
                # Lấy ngày hiện tại theo múi giờ Việt Nam
                today = current_time.strftime("%Y-%m-%d")
                
                # Lấy thời khóa biểu
                tkb_data = await self.ttvu_client.get_tkb()
                
                if not tkb_data or "ds_tuan_tkb" not in tkb_data:
                    logger.error("Không thể lấy thời khóa biểu để gửi thông báo!")
                    await asyncio.sleep(300)  # Đợi 5 phút và thử lại
                    continue
                
                # Tìm các môn học trong ngày
                for tuan in tkb_data["ds_tuan_tkb"]:
                    for mon in tuan["ds_thoi_khoa_bieu"]:
                        if mon["ngay_hoc"].startswith(today):
                            # Tạo ID duy nhất cho môn học này trong ngày
                            mon_id = f"{mon.get('ngay_hoc', today)}_{mon.get('ten_mon', 'unknown')}_{mon.get('tiet_bat_dau', 0)}"
                            
                            # Kiểm tra xem đã gửi thông báo cho môn này chưa
                            if mon_id in self.last_reminder_sent:
                                continue
                            
                            # Lấy giờ bắt đầu của môn học
                            tiet_bat_dau = mon.get("tiet_bat_dau")
                            if not isinstance(tiet_bat_dau, int):
                                try:
                                    tiet_bat_dau = int(tiet_bat_dau)
                                except (ValueError, TypeError):
                                    logger.error(f"Lỗi: tiet_bat_dau không phải số nguyên: {tiet_bat_dau}")
                                    continue
                                    
                            start_time = tiet_to_hour(tiet_bat_dau)
                            
                            # Chuyển đổi sang datetime object (sử dụng ngày hiện tại từ múi giờ Việt Nam)
                            try:
                                hour, minute = map(int, start_time.split(":"))
                                class_time = datetime(
                                    current_time.year, 
                                    current_time.month, 
                                    current_time.day, 
                                    hour, 
                                    minute, 
                                    tzinfo=current_time.tzinfo  # Sử dụng cùng múi giờ
                                )
                                
                                # Tính khoảng thời gian còn lại đến khi bắt đầu học
                                time_until_class = (class_time - current_time).total_seconds() / 60  # phút
                                
                                # Kiểm tra nếu còn 60-65 phút nữa là đến giờ học
                                if 60 <= time_until_class <= 65:
                                    # Gửi thông báo và đánh dấu đã gửi
                                    await self.send_reminder(mon, start_time)
                                    self.last_reminder_sent[mon_id] = current_time
                                    logger.info(f"Đã đánh dấu đã gửi thông báo cho môn: {mon.get('ten_mon', 'unknown')} - {mon_id}")
                            except Exception as e:
                                logger.error(f"Lỗi khi xử lý thời gian học: {e}")
                                continue
                
                # Xóa các bản ghi cũ
                self._cleanup_old_reminders()
                
                # Đợi trước khi kiểm tra lại
                await asyncio.sleep(REMINDER_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Lỗi trong quá trình kiểm tra và gửi thông báo: {e}")
                import traceback
                logger.error(f"Chi tiết lỗi: {traceback.format_exc()}")
                await asyncio.sleep(300)  # Đợi 5 phút trước khi thử lại
    
    def _cleanup_old_reminders(self):
        """Xóa các bản ghi thông báo cũ (từ hôm qua trở về trước)"""
        current_date = get_vietnam_date()
        keys_to_remove = [k for k in self.last_reminder_sent.keys() if not k.startswith(current_date)]
        for k in keys_to_remove:
            del self.last_reminder_sent[k]
            
    async def send_reminder(self, mon, start_time):
        """Gửi thông báo nhắc nhở cho tất cả người dùng đã đăng ký"""
        if not self.application:
            logger.error("❌ Chưa thiết lập application cho reminder!")
            return
        
        try:
            # Lấy thông tin môn học một cách an toàn
            ten_mon = mon.get('ten_mon', 'Không có tên')
            ma_phong = mon.get('ma_phong', 'Không xác định')
            ten_giang_vien = mon.get('ten_giang_vien', 'Không xác định')
            
            # Tạo thông báo
            reminder_text = (
                f"⏰ *NHẮC NHỞ*: Còn 1 tiếng nữa là đến giờ học!\n\n"
                f"📚 Môn: *{ten_mon}*\n"
                f"⏰ Thời gian: {start_time}\n"
                f"🏫 Phòng: {ma_phong}\n"
                f"👨‍🏫 Giảng viên: {ten_giang_vien}"
            )
            
            logger.info(f"Đang gửi thông báo cho {len(self.user_manager.registered_users)} người dùng về môn {ten_mon}")
            
            # Tạo bản sao danh sách người dùng để tránh lỗi khi danh sách thay đổi trong quá trình gửi
            registered_users_copy = list(self.user_manager.registered_users)
            
            # Gửi thông báo cho tất cả người dùng đã đăng ký
            for user_id in registered_users_copy:
                try:
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=reminder_text,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Đã gửi nhắc nhở cho người dùng {user_id} về môn {ten_mon}")
                except Exception as e:
                    logger.error(f"Lỗi gửi thông báo cho người dùng {user_id}: {e}")
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo: {e}")