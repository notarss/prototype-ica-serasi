"""Modul 1: ref_wilayah. Pemilik: B. Aturan: kontrak API bagian 2 dan 4 (W1-01)."""
from fastapi import APIRouter, HTTPException, Request

from db import koneksi
from umum import (ambil_rows, baca_json, catat_batch, halaman, jawab, teks_valid)

router = APIRouter(prefix="/api/v1")

# field wajib dan panjang maksimum (sama dengan kolom di 001_schema.sql)
FIELD_WILAYAH = {
    "kode_desa_kelurahan": 10, "nama_desa_kelurahan": 150,
    "kode_kecamatan": 10, "nama_kecamatan": 100,
    "kode_kabkota": 4, "nama_kabkota": 150,
    "kode_provinsi": 2, "nama_provinsi": 100,
}


def _cek_baris(baris):
    """Mengembalikan nama field pertama yang bermasalah, atau None bila baris lengkap."""
    if not isinstance(baris, dict):
        return "-"
    for field, maks in FIELD_WILAYAH.items():
        if not teks_valid(baris, field, maks):
            return field
    return None


@router.post("/ref-wilayah/bulk")
async def terima_wilayah(request: Request):
    rows = ambil_rows(await baca_json(request))
    total = len(rows)

    cacat = []
    for nomor, baris in enumerate(rows, start=1):
        field = _cek_baris(baris)
        if field is not None:
            cacat.append({"baris": nomor, "kode": "W1-01", "field": field,
                          "pesan": f"field '{field}' kosong, bukan teks, atau terlalu panjang", "data": baris})

    with koneksi() as con:
        if cacat:      # satu baris cacat = seluruh batch ditolak, tidak ada yang disimpan
            batch_id = catat_batch(con, "ref_wilayah", total, 0, total, cacat)
            return jawab({
                "batch_id": batch_id, "dataset": "ref_wilayah", "total": total,
                "diterima": 0, "ditolak": total, "batch_ditolak": True,
                "hasil": [{"baris": g["baris"], "status": "DITOLAK",
                           "error": {"kode": g["kode"], "field": g["field"], "pesan": g["pesan"]}}
                          for g in cacat]})
        with con.cursor() as cur:
            cur.executemany(
                "INSERT INTO ref_wilayah (kode_desa_kelurahan, nama_desa_kelurahan, kode_kecamatan, "
                "nama_kecamatan, kode_kabkota, nama_kabkota, kode_provinsi, nama_provinsi) "
                "VALUES (%(kode_desa_kelurahan)s, %(nama_desa_kelurahan)s, %(kode_kecamatan)s, "
                "%(nama_kecamatan)s, %(kode_kabkota)s, %(nama_kabkota)s, %(kode_provinsi)s, %(nama_provinsi)s) "
                "ON CONFLICT (kode_desa_kelurahan) DO UPDATE SET "
                "nama_desa_kelurahan = EXCLUDED.nama_desa_kelurahan, kode_kecamatan = EXCLUDED.kode_kecamatan, "
                "nama_kecamatan = EXCLUDED.nama_kecamatan, kode_kabkota = EXCLUDED.kode_kabkota, "
                "nama_kabkota = EXCLUDED.nama_kabkota, kode_provinsi = EXCLUDED.kode_provinsi, "
                "nama_provinsi = EXCLUDED.nama_provinsi, diterima_pada = now()",
                [{f: b[f] for f in FIELD_WILAYAH} for b in rows])
        batch_id = catat_batch(con, "ref_wilayah", total, total, 0, [])
    return jawab({"batch_id": batch_id, "dataset": "ref_wilayah", "total": total,
                  "diterima": total, "ditolak": 0, "batch_ditolak": False,
                  "hasil": [{"baris": n, "status": "DITERIMA"} for n in range(1, total + 1)]})


@router.get("/ref-wilayah")
def daftar_wilayah(page: int = 1, per_page: int = 20, q: str | None = None,
                   kode_provinsi: str | None = None, kode_kabkota: str | None = None):
    page, per_page, offset = halaman(page, per_page)
    syarat, param = [], []
    if q:
        syarat.append("(nama_desa_kelurahan ILIKE %s OR nama_kecamatan ILIKE %s OR kode_desa_kelurahan LIKE %s)")
        param += [f"%{q}%", f"%{q}%", f"{q}%"]
    if kode_provinsi:
        syarat.append("kode_provinsi = %s"); param.append(kode_provinsi)
    if kode_kabkota:
        syarat.append("kode_kabkota = %s"); param.append(kode_kabkota)
    where = ("WHERE " + " AND ".join(syarat)) if syarat else ""
    with koneksi() as con:
        total = con.execute(f"SELECT count(*) AS n FROM ref_wilayah {where}", param).fetchone()["n"]
        items = con.execute(
            f"SELECT * FROM ref_wilayah {where} ORDER BY kode_desa_kelurahan LIMIT %s OFFSET %s",
            param + [per_page, offset]).fetchall()
    return jawab({"page": page, "per_page": per_page, "total": total, "items": items})


@router.get("/ref-wilayah/{kode_desa_kelurahan}")
def detail_wilayah(kode_desa_kelurahan: str):
    with koneksi() as con:
        baris = con.execute("SELECT * FROM ref_wilayah WHERE kode_desa_kelurahan = %s",
                            (kode_desa_kelurahan,)).fetchone()
    if baris is None:
        raise HTTPException(status_code=404, detail="kode_desa_kelurahan tidak ditemukan")
    return jawab(baris)
