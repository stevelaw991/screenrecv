"""
WindowsSyncService - Windows 同步服务
守护进程，监控 SystemUpdateService 并自动重启
"""

import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
import json

# 本地模块
from utils import load_config, Logger, ensure_single_instance


class ProcessWatchdog:
    """进程守护器"""
    
    def __init__(self):
        self.config = load_config()
        self.logger = Logger(self.config)
        self.target_process_name = "SystemUpdateService.exe"
        self.target_script_name = "SystemUpdateService.py"
        self.running = False
        self.process = None
        
        # 确保只有一个守护进程实例运行
        if not ensure_single_instance("watchdog.lock"):
            self.logger.error("Another watchdog instance is already running")
            sys.exit(1)
        
        self.logger.info("WindowsSyncService initialized")
    
    def find_target_process(self):
        """查找目标进程"""
        try:
            # 使用 tasklist 命令查找进程
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {self.target_process_name}', '/FO', 'CSV'],
                capture_output=True, text=True, shell=True
            )
            
            if result.returncode == 0 and self.target_process_name in result.stdout:
                # 找到进程，返回一个简单的进程对象
                return {'found': True, 'name': self.target_process_name}
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding target process: {str(e)}")
            return None
    
    def start_target_process(self):
        """启动目标进程"""
        try:
            # 确定可执行文件/脚本所在的目录
            if getattr(sys, 'frozen', False):
                # 如果是 PyInstaller 打包的 exe
                current_dir = os.path.dirname(sys.executable)
            else:
                # 如果是作为 .py 脚本运行
                current_dir = os.path.dirname(os.path.abspath(__file__))

            # 尝试启动编译后的exe文件
            exe_path = os.path.join(current_dir, self.target_process_name)
            if os.path.exists(exe_path):
                self.logger.info(f"Starting {self.target_process_name}")
                self.process = subprocess.Popen(
                    [exe_path],
                    cwd=current_dir,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
            else:
                # 如果exe不存在，尝试启动Python脚本
                script_path = os.path.join(current_dir, self.target_script_name)
                if os.path.exists(script_path):
                    self.logger.info(f"Starting {self.target_script_name}")
                    self.process = subprocess.Popen(
                        [sys.executable, script_path],
                        cwd=current_dir,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )
                else:
                    self.logger.error("Target process file not found")
                    return False
            
            # 等待一下确保进程启动
            time.sleep(2)
            
            if self.process and self.process.poll() is None:
                self.logger.info(f"Target process started successfully, PID: {self.process.pid}")
                return True
            else:
                self.logger.error("Failed to start target process")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting target process: {str(e)}")
            return False
    
    def is_process_healthy(self, proc_info):
        """检查进程是否健康"""
        try:
            if not proc_info or not proc_info.get('found'):
                return False
            
            # 简单检查：如果进程还在运行，就认为是健康的
            # 使用 tasklist 再次确认进程存在
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {self.target_process_name}', '/FO', 'CSV'],
                capture_output=True, text=True, shell=True
            )
            
            return result.returncode == 0 and self.target_process_name in result.stdout
            
        except Exception as e:
            self.logger.error(f"Error checking process health: {str(e)}")
            return False
    
    def terminate_process(self, proc_info):
        """终止进程"""
        try:
            if proc_info and proc_info.get('found'):
                # 使用 taskkill 命令终止进程
                result = subprocess.run(
                    ['taskkill', '/F', '/IM', self.target_process_name],
                    capture_output=True, text=True, shell=True
                )
                
                if result.returncode == 0:
                    self.logger.info("Target process terminated")
                else:
                    self.logger.warning(f"Failed to terminate process: {result.stderr}")
                
        except Exception as e:
            self.logger.error(f"Error terminating process: {str(e)}")
    
    def monitor_loop(self):
        """监控循环"""
        check_interval = self.config['watchdog']['check_interval_seconds']
        restart_delay = self.config['watchdog']['restart_delay_seconds']
        
        self.logger.info(f"Starting monitor loop, check interval: {check_interval}s")
        
        while self.running:
            try:
                # 查找目标进程
                target_proc = self.find_target_process()
                
                if target_proc and self.is_process_healthy(target_proc):
                    # 进程存在且健康
                    self.logger.debug("Target process is running and healthy")
                else:
                    # 进程不存在或不健康
                    if target_proc:
                        self.logger.warning("Target process is unhealthy, terminating...")
                        self.terminate_process(target_proc)
                    else:
                        self.logger.warning("Target process not found")
                    
                    # 等待一下再重启
                    self.logger.info(f"Waiting {restart_delay}s before restart...")
                    time.sleep(restart_delay)
                    
                    if self.running:  # 确保还在运行状态
                        # 重启目标进程
                        if self.start_target_process():
                            self.logger.info("Target process restarted successfully")
                        else:
                            self.logger.error("Failed to restart target process")
                
                # 等待下次检查
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Monitor interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Monitor loop error: {str(e)}")
                time.sleep(check_interval)
    
    def start(self):
        """启动守护服务"""
        try:
            self.running = True
            self.logger.info("WindowsSyncService starting...")
            
            # 启动监控循环
            self.monitor_loop()
            
        except Exception as e:
            self.logger.error(f"Error starting service: {str(e)}")
        finally:
            self.stop()
    
    def stop(self):
        """停止守护服务"""
        try:
            self.running = False
            self.logger.info("WindowsSyncService stopping...")
            
            # 终止目标进程
            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                except Exception:
                    pass
            
            self.logger.info("WindowsSyncService stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping service: {str(e)}")


def main():
    """主函数"""
    try:
        # 设置信号处理器
        if sys.platform == "win32":
            import signal
            def handler(event):
                if event in [signal.SIGINT, signal.SIGTERM]:
                    emergency_log("WindowsSyncService received termination signal")
                    sys.exit(0)
            
            # 注册信号处理器
            signal.signal(signal.SIGINT, handler)
            signal.signal(signal.SIGTERM, handler)
        
        # 创建并启动守护进程
        watchdog = ProcessWatchdog()
        watchdog.start()
        
    except KeyboardInterrupt:
        emergency_log("WindowsSyncService interrupted by user")
    except Exception as e:
        emergency_log(f"WindowsSyncService fatal error: {str(e)}")
        sys.exit(1)


def emergency_log(message):
    """紧急日志记录"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # 写入日志文件
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        with open(log_dir / "watchdog.log", "a", encoding="utf-8") as f:
            f.write(log_message)
            
    except Exception:
        pass  # 忽略日志记录错误


if __name__ == "__main__":
    main()
