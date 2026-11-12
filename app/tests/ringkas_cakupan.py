"""Jalankan seluruh uji white box dengan pengukur cakupan, lalu ringkas cakupan per fungsi.

Pakai (dari folder app):  python tests/ringkas_cakupan.py
Laporan cakupan bawaan menghitung seluruh berkas modul3.py, termasuk fungsi yang tidak diuji.
Skrip ini membatasi hitungan pada baris milik _cek_lapis1 dan bentuk_komponen.
"""
import inspect
import json
import subprocess
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))

import modul3  # noqa: E402
import turunan  # noqa: E402

FUNGSI = [("modul3.py", "_cek_lapis1", modul3._cek_lapis1),
          ("turunan.py", "bentuk_komponen", turunan.bentuk_komponen)]

with tempfile.TemporaryDirectory() as tmp:
    keluaran = Path(tmp) / "cakupan.json"
    proses = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=no", "--cov=modul3", "--cov=turunan",
                             "--cov-branch", f"--cov-report=json:{keluaran}"],
                            cwd=APP, capture_output=True, text=True)
    data = json.loads(keluaran.read_text(encoding="utf-8"))

print("Hasil pytest:", proses.stdout.strip().splitlines()[-1])
print()
print(f"{'Fungsi':<18}{'Baris':<10}{'Pernyataan':<14}{'Cabang':<10}")
for berkas, nama, fungsi in FUNGSI:
    sumber, awal = inspect.getsourcelines(fungsi)
    akhir = awal + len(sumber) - 1
    d = next(v for k, v in data["files"].items() if k.endswith(berkas))
    jalan = [x for x in d["executed_lines"] if awal <= x <= akhir]
    lewat = [x for x in d["missing_lines"] if awal <= x <= akhir]
    cb_jalan = [x for x in d["executed_branches"] if awal <= x[0] <= akhir]
    cb_lewat = [x for x in d["missing_branches"] if awal <= x[0] <= akhir]
    print(f"{nama:<18}{f'{awal}-{akhir}':<10}{f'{len(jalan)}/{len(jalan) + len(lewat)}':<14}"
          f"{f'{len(cb_jalan)}/{len(cb_jalan) + len(cb_lewat)}':<10}")
