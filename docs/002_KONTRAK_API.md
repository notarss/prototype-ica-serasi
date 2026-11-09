# Kontrak API dan Aturan Purwarupa ICA Serasi (Modul 1 sampai 5)

Dokumen ini adalah kesepakatan bersama A, B, dan C. Ubah hanya lewat kesepakatan bertiga,
dan catat perubahannya di bagian "Riwayat" paling bawah.

Sumber aturan: DPPL V5.04 (Bab 2.4, 2.5, 4.2, 5.1), UR V5.04, dan dokumen interoperabilitas.
Bentuk endpoint, format respons, dan kode kesalahan **tidak ditetapkan oleh sumber mana pun**.
Itu rancangan purwarupa, jadi jangan menyebutnya "mengikuti DPPL" di laporan.

## 1. Konvensi umum

- Prefiks: `/api/v1`. Format: JSON (UTF-8). Tanggal: ISO 8601 (`YYYY-MM-DD`).
- Angka uang: string desimal dengan dua angka di belakang koma (`"1000000001.00"`), bukan float.
- Porsi kepemilikan: skala 0 sampai 100, enam desimal (`33.333334`).
- Kode HTTP:
  - `200` batch diproses (walau sebagian baris ditolak, ini partial acceptance).
  - `400` isi permintaan bukan JSON atau kosong.
  - `422` struktur permintaan salah (misalnya `rows` tidak ada), seluruh batch tidak diproses.
  - `404` data tidak ditemukan. `405` UPDATE atau DELETE pada `reviu_bast` (append-only).
- Tidak ada autentikasi. Pengirim memilih peran di antarmuka (tidak dibangun sungguhan).

## 2. Endpoint penerimaan data (dipanggil pengirim pengganti SIMKOPDES)

| Endpoint | Modul | Perilaku | Pemilik |
|---|---|---|---|
| `POST /api/v1/ref-wilayah/bulk` | 1 | Terima array `rows`. Cek hanya kelengkapan dan format. Satu baris cacat berarti **seluruh batch ditolak** (kode `W1-01`). Simpan dengan upsert pada `kode_desa_kelurahan`. | B |
| `POST /api/v1/ref-kdkmp` | 2 | Lima lapis validasi berurutan, partial acceptance per baris. | A |
| `POST /api/v1/reviu-bast` | 3 | Lima pemeriksaan berurutan (lihat 4), partial acceptance per baris, append-only. | A |

### Permintaan `ref-kdkmp` (contoh)

```json
{
  "rows": [
    {
      "kode_desa_kelurahan": "3201010001",
      "nomor_induk_koperasi": "NIKOP-1",
      "nama_koperasi": "Koperasi Contoh 1",
      "struktur_kepemilikan": 2,
      "porsi_kepemilikan": 33.333334,
      "jenis_koperasi": "KDMP"
    }
  ]
}
```

Nama dan kode kecamatan, kabupaten/kota, dan provinsi **tidak dikirim**. Sistem mengisinya dari
`ref_wilayah` (UR: "elemen data lain ... diturunkan oleh SIKD").

### Permintaan `reviu-bast` (nama field mengikuti DPPL V5.04)

```json
{
  "rows": [
    {
      "uuid_reviu_bast": "5f1f0f7e-8d3e-4a52-9c45-0c8a1b9b0a11",
      "nomor_induk_koperasi": "NIKOP-1",
      "nama_koperasi": "Koperasi Contoh 1",
      "jenis_koperasi": "KDMP",
      "kode_kecamatan": "320101",
      "kode_kabkota": "3201",
      "kode_provinsi": "32",
      "nomor_reviu_bast": "R-001",
      "tanggal_reviu_bast": "2026-08-01",
      "jenis_reviu_bast": 1,
      "nilai_reviu_bast": "1000000001.00",
      "nilai_bast_bangunan_kdkmp": "600000001.00",
      "nilai_bast_sarana_prasarana_kdkmp": "300000000.00",
      "nilai_bast_kendaraan_kdkmp": "100000000.00"
    }
  ]
}
```

UR V5.05 memakai nama field lain (`nilai_BAST`, `nilai_fisik_Gerai_Pergudangan`, dan seterusnya).
Purwarupa mengikuti DPPL, jadi memakai nama V5.04.

### Respons (sama untuk ketiga endpoint)

```json
{
  "batch_id": "b2a8e6f0-1c5d-4e0b-8c1d-3d6c3f0a7a10",
  "dataset": "ref_kdkmp",
  "total": 3,
  "diterima": 2,
  "ditolak": 1,
  "hasil": [
    { "baris": 1, "status": "DITERIMA" },
    { "baris": 2, "status": "DITERIMA" },
    {
      "baris": 3,
      "status": "DITOLAK",
      "error": {
        "kode": "K2-02",
        "field": "kode_desa_kelurahan",
        "pesan": "kode_desa_kelurahan 9999999999 tidak ditemukan di ref_wilayah"
      }
    }
  ]
}
```

Hanya **satu** kesalahan per baris (kegagalan pertama), lihat keputusan D4.

### Respons `ref-wilayah/bulk` bila batch ditolak (W1-01)

HTTP tetap `200`. `diterima` = 0, `ditolak` = `total`, `batch_ditolak` = `true`. Field
`batch_ditolak` ada di respons Modul 1 saja (`false` bila diterima). `hasil` **hanya memuat baris yang
cacat**, masing-masing berstatus `DITOLAK` dengan `error.kode = "W1-01"`. Baris lain tidak didaftar.

```json
{ "batch_id": "...", "dataset": "ref_wilayah", "total": 130, "diterima": 0, "ditolak": 130,
  "batch_ditolak": true,
  "hasil": [ { "baris": 58, "status": "DITOLAK",
               "error": { "kode": "W1-01", "field": "nama_kecamatan", "pesan": "field wajib kosong" } } ] }
```

### Bentuk respons semua endpoint daftar (GET)

```json
{ "page": 1, "per_page": 20, "total": 120, "items": [ { "...": "..." } ] }
```

`total` = jumlah seluruh baris yang cocok filter (bukan jumlah `items`). Pelari kasus memakai `total`
untuk memeriksa jumlah data tersimpan, dan `items` pada `/komponen-aset-desa` memuat minimal
`nomor_induk_koperasi`, `kode_desa_kelurahan`, `nilai_reviu_bast_desa`, `nilai_bast_bangunan_desa`,
`nilai_bast_sarana_prasarana_desa`, `nilai_bast_kendaraan_desa` (uang sebagai string dua desimal).

### Mengurai angka

Uang dan porsi **harus diurai sebagai Decimal (bukan float)**. Contoh: `33.333334 + 33.333333 + 33.333333`
dengan float tidak tepat `100.000000`, padahal aturan K2-05 menuntut tepat. Di Python gunakan
`Decimal(str(x))`; di PostgreSQL gunakan `NUMERIC`. Porsi dikirim sebagai angka JSON, uang sebagai string.

## 3. Endpoint baca (dipakai layar dan pengujian)

| Endpoint | Isi | Pemilik |
|---|---|---|
| `GET /api/v1/ref-wilayah` dan `/{kode_desa_kelurahan}` | Daftar (halaman, filter `q`, `kode_provinsi`, `kode_kabkota`) dan detail | B |
| `GET /api/v1/ref-kdkmp` dan `/{kode_desa_kelurahan}` | Daftar (filter `q`, `jenis_koperasi`, `nomor_induk_koperasi`) dan detail | A (data), C (layar) |
| `GET /api/v1/reviu-bast` dan `/{uuid_reviu_bast}` | Daftar (filter `nomor_induk_koperasi`, `jenis_reviu_bast`) dan detail | A |
| `GET /api/v1/batches` dan `/{batch_id}/errors` | Riwayat pengiriman dan error log per baris | A |
| `GET /api/v1/komponen-aset-desa` | Daftar (filter `kode_desa_kelurahan`, `nomor_induk_koperasi`) | B |
| `GET /api/v1/basis-permohonan-bank` | Daftar dengan filter yang sama (Modul 5, target tambahan) | B |
| `POST /api/v1/internal/derive/{nomor_induk_koperasi}` | Bentuk ulang data turunan satu NIKOP (idempoten, untuk pengujian) | B |
| `POST /api/v1/internal/reset` | Kosongkan semua tabel data dan `error_log`, jawab `200`. Hanya untuk pengujian, jangan tampil di layar | B |

Parameter halaman: `page` (mulai 1) dan `per_page` (bawaan 20, maksimum 100).

## 4. Aturan validasi (berurutan, berhenti di kegagalan pertama)

### Modul 2, `ref_kdkmp`

| Urut | Kode | Pemeriksaan | Dasar |
|---|---|---|---|
| 1 | `K2-01` | Semua field wajib ada, tipe dan panjang benar, `struktur_kepemilikan` bernilai 1 atau 2, `porsi_kepemilikan` lebih dari 0 dan paling banyak 100 | DPPL 5.1 baris 2 |
| 2 | `K2-02` | `kode_desa_kelurahan` ada di `ref_wilayah` | DPPL 2.4.2 |
| 3 | `K2-03` | Tidak ada duplikasi `kode_desa_kelurahan` (sudah tersimpan, atau muncul dua kali dalam batch) | DPPL 2.4.2 |
| 4 | `K2-04` | `jenis_koperasi` bernilai `KDMP` atau `KKMP` dan seragam untuk semua baris ber-NIKOP sama dalam batch (D1) | DPPL 2.4.2 |
| 5 | `K2-05` | Jumlah `porsi_kepemilikan` semua baris satu NIKOP dalam batch tepat `100.000000`. Bila tidak, **semua** baris NIKOP itu ditolak (D3) | UR V5.04 dan DPPL 5.1 |

Catatan sumber: DPPL Bab 2.4.2 menyebut empat lapis, sedangkan DPPL Bab 5.1 dan tabel UR V5.04
memuat lima (ditambah jumlah porsi). Purwarupa memakai lima. Selisih ini sudah dicatat di laporanmu
(subbab 5.2.6) dan bisa dipakai lagi sebagai temuan.

Baris lolos disimpan dengan `status = 'AKTIF'`.

### Modul 3, `reviu_bast`

| Urut | Kode | Pemeriksaan | Dasar |
|---|---|---|---|
| 1 | `R3-01` | Format dan kelengkapan field | umum |
| 2 | `R3-02` | `nomor_induk_koperasi` terdaftar di `ref_kdkmp` | UAT Modul 3 |
| 3 | `R3-07` | `uuid_reviu_bast` belum ada dan pasangan (NIKOP, `jenis_reviu_bast`) belum ada (append-only) | DPPL 4.2 butir 3 |
| 4 | `R3-03` | Kewilayahan cocok dengan `ref_kdkmp` (D2) | DPPL 2.4.3 kriteria 1 |
| 5 | `R3-04` | `jenis_koperasi` sama dengan `ref_kdkmp` | kriteria 2 |
| 6 | `R3-05` | `nilai_reviu_bast` tidak melebihi Rp3.000.000.000 | kriteria 3 |
| 7 | `R3-06` | Tiga komponen dijumlahkan sama dengan `nilai_reviu_bast` | kriteria 4 |

### Modul 1

| Kode | Pemeriksaan |
|---|---|
| `W1-01` | File atau array cacat atau ada baris tidak lengkap, seluruh batch ditolak |

## 5. Aturan turunan (Modul 4 dan 5)

**Pemicu:** setiap kali satu baris `reviu_bast` diterima, sistem membentuk (atau membentuk ulang)
`komponen_aset_desa` dan `basis_permohonan_bank` untuk NIKOP itu (DPPL 5.1 bagian C).
Tidak ada input manual. Layar tidak punya tombol ubah, hapus, atau tambah.

Untuk setiap baris `ref_kdkmp` dengan NIKOP yang sama:

```
nilai_desa = ROUND( porsi_kepemilikan / 100 * nilai_tingkat_NIKOP , 2 )   -- pembulatan half up
```

Berlaku untuk `nilai_reviu_bast` dan tiga komponen (bangunan, sarana prasarana, kendaraan).
`basis_permohonan_bank.nilai_reviu_bast_desa` **diambil dari** `komponen_aset_desa`, tidak dihitung
ulang (DPPL 4.2 butir 5). Karena itu Modul 5 tidak bisa dibangun tanpa Modul 4.

## 6. Invarian yang diuji otomatis

| Kode | Pernyataan |
|---|---|
| I1 | Untuk setiap NIKOP di `ref_kdkmp`, jumlah `porsi_kepemilikan` = 100.000000 |
| I2 | `abs(nilai_NIKOP - jumlah nilai_desa) <= 0.005 * jumlah_desa` untuk tiap komponen |
| I3 | Data `reviu_bast` yang sudah diterima tidak bisa diubah atau dihapus lewat API (405) |
| I4 | Baris yang ditolak tidak tersimpan di tabel tujuan dan tercatat di `error_log` |
| I5 | Data dummy bernilai bulat (kelipatan Rp1.000.000 dan porsi yang membagi habis) menghasilkan selisih tepat 0 |

I2 bukan "selisih nol". Pengujian di PostgreSQL membuktikan pembulatan dua desimal bisa
meninggalkan selisih Rp0,01 (contoh: porsi 33,333334 / 33,333333 / 33,333333 dengan nilai
Rp1.000.000.001,00 menghasilkan selisih Rp0,01). DPPL hanya mengatur pembulatan porsi (metode
sisa terbesar, dijalankan SIMKOPDES), **tidak** pembulatan nilai rupiah turunan. Ini temuan
yang layak masuk analisis Bab 5.

## 7. Keputusan desain (nilai bawaan; ubah hanya bila bertiga setuju)

| Kode | Keputusan | Alasan |
|---|---|---|
| D1 | "Konsistensi `jenis_koperasi`" berarti nilainya KDMP atau KKMP dan seragam per NIKOP dalam satu batch. Keseragaman dinilai di antara baris yang lolos lapis 1 sampai 3; bila tidak seragam, **semua** baris NIKOP itu yang sampai ke lapis 4 ditolak `K2-04` | Sumber tidak mendefinisikannya lebih jauh |
| D2 | Kewilayahan reviu cocok bila (kecamatan, kab/kota, provinsi) sama dengan **salah satu** baris `ref_kdkmp` ber-NIKOP itu | NIKOP BERSAMA bisa punya beberapa desa; sumber tidak menjelaskan baris mana yang dibandingkan |
| D3 | Jumlah porsi dievaluasi per NIKOP dalam satu batch. Pengiriman bertahap lintas batch untuk NIKOP BERSAMA tidak didukung | Sumber tidak menjelaskan apakah jumlah dihitung per pengiriman atau kumulatif |
| D4 | Berhenti di kegagalan pertama per baris | Sumber menyebut validasi "berurutan" |
| D5 | Porsi berskala 0 sampai 100, pembagian dengan 100 pada rumus, pembulatan half up | UR menyebut skala 0 sampai 100; DPPL menulis rumus tanpa pembagian |
| D6 | PK komposit `komponen_aset_desa` = (`kode_desa_kelurahan`, `uuid_reviu_bast`) | DPPL tidak menetapkan PK |
| D7 | `jenis_koperasi` disimpan sebagai teks `KDMP` atau `KKMP` | Sumber tidak memetakan kode digit |
| D8 | `TUNGGAL` tidak dipaksa berporsi 100 | Sumber tidak mewajibkannya |
| D9 | Duplikasi `kode_desa_kelurahan` dalam satu batch: kemunculan **pertama** diperiksa seperti biasa, hanya kemunculan **berikutnya** yang ditolak `K2-03` | Sumber tidak menyebut baris mana yang ditolak |
| D10 | Jumlah porsi (K2-05) dihitung atas baris NIKOP itu yang **lolos lapis 1 sampai 4**. Baris yang sudah ditolak di lapis lebih awal tidak dihitung, sehingga baris saudaranya yang lolos ikut ditolak `K2-05` (jumlah jadi kurang dari 100) | Akibat langsung D3 dan D4; menjaga I1 |

Setiap keputusan di atas yang menambal ketidakjelasan sumber layak dicatat di laporan sebagai
asumsi purwarupa.

## 8. Aturan kerja Git

- Cabang: `main` (dilindungi), `modul-1`, `modul-2`, `modul-3`, `modul-4`, `modul-5`, `ui`.
- Satu PR kecil per fitur. Minimal satu orang lain membaca sebelum digabung.
- Pesan commit dalam bahasa Indonesia, awali dengan modul: `modul-2: tambah validasi duplikasi`.
- Jangan commit data sungguhan. Jangan unggah repo ke publik.

## 9. Pembagian tanggung jawab

| Bagian | Pemilik |
|---|---|
| Skema, migrasi, Modul 1, Modul 4, Modul 5, Docker Compose | B |
| Modul 2, Modul 3, error log, tes otomatis validasi | A |
| Layar, pengirim pengganti SIMKOPDES, data dummy, pemetaan dan eksekusi UAT | C |

## Riwayat perubahan

| Tanggal | Perubahan | Disetujui |
|---|---|---|
| 8 Nov 2026 | Versi awal | Arsa, Adit, Rizqy |
| 8 Nov 2026 | Tambah bentuk respons W1-01 dan daftar, aturan Decimal, endpoint reset, D9, D10, penegasan D1. Selaras dengan kunci jawaban `uji/data_dummy/harapan.json` | Arsa, Adit, Rizqy |
