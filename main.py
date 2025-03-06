import asyncio
import os
from datetime import datetime
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, PicklePersistence
from config import TELEGRAM_TOKEN, TOKEN_REFRESH_INTERVAL, logger, DATA_DIR
from ttvu_client import TTVUClient
from user_manager import UserManager
from bot_commands import BotCommands
from reminder import ReminderService
from utils import get_vietnam_datetime_formatted

# Đường dẫn đến file lưu trữ dữ liệu persistence
PERSISTENCE_PATH = os.path.join(DATA_DIR, 'bot_data.pickle')

# Khởi tạo các đối tượng chính của ứng dụng
ttvu_client = None
user_manager = None
bot_commands = None
reminder_service = None

async def refresh_ttvu_token():
    """Task làm mới token TTVU định kỳ"""
    # Đợi 2 phút để đảm bảo quá trình khởi động đã ổn định
    await asyncio.sleep(120)
    
    while True:
        try:
            # Đợi thời gian định kỳ
            await asyncio.sleep(TOKEN_REFRESH_INTERVAL)
            
            # Thực hiện làm mới token
            logger.info(f"🔄 Làm mới token TTVU theo lịch trình... ({get_vietnam_datetime_formatted()})")
            success = await ttvu_client.refresh_token()
            
            if not success:
                logger.error("❌ Không thể làm mới token TTVU")
            else:
                logger.info("✅ Đã làm mới token TTVU thành công!")
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi làm mới token TTVU: {e}")

async def setup_bot():
    """Thiết lập và khởi tạo bot"""
    global ttvu_client, user_manager, bot_commands, reminder_service
    
    # Khởi tạo các đối tượng
    ttvu_client = TTVUClient()
    user_manager = UserManager()
    bot_commands = BotCommands(ttvu_client, user_manager)
    reminder_service = ReminderService(ttvu_client, user_manager)
    
    # Tải danh sách người dùng đã đăng ký
    await user_manager.load_users()
    
    # Đăng nhập TTVU khi bot khởi động
    logger.info("🔄 Khởi tạo phiên đăng nhập TTVU ban đầu...")
    _, login_success = await ttvu_client.login()
        
    if not login_success:
        logger.error("❌ Không thể đăng nhập vào TTVU. Kiểm tra lại thông tin đăng nhập.")
        return None
    
    # Thiết lập persistence để lưu trữ dữ liệu của bot
    persistence = PicklePersistence(filepath=PERSISTENCE_PATH)

    # Khởi tạo bot với token và persistence
    app = Application.builder().token(TELEGRAM_TOKEN).persistence(persistence).build()
    
    # Thiết lập application cho reminder service
    reminder_service.set_application(app)
    
    # Đăng ký các handlers cho lệnh
    app.add_handler(CommandHandler("start", bot_commands.start_command))
    app.add_handler(CommandHandler("help", bot_commands.help_command))
    app.add_handler(CommandHandler("tkb", bot_commands.tkb_command))
    app.add_handler(CommandHandler("dangky", bot_commands.register_command))
    app.add_handler(CommandHandler("huydangky", bot_commands.unregister_command))
    app.add_handler(CommandHandler("chonngay", bot_commands.date_picker_command))
    
    # Đăng ký handler cho callback query (xử lý khi bấm nút inline keyboard)
    app.add_handler(CallbackQueryHandler(bot_commands.handle_callback_query))
    
    # Đăng ký handler cho tin nhắn văn bản (xử lý khi bấm nút trên reply keyboard)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_commands.handle_text_message))
    
    return app

async def main():
    """Hàm chính của ứng dụng"""
    # In thời gian khởi động theo múi giờ Việt Nam
    logger.info(f"🚀 Bot khởi động vào: {get_vietnam_datetime_formatted()}")

    # Thiết lập bot
    app = await setup_bot()
    
    if not app:
        logger.error("❌ Không thể thiết lập bot. Thoát chương trình.")
        return
    
    # Khởi động bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("🚀 Bot Telegram đã khởi động!")
    
    # Khởi động các background tasks
    refresh_token_task = asyncio.create_task(refresh_ttvu_token())
    save_users_task = asyncio.create_task(user_manager.start_periodic_save())
    reminder_task = asyncio.create_task(reminder_service.check_and_send_reminders())
    
    # Lưu các task vào ứng dụng để có thể quản lý
    app.bot_tasks = {
        'refresh_token': refresh_token_task,
        'save_users': save_users_task,
        'reminder': reminder_task
    }
    
    logger.info("🚀 Tất cả các tác vụ đã được khởi động!")
    
    # Chạy cho đến khi nhận được signal dừng
    try:
        # Tạo event để giữ ứng dụng chạy
        stop_event = asyncio.Event()
        await stop_event.wait()  # Chạy vô hạn cho đến khi có KeyboardInterrupt
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot đang dừng...")
    finally:
        # Hủy các background tasks
        for task_name, task in app.bot_tasks.items():
            logger.info(f"Đang dừng tác vụ: {task_name}")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Lưu danh sách người dùng trước khi tắt
        await user_manager.save_users()
        
        # Dọn dẹp TTVU client
        await ttvu_client.cleanup()
        
        # Dừng bot gracefully
        logger.info("Đang dừng bot Telegram...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        
        logger.info("Bot đã dừng hoàn toàn. Tạm biệt!")

# Khởi chạy bot
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot đã dừng do nhận được tín hiệu thoát.")
    except Exception as e:
        logger.critical(f"Bot đã dừng do lỗi nghiêm trọng: {e}")
        import traceback
        logger.critical(traceback.format_exc())