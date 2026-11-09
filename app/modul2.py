"""Modul 2: ref_kdkmp. Pemilik: A. Aturan: kontrak API bagian 4 (K2-01 sampai K2-05) dan bagian 7."""
from decimal import Decimal

from fastapi import APIRouter, Request

from db import koneksi
from umum import ambil_rows, baca_json, catat_batch, halaman, jawab, susun_respons, teks_valid

router = APIRouter(prefix="/api/v1")

# Kolom nama kecamatan, kabupaten, dan seterusnya TIDAK dikirim pengirim.
# Sistem menyalinnya dari ref_wilayah lewat INSERT ... SELECT.
SQL_SIMPAN = """
INSERT INTO ref_kdkmp (
    kode_desa_kelurahan, nama_desa_kelurahan, kode_kecamatan, nama_kecamatan,
    kode_kabkota, nama_kabkota, kode_provinsi, nama_provinsi,
    nomor_induk_koperasi, nama_koperasi, struktur_kepemilikan, porsi_kepemilikan,
    jenis_koperasi, batch_id)
SELECT
    w.kode_desa_kelurahan, w.nama_desa_kelurahan, w.kode_kecamatan, w.nama_kecamatan,
    w.kode_kabkota, w.nama_kabkota, w.kode_provinsi, w.nama_provinsi,
    %(nomor_induk_koperasi)s, %(nama_koperasi)s, %(struktur_kepemilikan)s, %(porsi_kepemilikan)s,
    %(jenis_koperasi)s, %(batch_id)s::uuid
FROM ref_wilayah w
WHERE w.kode_desa_kelurahan = %(kode_desa_kelurahan)s
"""
JENIS_VALID = ("KDMP", "KKMP")

# Field teks wajib dan panjang maksimumnya (sama dengan kolom di 001_schema.sql)
FIELD_TEKS = {"kode_desa_kelurahan": 10, "nomor_induk_koperasi": 30, "nama_koperasi": 255, "jenis_koperasi": 10}


def _cek_lapis1(baris):
    """K2-01. Mengembalikan (field, pesan) untuk kegagalan pertama, atau None bila lolos."""
    if not isinstance(baris, dict):
        return ("-", "baris bukan objek JSON")
    for field, maks in FIELD_TEKS.items():
        if not teks_valid(baris, field, maks):
            return (field, f"field '{field}' kosong, bukan teks, atau lebih dari {maks} karakter")
    s = baris.get("struktur_kepemilikan")
    if isinstance(s, bool) or s not in (1, 2):          # bool dicek dulu: True == 1 di Python
        return ("struktur_kepemilikan", "harus 1 (TUNGGAL) atau 2 (BERSAMA)")
    p = baris.get("porsi_kepemilikan")
    if isinstance(p, bool) or not isinstance(p, (int, Decimal)):
        return ("porsi_kepemilikan", "harus berupa angka")
    if not (0 < p <= 100):
        return ("porsi_kepemilikan", "harus lebih dari 0 dan paling banyak 100")
    return None


def _tolak(galat, nomor, baris, kode, field, pesan):
    """Catat satu baris ditolak. Daftar `galat` ini nanti ditulis ke error_log oleh catat_batch."""
    galat.append({"baris": nomor, "kode": kode, "field": field, "pesan": pesan, "data": baris})


@router.post("/ref-kdkmp")
async def terima_kdkmp(request: Request):
    rows = ambil_rows(await baca_json(request))
    total = len(rows)
    galat = []                      # satu entri per baris yang ditolak

    # Lapis 1 (K2-01): per baris, tanpa database
    hidup = []                      # (nomor, baris) yang masih lolos
    for nomor, baris in enumerate(rows, start=1):
        g = _cek_lapis1(baris)
        if g:
            _tolak(galat, nomor, baris, "K2-01", g[0], g[1])
        else:
            hidup.append((nomor, baris))

    with koneksi() as con:
        # Lapis 2 (K2-02): kode desa harus ada di ref_wilayah (satu query untuk semua baris)
        kode_dicari = [b["kode_desa_kelurahan"] for _, b in hidup]
        ada = {r["kode_desa_kelurahan"] for r in con.execute(
            "SELECT kode_desa_kelurahan FROM ref_wilayah WHERE kode_desa_kelurahan = ANY(%s)",
            (kode_dicari,)).fetchall()}
        hidup2 = []                 # lolos lapis 1 dan 2; dipakai lapis 3 pada tahap berikutnya
        for nomor, baris in hidup:
            if baris["kode_desa_kelurahan"] not in ada:
                _tolak(galat, nomor, baris, "K2-02", "kode_desa_kelurahan",
                       f"kode_desa_kelurahan {baris['kode_desa_kelurahan']} tidak ditemukan di ref_wilayah")
            else:
                hidup2.append((nomor, baris))
                
        # Lapis 3 (K2-03): desa belum tersimpan di ref_kdkmp, dan tidak muncul dua kali dalam batch ini
        sudah = {r["kode_desa_kelurahan"] for r in con.execute(
            "SELECT kode_desa_kelurahan FROM ref_kdkmp WHERE kode_desa_kelurahan = ANY(%s)",
            ([b["kode_desa_kelurahan"] for _, b in hidup2],)).fetchall()}
        terlihat = set()            # kode desa yang sudah lolos lapis 3 dalam batch ini
        hidup3 = []                 # lolos lapis 1 sampai 3; dipakai lapis 4 pada tahap berikutnya
        for nomor, baris in hidup2:
            kode = baris["kode_desa_kelurahan"]
            if kode in sudah or kode in terlihat:
                alasan = "sudah tersimpan di ref_kdkmp" if kode in sudah else "muncul lebih dari sekali dalam batch ini"
                _tolak(galat, nomor, baris, "K2-03", "kode_desa_kelurahan", f"kode_desa_kelurahan {kode} {alasan}")
            else:
                terlihat.add(kode)
                hidup3.append((nomor, baris))
        
        # Lapis 4 (K2-04): jenis_koperasi bernilai KDMP atau KKMP, dan seragam untuk semua baris
        # yang ber-NIKOP sama dalam batch ini (keputusan D1)
        per_nikop = {}
        for nomor, baris in hidup3:
            per_nikop.setdefault(baris["nomor_induk_koperasi"], []).append((nomor, baris))
        hidup4 = []                 # lolos lapis 1 sampai 4; dipakai lapis 5 pada tahap berikutnya
        for kelompok in per_nikop.values():
            jenis_di_kelompok = {b["jenis_koperasi"] for _, b in kelompok}
            for nomor, baris in kelompok:
                if baris["jenis_koperasi"] not in JENIS_VALID:
                    _tolak(galat, nomor, baris, "K2-04", "jenis_koperasi",
                           f"jenis_koperasi '{baris['jenis_koperasi']}' harus KDMP atau KKMP")
                elif len(jenis_di_kelompok) > 1:
                    _tolak(galat, nomor, baris, "K2-04", "jenis_koperasi",
                           f"jenis_koperasi tidak seragam untuk nomor_induk_koperasi {baris['nomor_induk_koperasi']}")
                else:
                    hidup4.append((nomor, baris))

        galat.sort(key=lambda g: g["baris"])
        nomor_ditolak = {g["baris"] for g in galat}
        batch_id = catat_batch(con, "ref_kdkmp", total, total - len(galat), len(galat), galat)
        for nomor, baris in enumerate(rows, start=1):
            if nomor in nomor_ditolak:
                continue
            con.execute(SQL_SIMPAN, {**baris, "batch_id": batch_id})

    return jawab(susun_respons("ref_kdkmp", batch_id, total, galat))


@router.get("/ref-kdkmp")
def daftar_kdkmp(page: int = 1, per_page: int = 20, q: str | None = None,
                 jenis_koperasi: str | None = None, nomor_induk_koperasi: str | None = None):
    page, per_page, offset = halaman(page, per_page)
    syarat, param = [], []
    if q:
        syarat.append("(nama_koperasi ILIKE %s OR nama_desa_kelurahan ILIKE %s)")
        param += [f"%{q}%", f"%{q}%"]
    if jenis_koperasi:
        syarat.append("jenis_koperasi = %s"); param.append(jenis_koperasi)
    if nomor_induk_koperasi:
        syarat.append("nomor_induk_koperasi = %s"); param.append(nomor_induk_koperasi)
    where = ("WHERE " + " AND ".join(syarat)) if syarat else ""
    with koneksi() as con:
        total = con.execute(f"SELECT count(*) AS n FROM ref_kdkmp {where}", param).fetchone()["n"]
        items = con.execute(
            f"SELECT * FROM ref_kdkmp {where} ORDER BY kode_desa_kelurahan LIMIT %s OFFSET %s",
            param + [per_page, offset]).fetchall()
    return jawab({"page": page, "per_page": per_page, "total": total, "items": items})