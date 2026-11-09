"""Koneksi ke PostgreSQL. Membaca pengaturan dari berkas .env di folder utama repo."""
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _dsn():
    return (f"host={os.getenv('DB_HOST', 'localhost')} port={os.getenv('DB_PORT', '5433')} "
            f"dbname={os.getenv('DB_NAME')} user={os.getenv('DB_USER')} password={os.getenv('DB_PASSWORD')}")


@contextmanager
def koneksi():
    """Pakai: `with koneksi() as con:`. Berhasil sampai akhir = COMMIT, ada galat = ROLLBACK otomatis."""
    with psycopg.connect(_dsn(), row_factory=dict_row) as con:
        yield con
