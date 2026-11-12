"""Uji white box fungsi _cek_lapis1 (aturan R3-01) pada modul3.py.

Jalur P01 sampai P13 mengikuti Control Flow Graph pada subbab 5.4.6.1 (V(G) = 13).
Kasus K1 sampai K7 menguji kondisi majemuk dan nilai tepi yang satu jalur tidak membedakan.
Fungsi ini murni: tidak memakai basis data.
"""
from decimal import Decimal

import pytest

from modul3 import _cek_lapis1

DASAR = {
    "uuid_reviu_bast": "5f1f0f7e-8d3e-4a52-9c45-0c8a1b9b0a11",
    "nomor_induk_koperasi": "N1", "nama_koperasi": "Koperasi Uji", "jenis_koperasi": "KDMP",
    "kode_kecamatan": "320101", "kode_kabkota": "3201", "kode_provinsi": "32",
    "nomor_reviu_bast": "R-001", "tanggal_reviu_bast": "2026-08-01", "jenis_reviu_bast": 1,
    "nilai_reviu_bast": "1000000.00", "nilai_bast_bangunan_kdkmp": "600000.00",
    "nilai_bast_sarana_prasarana_kdkmp": "300000.00", "nilai_bast_kendaraan_kdkmp": "100000.00",
}


def baris(**ubah):
    return {**DASAR, **ubah}


def harus_galat(hasil, field, kunci):
    """Hasil harus berupa (field, pesan) dengan field yang diharapkan dan kata kunci pada pesan."""
    assert hasil is not None, "fungsi mengembalikan None (lolos), padahal seharusnya galat"
    assert hasil[0] == field
    assert kunci in hasil[1]


# ---- Jalur dasar -------------------------------------------------------------------------

@pytest.mark.parametrize("masukan", ["bukan objek", ["a"], None], ids=["teks", "daftar", "None"])
def test_P01_baris_bukan_objek(masukan):                      # 1-2-3-22
    harus_galat(_cek_lapis1(masukan), "-", "bukan objek JSON")


def test_P02_field_teks_pertama_kosong():                     # 1-2-4-5-6-22
    harus_galat(_cek_lapis1(baris(uuid_reviu_bast="")), "uuid_reviu_bast", "kosong")


@pytest.mark.parametrize("ubah,field", [
    ({"nomor_induk_koperasi": ""}, "nomor_induk_koperasi"),          # gagal pada field kedua
    ({"nomor_reviu_bast": "R" * 61}, "nomor_reviu_bast"),            # gagal pada field kedelapan
], ids=["field-ke-2", "field-ke-8"])
def test_P03_field_teks_berikutnya_tidak_valid(ubah, field):  # 1-2-4-5-4-5-6-22
    harus_galat(_cek_lapis1(baris(**ubah)), field, "kosong, bukan teks, atau lebih dari")


@pytest.mark.parametrize("nilai", [
    "5F1F0F7E-8D3E-4A52-9C45-0C8A1B9B0A11",     # huruf besar: UUID sah, tetapi bukan bentuk kanonik
    "5f1f0f7e8d3e4a529c450c8a1b9b0a11",         # tanpa tanda hubung: UUID sah, bukan bentuk kanonik
    "bukan-uuid",                               # memicu ValueError pada uuid.UUID()
], ids=["huruf-besar", "tanpa-hubung", "bukan-uuid"])
def test_P04_uuid_tidak_kanonik(nilai):                       # 1-2-(4-5)x8-4-7-8-22
    harus_galat(_cek_lapis1(baris(uuid_reviu_bast=nilai)), "uuid_reviu_bast", "8-4-4-4-12")


@pytest.mark.parametrize("nilai", [None, 20260801], ids=["None", "angka"])
def test_P05_tanggal_bukan_teks(nilai):                       # ...-7-9-11-22
    harus_galat(_cek_lapis1(baris(tanggal_reviu_bast=nilai)), "tanggal_reviu_bast", "YYYY-MM-DD")


@pytest.mark.parametrize("nilai", ["01-08-2026", "2026-8-1", "2026-08-01 "],
                         ids=["dd-mm-yyyy", "tanpa-nol", "spasi-akhir"])
def test_P06_tanggal_teks_tidak_cocok_pola(nilai):            # ...-9-10-11-22
    harus_galat(_cek_lapis1(baris(tanggal_reviu_bast=nilai)), "tanggal_reviu_bast", "YYYY-MM-DD")


@pytest.mark.parametrize("nilai", ["2026-02-30", "2026-13-01", "2026-00-10"],
                         ids=["30-februari", "bulan-13", "bulan-0"])
def test_P07_tanggal_tidak_ada_di_kalender(nilai):            # ...-10-12-13-22
    harus_galat(_cek_lapis1(baris(tanggal_reviu_bast=nilai)), "tanggal_reviu_bast", "kalender")


def test_P08_jenis_reviu_bertipe_bool():                      # ...-12-14-16-22
    harus_galat(_cek_lapis1(baris(jenis_reviu_bast=True)), "jenis_reviu_bast", "1, 2, 3, atau 4")


@pytest.mark.parametrize("nilai", [5, 0, "1", None], ids=["5", "0", "teks-1", "None"])
def test_P09_jenis_reviu_di_luar_1_sampai_4(nilai):           # ...-14-15-16-22
    harus_galat(_cek_lapis1(baris(jenis_reviu_bast=nilai)), "jenis_reviu_bast", "1, 2, 3, atau 4")


@pytest.mark.parametrize("nilai", [Decimal("1000"), None], ids=["angka-Decimal", "None"])
def test_P10_field_uang_pertama_bukan_teks(nilai):            # ...-15-17-18-20-22
    harus_galat(_cek_lapis1(baris(nilai_reviu_bast=nilai)), "nilai_reviu_bast", "teks angka desimal")


@pytest.mark.parametrize("nilai", ["1.234", "-5"], ids=["3-desimal", "negatif"])
def test_P11_field_uang_pertama_tidak_cocok_pola(nilai):      # ...-18-19-20-22
    harus_galat(_cek_lapis1(baris(nilai_reviu_bast=nilai)), "nilai_reviu_bast", "teks angka desimal")


@pytest.mark.parametrize("nilai", ["abc", ".5"], ids=["huruf", "tanpa-digit-depan"])
def test_P12_field_uang_berikutnya_tidak_valid(nilai):        # ...-19-17-18-19-20-22
    harus_galat(_cek_lapis1(baris(nilai_bast_bangunan_kdkmp=nilai)),
                "nilai_bast_bangunan_kdkmp", "teks angka desimal")


def test_P13_baris_lolos():                                   # ...-17-21-22
    assert _cek_lapis1(baris()) is None


# ---- Kondisi majemuk dan nilai tepi ---------------------------------------------------------

def test_K1_panjang_teks_tepat_di_batas():
    assert _cek_lapis1(baris(nomor_reviu_bast="R" * 60)) is None          # maksimum 60: lolos
    assert _cek_lapis1(baris(nomor_reviu_bast="R" * 61)) is not None      # 61: ditolak


@pytest.mark.parametrize("nilai", [123, "   "], ids=["bukan-teks", "hanya-spasi"])
def test_K2_teks_wajib_bukan_angka_dan_bukan_spasi(nilai):
    harus_galat(_cek_lapis1(baris(nama_koperasi=nilai)), "nama_koperasi", "kosong, bukan teks")


@pytest.mark.parametrize("nilai", [1, 2, 3, 4])
def test_K3_jenis_reviu_empat_nilai_sah_lolos(nilai):
    assert _cek_lapis1(baris(jenis_reviu_bast=nilai)) is None


@pytest.mark.parametrize("nilai,lolos", [
    ("1", True), ("1234567890123", True), ("1234567890123.99", True),   # 13 digit, 2 desimal: lolos
    ("12345678901234", False), ("1.234", False), ("0.5", True), ("00", True),   # 14 digit, 3 desimal: ditolak
], ids=["1", "13-digit", "13-digit-2-desimal", "14-digit", "3-desimal", "0.5", "00"])
def test_K4_batas_pola_uang(nilai, lolos):
    assert (_cek_lapis1(baris(nilai_reviu_bast=nilai)) is None) is lolos


def test_K5_kegagalan_pertama_menentukan_hasil():
    """Dua field salah sekaligus: fungsi berhenti di yang pertama menurut urutan pemeriksaan."""
    hasil = _cek_lapis1(baris(jenis_reviu_bast=9, tanggal_reviu_bast="2026-02-30"))
    assert hasil[0] == "tanggal_reviu_bast"          # tanggal diperiksa sebelum jenis


def test_K6_digit_non_ascii_pada_tanggal_ditolak():
    """Pola \\d menerima digit Arab-Indik, tetapi date.fromisoformat menolaknya pada langkah kalender."""
    harus_galat(_cek_lapis1(baris(tanggal_reviu_bast="٢٠٢٦-٠٨-٠١")), "tanggal_reviu_bast", "kalender")


def test_K7_digit_non_ascii_pada_nilai_uang_ditolak():
    """Kontrak: nilai uang berformat angka desimal biasa. Pola \\d pada POLA_UANG juga menerima digit
    non-ASCII, sehingga baris ini lolos R3-01 lalu membuat PostgreSQL menolak ::numeric (HTTP 500)."""
    harus_galat(_cek_lapis1(baris(nilai_reviu_bast="١٠٠٠.٠٠")), "nilai_reviu_bast", "teks angka desimal")
