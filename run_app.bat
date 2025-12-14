@echo off
echo ==========================================
echo      HE THONG XEP LICH THI - SETUP
echo ==========================================

cd /d "%~dp0"

:: 1. Kiem tra va tao moi truong ao
if not exist venv (
    echo [+] Dang tao moi truong ao venv...
    python -m venv venv
) else (
    echo [+] Moi truong ao da ton tai.
)

:: 2. Kich hoat moi truong
echo [+] Dang kich hoat venv...
call venv\Scripts\activate

:: 3. Cai dat thu vien
echo [+] Dang cai dat thu vien can thiet...
pip install fastapi uvicorn pandas openpyxl jinja2 python-multipart

:: 4. Tao du lieu mau neu chua co
if not exist sample_data.xlsx (
    echo [+] Dang tao du lieu mau...
    python create_sample_data.py
)

:: 5. Mo trinh duyet va chay server
echo.
echo ==========================================
echo      DANG KHOI DONG SERVER...
echo      Truy cap: http://127.0.0.1:8000
echo ==========================================
echo.

:: Mo trinh duyet sau 3 giay
timeout /t 3 >nul
start http://127.0.0.1:8000

:: Chay server
uvicorn backend.main:app --reload
pause
