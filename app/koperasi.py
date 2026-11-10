"""Koperasi per NIK (gabungan semua desa pemegang porsi), untuk layar Referensi KDKMP. Pemilik: A."""
from fastapi import APIRouter, HTTPException

from db import koneksi
from umum import halaman, jawab

router = APIRouter(prefix="/api/v1")

# Satu baris per NIKOP. ref_kdkmp menyimpan satu baris per desa, jadi baris desa digabung di sini.
SQL_RINGKAS = """
SELECT nomor_induk_koperasi,
       min(nama_koperasi)        AS nama_koperasi,
       min(jenis_koperasi)       AS jenis_koperasi,
       min(struktur_kepemilikan) AS struktur_kepemilikan,
       min(status)               AS status,
       count(*)                  AS jumlah_desa,
       sum(porsi_kepemilikan)    AS total_porsi,
       string_agg(nama_desa_kelurahan, ', ' ORDER BY kode_desa_kelurahan) AS wilayah_pemilik,
       string_agg(DISTINCT nama_kabkota, ', ' ORDER BY nama_kabkota)      AS nama_kabkota,
       string_agg(DISTINCT nama_provinsi, ', ' ORDER BY nama_provinsi)    AS nama_provinsi
FROM ref_kdkmp
"""


@router.get("/koperasi")
def daftar_koperasi(page: int = 1, per_page: int = 20, kode_provinsi: str | None = None,
                    kode_kabkota: str | None = None, jenis_koperasi: str | None = None,
                    q: str | None = None):
    page, per_page, offset = halaman(page, per_page)
    syarat, param_syarat = [], []          # menyaring baris desa sebelum digabung
    if jenis_koperasi:
        syarat.append("jenis_koperasi = %s"); param_syarat.append(jenis_koperasi)
    if q:
        syarat.append("(nama_koperasi ILIKE %s OR nomor_induk_koperasi LIKE %s)")
        param_syarat += [f"%{q}%", f"{q}%"]
    having, param_having = [], []          # koperasi tampil bila SALAH SATU desanya cocok
    if kode_provinsi:
        having.append("bool_or(kode_provinsi = %s)"); param_having.append(kode_provinsi)
    if kode_kabkota:
        having.append("bool_or(kode_kabkota = %s)"); param_having.append(kode_kabkota)
    where = ("WHERE " + " AND ".join(syarat)) if syarat else ""
    hav = ("HAVING " + " AND ".join(having)) if having else ""
    dasar = f"{SQL_RINGKAS} {where} GROUP BY nomor_induk_koperasi {hav}"
    param = param_syarat + param_having
    with koneksi() as con:
        total = con.execute(f"SELECT count(*) AS n FROM ({dasar}) t", param).fetchone()["n"]
        items = con.execute(f"{dasar} ORDER BY nomor_induk_koperasi LIMIT %s OFFSET %s",
                            param + [per_page, offset]).fetchall()
    return jawab({"page": page, "per_page": per_page, "total": total, "items": items})


@router.get("/koperasi/{nomor_induk_koperasi}")
def detail_koperasi(nomor_induk_koperasi: str):
    with koneksi() as con:
        profil = con.execute(f"{SQL_RINGKAS} WHERE nomor_induk_koperasi = %s GROUP BY nomor_induk_koperasi",
                             (nomor_induk_koperasi,)).fetchone()
        if profil is None:
            raise HTTPException(status_code=404, detail="nomor_induk_koperasi tidak ditemukan")
        desa = con.execute(
            "SELECT kode_desa_kelurahan, nama_desa_kelurahan, nama_kecamatan, nama_kabkota, nama_provinsi, "
            "porsi_kepemilikan FROM ref_kdkmp WHERE nomor_induk_koperasi = %s ORDER BY kode_desa_kelurahan",
            (nomor_induk_koperasi,)).fetchall()
        riwayat = con.execute(
            "SELECT uuid_reviu_bast, nomor_reviu_bast, tanggal_reviu_bast, jenis_reviu_bast, nilai_reviu_bast, "
            "nilai_bast_bangunan_kdkmp, nilai_bast_sarana_prasarana_kdkmp, nilai_bast_kendaraan_kdkmp "
            "FROM reviu_bast WHERE nomor_induk_koperasi = %s ORDER BY tanggal_reviu_bast DESC, jenis_reviu_bast",
            (nomor_induk_koperasi,)).fetchall()
    return jawab({"profil": profil, "desa": desa, "riwayat_reviu": riwayat})