"""Daftar pilihan untuk dropdown filter di layar. Pemilik: A."""
from fastapi import APIRouter

from db import koneksi
from umum import jawab

router = APIRouter(prefix="/api/v1/opsi")


@router.get("/provinsi")
def opsi_provinsi():
    with koneksi() as con:
        items = con.execute("SELECT DISTINCT kode_provinsi, nama_provinsi FROM ref_wilayah "
                            "ORDER BY nama_provinsi").fetchall()
    return jawab({"items": items})


@router.get("/kabkota")
def opsi_kabkota(kode_provinsi: str | None = None):
    syarat, param = "", []
    if kode_provinsi:
        syarat = "WHERE kode_provinsi = %s"; param.append(kode_provinsi)
    with koneksi() as con:
        items = con.execute(f"SELECT DISTINCT kode_kabkota, nama_kabkota, kode_provinsi FROM ref_wilayah {syarat} "
                            f"ORDER BY nama_kabkota", param).fetchall()
    return jawab({"items": items})