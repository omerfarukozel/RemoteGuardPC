# -*- coding: utf-8 -*-

import os
import logging
import subprocess
import platform
import time
import asyncio
import requests
import wmi
from datetime import datetime, timedelta
from threading import Thread

# Telegram kütüphaneleri
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    MessageHandler,
    filters
)

# Sistem kontrol kütüphaneleri
import psutil
import pyautogui
import cv2
import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy.io.wavfile import write
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Diğer kütüphaneler
from dotenv import load_dotenv
import ctypes
import speedtest

# Loglama ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# .env dosyasından çevresel değişkenleri yükle
load_dotenv()

# Telegram bot token'ı ve yetkili kullanıcı ID'sini al
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID'))

# Buton callback'leri için sabitler ekleyelim
class Callbacks:
    # Ana menü
    MENU_SYSTEM = "menu_system"
    MENU_POWER = "menu_power"
    MENU_APPS = "menu_apps"
    MENU_VOLUME = "menu_volume"
    MENU_MAIN = "menu_main"
    
    # Güç işlemleri
    POWER_SHUTDOWN = "power_shutdown"
    POWER_RESTART = "power_restart"
    POWER_LOCK = "power_lock"
    
    # Sistem işlemleri
    SYS_INFO = "sys_info"
    SYS_PERF = "sys_perf"
    SYS_BATTERY = "sys_battery"
    SYS_SCREEN = "sys_screen"
    
    # Ses işlemleri
    VOL_UP = "vol_up"
    VOL_DOWN = "vol_down"
    VOL_CUSTOM = "vol_custom"
    VOL_MUTE = "vol_mute"
    
    # Yeni özellikler için callback'ler
    RECORD_AUDIO = "record_audio"
    RECORD_SCREEN = "record_screen"
    WEBCAM_PHOTO = "webcam_photo"
    WEBCAM_MONITOR = "webcam_monitor"
    
    # Kamera ve Kayıt menüsü
    MENU_CAMERA = "menu_camera"  # Yeni ana menü butonu için
    CAM_PHOTO = "cam_photo"      # Fotoğraf çek
    CAM_MONITOR = "cam_monitor"  # Hareket algılama başlat/durdur
    CAM_MONITOR_STOP = "cam_monitor_stop"  # Hareket algılama durdur
    RECORD_AUDIO = "record_audio"  # Ses kaydı
    RECORD_SCREEN = "record_screen"  # Ekran kaydı
    
    # Süre bekleme durumları
    WAITING_AUDIO_DURATION = "waiting_audio_duration"
    WAITING_SCREEN_DURATION = "waiting_screen_duration"

def create_main_menu():
    """Ana menü butonlarını oluştur"""
    keyboard = [
        [
            InlineKeyboardButton("🖥️ Sistem", callback_data=Callbacks.MENU_SYSTEM),
            InlineKeyboardButton("⚡ Güç", callback_data=Callbacks.MENU_POWER)
        ],
        [
            InlineKeyboardButton("📱 Uygulamalar", callback_data=Callbacks.MENU_APPS),
            InlineKeyboardButton("🔊 Ses", callback_data=Callbacks.MENU_VOLUME)
        ],
        [
            InlineKeyboardButton("📸 Kamera & Kayıt", callback_data=Callbacks.MENU_CAMERA)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_system_menu():
    """Sistem menüsü butonlarını oluştur"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Sistem Bilgisi", callback_data=Callbacks.SYS_INFO),
            InlineKeyboardButton("💻 Performans", callback_data=Callbacks.SYS_PERF)
        ],
        [
            InlineKeyboardButton("🔋 Batarya", callback_data=Callbacks.SYS_BATTERY),
            InlineKeyboardButton("📸 Ekran Görüntüsü", callback_data=Callbacks.SYS_SCREEN)
        ],
        [InlineKeyboardButton("◀️ Ana Menü", callback_data=Callbacks.MENU_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_power_menu():
    """Güç menüsü butonlarını oluştur"""
    keyboard = [
        [
            InlineKeyboardButton("⭕ Kapat", callback_data=Callbacks.POWER_SHUTDOWN),
            InlineKeyboardButton("🔄 Yeniden Başlat", callback_data=Callbacks.POWER_RESTART)
        ],
        [
            InlineKeyboardButton("🔒 Kilitle", callback_data=Callbacks.POWER_LOCK)
        ],
        [InlineKeyboardButton("◀️ Ana Menü", callback_data=Callbacks.MENU_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_volume_menu():
    """Ses menüsü butonlarını oluştur"""
    keyboard = [
        [
            InlineKeyboardButton("🔊 Ses +", callback_data=Callbacks.VOL_UP),
            InlineKeyboardButton(" Ses -", callback_data=Callbacks.VOL_DOWN)
        ],
        [
            InlineKeyboardButton("🎚️ Özel Değer", callback_data=Callbacks.VOL_CUSTOM),
            InlineKeyboardButton("🔇 Sessiz", callback_data=Callbacks.VOL_MUTE)
        ],
        [InlineKeyboardButton("◀️ Ana Menü", callback_data=Callbacks.MENU_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_camera_menu():
    """Kamera ve kayıt menüsü butonlarını oluştur"""
    keyboard = [
        [
            InlineKeyboardButton("📸 Webcam Fotoğraf", callback_data=Callbacks.CAM_PHOTO),
            InlineKeyboardButton("👁️ Hareket Algılama", callback_data=Callbacks.CAM_MONITOR)
        ],
        [
            InlineKeyboardButton("🎙️ Ses Kaydı", callback_data=Callbacks.RECORD_AUDIO),
            InlineKeyboardButton("🎥 Ekran Kaydı", callback_data=Callbacks.RECORD_SCREEN)
        ],
        [InlineKeyboardButton("◀️ Ana Menü", callback_data=Callbacks.MENU_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

# Güvenlik kontrolü için dekoratör
def authorized_only(func):
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        command = update.message.text
        
        # Önce engellenen kullanıcıları kontrol et
        if user.id in self.blocked_users:
            await update.message.reply_text("🚫 Erişiminiz engellenmiştir!")
            return
        
        if user.id != AUTHORIZED_USER_ID:
            # Yetkisiz erişim girişimini kaydet
            if user.id not in self.unauthorized_attempts:
                self.unauthorized_attempts[user.id] = []
            
            # IP adresini al (eğer mevcutsa)
            ip_address = None
            if update.message and update.message.from_user:
                try:
                    ip_address = context.bot_data.get('ip_address', 'Bilinmiyor')
                except:
                    ip_address = 'Alınamadı'
            
            attempt_info = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'command': command,
                'username': user.username,
                'first_name': user.first_name,
                'language': user.language_code,
                'ip_address': ip_address
            }
            self.unauthorized_attempts[user.id].append(attempt_info)
            
            # Yetkisiz erişim girişimi hakkında yetkili kullanıcıya bildirim gönder
            alert_message = f"""
🚨 *Yetkisiz Erişim Denemesi*

👤 *Kullanıcı Bilgileri:*
İsim: {user.first_name}
Kullanıcı Adı: @{user.username if user.username else "Yok"}
ID: `{user.id}`
Dil: {user.language_code}
IP: {ip_address}

📍 *Denenen Komut:* `{command}`
📊 *Toplam Deneme Sayısı:* {len(self.unauthorized_attempts[user.id])}

⏰ Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            try:
                # Yetkili kullanıcıya bildirim gönder
                await self.app.bot.send_message(
                    chat_id=AUTHORIZED_USER_ID,
                    text=alert_message,
                    parse_mode='Markdown'
                )
                
                # Kullanıcının profil fotoğrafını da gönder (varsa)
                photos = await self.app.bot.get_user_profile_photos(user.id, limit=1)
                if photos.photos:
                    photo_file = await photos.photos[0][0].get_file()
                    await self.app.bot.send_photo(
                        chat_id=AUTHORIZED_USER_ID,
                        photo=photo_file.file_id,
                        caption=f"🔍 Yetkisiz kullanıcının profil fotoğrafı\n(Deneme #{len(self.unauthorized_attempts[user.id])})"
                    )
                
                # Otomatik engelleme sistemi
                if len(self.unauthorized_attempts[user.id]) >= 5:
                    if user.id not in self.blocked_users:
                        self.blocked_users.add(user.id)
                        warning = f"""
⚠️ *Güvenlik Uyarısı*
Kullanıcı 5 başarısız deneme yaptığı için otomatik olarak engellendi!

👤 Kullanıcı: {user.first_name}
🆔 ID: `{user.id}`
📱 Kullanıcı Adı: @{user.username if user.username else "Yok"}
🌐 IP: {ip_address}

Engeli kaldırmak için: `/unblock {user.id}`
"""
                        await self.app.bot.send_message(
                            chat_id=AUTHORIZED_USER_ID,
                            text=warning,
                            parse_mode='Markdown'
                        )
                
            except Exception as e:
                print(f"Bildirim gönderme hatası: {str(e)}")
            
            # Yetkisiz kullanıcıya mesaj gönder
            await update.message.reply_text("⛔ Bu komutu kullanma yetkiniz yok!")
            return
        return await func(self, update, context)
    return wrapper

class RemoteControlBot:
    def __init__(self):
        self.app = Application.builder().token(TOKEN).build()
        self.setup_handlers()
        self.wmi = wmi.WMI()
        self.monitoring = False
        self.webcam_monitoring = False
        self.recording_screen = False  # Ekran kaydı durumu
        self.recording_audio = False   # Ses kaydı durumu
        self.watched_folders = {}
        self.scheduled_tasks = []
        self.unauthorized_attempts = {}
        self.blocked_users = set()
        
        # Başlangıç bildirimi gönder
        self.send_startup_notification()

    def send_startup_notification(self):
        """Bilgisayar açılış bildirimi gönder"""
        try:
            # Sistem bilgilerini al
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            ip_address = requests.get('https://api.ipify.org').text
            system = platform.uname()
            
            notification = f"""
🖥️ *Bot Başlatıldı!*

⏰ Başlangıç Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🌐 IP Adresi: `{ip_address}`

💻 *Sistem Bilgileri:*
• İşletim Sistemi: {system.system} {system.release}
• Bilgisayar Adı: {system.node}
• CPU: {system.processor}

🔋 Pil Durumu: {self.get_battery_status()}
"""
            # Senkron HTTP isteği kullan
            requests.post(
                f'https://api.telegram.org/bot{TOKEN}/sendMessage',
                json={
                    'chat_id': AUTHORIZED_USER_ID,
                    'text': notification,
                    'parse_mode': 'Markdown'
                }
            )

            # Ana menüyü otomatik gönder
            requests.post(
                f'https://api.telegram.org/bot{TOKEN}/sendMessage',
                json={
                    'chat_id': AUTHORIZED_USER_ID,
                    'text': "🤖 *Uzaktan Kontrol Menüsü*\nLütfen bir işlem seçin:",
                    'parse_mode': 'Markdown',
                    'reply_markup': {
                        'inline_keyboard': [
                            [
                                {'text': '🖥️ Sistem', 'callback_data': 'menu_system'},
                                {'text': '⚡ Güç', 'callback_data': 'menu_power'}
                            ],
                            [
                                {'text': '📱 Uygulamalar', 'callback_data': 'menu_apps'},
                                {'text': '🔊 Ses', 'callback_data': 'menu_volume'}
                            ],
                            [
                                {'text': '📸 Kamera & Kayıt', 'callback_data': 'menu_camera'}
                            ]
                        ]
                    }
                }
            )

        except Exception as e:
            print(f"Başlangıç bildirimi gönderme hatası: {str(e)}")

    def get_battery_status(self):
        """Pil durumunu kontrol et"""
        try:
            battery = psutil.sensors_battery()
            if battery:
                status = "🔌 Şarjda" if battery.power_plugged else "🔋 Pilde"
                return f"{status} ({battery.percent}%)"
            return "Pil bilgisi alınamadı"
        except:
            return "Pil bilgisi alınamadı"

    @authorized_only
    async def show_unauthorized_attempts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Yetkisiz erişim denemelerinin istatistiklerini göster"""
        if not self.unauthorized_attempts:
            await update.message.reply_text("Henüz yetkisiz erişim denemesi kaydedilmedi.")
            return

        report = "📊 *Yetkisiz Erişim Denemeleri:*\n\n"
        for user_id, attempts in self.unauthorized_attempts.items():
            report += f"👤 Kullanıcı: {attempts[-1]['first_name']}\n"
            report += f"🔖 ID: `{user_id}`\n"
            report += f"👤 Kullanıcı Adı: @{attempts[-1]['username'] if attempts[-1]['username'] else 'Yok'}\n"
            report += f"📝 Toplam Deneme: {len(attempts)}\n"
            report += f"⏰ Son Deneme: {attempts[-1]['time']}\n"
            report += f"🔍 Son Komut: `{attempts[-1]['command']}`\n"
            report += f"🚫 Durum: {'Engellendi' if user_id in self.blocked_users else 'Aktif'}\n\n"

        await update.message.reply_text(report, parse_mode='Markdown')

    def setup_handlers(self):
        """Komut işleyicilerini ayarla"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CallbackQueryHandler(self.button_click))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    @authorized_only
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bot başlatıldığında ana menü göster"""
        await update.message.reply_text(
            "🤖 *Uzaktan Kontrol Menüsü*\n"
            "Lütfen bir işlem seçin:",
            reply_markup=create_main_menu(),
            parse_mode='Markdown'
        )

    @authorized_only
    async def take_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ekran görüntüsü al ve gnder"""
        screenshot = pyautogui.screenshot()
        screenshot.save("screenshot.png")
        await update.message.reply_photo(photo=open("screenshot.png", "rb"))
        os.remove("screenshot.png")

    @authorized_only
    async def shutdown_pc(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bilgisayarı kapat"""
        await update.message.reply_text("Bilgisayar kapatılıyor...")
        os.system("shutdown /s /t 1")

    @authorized_only
    async def run_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Komut satırı komutu çalıştır"""
        command = ' '.join(context.args)
        try:
            result = subprocess.check_output(command, shell=True, text=True)
            await update.message.reply_text(f"Komut çıktısı:\n{result}")
        except Exception as e:
            await update.message.reply_text(f"Hata: {str(e)}")

    @authorized_only
    async def disconnect_internet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """İnternet bağlantısnı kes"""
        os.system("ipconfig /release")
        await update.message.reply_text("��nternet bağlantısı kesildi.")

    @authorized_only
    async def kill_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Belirtilen programı kapat"""
        if not context.args:
            await update.message.reply_text("Lütfen bir program adı belirtin.")
            return
        
        process_name = context.args[0]
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == process_name:
                proc.kill()
                await update.message.reply_text(f"{process_name} kapatıldı.")
                return
        await update.message.reply_text(f"{process_name} bulunamadı.")

    @authorized_only
    async def change_volume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ses seviyesini değiştir"""
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Lütfen 0-100 arası bir değer girin.")
            return
        
        volume = int(context.args[0])
        if 0 <= volume <= 100:
            # Windows için ses kontrolü
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume_obj = cast(interface, POINTER(IAudioEndpointVolume))
            volume_obj.SetMasterVolumeLevelScalar(volume / 100.0, None)
            await update.message.reply_text(f"Ses seviyesi {volume} olarak ayarlandı.")
        else:
            await update.message.reply_text("Geçersiz ses seviyesi.")

    @authorized_only
    async def list_processes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Çalışan uygulamalar listele"""
        processes = []
        for proc in psutil.process_iter(['name', 'memory_percent']):
            try:
                processes.append(f"{proc.info['name']}: {proc.info['memory_percent']:.1f}% RAM")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        message = "Çalışan uygulamalar:\n" + "\n".join(processes[:20])
        await update.message.reply_text(message)

    @authorized_only
    async def lock_screen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ekranı kilitle"""
        ctypes.windll.user32.LockWorkStation()
        await update.message.reply_text("Ekran kilitlendi.")

    @authorized_only
    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mevcut komutları ve açıklamalarını göster"""
        help_text = """
🤖 <b>Uzaktan Kontrol Bot Komutları</b>

 <b>Temel Komutlar:</b>
📸 /screenshot - Ekran görüntüsü alır ve gönderir
⭕ /shutdown - Bilgisayarı kapatır
💻 /restart - Bilgisayarı yeniden başlatır
💻 /lock - Bilgisayar ekranını kilitler
📱 /apps - Çalışan uygulamaları gösterir ve kapatma imkanı sunar

💻 <b>Sistem Kontrolü:</b>
/cmd - Komut satırı komutu çalıştırır
    Örnek: <code>/cmd dir</code>
    Örnek: <code>/cmd ipconfig</code>
/kill - Belirtilen programı kapatır
    Örnek: <code>/kill chrome.exe</code>
/processes - Çalışan uygulamaları listeler

🔊 <b>Ses ve Görüntü:</b>
/volume - Ses seviyesini ayarlar (0-100)
    Örnek: <code>/volume 50</code>
/brightness - Ekran parlaklğını ayarlar (0-100)
    Örnek: <code>/brightness 70</code>

📊 <b>Sistem İzleme:</b>
/system - CPU, RAM ve Disk kullanımını gösterir
/speedtest - İnternet hızını ölçer
/battery - Batarya durumunu gösterir
/temp - Sistem sıcaklıklarını gösterir
/performance - Detayl sistem performans raporu

🌐 <b>Ağ İşlemleri:</b>
/disconnect - İnternet bağlantısını keser
/speedtest - İnternet hızını ölçer

📁 <b>Dosya İşlemleri:</b>
/files [yol] - Klasör içeriğini listeler
    Örnek: <code>/files C:\\Users</code>
/download [dosya_yolu] - Dosyayı indirir
    Örnek: <code>/download C:\\rapor.pdf</code>

🔒 <b>Güç Yönetimi:</b>
/schedule_power [shutdown/restart/sleep] [dakika] - Zamanlanmış güç işlemi
    Örnek: <code>/schedule_power shutdown 30</code>
/cancel_power - Zamanlanmış güç işlemini iptal et

🛠 <b>Diğer Özellikler:</b>
/clipboard - Pano içeriğini gösterir
/help veya /komutlar - Bu yardım mesajını gösterir

🔒 <b>Güvenlik:</b>
/unauthorized_attempts - Yetkisiz erişim denemelerini göster
/block [kullanıcı_id] - Kullanıcıyı engelle
/unblock [kullanıcı_id] - Kullanıcının engelini kaldır

<i>⚠️ Not: Tüm komutlar sadece yetkili kullanıcı tarafından kullanılabilir.</i>
"""
        await update.message.reply_text(help_text, parse_mode='HTML')

    @authorized_only
    async def system_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """CPU, RAM ve Disk kullanım bilgilerini göster"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        info = f"""
💻 *Sistem Bilgileri*

*Donanım:*
• İşlemci: {system.processor}
• CPU Kullanımı: {cpu_percent}%
• Çekirdek Sayısı: {psutil.cpu_count()}

*Bellek:*
• RAM Kullanımı: {memory.percent}%
• Toplam RAM: {memory.total // (1024**3)} GB
• Kullanılan: {memory.used // (1024**3)} GB
• Boş: {memory.free // (1024**3)} GB

*Depolama:*
• Disk Kullanımı: {disk.percent}%
• Toplam Alan: {disk.total // (1024**3)} GB
• Boş Alan: {disk.free // (1024**3)} GB

*Sistem:*
• OS: {system.system} {system.release}
• Sürüm: {system.version}
• Makine: {system.machine}
• {battery_status}

⏰ Güncelleme: {datetime.now().strftime('%H:%M:%S')}
"""
        await update.message.reply_text(info, parse_mode='Markdown')

    @authorized_only
    async def internet_speed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """İnternet hızını ölç"""
        await update.message.reply_text("İnternet hızı lçülüyor... (Bu işlem biraz zaman alabilir)")
        st = speedtest.Speedtest()
        download_speed = st.download() / 1_000_000  # Mbps
        upload_speed = st.upload() / 1_000_000  # Mbps
        
        result = f"""
🌐 *İnternet Hızı:*
Download: {download_speed:.2f} Mbps
Upload: {upload_speed:.2f} Mbps
"""
        await update.message.reply_text(result, parse_mode='Markdown')

    @authorized_only
    async def battery_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Batarya durumunu göster"""
        battery = psutil.sensors_battery()
        if battery:
            status = "Şarj oluyor ⚡" if battery.power_plugged else "Pilde 🔋"
            info = f"""
🔋 *Batarya Durumu*

• Şarj Seviyesi: {battery.percent}%
• Durum: {status}
• Kalan Süre: {timedelta(seconds=battery.secsleft)} (tahmini)
"""
        else:
            info = "🖥️ *Batarya Bilgisi*\n\nBu cihazda batarya bulunmuyor veya bilgi alınamıyor."
        
        keyboard = [[InlineKeyboardButton("🔄 Yenile", callback_data=Callbacks.SYS_BATTERY)],
                   [InlineKeyboardButton("◀️ Geri", callback_data=Callbacks.MENU_SYSTEM)]]
        
        await query.edit_message_text(
            info,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    @authorized_only
    async def system_temp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sistem durumunu göster"""
        info = """
🖥 *Sistem Durumu:*
CPU Kullanımı: {}%
RAM Kullanımı: {}%
CPU Frekansı: {:.1f} MHz
""".format(
            psutil.cpu_percent(),
            psutil.virtual_memory().percent,
            psutil.cpu_freq().current
        )
        await update.message.reply_text(info, parse_mode='Markdown')

    @authorized_only
    async def list_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Belirtilen klasördeki dosyaları listele"""
        path = ' '.join(context.args) if context.args else os.getcwd()
        try:
            files = os.listdir(path)
            message = f"📂 *{path} içeriği:*\n\n"
            for f in files:
                full_path = os.path.join(path, f)
                size = os.path.getsize(full_path) / (1024*1024)  # MB
                message += f"{'📁' if os.path.isdir(full_path) else '📄'} {f} ({size:.1f} MB)\n"
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"Hata: {str(e)}")

    @authorized_only
    async def download_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Belirtilen dosyayı Telegram'a gönder"""
        if not context.args:
            await update.message.reply_text("Lütfen bir dosya yolu belirtin.")
            return
        
        file_path = ' '.join(context.args)
        try:
            if os.path.getsize(file_path) > 50 * 1024 * 1024:  # 50MB limit
                await update.message.reply_text("Dosya boyutu çok büyük (max: 50MB)")
                return
            
            await update.message.reply_document(document=open(file_path, "rb"))
        except Exception as e:
            await update.message.reply_text(f"Hata: {str(e)}")

    @authorized_only
    async def change_brightness(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ekran parlaklığını ayarla"""
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Lütfen 0-100 arası bir değer girin.")
            return
        
        brightness = int(context.args[0])
        if 0 <= brightness <= 100:
            try:
                import wmi
                wmi.WMI(namespace='wmi').WmiMonitorBrightnessMethods()[0].WmiSetBrightness(brightness, 0)
                await update.message.reply_text(f"Parlaklık {brightness} olarak ayarlandı.")
            except Exception as e:
                await update.message.reply_text(f"Hata: {str(e)}")
        else:
            await update.message.reply_text("Geçersiz parlaklık değeri.")

    @authorized_only
    async def get_clipboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pano içeriğini göster"""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            await update.message.reply_text(f"📋 Pano içeriği:\n{data}")
        except Exception as e:
            await update.message.reply_text(f"Hata: {str(e)}")

    @authorized_only
    async def performance_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Detaylı performans raporu oluştur"""
        report = "📊 *Sistem Performans Raporu*\n\n"
        
        # CPU Bilgileri
        cpu_freq = psutil.cpu_freq()
        report += f"*CPU:*\n"
        report += f"- Kullanım: {psutil.cpu_percent()}%\n"
        report += f"- Frekans: {cpu_freq.current:.1f}MHz\n"
        report += f"- Çekirdek Sayısı: {psutil.cpu_count()}\n\n"
        
        # RAM Bilgileri
        mem = psutil.virtual_memory()
        report += f"*RAM:*\n"
        report += f"- Toplam: {mem.total/1024/1024/1024:.1f}GB\n"
        report += f"- Kullanılan: {mem.used/1024/1024/1024:.1f}GB\n"
        report += f"- Boş: {mem.free/1024/1024/1024:.1f}GB\n\n"
        
        # Disk Bilgileri
        report += "*Diskler:*\n"
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                report += f"- {partition.device}: {usage.percent}% dolu\n"
            except:
                continue
        
        # Ağ Bilgileri
        net_io = psutil.net_io_counters()
        report += f"\n*Ağ İstatistikleri:*\n"
        report += f"- Gönderilen: {net_io.bytes_sent/1024/1024:.1f}MB\n"
        report += f"- Alınan: {net_io.bytes_recv/1024/1024:.1f}MB\n"
        
        await update.message.reply_text(report, parse_mode='Markdown')

    @authorized_only
    async def schedule_power_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Zamanlanmış güç işlemi"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "Kullanım: /schedule_power <action> <minutes>\n"
                "Actions: shutdown, restart, sleep\n"
                "Örnek: /schedule_power shutdown 30"
            )
            return
        
        action = context.args[0].lower()
        try:
            minutes = int(context.args[1])
        except ValueError:
            await update.message.reply_text("❌ Geçersiz süre! Dakika olarak sayı girin.")
            return
        
        actions = {
            'shutdown': ('Kapatma', 'shutdown /s /t'),
            'restart': ('Yeniden başlatma', 'shutdown /r /t'),
            'sleep': ('Uyku modu', 'rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
        }
        
        if action not in actions:
            await update.message.reply_text(
                "❌ Geçersiz işlem!\n"
                "Kullanılabilir işlemler: shutdown, restart, sleep"
            )
            return
        
        action_name, command = actions[action]
        
        if action != 'sleep':
            command = f"{command} {minutes * 60}"
        
        try:
            os.system(command)
            await update.message.reply_text(
                f"⏰ {action_name} işlemi {minutes} dakika sonra gerçekleşecek\n"
                "İptal etmek için /cancel_power komutunu kullanın."
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {str(e)}")

    @authorized_only
    async def cancel_power_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Zamanlanmış güç işlemini iptal et"""
        try:
            os.system('shutdown /a')
            await update.message.reply_text("✅ Zamanlanmış güç işlemi iptal edildi")
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {str(e)}")

    @authorized_only
    async def block_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Kullanıcıyı engelle"""
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Kullanım: /block <user_id>")
            return
        
        user_id = int(context.args[0])
        if user_id == AUTHORIZED_USER_ID:
            await update.message.reply_text("❌ Yetkili kullanıcıyı engelleyemezsiniz!")
            return
        
        self.blocked_users.add(user_id)
        await update.message.reply_text(f"🚫 {user_id} ID'li kullanıcı engellendi.")

    @authorized_only
    async def unblock_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Kullanıcnın engelini kaldır"""
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Kullanım: /unblock <user_id>")
            return
        
        user_id = int(context.args[0])
        if user_id in self.blocked_users:
            self.blocked_users.remove(user_id)
            await update.message.reply_text(f"✅ {user_id} ID'li kullanıcının engeli kaldırıldı.")
        else:
            await update.message.reply_text("Bu kullanıcı zaten engellenmemiş.")

    @authorized_only
    async def restart_pc(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bilgisayarı yeniden başlat"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Evet", callback_data='restart_yes'),
                InlineKeyboardButton("❌ Hayır", callback_data='restart_no')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔄 Bilgisayarı yeniden başlatmak istediğinize emin misiniz?",
            reply_markup=reply_markup
        )

    @authorized_only
    async def show_running_apps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Çalışan uygulamaları butonlar halinde göster"""
        apps = []
        for proc in psutil.process_iter(['name', 'pid', 'memory_percent']):
            try:
                # Sadece penceresi olan uygulamaları listele
                if proc.info['memory_percent'] > 0.1:  # Önemsiz işlemleri filtrele
                    apps.append({
                        'name': proc.info['name'],
                        'pid': proc.info['pid'],
                        'memory': proc.info['memory_percent']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # RAM kullanımına g��re sırala
        apps.sort(key=lambda x: x['memory'], reverse=True)
        
        # En çok RAM kullanan 10 uygulamayı göster
        keyboard = []
        for app in apps[:10]:
            keyboard.append([InlineKeyboardButton(
                f"🚫 {app['name']} ({app['memory']:.1f}%)",
                callback_data=f"kill_{app['pid']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📱 *Çalışan Uygulamalar*\n"
            "Kapatmak istediğiniz uygulamaya tıklayın:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Buton tıklamalarını işle"""
        query = update.callback_query
        await query.answer()

        # Ana menü navigasyonu
        if query.data == Callbacks.MENU_MAIN:
            # Eğer herhangi bir kayıt devam ediyorsa uyarı ver
            if self.webcam_monitoring or self.recording_screen or self.recording_audio:
                await query.edit_message_text(
                    "⚠️ Aktif kayıt işlemi devam ediyor!\n"
                    "Ana menüye dönmeden önce lütfen kaydı durdurun.",
                    reply_markup=create_camera_menu()
                )
                return
            
            await query.edit_message_text(
                "🤖 *Ana Menü*\nLütfen bir işlem seçin:",
                reply_markup=create_main_menu(),
                parse_mode='Markdown'
            )
            return

        elif query.data == Callbacks.MENU_SYSTEM:
            await query.edit_message_text(
                text="💻 *Sistem Menüsü*\n\n"
                     "Lütfen yapmak istediğiniz işlemi seçin:\n\n"
                     "📊 Sistem Bilgisi - Detaylı donanım ve performans bilgileri\n"
                     "💾 Performans - CPU, RAM ve disk kullanım raporu\n"
                     "🔋 Batarya - Pil durumu ve kalan süre\n"
                     "📸 Ekran Görüntüsü - Anlık ekran görüntüsü al",
                reply_markup=create_system_menu(),
                parse_mode='Markdown'
            )
            return

        elif query.data == Callbacks.MENU_POWER:
            await query.edit_message_text(
                "⚡ *Güç Menüsü*\nLütfen bir işlem seçin:",
                reply_markup=create_power_menu(),
                parse_mode='Markdown'
            )
            return

        elif query.data == Callbacks.MENU_APPS:
            apps = []
            for proc in psutil.process_iter(['name', 'pid', 'memory_percent']):
                try:
                    if proc.info['memory_percent'] > 0.1:
                        apps.append({
                            'name': proc.info['name'],
                            'pid': proc.info['pid'],
                            'memory': proc.info['memory_percent']
                        })
                except:
                    continue

            apps.sort(key=lambda x: x['memory'], reverse=True)
            keyboard = []
            for app in apps[:10]:
                keyboard.append([InlineKeyboardButton(
                    f"🚫 {app['name']} ({app['memory']:.1f}%)",
                    callback_data=f"kill_{app['pid']}"
                )])
            keyboard.append([InlineKeyboardButton("◀️ Ana Menü", callback_data=Callbacks.MENU_MAIN)])
            await query.edit_message_text(
                "📱 *Çalışan Uygulamalar*\nKapatmak istediğiniz uygulamaya tıklayın:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return

        # Güç işlemleri
        elif query.data == Callbacks.POWER_SHUTDOWN:
            await query.edit_message_text("⭕ Bilgisayar kapatılıyor...")
            os.system("shutdown /s /t 1")

        elif query.data == Callbacks.POWER_RESTART:
            await query.edit_message_text("🔄 Bilgisayar yeniden başlatılıyor...")
            os.system("shutdown /r /t 1")

        elif query.data == Callbacks.POWER_LOCK:
            ctypes.windll.user32.LockWorkStation()
            await query.edit_message_text("🔒 Ekran kilitlendi")

        # Sistem işlemleri
        elif query.data == Callbacks.SYS_INFO:
            try:
                # Sistem bilgilerini al
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                battery = psutil.sensors_battery()
                system = platform.uname()
                
                # Batarya durumu
                if battery:
                    battery_status = f"🔋 Batarya: {battery.percent}% ({'Şarjda ⚡' if battery.power_plugged else 'Pilde'})"
                else:
                    battery_status = "🔌 Masaüstü PC"
                
                info = f"""
💻 *Sistem Bilgileri*

*Donanım:*
• İşlemci: {system.processor}
• CPU Kullanımı: {cpu_percent}%
• Çekirdek Sayısı: {psutil.cpu_count()}

*Bellek:*
• RAM Kullanımı: {memory.percent}%
• Toplam RAM: {memory.total // (1024**3)} GB
• Kullanılan: {memory.used // (1024**3)} GB
• Boş: {memory.free // (1024**3)} GB

*Depolama:*
• Disk Kullanımı: {disk.percent}%
• Toplam Alan: {disk.total // (1024**3)} GB
• Boş Alan: {disk.free // (1024**3)} GB

*Sistem:*
• OS: {system.system} {system.release}
• Sürüm: {system.version}
• Makine: {system.machine}
• {battery_status}

⏰ Güncelleme: {datetime.now().strftime('%H:%M:%S')}
"""
                keyboard = [[InlineKeyboardButton("🔄 Yenile", callback_data=Callbacks.SYS_INFO)],
                           [InlineKeyboardButton("◀️ Geri", callback_data=Callbacks.MENU_SYSTEM)]]
                
                await query.edit_message_text(
                    info,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            except Exception as e:
                await query.edit_message_text(
                    f"❌ Sistem bilgileri alınırken hata oluştu: {str(e)}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Geri", callback_data=Callbacks.MENU_SYSTEM)
                    ]])
                )

        elif query.data == Callbacks.SYS_PERF:
            try:
                # Performans raporu oluştur
                report = "📊 *Sistem Performans Raporu*\n\n"
                
                # CPU Bilgileri
                cpu_freq = psutil.cpu_freq()
                report += f"*CPU:*\n"
                report += f"- Kullanım: {psutil.cpu_percent()}%\n"
                report += f"- Frekans: {cpu_freq.current:.1f}MHz\n"
                report += f"- Çekirdek Sayısı: {psutil.cpu_count()}\n\n"
                
                # RAM Bilgileri
                mem = psutil.virtual_memory()
                report += f"*RAM:*\n"
                report += f"- Toplam: {mem.total/1024/1024/1024:.1f}GB\n"
                report += f"- Kullanılan: {mem.used/1024/1024/1024:.1f}GB\n"
                report += f"- Boş: {mem.free/1024/1024/1024:.1f}GB\n\n"
                
                # Disk Bilgileri
                report += "*Diskler:*\n"
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        report += f"- {partition.device}: {usage.percent}% dolu\n"
                    except:
                        continue
                
                keyboard = [[InlineKeyboardButton("🔄 Yenile", callback_data=Callbacks.SYS_PERF)],
                           [InlineKeyboardButton("◀️ Geri", callback_data=Callbacks.MENU_SYSTEM)]]
                
                await query.edit_message_text(
                    report,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            except Exception as e:
                await query.edit_message_text(
                    f"❌ Performans bilgileri alınırken hata oluştu: {str(e)}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Geri", callback_data=Callbacks.MENU_SYSTEM)
                    ]])
                )

        elif query.data == Callbacks.SYS_BATTERY:
            try:
                battery = psutil.sensors_battery()
                if battery:
                    status = "⚡ Şarj Oluyor" if battery.power_plugged else "🔋 Pil Kullanılıyor"
                    time_left = str(timedelta(seconds=battery.secsleft)) if battery.secsleft != -1 else "Hesaplanamıyor"
                    
                    info = f"""
🔋 *Batarya Durumu*

• Şarj Seviyesi: {battery.percent}%
• Durum: {status}
• Kalan Süre: {time_left}
• Güç Bağlı: {'✅' if battery.power_plugged else '❌'}

⏰ Güncelleme: {datetime.now().strftime('%H:%M:%S')}
"""
                else:
                    info = "🖥️ *Batarya Bilgisi*\n\nBu cihazda batarya bulunmuyor veya bilgi alınamıyor."
                
                keyboard = [[InlineKeyboardButton("🔄 Yenile", callback_data=Callbacks.SYS_BATTERY)],
                           [InlineKeyboardButton("◀️ Geri", callback_data=Callbacks.MENU_SYSTEM)]]
                
                await query.edit_message_text(
                    info,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            except Exception as e:
                await query.edit_message_text(
                    f"❌ Batarya bilgileri alınırken hata oluştu: {str(e)}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Geri", callback_data=Callbacks.MENU_SYSTEM)
                    ]])
                )

        elif query.data == Callbacks.SYS_SCREEN:
            try:
                screenshot = pyautogui.screenshot()
                screenshot.save("screenshot.png")
                
                # Önce fotoğrafı gönder
                await query.message.reply_photo(
                    photo=open("screenshot.png", "rb"),
                    caption="📸 Ekran görüntüsü alındı."
                )
                
                # Sonra sistem menüsünü göster
                await query.edit_message_text(
                    "💻 *Sistem Menüsü*\n\n"
                    "Lütfen yapmak istediğiniz işlemi seçin:\n\n"
                    "📊 Sistem Bilgisi - Detaylı donanım ve performans bilgileri\n"
                    "💾 Performans - CPU, RAM ve disk kullanım raporu\n"
                    "🔋 Batarya - Pil durumu ve kalan süre\n"
                    "📸 Ekran Görüntüsü - Anlık ekran görüntüsü al",
                    reply_markup=create_system_menu(),
                    parse_mode='Markdown'
                )
                
                # Geçici dosyayı sil
                os.remove("screenshot.png")
            except Exception as e:
                await query.edit_message_text(
                    f"❌ Ekran görüntüsü alınırken hata oluştu: {str(e)}",
                    reply_markup=create_system_menu()
                )

        # Uygulama kapatma işlemi
        elif query.data.startswith('kill_'):
            try:
                pid = int(query.data.split('_')[1])
                process = psutil.Process(pid)
                process_name = process.name()
                process.kill()
                await query.edit_message_text(
                    f"✅ {process_name} başarıyla kapatıldı!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Geri", callback_data=Callbacks.MENU_APPS)
                    ]])
                )
            except Exception as e:
                await query.edit_message_text(f"❌ Hata: {str(e)}")

        # Ses menüsü
        elif query.data == Callbacks.MENU_VOLUME:
            current_volume = self.get_current_volume()
            await query.edit_message_text(
                f"🔊 *Ses Menüsü*\nMevcut ses seviyesi: {current_volume}%\nLütfen bir işlem seçin:",
                reply_markup=create_volume_menu(),
                parse_mode='Markdown'
            )
            return

        # Ses kontrolleri
        elif query.data in [Callbacks.VOL_UP, Callbacks.VOL_DOWN, Callbacks.VOL_MUTE]:
            try:
                current_volume = self.get_current_volume()
                
                if query.data == Callbacks.VOL_UP:
                    new_volume = min(current_volume + 10, 100)
                elif query.data == Callbacks.VOL_DOWN:
                    new_volume = max(current_volume - 10, 0)
                else:  # VOL_MUTE
                    new_volume = 0
                
                if self.set_volume(new_volume):
                    message = "🔇 Ses kapatıldı" if new_volume == 0 else f"🔊 Ses seviyesi {new_volume}% olarak ayarlandı"
                    await query.edit_message_text(
                        message,
                        reply_markup=create_volume_menu()
                    )
                else:
                    await query.edit_message_text(
                        "❌ Ses ayarlanırken hata oluştu!",
                        reply_markup=create_volume_menu()
                    )
            except Exception as e:
                print(f"Ses kontrolü hatası: {str(e)}")
                await query.edit_message_text(
                    "❌ Ses kontrolünde hata oluştu!",
                    reply_markup=create_volume_menu()
                )
            return

        # Kamera ve Kayıt menüs
        elif query.data == Callbacks.MENU_CAMERA:
            await query.edit_message_text(
                "📸 *Kamera ve Kayıt Menüsü*\n\n"
                "• Webcam Fotoğraf - Anlık fotoğraf çeker\n"
                "• Hareket Algılama - Webcam ile hareketi algılar\n"
                "• Ses Kaydı - Ses kaydı alır\n"
                "• Ekran Kaydı - Ekran videosu kaydeder",
                reply_markup=create_camera_menu(),
                parse_mode='Markdown'
            )

        # Webcam fotoğraf çekme
        elif query.data == Callbacks.CAM_PHOTO:
            await query.edit_message_text("📸 Fotoğraf çekiliyor...")
            if await self.take_webcam_photo():
                try:
                    await query.message.reply_photo(
                        photo=open("webcam.jpg", "rb"),
                        caption="📸 Webcam Fotoğrafı"
                    )
                    os.remove("webcam.jpg")
                    await query.edit_message_text(
                        "✅ Fotoğraf çekildi!",
                        reply_markup=create_camera_menu()
                    )
                except Exception as e:
                    await query.edit_message_text(
                        f"❌ Fotoğraf gönderilirken hata oluştu: {str(e)}",
                        reply_markup=create_camera_menu()
                    )
            else:
                await query.edit_message_text(
                    "❌ Fotoğraf çekilemedi! Kamera bağlantısını kontrol edin.",
                    reply_markup=create_camera_menu()
                )
            return

        # Hareket algılama kontrolü
        elif query.data == Callbacks.CAM_MONITOR:
            if self.recording_screen or self.recording_audio:
                await query.edit_message_text(
                    "❌ Ekran kaydı veya ses kaydı devam ederken hareket algılama başlatılamaz.\n"
                    "Lütfen önce diğer kaydı durdurun.",
                    reply_markup=create_camera_menu()
                )
                return
            
            if not self.webcam_monitoring:
                await query.edit_message_text(
                    "👁️ Hareket algılama başlatılıyor...",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🛑 Hareket Algılamayı Durdur", callback_data=Callbacks.CAM_MONITOR_STOP)
                    ]])
                )
                # Hareket algılamayı ayrı bir thread'de başlat
                Thread(target=lambda: asyncio.run(self.start_webcam_monitor())).start()
            else:
                self.webcam_monitoring = False
                await query.edit_message_text(
                    "✅ Hareket algılama durduruldu!",
                    reply_markup=create_camera_menu()
                )
            return

        # Hareket algılamayı durdurma
        elif query.data == Callbacks.CAM_MONITOR_STOP:
            if self.webcam_monitoring:
                self.webcam_monitoring = False
                await query.edit_message_text(
                    "✅ Hareket algılama durduruldu!",
                    reply_markup=create_camera_menu()
                )
            else:
                await query.edit_message_text(
                    "❌ Hareket algılama zaten kapalı!",
                    reply_markup=create_camera_menu()
                )

        # Ekran kaydı kontrolü
        elif query.data == Callbacks.RECORD_SCREEN:
            if self.webcam_monitoring or self.recording_audio:
                await query.edit_message_text(
                    "❌ Hareket algılama veya ses kaydı devam ederken ekran kaydı başlatılamaz.\n"
                    "Lütfen önce diğer kaydı durdurun.",
                    reply_markup=create_camera_menu()
                )
                return
            
            if not self.recording_screen:
                # Süre seçimi için butonlar
                keyboard = [
                    [
                        InlineKeyboardButton("10 saniye", callback_data="screen_10"),
                        InlineKeyboardButton("30 saniye", callback_data="screen_30")
                    ],
                    [
                        InlineKeyboardButton("60 saniye", callback_data="screen_60"),
                        InlineKeyboardButton("90 saniye", callback_data="screen_90")
                    ],
                    [
                        InlineKeyboardButton("120 saniye", callback_data="screen_120")
                    ],
                    [InlineKeyboardButton("❌ İptal", callback_data=Callbacks.MENU_CAMERA)]
                ]
                
                await query.edit_message_text(
                    "🎥 Ekran kaydı süresi seçin:\n\n"
                    "Not: Uzun kayıtlar daha büyük dosya boyutuna sahip olacaktır.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                self.recording_screen = False
                await query.edit_message_text(
                    "✅ Ekran kaydı durduruldu!",
                    reply_markup=create_camera_menu()
                )
            return

        # Ekran kaydı süresi seçimi
        elif query.data.startswith("screen_"):
            try:
                duration = int(query.data.split("_")[1])
                await query.edit_message_text(f"🎥 {duration} saniyelik ekran kaydı başlatılıyor...")
                
                self.recording_screen = True
                if await self.record_screen(duration):
                    # Video dosyasını gönder
                    await query.message.reply_video(
                        video=open("screen_recording.mp4", "rb"),
                        caption=f"🎥 {duration} Saniyelik Ekran Kaydı",
                        supports_streaming=True
                    )
                    # Dosyayı sil
                    os.remove("screen_recording.mp4")
                    await query.edit_message_text(
                        "✅ Ekran kaydı tamamlandı!",
                        reply_markup=create_camera_menu()
                    )
                else:
                    await query.edit_message_text(
                        "❌ Ekran kaydı başarısız!",
                        reply_markup=create_camera_menu()
                    )
                self.recording_screen = False
            except Exception as e:
                print(f"Ekran kaydı işleme hatası: {str(e)}")
                await query.edit_message_text(
                    "❌ Ekran kaydı sırasında hata oluştu!",
                    reply_markup=create_camera_menu()
                )
                self.recording_screen = False
            return

        # Ses kaydı kontrolü
        elif query.data == Callbacks.RECORD_AUDIO:
            if self.webcam_monitoring or self.recording_screen:
                await query.edit_message_text(
                    "❌ Hareket algılama veya ekran kaydı devam ederken ses kaydı başlatılamaz.\n"
                    "Lütfen önce diğer kaydı durdurun.",
                    reply_markup=create_camera_menu()
                )
                return
            
            if not self.recording_audio:
                self.recording_audio = True
                # Ses kaydı başlat...
                await query.edit_message_text(
                    "🎙️ Kaç saniyelik ses kaydı almak istiyorsunuz? (5-60 saniye)",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("10 saniye", callback_data="audio_10"),
                        InlineKeyboardButton("30 saniye", callback_data="audio_30")
                    ], [
                        InlineKeyboardButton("60 saniye", callback_data="audio_60"),
                        InlineKeyboardButton("İptal", callback_data=Callbacks.MENU_CAMERA)
                    ]])
                )
            else:
                self.recording_audio = False
                await query.edit_message_text(
                    "✅ Ses kaydı durduruldu!",
                    reply_markup=create_camera_menu()
                )
            return

        # Ses kaydı süresi seçimi
        elif query.data.startswith("audio_"):
            try:
                duration = int(query.data.split("_")[1])
                await query.edit_message_text(f"🎙️ {duration} saniyelik ses kaydı başlatılıyor...")
                
                self.recording_audio = True
                if await self.record_audio(duration):
                    # Ses dosyasını gönder
                    await query.message.reply_audio(
                        audio=open("recording.wav", "rb"),
                        caption=f"🎙️ {duration} Saniyelik Ses Kaydı",
                        duration=duration
                    )
                    # Dosyayı sil
                    os.remove("recording.wav")
                    await query.edit_message_text(
                        "✅ Ses kaydı tamamlandı!",
                        reply_markup=create_camera_menu()
                    )
                else:
                    await query.edit_message_text(
                        "❌ Ses kaydı başarısız!",
                        reply_markup=create_camera_menu()
                    )
                self.recording_audio = False
            except Exception as e:
                print(f"Ses kaydı işleme hatası: {str(e)}")
                await query.edit_message_text(
                    "❌ Ses kaydı sırasında hata oluştu!",
                    reply_markup=create_camera_menu()
                )
                self.recording_audio = False
            return

    def run(self):
        """Botu başlat"""
        print("Bot başlatılıyor...")
        try:
            self.app.run_polling()
            print("Bot başarıyla başlatıldı!")
        except Exception as e:
            print(f"Bot başlatılırken hata oluştu: {str(e)}")

    def get_current_volume(self):
        """Mevcut ses seviyesini al"""
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            current_volume = int(volume.GetMasterVolumeLevelScalar() * 100)
            volume.Release()  # COM nesnesini serbest bırak
            interface.Release()  # Interface'i serbest bırak
            return current_volume
        except Exception as e:
            print(f"Ses seviyesi alınırken hata: {str(e)}")
            return 0

    def set_volume(self, volume_level):
        """Ses seviyesini ayarla"""
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(volume_level / 100, None)
            
            # COM nesnelerini temizle
            volume.Release()
            interface.Release()
            return True
        except Exception as e:
            print(f"Ses seviyesi ayarlanırken hata: {str(e)}")
            return False

    @authorized_only
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Metin mesajlarını işle"""
        if context.user_data.get('waiting_for') == Callbacks.WAITING_AUDIO_DURATION:
            try:
                duration = int(update.message.text)
                if 5 <= duration <= 60:
                    await update.message.reply_text(f"🎙️ {duration} saniyelik ses kaydı başlıyor...")
                    if await self.record_audio(duration):
                        await update.message.reply_audio(
                            audio=open("recording.wav", "rb"),
                            caption=f"🎙️ {duration} Saniyelik Ses Kaydı"
                        )
                        os.remove("recording.wav")
                        # Ana menüye dön
                        await update.message.reply_text(
                            "🤖 *Ana Menü*\nLütfen bir işlem seçin:",
                            reply_markup=create_main_menu(),
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(
                            "❌ Ses kaydedilemedi!",
                            reply_markup=create_main_menu()
                        )
                else:
                    await update.message.reply_text(
                        "❌ Lütfen 5-60 saniye arasında bir değer girin!",
                        reply_markup=create_main_menu()
                    )
            except ValueError:
                await update.message.reply_text(
                    "❌ Lütfen geçerli bir sayı girin!",
                    reply_markup=create_main_menu()
                )
            context.user_data['waiting_for'] = None

        elif context.user_data.get('waiting_for') == Callbacks.WAITING_SCREEN_DURATION:
            try:
                duration = int(update.message.text)
                if 5 <= duration <= 120:
                    await update.message.reply_text(f"🎥 {duration} saniyelik ekran kaydı başlıyor...")
                    if await self.record_screen(duration):
                        await update.message.reply_video(
                            video=open("screen_recording.mp4", "rb"),
                            caption=f"🎥 {duration} Saniyelik Ekran Kaydı"
                        )
                        os.remove("screen_recording.mp4")
                        # Ana menüye dön
                        await update.message.reply_text(
                            "🤖 *Ana Menü*\nLütfen bir işlem seçin:",
                            reply_markup=create_main_menu(),
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(
                            "❌ Ekran kaydedilemedi!",
                            reply_markup=create_main_menu()
                        )
                else:
                    await update.message.reply_text(
                        "❌ Lütfen 5-120 saniye arasında bir değer girin!",
                        reply_markup=create_main_menu()
                    )
            except ValueError:
                await update.message.reply_text(
                    "❌ Lütfen geçerli bir sayı girin!",
                    reply_markup=create_main_menu()
                )
            context.user_data['waiting_for'] = None

        elif context.user_data.get('waiting_for_volume'):
            try:
                volume = int(update.message.text)
                if 0 <= volume <= 100:
                    if self.set_volume(volume):
                        await update.message.reply_text(
                            f"🔊 Ses seviyesi {volume}% olarak ayarlandı",
                            reply_markup=create_volume_menu()
                        )
                    else:
                        await update.message.reply_text("❌ Ses ayarlanırken hata oluştu!")
                else:
                    await update.message.reply_text("❌ Lütfen 0-100 arası bir değer girin!")
            except ValueError:
                await update.message.reply_text("❌ Lütfen geçerli bir sayı girin!")
            context.user_data['waiting_for_volume'] = False

    async def record_audio(self, duration=5):
        """Ses kaydı al"""
        try:
            print("Ses kaydı başlatılıyor...")
            fs = 44100  # Örnekleme hızı
            channels = 2  # Stereo kayıt
            
            print(f"Kayıt parametreleri: {duration} saniye, {fs} Hz, {channels} kanal")
            
            # Ses kaydını başlat
            print("Kayıt başlıyor...")
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=channels, dtype='float32')
            sd.wait()  # Kayıt tamamlanana kadar bekle
            print("Kayıt tamamlandı, dosya kaydediliyor...")
            
            # Ses dosyasını kaydet
            write('recording.wav', fs, recording)
            print("Ses dosyası kaydedildi: recording.wav")
            return True
            
        except Exception as e:
            print(f"Ses kaydı hatası: {str(e)}")
            print("Hata detayı:", e.__class__.__name__)
            import traceback
            traceback.print_exc()
            return False

    async def record_screen(self, duration=10):
        """Ekran videosu kaydet"""
        try:
            print(f"Ekran kaydı başlatılıyor... ({duration} saniye)")
            
            # Ekran boyutlarını al
            screen_width, screen_height = pyautogui.size()
            output_filename = 'screen_recording.mp4'
            fps = 10.0
            
            print(f"Video ayarları: {screen_width}x{screen_height}, {fps} FPS")
            
            # Video yazıcıyı başlat
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                output_filename, 
                fourcc, 
                fps, 
                (screen_width, screen_height)
            )
            
            if not out.isOpened():
                print("Video yazıcı açılamadı!")
                return False
            
            print("Kayıt başlıyor...")
            start_time = time.time()
            frame_count = 0
            next_frame_time = start_time
            frame_interval = 1.0 / fps
            
            try:
                while True:
                    current_time = time.time()
                    elapsed_time = current_time - start_time
                    
                    # Kayıt süresini kontrol et
                    if elapsed_time >= duration:
                        break
                    
                    # FPS kontrolü
                    if current_time < next_frame_time:
                        await asyncio.sleep(0.001)  # 1ms bekle
                        continue
                    
                    # Ekran görüntüsü al
                    screenshot = pyautogui.screenshot()
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Kareyi kaydet
                    out.write(frame)
                    frame_count += 1
                    
                    # Sonraki kare zamanını ayarla
                    next_frame_time = start_time + (frame_count + 1) * frame_interval
                    
                    # Her saniye ilerlemeyi göster
                    if frame_count % int(fps) == 0:
                        print(f"Kayıt: {elapsed_time:.1f}/{duration} saniye ({frame_count} kare)")
                
                actual_duration = time.time() - start_time
                print(f"Kayıt tamamlandı: {frame_count} kare, {actual_duration:.1f} saniye")
                return True
                
            finally:
                out.release()
                print("Video yazıcı kapatıldı")
            
        except Exception as e:
            print(f"Ekran kaydı hatası: {str(e)}")
            print("Hata detayı:", e.__class__.__name__)
            import traceback
            traceback.print_exc()
            return False

    async def take_webcam_photo(self):
        """Webcam'den fotoğraf çek"""
        cap = None
        try:
            # Farklı kamera indekslerini dene
            for camera_index in range(2):
                try:
                    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                    if cap.isOpened():
                        print(f"Kamera {camera_index} açıldı")
                        break
                except:
                    if cap:
                        cap.release()
                    continue
            
            if not cap or not cap.isOpened():
                print("Hiçbir kamera bulunamadı!")
                return False
            
            # Kamera ayarlarını yap
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Kameranın hazırlanması için bekle
            time.sleep(1)
            
            # Birkaç test karesi al
            for _ in range(3):
                ret = cap.grab()
                if not ret:
                    print("Kare yakalanamadı!")
                    return False
            
            # Son kareyi oku
            ret, frame = cap.read()
            if not ret or frame is None:
                print("Kare okunamadı!")
                return False
            
            # Fotoğrafı kaydet
            cv2.imwrite("webcam.jpg", frame)
            return True
            
        except Exception as e:
            print(f"Webcam hatası: {str(e)}")
            return False
        finally:
            if cap:
                cap.release()

    async def start_webcam_monitor(self):
        """Hareket algılamayı başlat"""
        cap = None
        try:
            self.webcam_monitoring = True
            
            # Farklı kamera indekslerini dene
            for camera_index in range(2):
                try:
                    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                    if cap.isOpened():
                        print(f"Kamera {camera_index} açıldı")
                        break
                except:
                    if cap:
                        cap.release()
                    continue
            
            if not cap or not cap.isOpened():
                print("Hiçbir kamera bulunamadı!")
                return False
            
            # Kamera ayarlarını yap
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Kameranın hazırlanması için bekle
            time.sleep(1)
            
            # İlk kareyi al
            ret, frame1 = cap.read()
            if not ret or frame1 is None:
                print("İlk kare okunamadı!")
                return False
            
            # Hareket algılama parametreleri
            min_area = 3000  # Minimum hareket alanı
            motion_detected = False
            motion_count = 0
            last_detection_time = time.time()
            
            while self.webcam_monitoring:
                try:
                    # İkinci kareyi al
                    ret, frame2 = cap.read()
                    if not ret or frame2 is None:
                        print("Kare okunamadı!")
                        break
                    
                    # Frameleri gri tonlamaya çevir
                    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
                    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
                    
                    # Gürültü azaltma
                    gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
                    gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
                    
                    # Framelerin farkını al
                    diff = cv2.absdiff(gray1, gray2)
                    
                    # Threshold uygula
                    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                    
                    # Gürültüyü azalt
                    thresh = cv2.dilate(thresh, None, iterations=2)
                    
                    # Hareket olan bölgeleri bul
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    # Büyük hareketleri kontrol et
                    current_motion = False
                    for contour in contours:
                        if cv2.contourArea(contour) > min_area:
                            current_motion = True
                            break
                    
                    current_time = time.time()
                    if current_motion and (current_time - last_detection_time) > 5:
                        motion_count += 1
                        if motion_count >= 3:  # 3 ardışık hareket gerekli
                            # Hareket algılandı, fotoğraf çek ve gönder
                            cv2.imwrite("motion.jpg", frame2)
                            await self.send_motion_alert()
                            last_detection_time = current_time
                            motion_count = 0
                    else:
                        motion_count = max(0, motion_count - 1)
                    
                    # Frameleri güncelle
                    frame1 = frame2.copy()
                    
                    # Kısa bir bekleme
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"Kare işleme hatası: {str(e)}")
                    continue
            
        except Exception as e:
            print(f"Hareket algılama hatası: {str(e)}")
        finally:
            self.webcam_monitoring = False
            if cap:
                cap.release()

    async def send_motion_alert(self):
        """Hareket algılandığında bildirim gönder"""
        try:
            # Telegram API'yi kullanarak fotoğrafı gönder
            requests.post(
                f'https://api.telegram.org/bot{TOKEN}/sendPhoto',
                files={'photo': open('motion.jpg', 'rb')},
                data={
                    'chat_id': AUTHORIZED_USER_ID,
                    'caption': '🚨 Hareket Algılandı!'
                }
            )
            os.remove('motion.jpg')
        except Exception as e:
            print(f"Hareket bildirimi gönderme hatası: {str(e)}")

    async def stop_webcam_monitor(self):
        """Hareket algılamayı durdur"""
        self.webcam_monitoring = False

if __name__ == "__main__":
    bot = RemoteControlBot()
    bot.run() 
