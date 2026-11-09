"""Modul 2: ref_kdkmp. Aturan: kontrak API bagian 4 (K2-01 sampai K2-05) dan bagian 7."""
from fastapi import APIRouter, Request

from umum import ambil_rows, baca_json, jawab

router = APIRouter(prefix="/api/v1")


@router.post("/ref-kdkmp")
async def terima_kdkmp(request: Request):
    rows = ambil_rows(await baca_json(request))
    # TODO: tahap 1 sampai 5 (lihat langkah A4)
    return jawab({"jumlah_baris_diterima_server": len(rows)})