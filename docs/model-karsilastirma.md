# Model karşılaştırması (Faz 0.4, 16 Kasım 2026)

Kullanıcının kendi sesiyle, USB mikrofonla (USB PnP Audio Device) yapılan 24 kayıt:
İngilizce terimler içeren 20 Türkçe cümle (172 sn, 31 farklı terim), tamamı İngilizce bir cümle,
2 dakika 39 saniyelik serbest konuşma, uzaktan kısık konuşma ve sessizlik.
Kayıtlar ve cümle cümle rapor `recordings/set/` altında durur, git'e girmez.
Yeniden üretmek için: `uv run python spikes/model_compare.py`.

## Karar

**Varsayılan model `whisper-large-v3`** (faster-whisper, `float16`, `language="tr"`). Kullanıcı seçti.
`large-v3-turbo` tutulmadı: kullanıcı, daha başarısız olduğu için ikinci seçenek olarak da istemedi
(model silindi). Ekran kartı yükü önemli değil; ileride yalnızca **daha iyi** bir model çıkarsa eklenir.
Uygulama karışık dil hedefiyle devam eder; "yalnızca Türkçe" kipine ve Qwen3-ASR denemesine gerek kalmadı.

## Özet tablo

Ayarlar: **düz** = yalnızca `language="tr"`; **ipucu** = noktalı örnek bir Türkçe metin (`initial_prompt`);
**ipucu + sözlük** = ayrıca cümlelerdeki İngilizce terimlerin listesi (`hotwords`, yani en iyi durum).

| Model | Ayar | Kelime hatası | Harf hatası | İngilizce terim | Noktalama | Süre (172 sn ses) |
|---|---|---|---|---|---|---|
| large-v3 | düz | %4,0 | %1,1 | 29/31 | 18/20 | 6,2 sn |
| large-v3 | ipucu | %4,6 | %1,2 | 29/31 | 20/20 | 6,5 sn |
| large-v3 | ipucu + sözlük | %3,4 | %0,8 | 30/31 | 20/20 | 6,6 sn |
| large-v3-turbo | düz | %4,0 | %1,1 | 29/31 | 18/20 | 3,4 sn |
| large-v3-turbo | ipucu | %6,3 | %1,4 | 29/31 | 20/20 | 3,4 sn |
| large-v3-turbo | ipucu + sözlük | %6,3 | %1,4 | 29/31 | 19/20 | 3,4 sn |
| BuzzASR/turkish | düz | %9,8 | %2,6 | 23/31 | 1/20 | 6,0 sn |
| BuzzASR/turkish | ipucu | %14,9 | %2,3 | 25/31 | 19/20 | 6,4 sn |
| BuzzASR/turkish | ipucu + sözlük | %13,2 | %1,6 | 29/31 | 19/20 | 6,6 sn |

Ekran kartı belleği: large-v3 yaklaşık 3,9 GB, large-v3-turbo yaklaşık 2,2 GB.

## Bulgular

- **large-v3 ile turbo okunan cümlelerde berabere.** "düz" ayarda sonuçları aynı; diğer ayarlardaki
  bir iki kelimelik fark 20 cümlede anlamlı değil.
- **Serbest konuşmada large-v3 daha doğru.** İkisinin ayrıştığı yerlerde (Pomodoro/Komodoro,
  ölçüde/acıda, bölün/böyle, Listeniz/Bizdeniz) kullanıcı large-v3'ün doğru yazdığını söyledi.
- **BuzzASR elendi.** Sözlük verilmeyince İngilizce terimleri bozuyor (23–25/31), harf hatası
  yaklaşık iki katı, noktadan sonra boşluk koymuyor. Model ve dönüştürülmüş kopyası silindi.
- **İki Whisper modelinin de takıldığı terimler:** "commit" (komüt/komit) ve "refactor" (faktör).
  Sözlük large-v3'te "commit"i düzeltti, "refactor" yanlış kaldı.
- **Konuşma içindeki İngilizce cümleler** ("it's about 20 minutes, you know") İngilizce yazıldı.
  **Tamamı İngilizce bir cümle** ise `language="tr"` ile Türkçeye çevrildi ya da bozuldu.
- **Uzun konuşma hızlı ve kararlı:** 159 sn'lik kayıt large-v3'te 6 sn, turbo'da 2 sn sürdü;
  "düz" ve "ipucu" ayarlarında hiçbir bölüm yeniden denenmedi.
- **Sayılan hataların bir kısmı gerçek hata değil:** "hâlâ" yerine "hala"; 17. cümlede üç model de
  "Linux terminali" yazdı (büyük olasılıkla öyle okundu).

## Açık konular

- **İpucu metni:** noktalamayı 18'den 20'ye çıkardı ama iki modelde de bir iki yeni kelime hatası
  getirdi (ör. "Şifremi" → "Küfremi"). Faz 1'de gerçek kullanımda karar verilecek; ayarlanabilir olsun.
- **Sözlük:** en iyi durumda bile yalnızca 1 terim düzeltti; turbo'da serbest konuşmada yeniden
  denemelere yol açtı (14 bölümün 4'ü). Faz 3'te kalıyor, etkisi yeniden ölçülmeli.
- **Uydurma metin:** bu setteki uzak ve sessiz kayıtlar bütün modellerde boş çıktı. Faz 0.3'teki uzak
  kayıt ise üç modelde de uydurma metin verdi ("Altyazı M.K.", "İzlediğiniz için teşekkür ederim.")
  ve modelin güven değerleri (konuşma-yok olasılığı, ortalama log olasılık) bunu gerçek cümlelerden
  ayırmıyor. Önlem Faz 1'de tasarlanacak (ör. bilinen kalıpların listesi, giriş seviyesi).
- **Kapsam:** yalnızca USB mikrofon ve okunan cümleler; BTD 700 ile karşılaştırma yapılmadı.

## Ek: sözlük nasıl verilmeli (Faz 3, 16 Kasım 2026)

Aynı 20 cümleyle, large-v3 üzerinde dört yol karşılaştırıldı:

| Sözlüğün veriliş biçimi | Kelime hatası | Harf hatası | İngilizce terim |
|---|---|---|---|
| Sözlük yok (yalnızca noktalama ipucu) | %4,6 | %1,2 | 29/31 |
| `hotwords` parametresi, 31 terim | %3,4 | %0,8 | 30/31 |
| İpucunun başında "Terimler: commit, refactor, pull request." (3 terim) | %2,3 | %0,6 | 31/31 |
| İpucunun başında "Terimler: …" (31 terim) | %4,0 | %1,1 | 29/31 |

- **Karar:** sözlük, ipucu metninin başına "Terimler: …" satırı olarak eklenir (`config.build_prompt`).
  `hotwords` kullanılmıyor: 3 terimle "commit"i düzeltmedi.
- **Liste kısa tutulmalı:** 31 terimlik listede etki tamamen kayboldu. Sözlüğe yalnızca gerçekten yanlış
  yazılan terimler girmeli.
- **Yan etki ve önlemi:** kısık/uzak bir kayıtta model, ipucu metnini karıştırıp çıktı diye verdi
  ("Merhaba, bugün ne yapacağıma henüz karar vermedim…"). `textguard.is_prompt_echo` bunu yakalıyor:
  çıktının kelimelerinin en az %90'ı ipucunda geçiyorsa (ve çıktı en az 5 kelimeyse) metin yazılmıyor.
  20 gerçek cümlenin ve serbest konuşmanın hiçbiri bu kurala takılmadı.
