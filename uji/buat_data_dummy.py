#!/usr/bin/env python3
"""Pembangkit data dummy dan kunci jawaban purwarupa ICA Serasi (Modul 1 sampai 4).

Menghasilkan folder data_dummy/ berisi:
  - berkas JSON/CSV masukan untuk tiap langkah
  - harapan.json  : urutan langkah beserta hasil yang HARUS dihasilkan implementasi kalian
Deterministik (tanpa angka acak), jadi hasilnya sama di setiap komputer.
Semua nama dan kode wilayah fiktif. Tidak ada data sungguhan.

Pakai:  python3 buat_data_dummy.py [folder_keluaran]
"""
import csv
import json
import sys
import uuid
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import acuan_validator as acuan

NS = uuid.UUID("5d0b1f3e-0000-4000-8000-00000000a001")
uid = lambda nama: str(uuid.uuid5(NS, nama))
DUA = Decimal("0.01")

# ------------------------------------------------------------------ Wilayah (130 desa)
PROVINSI = {"98": "Provinsi Contoh Satu", "99": "Provinsi Contoh Dua"}
# (kode kab/kota, kode provinsi, nama, jumlah kecamatan, jenis koperasi di wilayah itu)
KABKOTA = [
    ("9801", "98", "Kabupaten Contoh 1A", 3, "KDMP"),
    ("9802", "98", "Kota Contoh 1B", 3, "KKMP"),
    ("9901", "99", "Kabupaten Contoh 2A", 3, "KDMP"),
    ("9902", "99", "Kabupaten Contoh 2B", 4, "KDMP"),
]


def bangun_wilayah():
    rows, jenis = [], {}
    n = 0
    for kab, prov, nama_kab, jml_kec, jns in KABKOTA:
        for k in range(1, jml_kec + 1):
            kec = f"{kab}{k:02d}"
            for d in range(1, 11):
                n += 1
                kode = f"{kec}{d:04d}"
                rows.append({
                    "kode_desa_kelurahan": kode,
                    "nama_desa_kelurahan": f"{'Kelurahan' if jns == 'KKMP' else 'Desa'} Contoh {n:03d}",
                    "kode_kecamatan": kec,
                    "nama_kecamatan": f"Kecamatan Contoh {kec}",
                    "kode_kabkota": kab,
                    "nama_kabkota": nama_kab,
                    "kode_provinsi": prov,
                    "nama_provinsi": PROVINSI[prov],
                })
                jenis[kode] = jns
    assert len(rows) == 130
    return rows, jenis


# ------------------------------------------------------------------ Koperasi (121 desa terpakai maksimal)
def bangun_koperasi(wilayah, jenis_wil):
    """Desa 1-60 TUNGGAL, 61-100 BERSAMA, 101-120 TUNGGAL, 121-130 dicadangkan untuk kasus gagal."""
    desa = [w["kode_desa_kelurahan"] for w in wilayah]
    koperasi = []                         # satu dict per koperasi, berisi daftar baris

    def tambah(kodes, struktur, porsi):
        seq = len(koperasi) + 1
        nikop = f"NIKOP-{seq:04d}"
        jenis = jenis_wil[kodes[0]]
        baris = [{
            "kode_desa_kelurahan": k, "nomor_induk_koperasi": nikop,
            "nama_koperasi": f"Koperasi Contoh {seq:04d}",
            "struktur_kepemilikan": struktur, "porsi_kepemilikan": p, "jenis_koperasi": jenis,
        } for k, p in zip(kodes, porsi)]
        koperasi.append({"nikop": nikop, "jenis": jenis, "struktur": struktur,
                         "desa": kodes, "baris": baris})

    for k in desa[0:60]:
        tambah([k], 1, [100.0])
    i = 60
    for ukuran in (3, 3, 3, 3, 2, 2, 2, 2, 4, 4, 4, 4, 4):
        porsi = {3: [33.333334, 33.333333, 33.333333], 2: [60.0, 40.0], 4: [25.0] * 4}[ukuran]
        tambah(desa[i:i + ukuran], 2, porsi)
        i += ukuran
    assert i == 100
    for k in desa[100:120]:
        tambah([k], 1, [100.0])
    assert len(koperasi) == 93
    return koperasi


# ------------------------------------------------------------------ Reviu BAST valid
def uang(x):
    return f"{Decimal(x):.2f}"


def bangun_reviu(koperasi, wil_per_desa):
    """43 reviu: 30 koperasi TUNGGAL pertama + 13 koperasi BERSAMA."""
    pilih = koperasi[:30] + koperasi[60:73]
    assert len(pilih) == 43 and all(k["struktur"] == 1 for k in koperasi[:30])
    rows, nontulat = [], {}
    bersama_ke = 0
    for urut, k in enumerate(pilih):
        w = wil_per_desa[k["desa"][-1]]            # wilayah desa TERAKHIR (menguji aturan D2)
        if k["struktur"] == 2:
            bersama_ke += 1
        # nilai: bulat kelipatan Rp1.000.000 agar selisih turunan tepat 0 (invarian I5),
        # kecuali dua koperasi 3-desa yang sengaja tidak bulat (menguji pembulatan, I2).
        if k["struktur"] == 2 and bersama_ke == 1:
            nilai, bgn, sar, knd = "1000000001.00", "600000001.00", "300000000.00", "100000000.00"
            nontulat[k["nikop"]] = True
        elif k["struktur"] == 2 and bersama_ke == 2:
            nilai, bgn, sar, knd = "2500000003.33", "1500000001.11", "750000001.11", "250000001.11"
            nontulat[k["nikop"]] = True
        else:
            total = (500 + 100 * (urut % 26)) * 1_000_000          # 500 juta sampai 3 miliar
            nilai, bgn, sar, knd = (uang(total), uang(total * 6 // 10),
                                    uang(total * 3 // 10), uang(total // 10))
        rows.append({
            "uuid_reviu_bast": uid(f"reviu-{k['nikop']}-1"),
            "nomor_induk_koperasi": k["nikop"], "nama_koperasi": k["baris"][0]["nama_koperasi"],
            "jenis_koperasi": k["jenis"],
            "kode_kecamatan": w["kode_kecamatan"], "kode_kabkota": w["kode_kabkota"],
            "kode_provinsi": w["kode_provinsi"],
            "nomor_reviu_bast": f"REVIU/{k['nikop']}/1",
            "tanggal_reviu_bast": f"2026-08-{1 + urut % 28:02d}",
            "jenis_reviu_bast": 1,
            "nilai_reviu_bast": nilai,
            "nilai_bast_bangunan_kdkmp": bgn,
            "nilai_bast_sarana_prasarana_kdkmp": sar,
            "nilai_bast_kendaraan_kdkmp": knd,
        })
    return rows, nontulat


# ------------------------------------------------------------------ Susun semua langkah
def main(keluar):
    keluar = Path(keluar)
    keluar.mkdir(parents=True, exist_ok=True)
    wilayah, jenis_wil = bangun_wilayah()
    wil = {w["kode_desa_kelurahan"]: w for w in wilayah}
    kop = bangun_koperasi(wilayah, jenis_wil)
    semua = [b for k in kop for b in k["baris"]]            # 120 baris, urut desa 1..120
    ada = {w["kode_desa_kelurahan"]: i for i, w in enumerate(wilayah)}
    langkah = []

    def simpan(nama, rows):
        (keluar / nama).write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
        return f"data_dummy/{nama}"

    def tambah(id_, judul, dataset, endpoint, berkas, harapan):
        langkah.append({"id": id_, "judul": judul, "dataset": dataset, "endpoint": endpoint,
                        "berkas": berkas, "harapan": harapan})

    def ditolak(**kv):
        return [{"baris": b, "kode": k} for b, k in kv.items()]

    # ---------------- Modul 1
    cacat = [dict(w) for w in wilayah]
    del cacat[57]["nama_kecamatan"]                          # baris 58 cacat
    tambah("S01", "Wilayah cacat: satu baris tanpa nama_kecamatan, seluruh batch ditolak",
           "ref_wilayah", "/api/v1/ref-wilayah/bulk", simpan("01a_ref_wilayah_cacat.json", cacat),
           {"batch_ditolak": True, "diterima": 0, "ditolak": 130, "baris_cacat": [58],
            "kode": "W1-01", "total_tersimpan": 0})
    tambah("S02", "Wilayah valid, 130 desa/kelurahan diterima",
           "ref_wilayah", "/api/v1/ref-wilayah/bulk", simpan("01b_ref_wilayah_valid.json", wilayah),
           {"batch_ditolak": False, "diterima": 130, "ditolak": 0, "total_tersimpan": 130})
    with (keluar / "01b_ref_wilayah_valid.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(wilayah[0]))
        w.writeheader(); w.writerows(wilayah)

    # ---------------- Modul 2: pengiriman bertahap
    b1 = semua[0:60]
    b2_valid = semua[60:80]                                   # desa 61-80
    b3 = semua[80:120]                                        # desa 81-120 (termasuk 118-120 yang diperbaiki)
    k118, k119, k120 = [dict(semua[i]) for i in (117, 118, 119)]
    k118["nama_koperasi"] = ""                                # K2-01
    k119["porsi_kepemilikan"] = 0                             # K2-01
    k120["kode_desa_kelurahan"] = k120["kode_desa_kelurahan"][:6] + "0099"   # K2-02, kode tidak ada
    b2 = b2_valid + [k118, k119, k120]
    tambah("S03", "ref_kdkmp batch 1: 60 koperasi TUNGGAL",
           "ref_kdkmp", "/api/v1/ref-kdkmp", simpan("02a_kdkmp_batch1.json", b1),
           {"diterima": 60, "ditolak": [], "total_tersimpan": 60})
    tambah("S04", "ref_kdkmp campuran: 20 baris valid (termasuk 8 koperasi BERSAMA) + 3 baris cacat. Menguji partial acceptance",
           "ref_kdkmp", "/api/v1/ref-kdkmp", simpan("02b_kdkmp_campuran.json", b2),
           {"diterima": 20, "ditolak": ditolak(**{"21": "K2-01", "22": "K2-01", "23": "K2-02"}),
            "total_tersimpan": 80})
    tambah("S05", "ref_kdkmp batch 3: kirim ulang utuh 40 baris, termasuk 3 baris yang sudah diperbaiki (resubmit)",
           "ref_kdkmp", "/api/v1/ref-kdkmp", simpan("02c_kdkmp_batch3_resubmit.json", b3),
           {"diterima": 40, "ditolak": [], "total_tersimpan": 120})

    # ---------------- Modul 2: kasus gagal. Tiap kasus mandiri, kecuali K2-03b yang menyimpan satu baris.
    def kop_baris(desa, nikop, jenis="KDMP", porsi=100.0, struktur=1, nama=None):
        return {"kode_desa_kelurahan": desa, "nomor_induk_koperasi": nikop,
                "nama_koperasi": nama if nama is not None else f"Koperasi Uji {nikop}",
                "struktur_kepemilikan": struktur, "porsi_kepemilikan": porsi, "jenis_koperasi": jenis}

    d = [w["kode_desa_kelurahan"] for w in wilayah]           # d[120]..d[129] = desa cadangan
    K = lambda i: d[119 + i]                                  # K(1) = desa ke-120+1 = cadangan pertama

    aneka = [kop_baris(K(1), "NIKOP-9101", nama=""),
             kop_baris(K(2), "NIKOP-9102", struktur=3),
             kop_baris(K(3), "NIKOP-9103", porsi="abc"),
             kop_baris(K(4)[:6] + "000199", "NIKOP-9104"),     # kode desa 12 karakter
             kop_baris(K(5), "NIKOP-9105", porsi=100.5)]
    kasus = [
        ("S06", "K2-01 aneka: nama kosong, struktur 3, porsi bukan angka, kode desa 12 karakter, porsi 100,5",
         "03a_k201_aneka.json", aneka, ditolak(**{str(i): "K2-01" for i in range(1, 6)})),
        ("S07", "Gagal ganda: kode desa tidak ada DAN porsi 0, harus K2-01 (lapis 1 lebih dulu dari lapis 2)",
         "03b_gagal_ganda.json", [kop_baris("9999999999", "NIKOP-9106", porsi=0)], ditolak(**{"1": "K2-01"})),
        ("S08", "K2-02: kode desa tidak ada di ref_wilayah",
         "03c_k202.json", [kop_baris("9801019999", "NIKOP-9107")], ditolak(**{"1": "K2-02"})),
        ("S09", "K2-03: desa sudah tersimpan dari batch 1",
         "03d_k203_tersimpan.json", [kop_baris(d[0], "NIKOP-9108")], ditolak(**{"1": "K2-03"})),
        ("S10", "K2-04: jenis_koperasi bukan KDMP atau KKMP",
         "03e_k204_nilai.json", [kop_baris(K(1), "NIKOP-9109", jenis="XXXX")], ditolak(**{"1": "K2-04"})),
        ("S11", "K2-04: dua baris satu NIKOP BERSAMA dengan jenis berbeda, kedua baris ditolak",
         "03f_k204_tidak_seragam.json",
         [kop_baris(K(1), "NIKOP-9110", "KDMP", 50.0, 2), kop_baris(K(2), "NIKOP-9110", "KKMP", 50.0, 2)],
         ditolak(**{"1": "K2-04", "2": "K2-04"})),
        ("S12", "K2-05: jumlah porsi 90 (50 + 40), kedua baris ditolak",
         "03g_k205_90.json",
         [kop_baris(K(1), "NIKOP-9111", "KDMP", 50.0, 2), kop_baris(K(2), "NIKOP-9111", "KDMP", 40.0, 2)],
         ditolak(**{"1": "K2-05", "2": "K2-05"})),
        ("S13", "K2-05: jumlah porsi 99,999999, semua baris ditolak",
         "03h_k205_kurang.json",
         [kop_baris(K(1), "NIKOP-9112", "KDMP", 33.333334, 2), kop_baris(K(2), "NIKOP-9112", "KDMP", 33.333333, 2),
          kop_baris(K(3), "NIKOP-9112", "KDMP", 33.333332, 2)],
         ditolak(**{"1": "K2-05", "2": "K2-05", "3": "K2-05"})),
        ("S14", "K2-05: jumlah porsi 100,000001, semua baris ditolak",
         "03i_k205_lebih.json",
         [kop_baris(K(1), "NIKOP-9113", "KDMP", 33.333334, 2), kop_baris(K(2), "NIKOP-9113", "KDMP", 33.333334, 2),
          kop_baris(K(3), "NIKOP-9113", "KDMP", 33.333333, 2)],
         ditolak(**{"1": "K2-05", "2": "K2-05", "3": "K2-05"})),
        ("S15", "K2-05: TUNGGAL berporsi 60 (jumlah 60), ditolak",
         "03j_k205_tunggal.json", [kop_baris(K(1), "NIKOP-9114", porsi=60.0)], ditolak(**{"1": "K2-05"})),
        ("S16", "Rambatan D10: satu dari tiga baris BERSAMA bermasalah (kode desa tidak ada), dua baris lain ikut K2-05",
         "03k_rambatan.json",
         [kop_baris(K(1), "NIKOP-9115", "KDMP", 33.333334, 2), kop_baris("9801019998", "NIKOP-9115", "KDMP", 33.333333, 2),
          kop_baris(K(3), "NIKOP-9115", "KDMP", 33.333333, 2)],
         ditolak(**{"1": "K2-05", "2": "K2-02", "3": "K2-05"})),
    ]
    for id_, judul, nama, rows, tolak in kasus:
        tambah(id_, judul, "ref_kdkmp", "/api/v1/ref-kdkmp", simpan(nama, rows),
               {"diterima": len(rows) - len(tolak), "ditolak": tolak, "total_tersimpan": 120})
    tambah("S17", "K2-03: duplikasi dalam satu batch. Baris pertama diterima, baris kedua (identik) ditolak. LANGKAH INI MENYIMPAN SATU BARIS",
           "ref_kdkmp", "/api/v1/ref-kdkmp",
           simpan("03l_k203_dalam_batch.json", [kop_baris(K(1), "NIKOP-9116"), kop_baris(K(1), "NIKOP-9116")]),
           {"diterima": 1, "ditolak": ditolak(**{"2": "K2-03"}), "total_tersimpan": 121})

    # ---------------- Modul 3
    reviu_valid, nontulat = bangun_reviu(kop, wil)
    tambah("S18", "reviu_BAST valid: 43 baris (30 TUNGGAL + 13 BERSAMA), memicu pembentukan komponen_aset_desa",
           "reviu_bast", "/api/v1/reviu-bast", simpan("04a_reviu_valid.json", reviu_valid),
           {"diterima": 43, "ditolak": [], "total_tersimpan": 43})

    def rv(nikop, **ubah):
        k = next(x for x in kop if x["nikop"] == nikop)
        w = wil[k["desa"][-1]]
        r = {"uuid_reviu_bast": uid(f"uji-{nikop}-{len(ubah)}-{sorted(ubah)}"),
             "nomor_induk_koperasi": nikop, "nama_koperasi": k["baris"][0]["nama_koperasi"],
             "jenis_koperasi": k["jenis"], "kode_kecamatan": w["kode_kecamatan"],
             "kode_kabkota": w["kode_kabkota"], "kode_provinsi": w["kode_provinsi"],
             "nomor_reviu_bast": f"UJI/{nikop}", "tanggal_reviu_bast": "2026-08-15", "jenis_reviu_bast": 1,
             "nilai_reviu_bast": "1000000.00", "nilai_bast_bangunan_kdkmp": "600000.00",
             "nilai_bast_sarana_prasarana_kdkmp": "300000.00", "nilai_bast_kendaraan_kdkmp": "100000.00"}
        r.update(ubah)
        return r

    asli_1 = reviu_valid[0]                                   # reviu asli NIKOP-0001
    gagal_reviu = [
        ("S19", "R3-01: nomor_reviu_bast kosong dan tanggal berformat salah",
         "04b_r301.json", [rv("NIKOP-0031", nomor_reviu_bast=""), rv("NIKOP-0031", tanggal_reviu_bast="01-08-2026")],
         ditolak(**{"1": "R3-01", "2": "R3-01"})),
        ("S20", "R3-02: NIKOP tidak terdaftar di ref_kdkmp",
         "04c_r302.json", [rv("NIKOP-0031", nomor_induk_koperasi="NIKOP-9998")], ditolak(**{"1": "R3-02"})),
        ("S21", "R3-07: reviu kedua untuk NIKOP dan jenis yang sama (uuid baru)",
         "04d_r307_pasangan.json", [rv("NIKOP-0001")], ditolak(**{"1": "R3-07"})),
        ("S22", "R3-07: kirim ulang reviu yang sama persis (append-only)",
         "04e_r307_ulang.json", [dict(asli_1)], ditolak(**{"1": "R3-07"})),
        ("S23", "R3-03: kecamatan tidak sesuai dengan desa mana pun milik NIKOP",
         "04f_r303.json", [rv("NIKOP-0031", kode_kecamatan="990204")], ditolak(**{"1": "R3-03"})),
        ("S24", "R3-04: jenis_koperasi tidak sesuai ref_kdkmp",
         "04g_r304.json", [rv("NIKOP-0031", jenis_koperasi="KDMP")], ditolak(**{"1": "R3-04"})),
        ("S25", "R3-05: nilai Rp3.000.000.001,00, komponen dibuat menjumlah agar hanya plafon yang gagal",
         "04h_r305.json",
         [rv("NIKOP-0031", nilai_reviu_bast="3000000001.00", nilai_bast_bangunan_kdkmp="1800000001.00",
             nilai_bast_sarana_prasarana_kdkmp="900000000.00", nilai_bast_kendaraan_kdkmp="300000000.00")],
         ditolak(**{"1": "R3-05"})),
        ("S26", "R3-06: tiga komponen menjumlah Rp999.999,00, bukan Rp1.000.000,00",
         "04i_r306.json", [rv("NIKOP-0031", nilai_bast_kendaraan_kdkmp="99999.00")], ditolak(**{"1": "R3-06"})),
        ("S27", "Gagal ganda: plafon terlampaui DAN komponen tidak menjumlah, harus R3-05 (plafon lebih dulu)",
         "04j_ganda_plafon.json",
         [rv("NIKOP-0031", nilai_reviu_bast="3000000001.00")], ditolak(**{"1": "R3-05"})),
        ("S28", "Gagal ganda: kecamatan salah DAN duplikat, harus R3-07 (duplikat lebih dulu dari wilayah)",
         "04k_ganda_duplikat.json", [rv("NIKOP-0001", kode_kecamatan="990204")], ditolak(**{"1": "R3-07"})),
    ]
    for id_, judul, nama, rows, tolak in gagal_reviu:
        tambah(id_, judul, "reviu_bast", "/api/v1/reviu-bast", simpan(nama, rows),
               {"diterima": len(rows) - len(tolak), "ditolak": tolak, "total_tersimpan": 43})

    # ---------------- Modul 4: nilai turunan yang diharapkan
    # Dihitung langsung dari definisi D5 (porsi/100 x nilai, half up, 2 desimal), bukan dari acuan_validator.
    turunan, jumlah_baris, selisih_maks = {}, 0, Decimal(0)
    for r in reviu_valid:
        k = next(x for x in kop if x["nikop"] == r["nomor_induk_koperasi"])
        per_desa = {}
        for b in k["baris"]:
            f = Decimal(str(b["porsi_kepemilikan"])) / 100
            per_desa[b["kode_desa_kelurahan"]] = {
                "nilai_reviu_bast_desa": str((f * Decimal(r["nilai_reviu_bast"])).quantize(DUA, ROUND_HALF_UP)),
                "nilai_bast_bangunan_desa": str((f * Decimal(r["nilai_bast_bangunan_kdkmp"])).quantize(DUA, ROUND_HALF_UP)),
                "nilai_bast_sarana_prasarana_desa": str((f * Decimal(r["nilai_bast_sarana_prasarana_kdkmp"])).quantize(DUA, ROUND_HALF_UP)),
                "nilai_bast_kendaraan_desa": str((f * Decimal(r["nilai_bast_kendaraan_kdkmp"])).quantize(DUA, ROUND_HALF_UP)),
            }
        selisih = Decimal(r["nilai_reviu_bast"]) - sum(Decimal(v["nilai_reviu_bast_desa"]) for v in per_desa.values())
        selisih_maks = max(selisih_maks, abs(selisih))
        batas = Decimal("0.005") * len(per_desa)
        assert abs(selisih) <= batas, (k["nikop"], selisih)             # invarian I2
        if k["nikop"] not in nontulat:
            assert selisih == 0, (k["nikop"], selisih)                  # invarian I5
        turunan[k["nikop"]] = {"uuid_reviu_bast": r["uuid_reviu_bast"], "selisih_nilai_reviu": str(selisih),
                               "desa": per_desa}
        jumlah_baris += len(per_desa)
    (keluar / "harapan_turunan.json").write_text(
        json.dumps({"total_baris_komponen_aset_desa": jumlah_baris, "selisih_pembulatan_terbesar": str(selisih_maks),
                    "koperasi_tidak_bulat": sorted(nontulat), "per_nikop": turunan}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    # ---------------- Tulis manifest
    (keluar / "harapan.json").write_text(
        json.dumps({"versi": 1, "catatan": "Jalankan langkah sesuai urutan pada basis data kosong. "
                    "Baris yang tidak tercantum di 'ditolak' harus berstatus DITERIMA.",
                    "langkah": langkah, "turunan": "data_dummy/harapan_turunan.json"},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    # ---------------- Pemeriksaan mandiri terhadap implementasi pembanding
    wilayah_db, kdkmp_db, reviu_db = {}, {}, {}
    for s in langkah:
        rows = json.loads((keluar / Path(s["berkas"]).name).read_text(encoding="utf-8"))["rows"]
        h = s["harapan"]
        if s["dataset"] == "ref_wilayah":
            batal, cacat_ = acuan.proses_wilayah(rows, wilayah_db)
            assert batal == h["batch_ditolak"] and (cacat_ == h.get("baris_cacat", [])), s["id"]
            continue
        db = kdkmp_db if s["dataset"] == "ref_kdkmp" else reviu_db
        hasil = (acuan.proses_kdkmp(rows, wilayah_db, kdkmp_db) if s["dataset"] == "ref_kdkmp"
                 else acuan.proses_reviu(rows, kdkmp_db, reviu_db))
        harap = {x["baris"] if isinstance(x["baris"], int) else int(x["baris"]): x["kode"] for x in h["ditolak"]}
        assert hasil == harap, (s["id"], hasil, harap)
        assert len(rows) - len(hasil) == h["diterima"], s["id"]
        assert len(db) == h["total_tersimpan"], (s["id"], len(db), h["total_tersimpan"])
    # turunan: bandingkan acuan_validator dengan perhitungan langsung di atas
    total = 0
    for r in reviu_db.values():
        if r["nomor_induk_koperasi"] not in turunan:
            continue
        for b in acuan.bentuk_komponen(r, kdkmp_db):
            e = turunan[r["nomor_induk_koperasi"]]["desa"][b["kode_desa_kelurahan"]]
            assert all(b[f] == e[f] for f in e), (b, e)
            total += 1
    assert total == jumlah_baris
    print(f"OK: {len(langkah)} langkah, {len(semua)} baris koperasi, {len(reviu_valid)} reviu, "
          f"{jumlah_baris} baris komponen_aset_desa, selisih pembulatan terbesar Rp{selisih_maks}")
    print(f"Berkas ditulis ke: {keluar}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data_dummy")
