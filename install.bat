@echo off
echo Remote Control Bot Kurulumu
echo -------------------------

REM Çalışma dizinini script konumuna ayarla
cd /d "%~dp0"

REM Requirements.txt kontrolü
if not exist "requirements.txt" (
    echo requirements.txt dosyasi bulunamadi!
    echo Lutfen dosyanin kurulum klasorunde oldugundan emin olun.
    pause
    exit
)

REM Python yolunu bul
for /f "tokens=*" %%i in ('where python3') do (
    set "PYTHON_PATH=%%i"
    goto :found_python
)
:found_python

REM Pythonw yolunu ayarla
set "PYTHONW_PATH=%PYTHON_PATH:python.exe=pythonw.exe%"

REM Python bilgilerini göster
echo Python Bilgileri:
echo Python Yolu: %PYTHON_PATH%
echo Pythonw Yolu: %PYTHONW_PATH%
python3 --version

REM Gerekli kütüphaneleri kur
echo.
echo Gerekli kutuphaneler yukleniyor...
echo Kullanilan requirements.txt: %CD%\requirements.txt
python3 -m pip install -r "%CD%\requirements.txt"

REM .env dosyası oluştur
echo.
echo Telegram Bot Token'inizi girin:
set /p TOKEN=
echo TELEGRAM_BOT_TOKEN=%TOKEN%> .env
echo.
echo Telegram Kullanici ID'nizi girin:
set /p USER_ID=
echo AUTHORIZED_USER_ID=%USER_ID%>> .env

REM VBScript oluştur
echo Otomatik baslatma ayarlaniyor...
set "STARTUP_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\RemoteGuardPC.vbs"

REM VBScript dosyasını oluştur
(
echo Option Explicit
echo On Error Resume Next
echo Dim WshShell, fso, strWorkDir, strPythonPath, strScriptPath
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo Set fso = CreateObject^("Scripting.FileSystemObject"^)
echo strWorkDir = "%CD%"
echo strPythonPath = "%PYTHONW_PATH%"
echo strScriptPath = strWorkDir ^& "\remote_control_bot.py"
echo.
echo If Not fso.FileExists^(strPythonPath^) Then
echo     MsgBox "Python bulunamadi: " ^& strPythonPath, 16, "Hata"
echo     WScript.Quit
echo End If
echo.
echo If Not fso.FileExists^(strScriptPath^) Then
echo     MsgBox "Bot scripti bulunamadi: " ^& strScriptPath, 16, "Hata"
echo     WScript.Quit
echo End If
echo.
echo WshShell.CurrentDirectory = strWorkDir
echo WshShell.Run """" ^& strPythonPath ^& """ """ ^& strScriptPath ^& """", 0, True
echo Set WshShell = Nothing
echo Set fso = Nothing
) > "%STARTUP_VBS%"

REM Eski görev varsa kaldır
schtasks /delete /tn "RemoteGuardPC Bot" /f >nul 2>&1

echo.
echo Kurulum tamamlandi!
echo Bot baslatiliyor...
echo Calisma dizini: %CD%
echo Python yolu: %PYTHONW_PATH%
echo VBScript yolu: %STARTUP_VBS%

REM Botu başlat
wscript "%STARTUP_VBS%"

echo.
echo Bot baslatildi. Hata mesaji gormediyseniz bot calisiyor demektir.
echo Telegram'dan bot'a mesaj gondererek test edebilirsiniz.
pause 
