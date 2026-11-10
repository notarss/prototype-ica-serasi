"""Modul 3: reviu_bast. Pemilik: A. Aturan: kontrak API bagian 4 (R3-01 sampai R3-07) dan bagian 7."""
import re
import uuid as uuid_lib
from datetime import date

from fastapi import APIRouter, HTTPException, Request

from db import koneksi
from turunan import bentuk_komponen
from umum import ambil_rows, baca_json, catat_batch, halaman, jawab, susun_respons, teks_valid

router = APIRouter(prefix="/api/v1")

# Field teks wajib dan panjang maksimumnya (sama dengan kolom di 001_schema.sql)
FIELD_TEKS = {
    "uuid_reviu_bast": 36, "nomor_induk_koperasi": 30, "nama_koperasi": 255, "jenis_koperasi": 10,
    "kode_kecamatan": 10, "kode_kabkota": 4, "kode_provinsi": 2, "nomor_reviu_bast": 60,
}
FIELD_UANG = ("nilai_reviu_bast", "nilai_bast_bangunan_kdkmp",
              "nilai_bast_sarana_prasarana_kdkmp", "nilai_bast_kendaraan_kdkmp")
POLA_TANGGAL = re.compile(r"\d{4}-\d{2}-\d{2}")
POLA_UANG = re.compile(r"\d{1,13}(\.\d{1,2})?")      # teks desimal, paling banyak 2 angka di belakang koma

# Nama kecamatan, kabupaten, dan provinsi tidak dikirim pengirim; disalin dari ref_wilayah.
SQL_SIMPAN = """
INSERT INTO reviu_bast (
    uuid_reviu_bast, nomor_induk_koperasi, nama_koperasi, jenis_koperasi,
    kode_kecamatan, nama_kecamatan, kode_kabkota, nama_kabkota, kode_provinsi, nama_provinsi,
    nomor_reviu_bast, tanggal_reviu_bast, jenis_reviu_bast, nilai_reviu_bast,
    nilai_bast_bangunan_kdkmp, nilai_bast_sarana_prasarana_kdkmp, nilai_bast_kendaraan_kdkmp, batch_id)
VALUES (
    %(uuid_reviu_bast)s::uuid, %(nomor_induk_koperasi)s, %(nama_koperasi)s, %(jenis_koperasi)s,
    %(kode_kecamatan)s::text,
    (SELECT nama_kecamatan FROM ref_wilayah WHERE kode_kecamatan = %(kode_kecamatan)s::text LIMIT 1),
    %(kode_kabkota)s::text,
    (SELECT nama_kabkota FROM ref_wilayah WHERE kode_kabkota = %(kode_kabkota)s::text LIMIT 1),
    %(kode_provinsi)s::text,
    (SELECT nama_provinsi FROM ref_wilayah WHERE kode_provinsi = %(kode_provinsi)s::text LIMIT 1),
    %(nomor_reviu_bast)s, %(tanggal_reviu_bast)s::date, %(jenis_reviu_bast)s,
    %(nilai_reviu_bast)s::numeric, %(nilai_bast_bangunan_kdkmp)s::numeric,
    %(nilai_bast_sarana_prasarana_kdkmp)s::numeric, %(nilai_bast_kendaraan_kdkmp)s::numeric,
    %(batch_id)s::uuid)
"""


def _cek_lapis1(baris):
    """R3-01. Mengembalikan (field, pesan) untuk kegagalan pertama, atau None bila lolos."""
    if not isinstance(baris, dict):
        return ("-", "baris bukan objek JSON")
    for field, maks in FIELD_TEKS.items():
        if not teks_valid(baris, field, maks):
            return (field, f"field '{field}' kosong, bukan teks, atau lebih dari {maks} karakter")
    try:
        kanonik = str(uuid_lib.UUID(baris["uuid_reviu_bast"])) == baris["uuid_reviu_bast"]
    except ValueError:
        kanonik = False
    if not kanonik:
        return ("uuid_reviu_bast", "harus UUID huruf kecil berformat 8-4-4-4-12")
    t = baris.get("tanggal_reviu_bast")
    if not (isinstance(t, str) and POLA_TANGGAL.fullmatch(t)):
        return ("tanggal_reviu_bast", "harus berformat YYYY-MM-DD")
    try:
        date.fromisoformat(t)
    except ValueError:
        return ("tanggal_reviu_bast", "bukan tanggal yang ada di kalender")
    j = baris.get("jenis_reviu_bast")
    if isinstance(j, bool) or j not in (1, 2, 3, 4):
        return ("jenis_reviu_bast", "harus 1, 2, 3, atau 4")
    for field in FIELD_UANG:
        v = baris.get(field)
        if not (isinstance(v, str) and POLA_UANG.fullmatch(v)):
            return (field, f"field '{field}' harus teks angka desimal, tanpa tanda, paling banyak 2 angka di belakang koma")
    return None


def _tolak(galat, nomor, baris, kode, field, pesan):
    galat.append({"baris": nomor, "kode": kode, "field": field, "pesan": pesan, "data": baris})


@router.post("/reviu-bast")
async def terima_reviu(request: Request):
    rows = ambil_rows(await baca_json(request))
    total = len(rows)

    galat = []                      # satu entri per baris yang ditolak

    # R3-01: format dan kelengkapan, per baris, tanpa database
    hidup = []                      # (nomor, baris) yang masih lolos
    for nomor, baris in enumerate(rows, start=1):
        g = _cek_lapis1(baris)
        if g:
            _tolak(galat, nomor, baris, "R3-01", g[0], g[1])
        else:
            hidup.append((nomor, baris))

    with koneksi() as con:
        # R3-02: nomor_induk_koperasi harus sudah terdaftar di ref_kdkmp (satu query untuk semua baris)
        terdaftar = {r["nomor_induk_koperasi"] for r in con.execute(
            "SELECT DISTINCT nomor_induk_koperasi FROM ref_kdkmp WHERE nomor_induk_koperasi = ANY(%s)",
            ([b["nomor_induk_koperasi"] for _, b in hidup],)).fetchall()}
        hidup2 = []                 # lolos R3-01 dan R3-02; diperiksa R3-07 di bawah
        for nomor, baris in hidup:
            if baris["nomor_induk_koperasi"] not in terdaftar:
                _tolak(galat, nomor, baris, "R3-02", "nomor_induk_koperasi",
                       f"nomor_induk_koperasi {baris['nomor_induk_koperasi']} belum terdaftar di ref_kdkmp")
            else:
                hidup2.append((nomor, baris))

        # R3-07: append-only. uuid belum pernah tersimpan DAN pasangan (NIKOP, jenis_reviu_bast) belum ada.
        uuid_ada = {r["u"] for r in con.execute(
            "SELECT uuid_reviu_bast::text AS u FROM reviu_bast WHERE uuid_reviu_bast = ANY(%s::uuid[])",
            ([b["uuid_reviu_bast"] for _, b in hidup2],)).fetchall()}
        pasangan_ada = {(r["nomor_induk_koperasi"], r["jenis_reviu_bast"]) for r in con.execute(
            "SELECT nomor_induk_koperasi, jenis_reviu_bast FROM reviu_bast WHERE nomor_induk_koperasi = ANY(%s)",
            ([b["nomor_induk_koperasi"] for _, b in hidup2],)).fetchall()}
        terlihat_uuid, terlihat_pasangan = set(), set()     # yang sudah muncul di batch ini
        hidup3 = []                 # lolos R3-01, R3-02, R3-07; dipakai R3-03 pada tahap berikutnya
        for nomor, baris in hidup2:
            u = baris["uuid_reviu_bast"]
            p = (baris["nomor_induk_koperasi"], baris["jenis_reviu_bast"])
            if u in uuid_ada or u in terlihat_uuid:
                _tolak(galat, nomor, baris, "R3-07", "uuid_reviu_bast", f"uuid_reviu_bast {u} sudah ada (data bersifat append-only)")
            elif p in pasangan_ada or p in terlihat_pasangan:
                _tolak(galat, nomor, baris, "R3-07", "jenis_reviu_bast",
                       f"NIKOP {p[0]} sudah punya reviu jenis {p[1]} (data bersifat append-only)")
            else:
                terlihat_uuid.add(u)
                terlihat_pasangan.add(p)
                hidup3.append((nomor, baris))

        galat.sort(key=lambda g: g["baris"])
        nomor_ditolak = {g["baris"] for g in galat}
        batch_id = catat_batch(con, "reviu_bast", total, total - len(galat), len(galat), galat)
        for nomor, baris in enumerate(rows, start=1):
            if nomor in nomor_ditolak:
                continue
            con.execute(SQL_SIMPAN, {**baris, "batch_id": batch_id})
            bentuk_komponen(con, baris["uuid_reviu_bast"])      # Modul 4 (dikerjakan B)

    return jawab(susun_respons("reviu_bast", batch_id, total, galat))


@router.get("/reviu-bast")
def daftar_reviu(page: int = 1, per_page: int = 20, nomor_induk_koperasi: str | None = None,
                 jenis_reviu_bast: int | None = None):
    page, per_page, offset = halaman(page, per_page)
    syarat, param = [], []
    if nomor_induk_koperasi:
        syarat.append("nomor_induk_koperasi = %s"); param.append(nomor_induk_koperasi)
    if jenis_reviu_bast is not None:
        syarat.append("jenis_reviu_bast = %s"); param.append(jenis_reviu_bast)
    where = ("WHERE " + " AND ".join(syarat)) if syarat else ""
    with koneksi() as con:
        total = con.execute(f"SELECT count(*) AS n FROM reviu_bast {where}", param).fetchone()["n"]
        items = con.execute(
            f"SELECT * FROM reviu_bast {where} ORDER BY nomor_induk_koperasi, jenis_reviu_bast LIMIT %s OFFSET %s",
            param + [per_page, offset]).fetchall()
    return jawab({"page": page, "per_page": per_page, "total": total, "items": items})


@router.get("/reviu-bast/{uuid_reviu_bast}")
def detail_reviu(uuid_reviu_bast: str):
    try:
        uuid_lib.UUID(uuid_reviu_bast)
    except ValueError:
        raise HTTPException(status_code=404, detail="uuid_reviu_bast tidak ditemukan")
    with koneksi() as con:
        baris = con.execute("SELECT * FROM reviu_bast WHERE uuid_reviu_bast = %s::uuid",
                            (uuid_reviu_bast,)).fetchone()
    if baris is None:
        raise HTTPException(status_code=404, detail="uuid_reviu_bast tidak ditemukan")
    return jawab(baris)
