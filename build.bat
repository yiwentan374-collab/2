@echo off
REM ============================================================
REM  一键打包脚本（Windows）——双击或在命令行运行
REM ============================================================
chcp 65001 >nul
echo [1/3] 安装依赖...
python -m pip install --upgrade pip
python -m pip install pillow pyinstaller

echo [2/3] 开始打包...
REM 方式 A：直接用 spec 文件（推荐，配置最全）
pyinstaller pet.spec --clean --noconfirm

REM 方式 B（等价的纯命令行，二选一）：
REM   注意 Windows 下 --add-data 用分号 ; 分隔
REM pyinstaller --noconfirm --clean --onefile --noconsole ^
REM   --name BichonPet ^
REM   --add-data "assets;assets" ^
REM   app.py

echo [3/3] 完成！exe 在 dist\BichonPet.exe
pause
