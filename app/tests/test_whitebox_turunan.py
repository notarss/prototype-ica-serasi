"""Uji white box fungsi bentuk_komponen (aturan turunan D5) pada turunan.py.

CFG pada subbab 5.4.6.2 memiliki V(G) = 2: lintasan D1 (tidak ada desa) dan D2 (satu desa atau lebih).
Rumus berada pada pernyataan SQL, sehingga uji memakai PostgreSQL sungguhan. Setiap uji bekerja
dalam satu transaksi yang di-rollback (lihat conftest.py).
"""
from decimal import Decimal

import pytest

from helper_db import baca_komponen, bulatkan, buat_koperasi, buat_reviu
from turunan import bentuk_komponen

KOLOM_NILAI = [  # (kolom hasil di komponen_aset_desa, indeks komponen pada tuple uji)
    ("nilai_bast_bangunan_desa", 0), ("nilai_bast_sarana_prasarana_desa", 1), ("nilai_bast_kendaraan_desa", 2)]


def test_D1_reviu_tanpa_desa_menghasilkan_nol_baris(con):
    """NIKOP tidak ada di ref_kdkmp. Lewat API kasus ini tertahan R3-02, tetapi fungsi tetap harus aman."""
    uuid_reviu = buat_reviu(con, "WB-TANPA-DESA", "100.00", "0.00", "0.00")
    bentuk_komponen(con, uuid_reviu)
    assert baca_komponen(con, uuid_reviu) == []


def test_D2_satu_desa_tunggal_menerima_seluruh_nilai(con):
    buat_koperasi(con, "WB-TUNGGAL", [("9990000001", "100.000000")])
    uuid_reviu = buat_reviu(con, "WB-TUNGGAL", "600.00", "300.00", "100.00")
    bentuk_komponen(con, uuid_reviu)
    (satu,) = baca_komponen(con, uuid_reviu)
    assert satu["nilai_reviu_bast_desa"] == Decimal("1000.00")
    assert satu["nilai_bast_bangunan_desa"] == Decimal("600.00")
    assert satu["nilai_bast_sarana_prasarana_desa"] == Decimal("300.00")
    assert satu["nilai_bast_kendaraan_desa"] == Decimal("100.00")


def test_D2_tiga_desa_bersama_dibagi_menurut_porsi(con):
    buat_koperasi(con, "WB-BERSAMA", [("9990000011", "50.000000"), ("9990000012", "30.000000"),
                                      ("9990000013", "20.000000")])
    uuid_reviu = buat_reviu(con, "WB-BERSAMA", "600000000.00", "300000000.00", "100000000.00")
    bentuk_komponen(con, uuid_reviu)
    baris = baca_komponen(con, uuid_reviu)
    assert [b["nilai_reviu_bast_desa"] for b in baris] == [
        Decimal("500000000.00"), Decimal("300000000.00"), Decimal("200000000.00")]
    assert sum(b["nilai_reviu_bast_desa"] for b in baris) == Decimal("1000000000.00")   # invarian I5: selisih nol


def test_D2_panggilan_kedua_tidak_menggandakan_baris(con):
    buat_koperasi(con, "WB-ULANG", [("9990000021", "60.000000"), ("9990000022", "40.000000")])
    uuid_reviu = buat_reviu(con, "WB-ULANG", "100.00", "0.00", "0.00")
    bentuk_komponen(con, uuid_reviu)
    pertama = baca_komponen(con, uuid_reviu)
    bentuk_komponen(con, uuid_reviu)
    kedua = baca_komponen(con, uuid_reviu)
    assert len(pertama) == len(kedua) == 2
    assert [b["nilai_reviu_bast_desa"] for b in kedua] == [b["nilai_reviu_bast_desa"] for b in pertama]


def test_D2_bentuk_ulang_memakai_porsi_terbaru(con):
    buat_koperasi(con, "WB-PORSI", [("9990000031", "60.000000"), ("9990000032", "40.000000")])
    uuid_reviu = buat_reviu(con, "WB-PORSI", "100.00", "0.00", "0.00")
    bentuk_komponen(con, uuid_reviu)
    con.execute("UPDATE ref_kdkmp SET porsi_kepemilikan = 70 WHERE kode_desa_kelurahan = '9990000031'")
    con.execute("UPDATE ref_kdkmp SET porsi_kepemilikan = 30 WHERE kode_desa_kelurahan = '9990000032'")
    bentuk_komponen(con, uuid_reviu)
    assert [b["nilai_reviu_bast_desa"] for b in baca_komponen(con, uuid_reviu)] == [
        Decimal("70.00"), Decimal("30.00")]


def test_D2_bentuk_ulang_hanya_menghapus_milik_reviu_itu(con):
    buat_koperasi(con, "WB-A", [("9990000041", "100.000000")])
    buat_koperasi(con, "WB-B", [("9990000042", "100.000000")])
    reviu_a = buat_reviu(con, "WB-A", "100.00", "0.00", "0.00")
    reviu_b = buat_reviu(con, "WB-B", "200.00", "0.00", "0.00")
    bentuk_komponen(con, reviu_a)
    bentuk_komponen(con, reviu_b)
    bentuk_komponen(con, reviu_a)                                  # bentuk ulang A
    assert len(baca_komponen(con, reviu_a)) == 1
    assert [b["nilai_reviu_bast_desa"] for b in baca_komponen(con, reviu_b)] == [Decimal("200.00")]


# ---- Kelas pembulatan: porsi, bangunan, sarana, kendaraan ------------------------------------

KASUS_BULAT = {
    "tepat":              ("50.000000", "600000000.00", "300000000.00", "100000000.00"),
    "turun-di-bawah-0.005": ("33.333333", "60.00", "30.00", "10.00"),
    "naik-di-atas-0.005":   ("66.666667", "60.00", "30.00", "10.00"),
    "seri-0.005-naik":      ("0.500000", "1.00", "0.00", "0.00"),     # 0,005 -> 0,01 (half up)
    "seri-0.025-naik":      ("2.500000", "1.00", "0.00", "0.00"),     # 0,025 -> 0,03 (half-even memberi 0,02)
    "seri-di-tiga-komponen": ("0.500000", "1.00", "1.00", "1.00"),
    "porsi-maksimum":       ("99.999999", "3000000000.00", "0.00", "0.00"),
    "porsi-minimum":        ("0.000001", "3000000000.00", "0.00", "0.00"),
    "hasil-di-bawah-sen":   ("0.000001", "1.00", "0.00", "0.00"),
}


@pytest.mark.parametrize("porsi,bangunan,sarana,kendaraan", KASUS_BULAT.values(), ids=KASUS_BULAT.keys())
def test_D2_pembulatan_dua_desimal_half_up(con, porsi, bangunan, sarana, kendaraan):
    # Desa kedua menampung sisa porsi agar total 100; yang diperiksa adalah desa pertama.
    sisa = Decimal("100") - Decimal(porsi)
    desa = [("9990000051", porsi)] + ([("9990000052", str(sisa))] if sisa > 0 else [])
    buat_koperasi(con, "WB-BULAT", desa)
    uuid_reviu = buat_reviu(con, "WB-BULAT", bangunan, sarana, kendaraan)
    bentuk_komponen(con, uuid_reviu)
    pertama = baca_komponen(con, uuid_reviu)[0]
    komponen = (bangunan, sarana, kendaraan)
    for kolom, i in KOLOM_NILAI:
        assert pertama[kolom] == bulatkan(porsi, komponen[i]), kolom
    nilai = Decimal(bangunan) + Decimal(sarana) + Decimal(kendaraan)
    assert pertama["nilai_reviu_bast_desa"] == bulatkan(porsi, nilai)


def test_D2_selisih_pembulatan_satu_sen_antara_jumlah_desa_dan_nilai_nikop(con):
    """Kelas yang sama dengan NIKOP-0061 pada paket uji: 0,5% dan 99,5% dari Rp1,00."""
    buat_koperasi(con, "WB-SELISIH", [("9990000061", "0.500000"), ("9990000062", "99.500000")])
    uuid_reviu = buat_reviu(con, "WB-SELISIH", "1.00", "0.00", "0.00")
    bentuk_komponen(con, uuid_reviu)
    baris = baca_komponen(con, uuid_reviu)
    assert [b["nilai_reviu_bast_desa"] for b in baris] == [Decimal("0.01"), Decimal("1.00")]
    assert sum(b["nilai_reviu_bast_desa"] for b in baris) - Decimal("1.00") == Decimal("0.01")
