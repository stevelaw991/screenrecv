"""
WindowsSyncService - Windows 同步服务
守护进程，监控 SystemUpdateService 并自动重启
"""

import os
import sys
import time
import subprocess
import psutil
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
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # 检查进程名
                    if proc.info['name'] and self.target_process_name.lower() in proc.info['name'].lower():
                        return proc
                    
                    # 检查命令行参数（对于Python脚本）
                    if proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        if self.target_script_name in cmdline:
                            return proc
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
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
    
    def is_process_healthy(self, proc):
        """检查进程是否健康"""
        try:
            if not proc or not proc.is_running():
                return False
            
            # 检查进程状态
            status = proc.status()
            if status in [psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD]:
                return False
            
            # 检查CPU使用率（可选）
            # cpu_percent = proc.cpu_percent()
            # if cpu_percent > 90:  # 如果CPU使用率过高
            #     self.logger.warning(f"Target process CPU usage high: {cpu_percent}%")
            
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
        except Exception as e:
            self.logger.error(f"Error checking process health: {str(e)}")
            return False
    
    def terminate_process(self, proc):
        """终止进程"""
        try:
            if proc and proc.is_running():
                proc.terminate()
                # 等待进程终止
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    # 如果进程不响应，强制杀死
                    proc.kill()
                    proc.wait(timeout=5)
                
                self.logger.info("Target process terminated")
                
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
            
            # 首次启动目标进程
            if not self.start_target_process():
                self.logger.error("Failed to start target process initially")
                return
            
            # 开始监控循环
            self.monitor_loop()
            
        except Exception as e:
            self.logger.error(f"Watchdog service error: {str(e)}")
        finally:
            self.stop()
    
    def stop(self):
        """停止守护服务"""
        self.running = False
        
        # 终止目标进程
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass
        
        self.logger.info("WindowsSyncService stopped")


def main():
    """主函数"""
    watchdog = None
    try:
        # 隐藏控制台窗口（Windows）
        # if sys.platform == "win32":
        #     import ctypes
        #     ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        
        # 创建并启动守护服务
        watchdog = ProcessWatchdog()
        watchdog.start()
        
    except (FileNotFoundError, RuntimeError) as e:
        # 配置文件加载等早期错误
        print(f"FATAL ERROR in Watchdog: {e}")
        time.sleep(10)
        sys.exit(1)
    except Exception as e:
        # 其他意外错误
        if watchdog and watchdog.logger:
            watchdog.logger.error(f"Fatal error: {str(e)}")
        else:
            # 日志系统未初始化，写入紧急日志
            emergency_log(f"Fatal error: {str(e)}")
        sys.exit(1)


def emergency_log(message):
    """紧急日志，在日志系统初始化失败时使用"""
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        with open(log_dir / "watchdog_emergency.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()}: {message}\n")
    except:
        pass


if __name__ == "__main__":
    main()
