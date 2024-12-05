@echo off
echo Remote Control Bot Kurulumu
echo -------------------------

REM Python kontrolü
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python bulunamadi! Lutfen Python 3.8 veya üstünü yükleyin.
    echo https://www.python.org/downloads/
    pause
    exit
)

REM Gerekli kütüphaneleri kur
echo Gerekli kutuphaneler yukleniyor...
pip install -r requirements.txt

REM .env dosyası oluştur
echo.
echo Telegram Bot Token'inizi girin:
set /p TOKEN=
echo TELEGRAM_BOT_TOKEN=%TOKEN%> .env
echo.
echo Telegram Kullanici ID'nizi girin:
set /p USER_ID=
echo AUTHORIZED_USER_ID=%USER_ID%>> .env

REM Otomatik başlatma için VBS dosyasını kopyala
echo Otomatik baslatma ayarlaniyor...
copy autostart.vbs "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\"

echo.
echo Kurulum tamamlandi!
echo Bot baslatiliyor...
start pythonw remote_control_bot.py

pause 