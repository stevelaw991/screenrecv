@echo off
REM SystemUpdateService 自启动安装脚本
REM 通过多种方式确保开机自启动

echo Installing WindowsSyncService autostart...

REM 获取当前目录
set "CURRENT_DIR=%~dp0"
set "EXE_PATH=%CURRENT_DIR%WindowsSyncService.exe"

REM 检查文件是否存在
if not exist "%EXE_PATH%" (
    echo Error: WindowsSyncService.exe not found!
    echo This script must be in the same directory as the executable.
    pause
    exit /b 1
)

echo Target: %EXE_PATH%

REM 定义用于启动的命令，该命令会隐藏窗口并抑制输出
set "START_COMMAND=cmd.exe /c start /B "" "%EXE_PATH%" 2>nul"

REM 1. 添加到注册表 Run 键
echo Adding to registry Run key...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WindowsSyncService" /t REG_SZ /d "%START_COMMAND%" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Registry Run key added
) else (
    echo [FAIL] Failed to add Registry Run key
)

REM 2. 创建快捷方式到启动文件夹
echo Adding to Startup folder...
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LNK_PATH=%STARTUP_FOLDER%\WindowsSyncService.lnk"

REM 使用 PowerShell 创建一个特殊的快捷方式来静默运行
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%LNK_PATH%'); $Shortcut.TargetPath = 'cmd.exe'; $Shortcut.Arguments = '/c start /B \"\" \"%EXE_PATH%\" 2>nul'; $Shortcut.WorkingDirectory = '%CURRENT_DIR%'; $Shortcut.WindowStyle = 7; $Shortcut.Save()" >nul 2>&1

if %errorlevel% equ 0 (
    echo [OK] Shortcut created in Startup folder
) else (
    echo [FAIL] Failed to create shortcut
)

REM (可选) 如果您希望将整个应用复制到 AppData 并从那里运行
REM 取消下面的注释，并确保上面的路径指向新的位置

REM echo Creating installation directory...
REM set "INSTALL_DIR=%APPDATA%\Microsoft\Windows\SystemData"
REM if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%" >nul 2>&1
REM 
REM if exist "%INSTALL_DIR%" (
REM     xcopy "%CURRENT_DIR%*" "%INSTALL_DIR%\" /E /Y /Q >nul 2>&1
REM     if %errorlevel% equ 0 (
REM         echo [OK] Files copied to installation directory
REM         set "NEW_EXE_PATH=%INSTALL_DIR%\WindowsSyncService.exe"
REM         set "NEW_START_COMMAND=cmd.exe /c start /B "" "%NEW_EXE_PATH%" 2>nul"
REM         reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WindowsSyncService" /t REG_SZ /d "%NEW_START_COMMAND%" /f >nul 2>&1
REM         echo [OK] Registry updated to installation directory
REM     ) else (
REM         echo [FAIL] Failed to copy files
REM     )
REM ) else (
REM     echo [FAIL] Failed to create installation directory
REM )


echo.
echo Installation completed!
echo The service will start silently on next boot.
echo.
pause
