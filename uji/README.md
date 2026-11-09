# Paket uji purwarupa ICA Serasi (Modul 1 sampai 4)

Semua data fiktif (nama dan kode wilayah buatan). Aman, tidak ada data Kemenkeu. Hanya butuh Python 3.9+, tanpa instal apa pun.

## Isi
| Berkas | Fungsi |
|---|---|
| `data_dummy/` | 130 desa, 120 baris koperasi (93 koperasi), 43 reviu, dan 28 berkas kasus |
| `data_dummy/harapan.json` | Kunci jawaban: tiap langkah, baris mana yang harus ditolak, kode errornya |
| `data_dummy/harapan_turunan.json` | Kunci jawaban Modul 4: 70 baris komponen_aset_desa |
| `jalankan_kasus.py` | Mengirim semua data ke aplikasi kalian lalu membandingkan dengan kunci jawaban |
| `server_tiruan.py` | Aplikasi tiruan yang sudah benar, untuk mencoba pelari dan melihat bentuk respons |
| `acuan_validator.py` | Aturan validasi dalam kode Python (bahan baca; jangan disalin mentah ke produk) |
| `buat_data_dummy.py` | Membuat ulang `data_dummy/` bila kontrak berubah |

## Cara pakai
1. Coba dulu dengan server tiruan (terminal 1): `python3 server_tiruan.py 8000`
2. Jalankan pelari (terminal 2): `python3 jalankan_kasus.py --url http://localhost:8000 --reset`
   Hasil yang benar: `Ringkasan: 29 lolos, 0 gagal`.
3. Untuk aplikasi kalian: nyalakan aplikasi, lalu jalankan perintah yang sama dengan `--url` aplikasi kalian.
4. Selama mengerjakan satu modul: `--sampai S05` (berhenti di langkah itu) atau `--hanya S12` (satu langkah).

## Aturan penting
- Langkah berurutan dan saling bergantung (data tersimpan bertambah). Selalu mulai dari basis data kosong (`--reset`).
- Bila satu langkah gagal, perbaiki **yang paling atas dulu**. Kegagalan berikutnya sering hanya akibat berantai.
- Kalau kalian yakin kunci jawaban yang salah (bukan aplikasi), jangan ubah berkasnya diam-diam. Bahas bertiga, ubah kontrak, lalu jalankan `buat_data_dummy.py`.
- Pelari ini disebut **pengujian fungsional berbasis skenario** di laporan. Jangan menyebutnya UAT: UAT dijalankan pengguna (Form UAT).

## Peta langkah
S01-S02 Modul 1 | S03-S17 Modul 2 | S18-S28 Modul 3 (S18 juga memicu Modul 4) | T01 Modul 4
