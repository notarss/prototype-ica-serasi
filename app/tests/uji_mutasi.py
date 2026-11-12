"""Uji kepekaan: sisipkan satu kesalahan buatan (mutan) pada salinan kode, lalu jalankan seluruh uji.

Uji dianggap peka bila jumlah uji gagal pada salinan bermutan lebih besar daripada jumlah gagal
pada kode asli. Skrip bekerja pada salinan di folder sementara dan tidak mengubah kode di repositori.
Pakai (dari folder app):  python tests/uji_mutasi.py
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
ENV = APP.parent / ".env"

MUTAN = [  # (berkas, teks asli, teks mutan, keterangan)
    ("turunan.py", "ROUND(k.porsi_kepemilikan * r.nilai_reviu_bast / 100, 2)",
     "TRUNC(k.porsi_kepemilikan * r.nilai_reviu_bast / 100, 2)", "ROUND diganti TRUNC pada nilai desa"),
    ("turunan.py", "ROUND(k.porsi_kepemilikan * r.nilai_bast_kendaraan_kdkmp / 100, 2)",
     "ROUND(k.porsi_kepemilikan * r.nilai_bast_bangunan_kdkmp / 100, 2)", "komponen kendaraan memakai nilai bangunan"),
    ("turunan.py", '    con.execute("DELETE FROM komponen_aset_desa WHERE uuid_reviu_bast = %s::uuid", (uuid_reviu_bast,))\n',
     "", "pernyataan DELETE dihapus"),
    ("turunan.py", "WHERE r.uuid_reviu_bast = %s::uuid",
     "WHERE r.uuid_reviu_bast IS NOT NULL AND %s::uuid IS NOT NULL", "WHERE tidak lagi memilih satu reviu"),
    ("modul3.py", "j not in (1, 2, 3, 4)", "j not in (1, 2, 3)", "jenis reviu 4 ditolak"),
    ("modul3.py", "isinstance(j, bool) or ", "", "pemeriksaan bool dihapus"),
    ("modul3.py", r"\d{1,13}(\.\d{1,2})?", r"\d{1,14}(\.\d{1,2})?", "batas uang 13 digit menjadi 14"),
    ("modul3.py", 'return ("tanggal_reviu_bast", "bukan tanggal yang ada di kalender")', "pass",
     "galat tanggal kalender dihapus"),
    ("modul3.py", 'str(uuid_lib.UUID(baris["uuid_reviu_bast"])) == baris["uuid_reviu_bast"]', "True",
     "bentuk kanonik uuid tidak diperiksa"),
    ("modul3.py", 'return ("-", "baris bukan objek JSON")', "pass", "galat bukan-objek dihapus"),
]


def jalankan(folder):
    hasil = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider"],
                           cwd=folder, capture_output=True, text=True)
    gagal = re.search(r"(\d+) failed", hasil.stdout)
    lulus = re.search(r"(\d+) passed", hasil.stdout)
    return int(gagal.group(1)) if gagal else 0, int(lulus.group(1)) if lulus else 0


def salin(tujuan_akar):
    shutil.copytree(APP, tujuan_akar / "app",
                    ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache"))
    if ENV.exists():
        shutil.copy(ENV, tujuan_akar / ".env")


with tempfile.TemporaryDirectory() as tmp:
    akar = Path(tmp) / "asli"
    salin(akar)
    dasar_gagal, dasar_lulus = jalankan(akar / "app")
    print(f"Kode asli: {dasar_gagal} gagal, {dasar_lulus} lulus\n")
    print(f"{'No':<4}{'Mutan':<44}{'Gagal':<8}{'Terdeteksi'}")
    terdeteksi = 0
    for i, (berkas, lama, baru, ket) in enumerate(MUTAN, 1):
        akar_m = Path(tmp) / f"m{i}"
        salin(akar_m)
        jalur = akar_m / "app" / berkas
        isi = jalur.read_text(encoding="utf-8")
        if lama not in isi:
            print(f"M{i:02d}  {ket:<44}teks asli tidak ditemukan; kode berbeda dari yang skrip harapkan")
            continue
        jalur.write_text(isi.replace(lama, baru, 1), encoding="utf-8")
        gagal, _ = jalankan(akar_m / "app")
        ya = gagal > dasar_gagal
        terdeteksi += ya
        print(f"M{i:02d}  {ket:<44}{gagal:<8}{'ya' if ya else 'TIDAK'}")
    print(f"\n{terdeteksi} dari {len(MUTAN)} mutan terdeteksi.")
