"""Modul 3: reviu_bast. Pemilik: A. Aturan: kontrak API bagian 4 (R3-01 sampai R3-07) dan bagian 7."""
import uuid as uuid_lib

from fastapi import APIRouter, HTTPException, Request

from db import koneksi
from turunan import bentuk_komponen
from umum import ambil_rows, baca_json, catat_batch, halaman, jawab, susun_respons

router = APIRouter(prefix="/api/v1")

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


@router.post("/reviu-bast")
async def terima_reviu(request: Request):
    rows = ambil_rows(await baca_json(request))
    total = len(rows)

    # Tahap berikutnya mengisi daftar ini dengan satu entri per baris yang ditolak:
    # {"baris": nomor, "kode": "R3-01", "field": "...", "pesan": "...", "data": baris}
    galat = []
    nomor_ditolak = {g["baris"] for g in galat}

    with koneksi() as con:
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