# 🧵 Tekstil Lead Finder

Türk tekstil üreticileri için otomatik müşteri bulma ve e-posta outreach sistemi.

## ✨ Özellikler

- 🔍 **Otomatik Lead Arama**: Google, Europages, Kompass dizinlerinden potansiyel müşterileri bulur
- 📧 **E-posta Bulma**: Web sitelerinden e-posta adreslerini otomatik tespit eder
- ✅ **E-posta Doğrulama**: MX kayıt kontrolü ile geçersiz e-postaları filtreler
- 📨 **Otomatik Outreach**: Çoklu dilde e-posta şablonları (EN, DE, TR, AR)
- 📊 **Dashboard**: Streamlit tabanlı görsel yönetim paneli
- 💾 **CRM Veritabanı**: Lead takibi ve kampanya yönetimi

## 🚀 Kurulum

### 1. Gereksinimleri Yükle

```bash
cd tekstil-lead-finder
pip install -r requirements.txt
```

### 2. Ortam Değişkenlerini Ayarla

```bash
cp .env.example .env
# .env dosyasını düzenleyin
```

### 3. Veritabanını Başlat

```bash
python main.py init
```

## 📖 Kullanım

### CLI Komutları

```bash
# Lead arama
python main.py search --query "textile importer" --country Germany

# Toplu arama (Avrupa pazarı)
python main.py bulk-search --market europe

# Lead listele
python main.py list-leads --with-email

# E-posta zenginleştirme
python main.py enrich-emails

# Excel'e aktar
python main.py export --format excel

# İstatistikler
python main.py stats

# E-posta kampanyası (önizleme)
python main.py send-campaign --template initial_contact_en --dry-run

# Dashboard başlat
python main.py dashboard
```

### Web Dashboard

```bash
streamlit run dashboard/app.py
```

Tarayıcınızda `http://localhost:8501` adresini açın.

## 📁 Proje Yapısı

```
tekstil-lead-finder/
├── config/
│   └── settings.py      # Ayarlar ve hedef pazarlar
├── scrapers/
│   ├── base_scraper.py  # Temel scraper sınıfı
│   ├── google_scraper.py    # Google/DuckDuckGo arama
│   └── directory_scraper.py # Europages, Kompass
├── email_tools/
│   └── email_finder.py  # E-posta bulma ve doğrulama
├── outreach/
│   ├── email_templates.py   # E-posta şablonları
│   └── email_sender.py      # Kampanya gönderimi
├── database/
│   └── models.py        # SQLAlchemy modelleri
├── dashboard/
│   └── app.py           # Streamlit dashboard
├── data/                # Veritabanı dosyaları
├── exports/             # Excel/CSV çıktıları
├── main.py              # CLI uygulaması
├── requirements.txt
└── .env.example
```

## ⚙️ Yapılandırma

### Hedef Pazarlar

`config/settings.py` dosyasında hedef ülkeleri ve şehirleri düzenleyin:

```python
TARGET_MARKETS = {
    "europe": {
        "Germany": ["Berlin", "Hamburg", "Munich"],
        "UK": ["London", "Manchester"],
        # ...
    }
}
```

### Arama Anahtar Kelimeleri

```python
SEARCH_KEYWORDS = {
    "en": ["textile importer", "clothing wholesaler", ...],
    "de": ["textil importeur", "bekleidung großhandel", ...],
}
```

### E-posta Şablonları

`outreach/email_templates.py` dosyasında şablonları özelleştirin.

## 🔒 Gmail SMTP Kurulumu

1. Google hesabınızda 2 Faktörlü Doğrulamayı etkinleştirin
2. [App Passwords](https://myaccount.google.com/apppasswords) sayfasına gidin
3. "Mail" için yeni bir uygulama şifresi oluşturun
4. Bu 16 karakterlik şifreyi `.env` dosyasına ekleyin

## 📊 Örnek İş Akışı

```bash
# 1. Almanya'da tekstil ithalatçılarını ara
python main.py search -q "textile importer" -c Germany -e

# 2. E-postası olmayanlar için zenginleştirme yap
python main.py enrich-emails

# 3. İstatistikleri kontrol et
python main.py stats

# 4. Excel'e aktar
python main.py export --with-email

# 5. Kampanya önizleme
python main.py send-campaign --template initial_contact_en --dry-run

# 6. Gerçek kampanya (dikkatli kullanın!)
python main.py send-campaign --template initial_contact_en --no-dry-run --limit 10
```

## ⚠️ Önemli Notlar

- **Rate Limiting**: Scraping işlemlerinde otomatik gecikme uygulanır
- **Günlük Limit**: E-posta gönderiminde günlük 50 limit (spam önleme)
- **GDPR**: Avrupa müşterilerine e-posta gönderirken GDPR kurallarına uyun
- **Etik Kullanım**: Spam yapmayın, değerli içerik sunun

## 🛠️ Geliştirme

```bash
# Testleri çalıştır
pytest tests/

# Linting
flake8 .

# Type checking
mypy .
```

## 📈 Yol Haritası

- [ ] LinkedIn Sales Navigator entegrasyonu
- [ ] Hunter.io API entegrasyonu
- [ ] Otomatik takip e-postaları (drip campaign)
- [ ] WhatsApp Business API entegrasyonu
- [ ] AI ile kişiselleştirilmiş e-posta içeriği

## 📄 Lisans

Bu proje özel kullanım içindir.

## 🤝 Destek

Sorularınız için issue açabilirsiniz.
