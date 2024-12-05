# 🤖️ RemoteGuardPC

Bilgisayarınızı güvenle uzaktan kontrol edin ve izleyin. RemoteGuardPC, Telegram üzerinden Windows bilgisayarınızı yönetmenizi sağlayan güçlü ve güvenli bir bot çözümüdür.

## 🌟 Neden RemoteGuardPC?

- 🔒 Güvenli erişim ve yetkilendirme
- 🖥️ Kapsamlı sistem kontrolü
- 📸 Gelişmiş izleme özellikleri
- 🚀 Kolay kurulum ve kullanım
- 🛡️ Hareket algılama ve bildirimler

## 🌟 Özellikler

### 💻 Sistem Kontrolü
- Sistem bilgilerini görüntüleme
- Performans izleme
- Batarya durumu
- Ekran görüntüsü alma

### ⚡ Güç Yönetimi
- Bilgisayarı kapatma
- Yeniden başlatma
- Ekran kilitleme

### 📱 Uygulama Yönetimi
- Çalışan uygulamaları listeleme
- Uygulama kapatma
- RAM kullanımını görüntüleme

### 🔊 Ses Kontrolü
- Ses seviyesi ayarlama
- Sessiz modu
- Özel ses seviyesi belirleme

### 📸 Kamera ve Kayıt
- Webcam fotoğraf çekme
- Hareket algılama ve bildirim
- Ses kaydı alma (5-60 saniye)
- Ekran videosu kaydetme (5-120 saniye)

### 🔒 Güvenlik
- Tek kullanıcı erişimi
- Yetkisiz erişim koruması
- Erişim kayıtları
- Kullanıcı engelleme sistemi

## 🚀 Kurulum Adımları

### 1. Ön Gereksinimler
- Python 3.8 veya üzeri
- Windows işletim sistemi
- Telegram hesabı
- Webcam (kamera özellikleri için)
- Mikrofon (ses kaydı için)

### 2. Bot Token Alma
1. Telegram'da [@BotFather](https://t.me/botfather) ile konuşma başlatın
2. `/newbot` komutunu gönderin
3. Bot için bir isim ve kullanıcı adı belirleyin
4. Size verilen API token'ı kaydedin

### 3. Kullanıcı ID Alma
1. Telegram'da [@userinfobot](https://t.me/userinfobot) ile konuşma başlatın
2. Size verilen ID numarasını kaydedin

### 4. Kurulum
1. Bu repository'yi klonlayın:

2. Otomatik başlatma için:
   - `autostart.vbs` dosyasını çalıştırın
   - Bot Windows başlangıcında otomatik çalışacaktır

## 📱 Kullanım Kılavuzu

### Temel Komutlar
1. Telegram'da botunuza `/start` yazın
2. Ana menüden istediğiniz kategoriyi seçin:
   - 🖥️ Sistem
   - ⚡ Güç
   - 📱 Uygulamalar
   - 🔊 Ses
   - 📸 Kamera & Kayıt

### Özellik Kullanımları

#### 📸 Kamera ve Kayıt
- **Webcam Fotoğraf**: Anlık fotoğraf çeker
- **Hareket Algılama**: Hareketi algılar ve bildirim gönderir
- **Ses Kaydı**: 5-60 saniye arası kayıt alır
- **Ekran Kaydı**: 5-120 saniye arası video kaydeder

#### 💻 Sistem Kontrolü
- Sistem bilgilerini görüntüleme
- Performans durumunu izleme
- Batarya seviyesi kontrolü
- Ekran görüntüsü alma

#### 🔊 Ses Kontrolü
- Ses seviyesini artırma/azaltma
- Özel seviye belirleme (0-100)
- Sessiz moda alma

## ⚠️ Güvenlik Önlemleri

### Önemli Uyarılar
1. Bot token'ınızı kimseyle paylaşmayın
2. `.env` dosyasını gizli tutun
3. Yetkisiz erişim girişimlerini takip edin
4. Düzenli olarak log kayıtlarını kontrol edin

### Güvenlik Özellikleri
- Tek kullanıcı erişimi
- Yetkisiz erişim bildirimleri
- Kullanıcı engelleme sistemi
- Erişim kayıtları tutma

## 🔧 Sorun Giderme

### Sık Karşılaşılan Sorunlar

1. **Bot Yanıt Vermiyor**
   - İnternet bağlantınızı kontrol edin
   - `.env` dosyasındaki token'ı kontrol edin
   - Bot'un çalışır durumda olduğunu doğrulayın

2. **Kamera/Mikrofon Çalışmıyor**
   - Cihaz izinlerini kontrol edin
   - Sürücülerin güncel olduğundan emin olun
   - Başka uygulamaların donanımı kullanmadığını kontrol edin

3. **Otomatik Başlatma Çalışmıyor**
   - `autostart.vbs` dosyasını yönetici olarak çalıştırın
   - Windows Görev Yöneticisi'nden başlangıç ayarlarını kontrol edin

## 📝 Lisans

RemoteGuardPC özgür bir yazılımdır ve MIT lisansı altında dağıtılmaktadır. Bu yazılımı;

- ✅ Özgürce kullanabilir
- ✅ Değiştirebilir
- ✅ Dağıtabilir
- ✅ Ticari amaçla kullanabilirsiniz

Tek şart, orijinal lisans ve telif hakkı bildiriminin korunmasıdır.

Detaylı bilgi için [LICENSE](LICENSE) dosyasına bakınız.

## 👨‍💻 Geliştirici

[Geliştirici Adı]
- GitHub: [@kullaniciadi](https://github.com/kullaniciadi)
- Telegram: [@kullaniciadi](https://t.me/kullaniciadi)

## 🤝 Katkıda Bulunma

1. Bu repository'yi fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/YeniOzellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik: Açıklama'`)
4. Branch'inizi push edin (`git push origin feature/YeniOzellik`)
5. Pull Request oluşturun

## 🌟 Teşekkürler

Bu projeyi kullandığınız için teşekkür ederiz. Yıldız ⭐️ vermeyi unutmayın!