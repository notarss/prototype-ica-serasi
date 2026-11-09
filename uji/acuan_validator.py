"""Implementasi pembanding aturan Modul 1 sampai 4 (kontrak API bagian 4, 5, dan 7).

Tujuan: memeriksa bahwa kunci jawaban (harapan.json) konsisten dengan aturan di kontrak.
Ini BUKAN kode produksi purwarupa. A dan B menulis implementasi sendiri, lalu
membandingkannya dengan harapan.json lewat jalankan_kasus.py.

Hanya memakai pustaka standar Python 3.9 atau lebih baru.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import date

JENIS_VALID = ("KDMP", "KKMP")
PLAFON = Decimal("3000000000")
DUA = Decimal("0.01")


def _angka(x):
    """Angka JSON (bukan bool, bukan string) menjadi Decimal, atau None."""
    if isinstance(x, bool) or not isinstance(x, (int, float, Decimal)):
        return None
    try:
        return Decimal(str(x))
    except InvalidOperation:
        return None


def _uang(x):
    """Uang dikirim sebagai string desimal. Mengembalikan Decimal atau None."""
    if not isinstance(x, str):
        return None
    try:
        v = Decimal(x)
    except InvalidOperation:
        return None
    return v if v >= 0 else None


def _teks(row, field, maks):
    v = row.get(field)
    return isinstance(v, str) and v.strip() != "" and len(v) <= maks


# ---------------------------------------------------------------- Modul 1
FIELD_WILAYAH = {
    "kode_desa_kelurahan": 10, "nama_desa_kelurahan": 150,
    "kode_kecamatan": 10, "nama_kecamatan": 100,
    "kode_kabkota": 4, "nama_kabkota": 150,
    "kode_provinsi": 2, "nama_provinsi": 100,
}


def proses_wilayah(rows, wilayah):
    """Mengembalikan (batch_ditolak, baris_cacat). Bila tidak ditolak, wilayah diperbarui."""
    cacat = [i + 1 for i, r in enumerate(rows)
             if not all(_teks(r, f, m) for f, m in FIELD_WILAYAH.items())]
    if cacat:
        return True, cacat
    for r in rows:
        wilayah[r["kode_desa_kelurahan"]] = {f: r[f] for f in FIELD_WILAYAH}
    return False, []


# ---------------------------------------------------------------- Modul 2
def _lapis1_kdkmp(r):
    if not (_teks(r, "kode_desa_kelurahan", 10) and _teks(r, "nomor_induk_koperasi", 30)
            and _teks(r, "nama_koperasi", 255) and _teks(r, "jenis_koperasi", 10)):
        return False
    s = r.get("struktur_kepemilikan")
    if isinstance(s, bool) or s not in (1, 2):
        return False
    p = _angka(r.get("porsi_kepemilikan"))
    return p is not None and Decimal(0) < p <= Decimal(100)


def proses_kdkmp(rows, wilayah, tersimpan):
    """Mengembalikan dict {nomor_baris: kode_error}. Baris yang tidak ada di dict diterima.
    `tersimpan` (dict kode_desa -> baris) diperbarui dengan baris yang diterima."""
    ditolak = {}
    hidup = []              # indeks baris yang masih lolos
    terlihat = set()
    for i, r in enumerate(rows):
        n = i + 1
        if not _lapis1_kdkmp(r):
            ditolak[n] = "K2-01"; continue
        if r["kode_desa_kelurahan"] not in wilayah:
            ditolak[n] = "K2-02"; continue
        if r["kode_desa_kelurahan"] in tersimpan or r["kode_desa_kelurahan"] in terlihat:
            ditolak[n] = "K2-03"; continue
        terlihat.add(r["kode_desa_kelurahan"])
        hidup.append(i)
    # Lapis 4 (D1): nilai KDMP/KKMP dan seragam per NIKOP di antara baris yang lolos lapis 1-3
    per_nikop = {}
    for i in hidup:
        per_nikop.setdefault(rows[i]["nomor_induk_koperasi"], []).append(i)
    hidup4 = []
    for idx in per_nikop.values():
        jenis = {rows[i]["jenis_koperasi"] for i in idx}
        for i in idx:
            if rows[i]["jenis_koperasi"] not in JENIS_VALID or len(jenis) > 1:
                ditolak[i + 1] = "K2-04"
            else:
                hidup4.append(i)
    # Lapis 5 (D3, D10): jumlah porsi per NIKOP atas baris yang lolos lapis 1-4
    per_nikop = {}
    for i in hidup4:
        per_nikop.setdefault(rows[i]["nomor_induk_koperasi"], []).append(i)
    for idx in per_nikop.values():
        total = sum(_angka(rows[i]["porsi_kepemilikan"]) for i in idx)
        for i in idx:
            if total != Decimal("100.000000"):
                ditolak[i + 1] = "K2-05"
            else:
                d = rows[i]["kode_desa_kelurahan"]
                tersimpan[d] = dict(rows[i])
                tersimpan[d]["_wil"] = wilayah[d]    # data wilayah turunan, diisi sistem
    return ditolak


# ---------------------------------------------------------------- Modul 3
def _lapis1_reviu(r):
    if not (_teks(r, "uuid_reviu_bast", 36) and _teks(r, "nomor_induk_koperasi", 30)
            and _teks(r, "nama_koperasi", 255) and _teks(r, "jenis_koperasi", 10)
            and _teks(r, "kode_kecamatan", 10) and _teks(r, "kode_kabkota", 4)
            and _teks(r, "kode_provinsi", 2) and _teks(r, "nomor_reviu_bast", 60)):
        return False
    try:
        t = r.get("tanggal_reviu_bast")
        if not isinstance(t, str) or len(t) != 10:
            return False
        date.fromisoformat(t)
    except ValueError:
        return False
    if isinstance(r.get("jenis_reviu_bast"), bool) or r.get("jenis_reviu_bast") not in (1, 2, 3, 4):
        return False
    return all(_uang(r.get(f)) is not None for f in (
        "nilai_reviu_bast", "nilai_bast_bangunan_kdkmp",
        "nilai_bast_sarana_prasarana_kdkmp", "nilai_bast_kendaraan_kdkmp"))


def proses_reviu(rows, tersimpan_kdkmp, reviu):
    """`reviu` adalah dict uuid -> baris. Mengembalikan {nomor_baris: kode_error}."""
    ditolak = {}
    terlihat_uuid = set()
    for i, r in enumerate(rows):
        n = i + 1
        if not _lapis1_reviu(r):
            ditolak[n] = "R3-01"; continue
        nikop = r["nomor_induk_koperasi"]
        koperasi = [k for k in tersimpan_kdkmp.values() if k["nomor_induk_koperasi"] == nikop]
        if not koperasi:
            ditolak[n] = "R3-02"; continue
        pasangan = {(v["nomor_induk_koperasi"], v["jenis_reviu_bast"]) for v in reviu.values()}
        if (r["uuid_reviu_bast"] in reviu or r["uuid_reviu_bast"] in terlihat_uuid
                or (nikop, r["jenis_reviu_bast"]) in pasangan):
            ditolak[n] = "R3-07"; continue
        # D2: kecamatan, kab/kota, provinsi harus sama dengan salah satu desa ber-NIKOP itu
        # (data wilayah disimpan di baris reviu pembanding lewat kunci "_wilayah")
        cocok = any(
            (k["_wil"]["kode_kecamatan"], k["_wil"]["kode_kabkota"], k["_wil"]["kode_provinsi"])
            == (r["kode_kecamatan"], r["kode_kabkota"], r["kode_provinsi"]) for k in koperasi)
        if not cocok:
            ditolak[n] = "R3-03"; continue
        if r["jenis_koperasi"] != koperasi[0]["jenis_koperasi"]:
            ditolak[n] = "R3-04"; continue
        nilai = _uang(r["nilai_reviu_bast"])
        if nilai > PLAFON:
            ditolak[n] = "R3-05"; continue
        jumlah = (_uang(r["nilai_bast_bangunan_kdkmp"]) + _uang(r["nilai_bast_sarana_prasarana_kdkmp"])
                  + _uang(r["nilai_bast_kendaraan_kdkmp"]))
        if jumlah != nilai:
            ditolak[n] = "R3-06"; continue
        terlihat_uuid.add(r["uuid_reviu_bast"])
        reviu[r["uuid_reviu_bast"]] = dict(r)
    return ditolak


# ---------------------------------------------------------------- Modul 4
def bentuk_komponen(reviu_baris, tersimpan_kdkmp):
    """Daftar baris komponen_aset_desa untuk satu reviu (D5: porsi/100, half up, 2 desimal)."""
    out = []
    nikop = reviu_baris["nomor_induk_koperasi"]
    for k in tersimpan_kdkmp.values():
        if k["nomor_induk_koperasi"] != nikop:
            continue
        faktor = _angka(k["porsi_kepemilikan"]) / Decimal(100)

        def hit(nama):
            return str((faktor * _uang(reviu_baris[nama])).quantize(DUA, rounding=ROUND_HALF_UP))

        out.append({
            "kode_desa_kelurahan": k["kode_desa_kelurahan"],
            "uuid_reviu_bast": reviu_baris["uuid_reviu_bast"],
            "nomor_induk_koperasi": nikop,
            "nilai_reviu_bast_desa": hit("nilai_reviu_bast"),
            "nilai_bast_bangunan_desa": hit("nilai_bast_bangunan_kdkmp"),
            "nilai_bast_sarana_prasarana_desa": hit("nilai_bast_sarana_prasarana_kdkmp"),
            "nilai_bast_kendaraan_desa": hit("nilai_bast_kendaraan_kdkmp"),
        })
    return out
