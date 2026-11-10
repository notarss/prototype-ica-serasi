"""Modul 4: komponen_aset_desa (data turunan, tanpa input manual). Pemilik: B."""
from fastapi import APIRouter

from db import koneksi
from umum import halaman, jawab

router = APIRouter(prefix="/api/v1")

# total_nilai_desa = jumlah tiga komponen desa (kolom "Total Desa" di layar).
SQL_DASAR = """
FROM komponen_aset_desa k
JOIN reviu_bast r ON r.uuid_reviu_bast = k.uuid_reviu_bast
"""


@router.get("/komponen-aset-desa")
def daftar_komponen(page: int = 1, per_page: int = 20, kode_desa_kelurahan: str | None = None,
                    nomor_induk_koperasi: str | None = None, kode_provinsi: str | None = None,
                    kode_kabkota: str | None = None, jenis_koperasi: str | None = None,
                    q: str | None = None):
    page, per_page, offset = halaman(page, per_page)
    syarat, param = [], []
    if kode_desa_kelurahan:
        syarat.append("k.kode_desa_kelurahan = %s"); param.append(kode_desa_kelurahan)
    if nomor_induk_koperasi:
        syarat.append("k.nomor_induk_koperasi = %s"); param.append(nomor_induk_koperasi)
    if kode_provinsi:
        syarat.append("k.kode_provinsi = %s"); param.append(kode_provinsi)
    if kode_kabkota:
        syarat.append("k.kode_kabkota = %s"); param.append(kode_kabkota)
    if jenis_koperasi:
        syarat.append("k.jenis_koperasi = %s"); param.append(jenis_koperasi)
    if q:
        syarat.append("(k.nama_desa_kelurahan ILIKE %s OR k.nama_koperasi ILIKE %s OR r.nomor_reviu_bast ILIKE %s)")
        param += [f"%{q}%", f"%{q}%", f"%{q}%"]
    where = ("WHERE " + " AND ".join(syarat)) if syarat else ""
    with koneksi() as con:
        total = con.execute(f"SELECT count(*) AS n {SQL_DASAR} {where}", param).fetchone()["n"]
        items = con.execute(
            f"SELECT k.*, r.nomor_reviu_bast, "
            f"(k.nilai_bast_bangunan_desa + k.nilai_bast_sarana_prasarana_desa + k.nilai_bast_kendaraan_desa) "
            f"AS total_nilai_desa {SQL_DASAR} {where} "
            f"ORDER BY k.nomor_induk_koperasi, k.kode_desa_kelurahan, k.uuid_reviu_bast LIMIT %s OFFSET %s",
            param + [per_page, offset]).fetchall()
    return jawab({"page": page, "per_page": per_page, "total": total, "items": items})