Option Explicit

' Windows Script Host nesnelerini oluştur
Dim WshShell, FSO, strPath, strPythonPath

' Nesneleri başlat
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' Bot dosyasının yolunu al
strPath = FSO.GetParentFolderName(WScript.ScriptFullName)

' Python yolunu bul
strPythonPath = "pythonw.exe"  ' Arka planda çalıştırmak için pythonw kullan

' Çalışma dizinini ayarla
WshShell.CurrentDirectory = strPath

' Botu başlat (görünmez modda)
WshShell.Run strPythonPath & " """ & strPath & "\remote_control_bot.py""", 0, False

' Nesneleri temizle
Set WshShell = Nothing
Set FSO = Nothing 