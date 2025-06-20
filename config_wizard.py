import json
import sys
import os
import base64
from getpass import getpass

# 导入新的加密模块
from crypter import encrypt

def get_user_input(prompt, default=None):
    """获取用户输入，支持默认值"""
    if default:
        display_prompt = f"{prompt} [{default}]: "
    else:
        display_prompt = f"{prompt}: "
    
    value = input(display_prompt)
    return value if value else default

def main():
    """主函数，引导用户完成配置"""
    print("--- SystemUpdateService 配置向导 ---")
    print("这将引导您创建一个加密的配置文件 (config.dat)。")
    print("请按提示输入您的配置信息。")
    print("-" * 40)

    config = {
        "webdav": {},
        "screenshot": {},
        "upload": {},
        "system": {},
        "watchdog": {}
    }

    # WebDAV 配置
    config['webdav']['url'] = get_user_input("请输入 WebDAV URL", "https://dav.jianguoyun.com/dav/")
    config['webdav']['username'] = get_user_input("请输入坚果云邮箱")
    config['webdav']['password'] = getpass("请输入为本应用生成的密码: ")
    config['webdav']['remote_path'] = get_user_input("请输入远程存储路径", "/ScreenCaptures/")

    # 截图配置
    config['screenshot']['interval_seconds'] = int(get_user_input("截图间隔（秒）", 5))
    config['screenshot']['format'] = "jpg"
    config['screenshot']['quality'] = int(get_user_input("图片质量 (1-100)", 85))
    config['screenshot']['max_width'] = int(get_user_input("最大图片宽度", 1920))
    config['screenshot']['max_height'] = int(get_user_input("最大图片高度", 1080))
    
    # 上传和系统配置（使用默认值）
    config['upload'] = {
        "retry_interval_seconds": 300,
        "max_retries": 5,
        "timeout_seconds": 30
    }
    config['system'] = {
        "log_level": "INFO",
        "max_log_size_mb": 10,
        "max_log_files": 5,
        "cache_cleanup_days": 7
    }
    config['watchdog'] = {
        "check_interval_seconds": 10,
        "restart_delay_seconds": 5
    }

    try:
        # 使用新的加密函数
        encrypted_config = encrypt(config)
        
        print(f"DEBUG: Encrypted data fingerprint: {encrypted_config[:16]}")

        # 保存到文件
        with open('config.dat', 'w', encoding='utf-8') as f:
            f.write(encrypted_config)

        print("-" * 40)
        print("✅ 配置成功！")
        print("加密的配置文件 'config.dat' 已生成。")
        print("现在您可以运行主程序了。")

    except Exception as e:
        print(f"\n❌ 错误：无法生成配置文件。")
        print(f"详细信息: {e}")
        # 如果是权限问题，提供提示
        if isinstance(e, win32api.error) and e.winerror == 5:
            print("提示：这可能是由于权限不足导致的。请尝试以管理员身份运行此向导。")

if __name__ == "__main__":
    main() 