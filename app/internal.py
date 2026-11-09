"""Endpoint khusus pengujian. Pemilik: B. Jangan ditampilkan di layar."""
from fastapi import APIRouter

from db import koneksi
from umum import jawab

router = APIRouter(prefix="/api/v1/internal")


@router.post("/reset")
def reset():
    """Kosongkan semua tabel data dan log. ref_jenis_reviu_bast (data acuan tetap) tidak disentuh."""
    with koneksi() as con:
        con.execute("TRUNCATE batch_log, error_log, ref_wilayah, ref_kdkmp, reviu_bast, "
                    "komponen_aset_desa, basis_permohonan_bank RESTART IDENTITY CASCADE")
    return jawab({"ok": True})
