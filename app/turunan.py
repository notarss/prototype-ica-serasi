"""Pembentukan data turunan (Modul 4 dan 5). Pemilik: B.

modul3.py memanggil bentuk_komponen() setelah satu baris reviu_bast diterima, di dalam
transaksi yang sama (parameter `con` adalah koneksi yang sama dengan penyimpanan reviu).
Aturan perhitungannya ada di kontrak API bagian 5.
"""

# nilai_desa = ROUND(porsi / 100 * nilai_NIKOP, 2). Dihitung di PostgreSQL dengan NUMERIC (bukan float).
# Urutan "porsi * nilai / 100" sengaja dipilih: perkalian dan pembagian dengan 100 pada NUMERIC selalu tepat.
# ROUND pada NUMERIC membulatkan 0,5 ke atas (half up), sesuai D5.
SQL_KOMPONEN = """
INSERT INTO komponen_aset_desa (
    kode_desa_kelurahan, uuid_reviu_bast, nama_desa_kelurahan,
    kode_kecamatan, nama_kecamatan, kode_kabkota, nama_kabkota, kode_provinsi, nama_provinsi,
    nomor_induk_koperasi, nama_koperasi, struktur_kepemilikan, porsi_kepemilikan, jenis_koperasi,
    nilai_reviu_bast, nilai_reviu_bast_desa, jenis_reviu_bast, tanggal_reviu_bast,
    nilai_bast_bangunan_kdkmp, nilai_bast_sarana_prasarana_kdkmp, nilai_bast_kendaraan_kdkmp,
    nilai_bast_bangunan_desa, nilai_bast_sarana_prasarana_desa, nilai_bast_kendaraan_desa)
SELECT
    k.kode_desa_kelurahan, r.uuid_reviu_bast, k.nama_desa_kelurahan,
    k.kode_kecamatan, k.nama_kecamatan, k.kode_kabkota, k.nama_kabkota, k.kode_provinsi, k.nama_provinsi,
    k.nomor_induk_koperasi, k.nama_koperasi, k.struktur_kepemilikan, k.porsi_kepemilikan, k.jenis_koperasi,
    r.nilai_reviu_bast, ROUND(k.porsi_kepemilikan * r.nilai_reviu_bast / 100, 2),
    r.jenis_reviu_bast, r.tanggal_reviu_bast,
    r.nilai_bast_bangunan_kdkmp, r.nilai_bast_sarana_prasarana_kdkmp, r.nilai_bast_kendaraan_kdkmp,
    ROUND(k.porsi_kepemilikan * r.nilai_bast_bangunan_kdkmp / 100, 2),
    ROUND(k.porsi_kepemilikan * r.nilai_bast_sarana_prasarana_kdkmp / 100, 2),
    ROUND(k.porsi_kepemilikan * r.nilai_bast_kendaraan_kdkmp / 100, 2)
FROM reviu_bast r
JOIN ref_kdkmp k ON k.nomor_induk_koperasi = r.nomor_induk_koperasi
WHERE r.uuid_reviu_bast = %s::uuid
"""


def bentuk_komponen(con, uuid_reviu_bast):
    """Bentuk (atau bentuk ulang) komponen_aset_desa untuk satu reviu: satu baris per desa milik NIKOP-nya."""
    con.execute("DELETE FROM komponen_aset_desa WHERE uuid_reviu_bast = %s::uuid", (uuid_reviu_bast,))
    con.execute(SQL_KOMPONEN, (uuid_reviu_bast,))