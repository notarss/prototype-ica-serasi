"""Modul 2: ref_kdkmp. Pemilik: A. Aturan: kontrak API bagian 4 (K2-01 sampai K2-05) dan bagian 7."""
from fastapi import APIRouter, Request

from db import koneksi
from umum import ambil_rows, baca_json, catat_batch, halaman, jawab, susun_respons

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

@router.post("/ref-kdkmp")
async def terima_kdkmp(request: Request):
    rows = ambil_rows(await baca_json(request))
    total = len(rows)

    # Tahap 2 sampai 5 akan mengisi daftar ini dengan satu entri per baris yang ditolak:
    # {"baris": nomor, "kode": "K2-01", "field": "...", "pesan": "...", "data": baris}
    galat = []
    nomor_ditolak = {g["baris"] for g in galat}

    with koneksi() as con:
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