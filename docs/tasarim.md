# Tasarım planı (Faz 5)

Durum: uygulandı ve kullanıcı gerçek ekranda onayladı (17 Kasım 2026). Bütün pencereler ve simgeler bu dilde.

## Fikir

Uygulamanın adı işini söylüyor: **konuş, baskıya dönsün.** Tasarım bu yüzden dikte uygulamalarının
alışılmış "mikrofon + mor gradyan" görünümünden değil, **matbaadan** besleniyor: mürekkep, kâğıt,
baskı renkleri (camgöbeği, macenta, sarı) ve provalardaki kesim işaretleri.

- Konuşurken ekranda titreyen bir **ses çizgisi** vardır; henüz "basılmamış" ham sestir.
- Konuşma bitince çizginin yerine cümleniz gelir ve bir kitap yazı tipiyle **dizilir**.
- Dizilen metnin durduğu alan bir kutuyla değil, köşelerindeki küçük **kesim işaretleriyle** belirlenir.

Cesur olan tek şey bu geçiştir (ses çizgisi → dizili metin). Geri kalan her şey sessiz ve düzenlidir.

## Renkler

| Ad | Değer | Nerede |
|---|---|---|
| Mürekkep | `#141B27` | Pencere zemini (nötr siyah değil, koyu mavi-siyah) |
| Tabaka | `#1D2635` | Zeminden bir kat yukarıdaki yüzeyler |
| Cetvel | `#2D394C` | İnce çizgiler, kenarlıklar, taban çizgisi |
| Kâğıt | `#EEF1F5` | Ana metin |
| Kurşun | `#8E9BB0` | İkincil metin (dizgi kurşununun grisi) |
| Macenta | `#F2559B` | Canlı ses: dinleme durumu ve ses çizgisi |
| Camgöbeği | `#3CC8E6` | İşlem ve sonuç: çevriliyor, yazıldı |
| Sarı | `#FFD257` | Ana eylem: o an en olası tek düğme (Bitir, Yapıştır ya da Dinlemeyi başlat) |
| Kırmızı | `#F2705A` | Sorun (baskıda macenta ile sarının üst üste gelmesi) |

Baskı renkleri süs değil, durum bilgisidir: aynı anda en çok ikisi görünür (durum rengi + ana düğme).
"Metin hazır ama yazılmadı" bir uyarı değil, otomatik yapıştırma kapalıyken olağan sonuçtur; bu yüzden
renksiz (kâğıt rengi) gösterilir ve sarı yalnızca "Yapıştır" düğmesindedir.

## Yazı

- **Instrument Sans** (arayüz): düğmeler, etiketler, durum, sayılar. Ağırlıklar 400, 500, 600.
- **Newsreader** (dizilen metin): çevrilen cümleler, geçmiş kayıtları, düzenleme alanı. Yer tutucular italik.
- İkisi de açık lisanslı (OFL) ve uygulamayla birlikte gelir; Türkçe karakterleri tamdır.
- Ölçek (piksel): 12 · 13 · 15 · 17 · 24. Başlıklar büyük harfle yazılmaz, harf aralığı açılmaz.
- İkisi de "değişken" yazı tipi: Qt'de ağırlık `setWeight` ile değil `wght` ekseniyle verilir (`theme.ui_font`, `theme.text_font`). Stil sayfasına yazı tipi özelliği yazılmaz; yazı tipleri kodla atanır.

## Yerleşim

Her şey sola hizalıdır. Küçük pencerenin boyutu sabittir (KWin kuralı köşesini sabitlediği için).

```
Dinlerken                                        Bittiğinde
┌──────────────────────────────────────────┐    ┌──────────────────────────────────────────┐
│ ● Dinliyor                  0:08    ◐ oto│    │ ✓ Yazıldı            [Dinlemeyi başlat]  │
│                                          │    │ ⌜                                      ⌝ │
│ ▁▂▅▇▅▃▂▁▁▂▃▅▇█▇▅▃▂▁  (ses çizgisi)       │    │  Kodu commit etmeden önce testleri      │
│ ──────────────────────────────────────── │    │  çalıştırmayı unutma.                   │
│                                          │    │ ⌞                                      ⌟ │
│                  Beklet   İptal   [Bitir]│    │ ◐ oto      Düzenle  Kopyala  Yapıştır  ✕ │
└──────────────────────────────────────────┘    └──────────────────────────────────────────┘
```

Ana pencere bir defter gibidir: üstte durum ve tek büyük düğme, altında geçmiş (solda saat, sağda
dizili metin), en altta ayarlar.

## İlkeler

1. Ses macenta, sonuç camgöbeği, eylem sarı. Renk başka bir şey için kullanılmaz.
2. Kullanıcının söylediği her şey Newsreader ile, uygulamanın söylediği her şey Instrument Sans ile yazılır.
3. Kutu yerine çizgi ve kesim işareti: bir alanın sınırı, içeriği taşıyorsa çizilir.
4. Hareket yalnızca sesi gösterir (ses çizgisi) ve kullanıcının eylemine cevap verir; kendiliğinden süs animasyonu yok.
5. Düğme adı ne yapıyorsa odur ve her yerde aynıdır: "Dinlemeyi başlat", "Bitir", "Kopyala", "Yapıştır".

## Alışılmış kalıplardan bilerek kaçınılanlar

- Simsiyah zemin + tek parlak vurgu: zemin mavi-siyah mürekkep, vurgu tek değil üç baskı rengi ve her biri bir durum.
- Her şeyi aynı yuvarlak köşeli kartlara bölmek: kart yok; çizgi, boşluk ve kesim işaretleri var.
- Büyük harfli küçük etiketler, ok işaretli düğmeler, süs gradyanları: yok.

## Uygulamadaki karşılıkları

- `ui/theme.py`: renkler, yazı tipleri, ortak stil; `theme.apply(app)` uygulamanın tamamına uygular.
- `ui/widgets.py`: `Waveform` (ses çizgisi), `PrintedText` (dizili metin), `CropFrame` (kesim işaretleri), `Switch`, `Card`, `Keycap` (tuş görünümü), `Rule`, `HistoryDelegate` (geçmiş satırı).
- Uygulamanın işareti beş çizgilik bir ses çizgisidir: tepside durum rengine boyanır (`ui/tray.py`), Kickoff'ta `assets/icon.svg` olarak görünür.
- `assets/fonts/`: iki yazı tipi ve OFL lisans metinleri.
- Küçük pencereler yuvarlak köşeli ve saydam zeminlidir; sorun çıkarsa `theme.ROUNDED_WINDOWS = False`.
- Görünümü ekransız denetlemek için pencereleri `QWidget.grab()` ile PNG'ye çizip bakmak yeterli (%150 ölçek).
