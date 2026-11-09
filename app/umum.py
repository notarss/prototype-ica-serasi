"""Fungsi bersama Modul 1, 2, dan 3. Pemilik: B. Ubah lewat Pull Request yang dibaca A."""
import json
import uuid
from decimal import Decimal

from fastapi import HTTPException, Request, Response
from psycopg.types.json import Jsonb


def _ke_teks(o):
    return str(o)          # Decimal, tanggal, UUID dikirim sebagai teks


def jawab(isi, kode=200):
    """Pengganti JSONResponse. Uang dan porsi (Decimal) keluar sebagai teks desimal, bukan float."""
    return Response(content=json.dumps(isi, default=_ke_teks, ensure_ascii=False),
                    media_type="application/json", status_code=kode)


async def baca_json(request: Request):
    """Baca body sebagai JSON. Angka desimal dibaca sebagai Decimal (bukan float), sesuai kontrak."""
    body = await request.body()
    try:
        return json.loads(body, parse_float=Decimal)
    except ValueError:
        raise HTTPException(status_code=400, detail="isi permintaan bukan JSON atau kosong")


def ambil_rows(data):
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise HTTPException(status_code=422, detail="field 'rows' (array) tidak ada")
    return data["rows"]


def teks_valid(baris, field, maks):
    v = baris.get(field)
    return isinstance(v, str) and v.strip() != "" and len(v) <= maks


def catat_batch(con, dataset, total, diterima, ditolak, galat):
    """Tulis satu baris batch_log dan satu baris error_log per entri `galat`.
    `galat` = daftar dict {baris, kode, field, pesan, data}. Mengembalikan batch_id (teks)."""
    batch_id = uuid.uuid4()
    con.execute(
        "INSERT INTO batch_log (batch_id, dataset, total_baris, baris_diterima, baris_ditolak) "
        "VALUES (%s, %s, %s, %s, %s)", (batch_id, dataset, total, diterima, ditolak))
    for g in galat:
        con.execute(
            "INSERT INTO error_log (batch_id, nomor_baris, kode_error, field, pesan, data_baris) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (batch_id, g["baris"], g["kode"], g.get("field"), g["pesan"],
             Jsonb(g.get("data"), dumps=lambda o: json.dumps(o, default=_ke_teks))))
    return str(batch_id)


def susun_respons(dataset, batch_id, total, galat):
    """Bentuk respons standar kontrak (bagian 2) untuk Modul 2 dan 3."""
    per_baris = {g["baris"]: g for g in galat}
    hasil = []
    for n in range(1, total + 1):
        if n in per_baris:
            g = per_baris[n]
            hasil.append({"baris": n, "status": "DITOLAK",
                          "error": {"kode": g["kode"], "field": g.get("field"), "pesan": g["pesan"]}})
        else:
            hasil.append({"baris": n, "status": "DITERIMA"})
    return {"batch_id": batch_id, "dataset": dataset, "total": total,
            "diterima": total - len(per_baris), "ditolak": len(per_baris), "hasil": hasil}


def halaman(page, per_page):
    """Batasi page >= 1 dan 1 <= per_page <= 100. Mengembalikan (page, per_page, offset)."""
    page = max(page, 1)
    per_page = min(max(per_page, 1), 100)
    return page, per_page, (page - 1) * per_page
