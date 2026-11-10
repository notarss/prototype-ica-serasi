"""Titik masuk aplikasi. Jalankan dari folder app/:  uvicorn main:app --reload --port 8000"""
from fastapi import FastAPI

import internal
import modul1
import modul2
import modul3
import modul4
import riwayat
from db import koneksi
from umum import jawab

app = FastAPI(title="Purwarupa ICA Serasi")
app.include_router(modul1.router)
app.include_router(modul2.router)
app.include_router(modul3.router)
app.include_router(modul4.router)
app.include_router(riwayat.router)
app.include_router(internal.router)
# A menambah: import modul2, modul3 lalu app.include_router(...)


@app.get("/healthz")
def healthz():
    with koneksi() as con:
        con.execute("SELECT 1")
    return jawab({"status": "ok"})