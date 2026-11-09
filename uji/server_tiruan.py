#!/usr/bin/env python3
"""Server tiruan: implementasi kontrak API memakai acuan_validator.py, tanpa basis data.

Fungsi: (1) membuktikan jalankan_kasus.py dan harapan.json konsisten dengan kontrak,
(2) contoh bentuk respons yang diharapkan pelari. BUKAN pengganti aplikasi kalian.

Pakai: python3 server_tiruan.py [port]        (bawaan 8000)
Uji pelari: MOCK_BUG=pembulatan|plafon python3 server_tiruan.py  (sengaja salah)
"""
import json
import os
import sys
import uuid
from decimal import ROUND_DOWN
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import acuan_validator as acuan

BUG = os.environ.get("MOCK_BUG", "")
NEGARA = {}
if BUG == "plafon":                     # sengaja salah: plafon R3-05 dimatikan
    acuan.PLAFON = acuan.Decimal("1e30")


def reset():
    NEGARA.clear()
    NEGARA.update(wilayah={}, kdkmp={}, reviu={}, komponen=[])


reset()


def hasil_batch(dataset, n, ditolak):
    hasil = []
    for i in range(1, n + 1):
        if i in ditolak:
            hasil.append({"baris": i, "status": "DITOLAK",
                          "error": {"kode": ditolak[i], "field": "-", "pesan": ditolak[i]}})
        else:
            hasil.append({"baris": i, "status": "DITERIMA"})
    return {"batch_id": str(uuid.uuid4()), "dataset": dataset, "total": n,
            "diterima": n - len(ditolak), "ditolak": len(ditolak), "hasil": hasil}


class H(BaseHTTPRequestHandler):
    def _kirim(self, kode, obj):
        b = json.dumps(obj).encode()
        self.send_response(kode)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass

    def do_POST(self):
        p = urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        try:
            isi = json.loads(self.rfile.read(n) or b"null")
        except ValueError:
            return self._kirim(400, {"error": "bukan JSON"})
        if p == "/api/v1/internal/reset":
            reset()
            return self._kirim(200, {"ok": True})
        if not isinstance(isi, dict) or not isinstance(isi.get("rows"), list):
            return self._kirim(422, {"error": "rows tidak ada"})
        rows = isi["rows"]
        if p == "/api/v1/ref-wilayah/bulk":
            batal, cacat = acuan.proses_wilayah(rows, NEGARA["wilayah"])
            if batal:
                r = hasil_batch("ref_wilayah", len(rows), {})
                r.update(diterima=0, ditolak=len(rows), batch_ditolak=True,
                         hasil=[{"baris": b, "status": "DITOLAK",
                                 "error": {"kode": "W1-01", "field": "-", "pesan": "baris tidak lengkap"}}
                                for b in cacat])
                return self._kirim(200, r)
            r = hasil_batch("ref_wilayah", len(rows), {})
            r["batch_ditolak"] = False
            return self._kirim(200, r)
        if p == "/api/v1/ref-kdkmp":
            tolak = acuan.proses_kdkmp(rows, NEGARA["wilayah"], NEGARA["kdkmp"])
            return self._kirim(200, hasil_batch("ref_kdkmp", len(rows), tolak))
        if p == "/api/v1/reviu-bast":
            sebelum = set(NEGARA["reviu"])
            tolak = acuan.proses_reviu(rows, NEGARA["kdkmp"], NEGARA["reviu"])
            for u in set(NEGARA["reviu"]) - sebelum:
                r = NEGARA["reviu"][u]
                NEGARA["komponen"] = [k for k in NEGARA["komponen"] if k["uuid_reviu_bast"] != u]
                for k in acuan.bentuk_komponen(r, NEGARA["kdkmp"]):
                    if BUG == "pembulatan":         # sengaja salah: pembulatan ke bawah
                        k = dict(k)
                        faktor = acuan._angka(NEGARA["kdkmp"][k["kode_desa_kelurahan"]]["porsi_kepemilikan"]) / 100
                        k["nilai_reviu_bast_desa"] = str((faktor * acuan._uang(r["nilai_reviu_bast"])).quantize(acuan.DUA, rounding=ROUND_DOWN))
                    NEGARA["komponen"].append(k)
            return self._kirim(200, hasil_batch("reviu_bast", len(rows), tolak))
        self._kirim(404, {"error": "tidak ada"})

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        sumber = {"/api/v1/ref-wilayah": list(NEGARA["wilayah"].values()),
                  "/api/v1/ref-kdkmp": [{k: v for k, v in x.items() if k != "_wil"} for x in NEGARA["kdkmp"].values()],
                  "/api/v1/reviu-bast": list(NEGARA["reviu"].values()),
                  "/api/v1/komponen-aset-desa": NEGARA["komponen"]}
        if u.path not in sumber:
            return self._kirim(404, {"error": "tidak ada"})
        data = sumber[u.path]
        for f in ("nomor_induk_koperasi", "kode_desa_kelurahan"):
            if f in q:
                data = [x for x in data if x.get(f) == q[f]]
        page, per = int(q.get("page", 1)), min(int(q.get("per_page", 20)), 100)
        self._kirim(200, {"page": page, "per_page": per, "total": len(data),
                          "items": data[(page - 1) * per: page * per]})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    HTTPServer(("127.0.0.1", port), H).serve_forever()
