from utils import get_vietnam_date, get_vietnam_datetime, format_tkb_message, validate_date_format
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from config import logger

class BotCommands:
    def __init__(self, ttvu_client, user_manager):
        self.ttvu_client = ttvu_client
        self.user_manager = user_manager
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /start"""
        user_first_name = update.effective_user.first_name
        welcome_text = (
            f"👋 Xin chào {user_first_name}!\n\n"
            "🤖 Đây là bot thông báo thời khóa biểu TVU.\n\n"
            "Bạn có thể sử dụng các nút bên dưới hoặc các lệnh:\n"
            "/help - Xem trợ giúp\n"
            "/dangky - Đăng ký nhận thông báo nhắc nhở\n"
            "/tkb - Xem thời khóa biểu hôm nay"
        )
        
        # Tạo bàn phím với nút bấm
        keyboard = [
            [KeyboardButton("📚 Thời khóa biểu hôm nay"), KeyboardButton("🔍 Xem TKB ngày khác")],
            [KeyboardButton("✅ Đăng ký nhận thông báo"), KeyboardButton("❌ Hủy đăng ký")],
            [KeyboardButton("ℹ️ Trợ giúp")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /help"""
        help_text = (
            "🤖 *Bot thông báo TKB TVU*\n\n"
            "*Các chức năng có sẵn:*\n\n"
            "📚 *Thời khóa biểu hôm nay* - Xem thời khóa biểu ngày hôm nay\n\n"
            "🔍 *Xem TKB ngày khác* - Chọn ngày khác để xem thời khóa biểu\n\n"
            "✅ *Đăng ký nhận thông báo* - Đăng ký để nhận thông báo trước giờ học 1 tiếng\n\n"
            "❌ *Hủy đăng ký* - Hủy đăng ký nhận thông báo\n\n"
            "ℹ️ *Trợ giúp* - Hiển thị hướng dẫn này\n\n"
            "⚠️ Bot sẽ tự động gửi thông báo trước 1 tiếng khi có tiết học (nếu bạn đã đăng ký)"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def register_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh đăng ký"""
        chat_id = update.effective_chat.id
        self.user_manager.register_user(chat_id)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Bạn đã đăng ký nhận thông báo nhắc nhở tiết học thành công!"
        )
        logger.info(f"Người dùng {chat_id} đã đăng ký nhận thông báo")
        
        # Lưu ngay khi có thay đổi
        await self.user_manager.save_users()
    
    async def unregister_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh hủy đăng ký"""
        chat_id = update.effective_chat.id
        success = self.user_manager.unregister_user(chat_id)
        
        if success:
            await context.bot.send_message(
                chat_id=chat_id,
                text="✅ Bạn đã hủy đăng ký nhận thông báo nhắc nhở tiết học!"
            )
            logger.info(f"Người dùng {chat_id} đã hủy đăng ký nhận thông báo")
            
            # Lưu ngay khi có thay đổi
            await self.user_manager.save_users()
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Bạn chưa đăng ký nhận thông báo!"
            )
    
    async def tkb_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh xem thời khóa biểu"""
        chat_id = update.effective_chat.id
        args = context.args

        # Xử lý ngày yêu cầu
        requested_date = None
        
        if len(args) == 1:
            date_input = args[0]
            requested_date = validate_date_format(date_input)
            
            if not requested_date:
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text="❌ Định dạng ngày không hợp lệ! Vui lòng sử dụng định dạng YYYY-MM-DD (ví dụ: 2025-03-08) hoặc DD/MM/YYYY (ví dụ: 08/03/2025)"
                )
                return
        else:
            # Lấy ngày hiện tại định dạng YYYY-MM-DD theo múi giờ Việt Nam
            requested_date = get_vietnam_date()

        await self.show_tkb_for_date(chat_id, requested_date, context.bot)
    
    async def show_tkb_for_date(self, chat_id, requested_date, bot):
        """Hiển thị thời khóa biểu cho ngày cụ thể"""
        await bot.send_message(chat_id, text=f"🔍 Đang tìm thời khóa biểu cho ngày {requested_date}...")
        
        # Lấy thời khóa biểu
        tkb_data = await self.ttvu_client.get_tkb()
        
        # Định dạng kết quả
        message_text, found = format_tkb_message(tkb_data, requested_date)
        
        if found:
            await bot.send_message(chat_id, text=message_text, parse_mode='Markdown')
        else:
            await bot.send_message(chat_id, text=f"❌ Không có lịch học vào ngày {requested_date}.")
    
    async def date_picker_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh chọn ngày"""
        # Lấy thông tin ngày hiện tại theo múi giờ Việt Nam
        vn_today = get_vietnam_datetime()
        current_month = vn_today.month
        current_year = vn_today.year
        
        # Lưu message_id trong user_data để có thể xóa sau
        message = await update.effective_chat.send_message(text="Đang tải bảng chọn ngày...")
        
        if 'datepicker_messages' not in context.user_data:
            context.user_data['datepicker_messages'] = []
        
        # Thêm message_id mới vào danh sách để có thể xóa sau
        context.user_data['datepicker_messages'].append(message.message_id)
        
        # Tạo bảng chọn năm và tháng
        await self.show_month_picker(update.effective_chat.id, current_year, current_month, context)
        
        # Xóa tin nhắn "Đang tải..."
        try:
            await message.delete()
        except BadRequest:
            pass
    
    async def show_month_picker(self, chat_id, year, month, context):
        """Hiển thị bảng chọn tháng"""
        # Tạo các nút cho các tháng
        keyboard = []
        row = []
        for i in range(1, 13):
            month_name = ['', 'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6', 
                          'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'][i]
            row.append(InlineKeyboardButton(month_name, callback_data=f"month:{year}:{i}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        # Thêm nút điều hướng năm
        keyboard.append([
            InlineKeyboardButton("◀️ Năm trước", callback_data=f"year:{year-1}:{month}"),
            InlineKeyboardButton("Năm sau ▶️", callback_data=f"year:{year+1}:{month}")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Gửi tin nhắn mới và lưu message_id
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=f"🗓️ Chọn tháng để xem thời khóa biểu (Năm {year}):",
            reply_markup=reply_markup
        )
        
        # Lưu message_id trong user_data
        if 'datepicker_messages' not in context.user_data:
            context.user_data['datepicker_messages'] = []
        
        context.user_data['datepicker_messages'].append(message.message_id)
    
    async def show_day_picker(self, chat_id, year, month, context):
        """Hiển thị bảng chọn ngày trong tháng"""
        import calendar
        
        # Lấy số ngày trong tháng
        num_days = calendar.monthrange(year, month)[1]
        
        # Tạo các nút cho các ngày
        keyboard = []
        row = []
        for i in range(1, num_days + 1):
            row.append(InlineKeyboardButton(str(i), callback_data=f"day:{year}:{month}:{i}"))
            if len(row) == 7:  # 7 ngày trên một hàng
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        # Thêm nút quay lại
        keyboard.append([InlineKeyboardButton("🔙 Quay lại chọn tháng", callback_data=f"back_to_months:{year}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        month_name = [
            'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
            'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'
        ][month - 1]
        
        # Gửi tin nhắn mới và lưu message_id
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=f"📅 Chọn ngày trong {month_name}, {year}:",
            reply_markup=reply_markup
        )
        
        # Lưu message_id trong user_data
        if 'datepicker_messages' not in context.user_data:
            context.user_data['datepicker_messages'] = []
        
        context.user_data['datepicker_messages'].append(message.message_id)
    
    async def cleanup_datepicker_messages(self, chat_id, context):
        """Xóa các tin nhắn date picker cũ"""
        if 'datepicker_messages' in context.user_data:
            for message_id in context.user_data['datepicker_messages']:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                except BadRequest as e:
                    # Bỏ qua lỗi nếu tin nhắn đã bị xóa
                    if "Message to delete not found" not in str(e):
                        logger.error(f"Lỗi khi xóa tin nhắn: {e}")
            
            # Xóa danh sách sau khi đã xử lý
            context.user_data['datepicker_messages'] = []
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý các tương tác từ inline keyboard"""
        query = update.callback_query
        data = query.data
        chat_id = query.message.chat_id
        
        # Thông báo đã nhận được sự kiện
        await query.answer()
        
        if data.startswith("month:"):
            # Xử lý khi người dùng chọn tháng
            _, year, month = data.split(":")
            year, month = int(year), int(month)
            
            # Xóa tin nhắn cũ
            await self.cleanup_datepicker_messages(chat_id, context)
            
            # Hiển thị bảng chọn ngày
            await self.show_day_picker(chat_id, year, month, context)
            
        elif data.startswith("day:"):
            # Xử lý khi người dùng chọn ngày
            _, year, month, day = data.split(":")
            year, month, day = int(year), int(month), int(day)
            
            # Format ngày theo định dạng YYYY-MM-DD
            selected_date = f"{year:04d}-{month:02d}-{day:02d}"
            
                   # Xóa tất cả tin nhắn date picker
            await self.cleanup_datepicker_messages(chat_id, context)
            
            # Hiển thị thời khóa biểu cho ngày đã chọn
            await self.show_tkb_for_date(chat_id, selected_date, context.bot)
            
        elif data.startswith("year:"):
            # Xử lý khi người dùng chọn năm khác
            _, year, month = data.split(":")
            year, month = int(year), int(month)
            
            # Xóa tin nhắn cũ
            await self.cleanup_datepicker_messages(chat_id, context)
            
            # Hiển thị bảng chọn tháng trong năm mới
            await self.show_month_picker(chat_id, year, month, context)
            
        elif data.startswith("back_to_months:"):
            # Quay lại chọn tháng
            _, year = data.split(":")
            year = int(year)
            
            # Xóa tin nhắn cũ
            await self.cleanup_datepicker_messages(chat_id, context)
            
            # Hiển thị bảng chọn tháng
            await self.show_month_picker(chat_id, year, 1, context)
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý tin nhắn văn bản từ nút bấm"""
        text = update.message.text
        chat_id = update.effective_chat.id
        
        if text == "📚 Thời khóa biểu hôm nay":
            # Xem thời khóa biểu hôm nay
            requested_date = get_vietnam_date()
            await self.show_tkb_for_date(chat_id, requested_date, context.bot)
            
        elif text == "🔍 Xem TKB ngày khác":
            # Mở bảng chọn ngày
            await self.date_picker_command(update, context)
            
        elif text == "✅ Đăng ký nhận thông báo":
            # Đăng ký nhận thông báo
            self.user_manager.register_user(chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text="✅ Bạn đã đăng ký nhận thông báo nhắc nhở tiết học thành công!"
            )
            logger.info(f"Người dùng {chat_id} đã đăng ký nhận thông báo")
            await self.user_manager.save_users()
            
        elif text == "❌ Hủy đăng ký":
            # Hủy đăng ký
            success = self.user_manager.unregister_user(chat_id)
            if success:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="✅ Bạn đã hủy đăng ký nhận thông báo nhắc nhở tiết học!"
                )
                logger.info(f"Người dùng {chat_id} đã hủy đăng ký nhận thông báo")
                await self.user_manager.save_users()
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Bạn chưa đăng ký nhận thông báo!"
                )
                
        elif text == "ℹ️ Trợ giúp":
            # Hiển thị trợ giúp
            await self.help_command(update, context)
            
        else:
            # Tin nhắn không nhận dạng được
            await context.bot.send_message(
                chat_id=chat_id,
                text="🤔 Tôi không hiểu lệnh này. Vui lòng sử dụng các nút hoặc lệnh có sẵn."
            )