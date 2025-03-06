import aiohttp
import asyncio
from datetime import datetime, timedelta
from config import TTVU_USERNAME, TTVU_PASSWORD, logger
from utils import get_vietnam_datetime

class TTVUClient:
    def __init__(self):
        self.access_token = None
        self.session_cookies = None
        self.last_login_time = None
        self.login_lock = asyncio.Lock()
        self.is_logging_in = False
        self._session = None  # Session HTTP hiện tại
        # Thời gian hết hạn cho phiên đăng nhập (phút)
        self.session_expiry_minutes = 20  # Giảm thời gian hết hạn xuống để đảm bảo làm mới trước khi thực sự hết hạn
    
    async def get_session(self):
        """
        Trả về session hiện tại hoặc tạo mới nếu cần
        """
        if self._session is None or self._session.closed:
            logger.debug("Tạo session HTTP mới")
            self._session = aiohttp.ClientSession()
            if self.session_cookies:
                self._session.cookie_jar.update_cookies(self.session_cookies)
        return self._session
    
    async def login(self, force=False):
        """
        Đăng nhập vào hệ thống TTVU và lấy token
        
        Args:
            force: Nếu True, sẽ bắt buộc đăng nhập mới ngay cả khi đã có phiên
        """
        # In ra thông tin debug về trạng thái phiên hiện tại
        has_valid = self.has_valid_session()
        if self.last_login_time:
            current_time = get_vietnam_datetime()
            time_diff = (current_time - self.last_login_time).total_seconds() / 60
            logger.debug(f"Trạng thái phiên: valid={has_valid}, token={bool(self.access_token)}, "
                        f"last_login={self.last_login_time.strftime('%H:%M:%S')}, "
                        f"time_since_login={time_diff:.1f} phút")
        
        # Kiểm tra xem đã có phiên đăng nhập hợp lệ hay chưa
        if not force and has_valid:
            logger.debug("Sử dụng phiên đăng nhập hiện có")
            return None, True
        
        # Tránh nhiều yêu cầu đăng nhập đồng thời
        async with self.login_lock:
            # Kiểm tra lại sau khi có được khóa (để tránh đăng nhập nhiều lần)
            if not force and self.has_valid_session():
                logger.debug("Sử dụng phiên đăng nhập hiện có (sau khi lấy lock)")
                return None, True
            
            # Đánh dấu đang trong quá trình đăng nhập
            self.is_logging_in = True
            
            # Đóng session cũ nếu có
            await self.close_session()
            
            # Tạo session mới
            session = await self.get_session()
            
            try:
                logger.info("📝 Bắt đầu quá trình đăng nhập TTVU...")
                
                # Truy cập trang đăng nhập trước để lấy cookies ban đầu
                await session.get("https://ttsv.tvu.edu.vn/")
                
                # Thực hiện đăng nhập
                login_response = await session.post(
                    "https://ttsv.tvu.edu.vn/api/auth/login",
                    data={
                        "username": TTVU_USERNAME,
                        "password": TTVU_PASSWORD,
                        "grant_type": "password"
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                    },
                )
                
                data = await login_response.json()
                
                if "access_token" in data:
                    self.access_token = data["access_token"]
                    # Lưu cookies của phiên đăng nhập
                    self.session_cookies = session.cookie_jar.filter_cookies("https://ttsv.tvu.edu.vn")
                    # Cập nhật thời gian đăng nhập gần nhất
                    self.last_login_time = get_vietnam_datetime()
                    
                    logger.info(f"✅ Đăng nhập TTVU thành công! (thời gian: {self.last_login_time.strftime('%H:%M:%S')})")
                    return None, True
                else:
                    logger.error(f"❌ Đăng nhập thất bại! Response: {data}")
                    return None, False

            except Exception as e:
                logger.error(f"❌ Lỗi đăng nhập TTVU: {e}")
                return None, False
            finally:
                # Hủy đánh dấu đang đăng nhập
                self.is_logging_in = False
    
    async def close_session(self):
        """Đóng session hiện tại nếu nó tồn tại và đang mở"""
        if self._session and not self._session.closed:
            logger.debug("Đóng session HTTP hiện tại")
            await self._session.close()
            self._session = None
    
    def has_valid_session(self):
        """Kiểm tra xem đã có phiên đăng nhập hợp lệ hay chưa"""
        # Kiểm tra xem có tất cả các thông tin đăng nhập hay không
        if not self.access_token or not self.last_login_time:
            return False
        
        # Phiên còn hiệu lực trong khoảng thời gian đã định
        current_time = get_vietnam_datetime()
        session_age = current_time - self.last_login_time
        is_valid = session_age < timedelta(minutes=self.session_expiry_minutes)
        
        # Log ra thời gian còn lại của phiên nếu đang gần hết hạn
        remaining_minutes = self.session_expiry_minutes - (session_age.total_seconds() / 60)
        if is_valid and remaining_minutes < 5:
            logger.debug(f"Phiên đăng nhập còn {remaining_minutes:.1f} phút trước khi hết hạn")
        
        return is_valid
    
    async def get_tkb(self):
        """Lấy thời khóa biểu từ hệ thống TTVU"""
        # Kiểm tra phiên đăng nhập
        if not self.has_valid_session():
            # Nếu chưa đăng nhập hoặc phiên đã hết hạn, đăng nhập lại
            logger.debug("Phiên đăng nhập không hợp lệ hoặc đã hết hạn")
            _, login_success = await self.login()
            if not login_success:
                logger.error("❌ Không thể đăng nhập để lấy thời khóa biểu!")
                return None
        else:
            logger.debug("Sử dụng phiên đăng nhập hiện có cho yêu cầu TKB")
        
        # Lấy session hiện tại
        session = await self.get_session()
        
        try:
            # Gửi yêu cầu lấy thời khóa biểu
            logger.debug("Gửi yêu cầu lấy thời khóa biểu")
            response = await session.post(
                "https://ttsv.tvu.edu.vn/api/sch/w-locdstkbtuanusertheohocky",
                json={
                    "filter": {"hoc_ky": 20242, "ten_hoc_ky": ""},
                    "additional": {
                        "paging": {"limit": 100, "page": 1},
                        "ordering": [{"name": None, "order_type": None}],
                    },
                },
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                    "Referer": "https://ttsv.tvu.edu.vn/",
                    "Origin": "https://ttsv.tvu.edu.vn"
                },
            )
            
            # Kiểm tra phản hồi
            if response.status == 401 or response.status == 403:
                logger.warning(f"⚠️ Token hết hạn (Lỗi {response.status}), đang đăng nhập lại...")
                
                # Bắt buộc đăng nhập mới
                _, login_success = await self.login(force=True)
                if not login_success:
                    return None
                
                # Thử lại sau khi đăng nhập
                return await self.get_tkb()
            
            # Đảm bảo phản hồi là JSON
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                text = await response.text()
                logger.error(f"❌ API trả về không phải JSON: {content_type}")
                logger.debug(f"Nội dung phản hồi: {text[:200]}...")
                
                # Bắt buộc đăng nhập mới
                _, login_success = await self.login(force=True)
                if not login_success:
                    return None
                
                # Thử lại sau khi đăng nhập
                return await self.get_tkb()
            
            logger.debug("Đã nhận được dữ liệu thời khóa biểu thành công")
            data = await response.json()
            return data.get("data", {})
        
        except Exception as e:
            logger.error(f"❌ Lỗi lấy thời khóa biểu: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def refresh_token(self):
        """Làm mới token định kỳ"""
        logger.info("🔄 Đang làm mới token TTVU định kỳ...")
        _, login_success = await self.login(force=True)
        return login_success
    
    async def cleanup(self):
        """Dọn dẹp tài nguyên khi đóng ứng dụng"""
        await self.close_session()