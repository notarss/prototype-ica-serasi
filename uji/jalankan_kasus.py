#!/usr/bin/env python3
"""Pelari kasus uji purwarupa ICA Serasi (Modul 1 sampai 4).

Mengirim data dummy ke aplikasi kalian lewat HTTP, lalu membandingkan hasilnya dengan
harapan.json dan harapan_turunan.json. Hanya memakai pustaka standar Python 3.9+.

Pakai:
  python3 jalankan_kasus.py --url http://localhost:8000 --reset
  python3 jalankan_kasus.py --url http://localhost:8000 --reset --sampai S05   # sampai langkah tertentu
  python3 jalankan_kasus.py --url http://localhost:8000 --hanya S12           # satu langkah (tanpa reset)

Langkah bergantung pada langkah sebelumnya (data tersimpan bertambah), jadi jalankan berurutan
pada basis data kosong. Gunakan --reset agar pelari memanggil POST /api/v1/internal/reset dulu.
Kode keluar 0 bila semua lolos, 1 bila ada yang gagal.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def panggil(url, metode="GET", isi=None):
    data = None if isi is None else json.dumps(isi).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=metode,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8") or "null")
        except ValueError:
            return e.code, None


def total_tersimpan(base, dataset):
    jalur = {"ref_wilayah": "ref-wilayah", "ref_kdkmp": "ref-kdkmp", "reviu_bast": "reviu-bast"}[dataset]
    st, body = panggil(f"{base}/api/v1/{jalur}?page=1&per_page=1")
    if st != 200 or not isinstance(body, dict) or "total" not in body:
        raise AssertionError(f"GET /{jalur} harus 200 dengan field 'total' (dapat {st})")
    return body["total"]


def periksa_langkah(base, s):
    """Mengembalikan daftar pesan kegagalan (kosong berarti lolos)."""
    gagal = []
    rows = json.loads((HERE / s["berkas"]).read_text(encoding="utf-8"))["rows"]
    h = s["harapan"]
    st, body = panggil(base + s["endpoint"], "POST", {"rows": rows})
    if st != 200:
        return [f"HTTP {st}, harusnya 200"]
    if not isinstance(body, dict) or "hasil" not in body:
        return ["respons tidak berisi 'hasil'"]
    if body.get("diterima") != h["diterima"]:
        gagal.append(f"diterima = {body.get('diterima')}, harusnya {h['diterima']}")
    if s["dataset"] == "ref_wilayah":
        if bool(body.get("batch_ditolak")) != h["batch_ditolak"]:
            gagal.append(f"batch_ditolak = {body.get('batch_ditolak')}, harusnya {h['batch_ditolak']}")
        if h["batch_ditolak"]:
            kena = sorted(x["baris"] for x in body["hasil"]
                          if x.get("status") == "DITOLAK" and x.get("error", {}).get("kode") == h["kode"])
            if kena != h["baris_cacat"]:
                gagal.append(f"baris cacat {kena}, harusnya {h['baris_cacat']}")
            if body.get("ditolak") != h["ditolak"]:
                gagal.append(f"ditolak = {body.get('ditolak')}, harusnya {h['ditolak']}")
    else:
        dapat = {x["baris"]: x["error"]["kode"] for x in body["hasil"]
                 if x.get("status") == "DITOLAK" and "error" in x}
        harap = {int(x["baris"]): x["kode"] for x in h["ditolak"]}
        if dapat != harap:
            for b in sorted(set(dapat) | set(harap)):
                if dapat.get(b) != harap.get(b):
                    gagal.append(f"baris {b}: kode {dapat.get(b) or 'DITERIMA'}, harusnya {harap.get(b) or 'DITERIMA'}")
        if body.get("ditolak") != len(harap):
            gagal.append(f"jumlah ditolak = {body.get('ditolak')}, harusnya {len(harap)}")
    try:
        tot = total_tersimpan(base, s["dataset"])
        if tot != h["total_tersimpan"]:
            gagal.append(f"total tersimpan = {tot}, harusnya {h['total_tersimpan']}")
    except AssertionError as e:
        gagal.append(str(e))
    return gagal


def periksa_turunan(base, berkas):
    """Membandingkan komponen_aset_desa dengan harapan_turunan.json."""
    gagal = []
    h = json.loads((HERE / berkas).read_text(encoding="utf-8"))
    items, page = [], 1
    while True:
        st, body = panggil(f"{base}/api/v1/komponen-aset-desa?page={page}&per_page=100")
        if st != 200 or "items" not in body:
            return [f"GET /komponen-aset-desa gagal (HTTP {st})"]
        items += body["items"]
        if len(items) >= body["total"] or not body["items"]:
            break
        page += 1
    if len(items) != h["total_baris_komponen_aset_desa"]:
        gagal.append(f"jumlah baris = {len(items)}, harusnya {h['total_baris_komponen_aset_desa']}")
    indeks = {(x["nomor_induk_koperasi"], x["kode_desa_kelurahan"]): x for x in items}
    medan = ("nilai_reviu_bast_desa", "nilai_bast_bangunan_desa",
             "nilai_bast_sarana_prasarana_desa", "nilai_bast_kendaraan_desa")
    salah = 0
    for nikop, d in h["per_nikop"].items():
        for desa, harap in d["desa"].items():
            x = indeks.get((nikop, desa))
            if x is None:
                gagal.append(f"{nikop}/{desa}: baris tidak ada"); salah += 1
            else:
                for f in medan:
                    if str(x.get(f)) != harap[f]:
                        gagal.append(f"{nikop}/{desa} {f} = {x.get(f)}, harusnya {harap[f]}"); salah += 1
            if salah >= 10:
                gagal.append("... (hanya 10 selisih pertama ditampilkan)")
                return gagal
    return gagal


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="alamat dasar aplikasi, mis. http://localhost:8000")
    ap.add_argument("--reset", action="store_true", help="panggil POST /api/v1/internal/reset sebelum mulai")
    ap.add_argument("--sampai", help="berhenti setelah langkah ini, mis. S05")
    ap.add_argument("--hanya", help="jalankan satu langkah saja, mis. S12 (tanpa reset)")
    ap.add_argument("--tanpa-turunan", action="store_true",
                    help="lewati pemeriksaan T01 (Modul 4), dipakai selama Modul 4 belum selesai")
    a = ap.parse_args()
    base = a.url.rstrip("/")
    man = json.loads((HERE / "data_dummy" / "harapan.json").read_text(encoding="utf-8"))

    if a.reset:
        st, _ = panggil(base + "/api/v1/internal/reset", "POST", {})
        if st != 200:
            print(f"Reset gagal (HTTP {st}). Pastikan POST /api/v1/internal/reset dibuat (kontrak bagian 3).")
            return 1
    lolos = gagal_n = 0
    for s in man["langkah"]:
        if a.hanya and s["id"] != a.hanya:
            continue
        try:
            pesan = periksa_langkah(base, s)
        except Exception as e:                                 # koneksi putus, JSON rusak, dan sebagainya
            pesan = [f"galat: {type(e).__name__}: {e}"]
        if pesan:
            gagal_n += 1
            print(f"GAGAL {s['id']}  {s['judul']}")
            for p in pesan:
                print(f"        - {p}")
        else:
            lolos += 1
            print(f"LOLOS {s['id']}  {s['judul']}")
        if a.sampai and s["id"] == a.sampai:
            break
    # Turunan (Modul 4) diperiksa bila S18 dijalankan
    if (not a.hanya or a.hanya == "S18") and not a.tanpa_turunan:
        if (not a.sampai) or a.sampai >= "S18":
            pesan = periksa_turunan(base, man["turunan"])
            if pesan:
                gagal_n += 1
                print("GAGAL T01  Komponen aset desa (Modul 4) sesuai harapan_turunan.json")
                for p in pesan:
                    print(f"        - {p}")
            else:
                lolos += 1
                print("LOLOS T01  Komponen aset desa (Modul 4) sesuai harapan_turunan.json")
    print(f"\nRingkasan: {lolos} lolos, {gagal_n} gagal")
    return 0 if gagal_n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
