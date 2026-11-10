"""Modul 4: komponen_aset_desa (data turunan, tanpa input manual). Pemilik: B."""
from fastapi import APIRouter

from db import koneksi
from umum import halaman, jawab

router = APIRouter(prefix="/api/v1")


@router.get("/komponen-aset-desa")
def daftar_komponen(page: int = 1, per_page: int = 20, kode_desa_kelurahan: str | None = None,
                    nomor_induk_koperasi: str | None = None):
    page, per_page, offset = halaman(page, per_page)
    syarat, param = [], []
    if kode_desa_kelurahan:
        syarat.append("kode_desa_kelurahan = %s"); param.append(kode_desa_kelurahan)
    if nomor_induk_koperasi:
        syarat.append("nomor_induk_koperasi = %s"); param.append(nomor_induk_koperasi)
    where = ("WHERE " + " AND ".join(syarat)) if syarat else ""
    with koneksi() as con:
        total = con.execute(f"SELECT count(*) AS n FROM komponen_aset_desa {where}", param).fetchone()["n"]
        items = con.execute(
            f"SELECT * FROM komponen_aset_desa {where} "
            f"ORDER BY nomor_induk_koperasi, kode_desa_kelurahan, uuid_reviu_bast LIMIT %s OFFSET %s",
            param + [per_page, offset]).fetchall()
    return jawab({"page": page, "per_page": per_page, "total": total, "items": items})