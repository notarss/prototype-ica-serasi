"""Riwayat pengiriman dan error log (dibaca layar). Pemilik: A. Kontrak API bagian 3."""
import uuid as uuid_lib

from fastapi import APIRouter, HTTPException

from db import koneksi
from umum import halaman, jawab

router = APIRouter(prefix="/api/v1")


@router.get("/batches")
def daftar_batch(page: int = 1, per_page: int = 20, dataset: str | None = None):
    page, per_page, offset = halaman(page, per_page)
    syarat, param = [], []
    if dataset:
        syarat.append("dataset = %s"); param.append(dataset)
    where = ("WHERE " + " AND ".join(syarat)) if syarat else ""
    with koneksi() as con:
        total = con.execute(f"SELECT count(*) AS n FROM batch_log {where}", param).fetchone()["n"]
        items = con.execute(
            f"SELECT * FROM batch_log {where} ORDER BY diterima_pada DESC, batch_id LIMIT %s OFFSET %s",
            param + [per_page, offset]).fetchall()
    return jawab({"page": page, "per_page": per_page, "total": total, "items": items})


@router.get("/batches/{batch_id}/errors")
def error_batch(batch_id: str, page: int = 1, per_page: int = 20, kode_error: str | None = None):
    try:
        uuid_lib.UUID(batch_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="batch_id tidak ditemukan")
    page, per_page, offset = halaman(page, per_page)
    syarat, param = ["batch_id = %s::uuid"], [batch_id]
    if kode_error:
        syarat.append("kode_error = %s"); param.append(kode_error)
    where = "WHERE " + " AND ".join(syarat)
    with koneksi() as con:
        ada = con.execute("SELECT 1 FROM batch_log WHERE batch_id = %s::uuid", (batch_id,)).fetchone()
        if ada is None:
            raise HTTPException(status_code=404, detail="batch_id tidak ditemukan")
        total = con.execute(f"SELECT count(*) AS n FROM error_log {where}", param).fetchone()["n"]
        items = con.execute(
            f"SELECT * FROM error_log {where} ORDER BY nomor_baris, id LIMIT %s OFFSET %s",
            param + [per_page, offset]).fetchall()
    return jawab({"batch_id": batch_id, "page": page, "per_page": per_page, "total": total, "items": items})