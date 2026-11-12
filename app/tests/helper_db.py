"""Pembantu uji white box untuk turunan.py: membangun data uji di dalam satu transaksi.

Semua data dibuat lewat koneksi yang di-rollback pada akhir tiap uji (lihat conftest.py),
sehingga basis data lokal tetap berada pada keadaan dasar. Kode wilayah berawalan 99
dan NIKOP berawalan WB- dipilih agar tidak bertabrakan dengan data dummy paket uji.
"""
import uuid
from decimal import ROUND_HALF_UP, Decimal


def buat_koperasi(con, nikop, desa, jenis="KDMP"):
    """desa = daftar (kode_desa, porsi). Struktur 1 (TUNGGAL) bila satu desa, 2 (BERSAMA) bila lebih."""
    struktur = 1 if len(desa) == 1 else 2
    for kode, porsi in desa:
        con.execute(
            "INSERT INTO ref_wilayah (kode_desa_kelurahan, nama_desa_kelurahan, kode_kecamatan, nama_kecamatan,"
            " kode_kabkota, nama_kabkota, kode_provinsi, nama_provinsi)"
            " VALUES (%s, %s, '990001', 'Kecamatan Uji', '9900', 'Kabupaten Uji', '99', 'Provinsi Uji')",
            (kode, f"Desa {kode}"))
        con.execute(
            "INSERT INTO ref_kdkmp (kode_desa_kelurahan, nama_desa_kelurahan, kode_kecamatan, nama_kecamatan,"
            " kode_kabkota, nama_kabkota, kode_provinsi, nama_provinsi, nomor_induk_koperasi, nama_koperasi,"
            " struktur_kepemilikan, porsi_kepemilikan, jenis_koperasi)"
            " VALUES (%s, %s, '990001', 'Kecamatan Uji', '9900', 'Kabupaten Uji', '99', 'Provinsi Uji',"
            " %s, 'Koperasi Uji', %s, %s::numeric, %s)",
            (kode, f"Desa {kode}", nikop, struktur, porsi, jenis))


def buat_reviu(con, nikop, bangunan, sarana, kendaraan):
    """Simpan satu reviu_bast. nilai_reviu_bast = jumlah tiga komponen (batasan CHECK pada skema)."""
    nilai = Decimal(bangunan) + Decimal(sarana) + Decimal(kendaraan)
    uuid_reviu = str(uuid.uuid4())
    con.execute(
        "INSERT INTO reviu_bast (uuid_reviu_bast, nomor_induk_koperasi, nama_koperasi, jenis_koperasi,"
        " kode_kecamatan, kode_kabkota, kode_provinsi, nomor_reviu_bast, tanggal_reviu_bast, jenis_reviu_bast,"
        " nilai_reviu_bast, nilai_bast_bangunan_kdkmp, nilai_bast_sarana_prasarana_kdkmp, nilai_bast_kendaraan_kdkmp)"
        " VALUES (%s::uuid, %s, 'Koperasi Uji', 'KDMP', '990001', '9900', '99', %s, '2026-08-01', 1,"
        " %s::numeric, %s::numeric, %s::numeric, %s::numeric)",
        (uuid_reviu, nikop, f"UJI/{nikop}", nilai, bangunan, sarana, kendaraan))
    return uuid_reviu


def baca_komponen(con, uuid_reviu):
    return con.execute(
        "SELECT * FROM komponen_aset_desa WHERE uuid_reviu_bast = %s::uuid ORDER BY kode_desa_kelurahan",
        (uuid_reviu,)).fetchall()


def bulatkan(porsi, nilai):
    """Pembanding independen: porsi * nilai / 100, dibulatkan dua desimal, 0,5 ke atas (D5)."""
    return (Decimal(porsi) * Decimal(nilai) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
