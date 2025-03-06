import pytz
from datetime import datetime, timedelta
import re

# Múi giờ Việt Nam
VN_TIMEZONE = pytz.timezone('Asia/Ho_Chi_Minh')

def get_vietnam_datetime():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam"""
    return datetime.now(VN_TIMEZONE)

def get_vietnam_datetime_formatted():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam dưới dạng chuỗi có định dạng"""
    return get_vietnam_datetime().strftime("%d/%m/%Y %H:%M:%S")

def get_vietnam_date():
    """Lấy ngày hiện tại theo múi giờ Việt Nam với định dạng YYYY-MM-DD"""
    return get_vietnam_datetime().strftime("%Y-%m-%d")

def tiet_to_hour(tiet):
    """Chuyển đổi từ số tiết sang giờ học"""
    from config import TIET_TO_HOUR_MAP
    return TIET_TO_HOUR_MAP.get(tiet, "Không xác định")

def validate_date_format(date_string):
    """
    Kiểm tra và chuyển đổi định dạng ngày
    Hỗ trợ các định dạng:
    - YYYY-MM-DD
    - DD/MM/YYYY
    
    Trả về định dạng chuẩn YYYY-MM-DD hoặc None nếu không hợp lệ
    """
    # Mẫu cho định dạng YYYY-MM-DD
    if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', date_string):
        try:
            # Tách các phần
            year, month, day = map(int, date_string.split('-'))
            
            # Kiểm tra tính hợp lệ
            if 1 <= month <= 12 and 1 <= day <= 31:
                # Định dạng lại để đảm bảo 2 chữ số cho tháng và ngày
                return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return None
    
    # Mẫu cho định dạng DD/MM/YYYY
    elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_string):
        try:
            # Tách các phần
            day, month, year = map(int, date_string.split('/'))
            
            # Kiểm tra tính hợp lệ
            if 1 <= month <= 12 and 1 <= day <= 31:
                # Chuyển sang định dạng YYYY-MM-DD
                return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return None
    
    return None

def format_tkb_message(tkb_data, requested_date):
    """Định dạng tin nhắn thời khóa biểu cho ngày cụ thể"""
    if not tkb_data or "ds_tuan_tkb" not in tkb_data:
        return "❌ Không thể lấy thông tin thời khóa biểu!", False
    
    # Tìm các môn học trong ngày yêu cầu
    found_classes = []
    
    for tuan in tkb_data["ds_tuan_tkb"]:
        for mon in tuan["ds_thoi_khoa_bieu"]:
            # Chỉ lấy phần ngày từ ngày học (bỏ giờ)
            if "ngay_hoc" in mon and mon["ngay_hoc"]:
                ngay_hoc = mon["ngay_hoc"].split('T')[0]
                
                # So sánh với ngày yêu cầu
                if ngay_hoc == requested_date:
                    found_classes.append(mon)
    
    # Sắp xếp theo tiết học
    found_classes.sort(key=lambda x: x.get("tiet_bat_dau", 0))
    
    # Không có lớp nào trong ngày này
    if not found_classes:
        return None, False
    
    # Định dạng ngày hiển thị
    display_date = datetime.strptime(requested_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    
    # Xây dựng tin nhắn
    message = f"📅 *Thời khóa biểu ngày {display_date}*\n\n"
    
    for i, lop in enumerate(found_classes, 1):
        # Lấy thông tin
        ten_mon = lop.get("ten_mon", "Không có tên")
        tiet_bat_dau = lop.get("tiet_bat_dau", "?")
        so_tiet = lop.get("so_tiet", "?")
        tiet_ket_thuc = int(tiet_bat_dau) + int(so_tiet) - 1 if isinstance(tiet_bat_dau, int) and isinstance(so_tiet, int) else "?"
        ma_phong = lop.get("ma_phong", "Không xác định")
        ten_giang_vien = lop.get("ten_giang_vien", "Không xác định")
        
        # Thời gian học
        gio_bat_dau = tiet_to_hour(tiet_bat_dau if isinstance(tiet_bat_dau, int) else 0)
        gio_ket_thuc = tiet_to_hour(tiet_ket_thuc if isinstance(tiet_ket_thuc, int) else 0)
        
        # Thông tin phòng, tiết học
        if isinstance(tiet_bat_dau, int) and isinstance(tiet_ket_thuc, int) and tiet_bat_dau == tiet_ket_thuc:
            thong_tin_tiet = f"Tiết {tiet_bat_dau}"
        else:
            thong_tin_tiet = f"Tiết {tiet_bat_dau}-{tiet_ket_thuc}"
        
        # Thêm vào tin nhắn
        message += f"🔸 *Môn {i}: {ten_mon}*\n"
        message += f"⏰ {gio_bat_dau} - {gio_ket_thuc} ({thong_tin_tiet})\n"
        message += f"🏫 Phòng: {ma_phong}\n"
        message += f"👨‍🏫 GV: {ten_giang_vien}\n\n"
    
    return message, True