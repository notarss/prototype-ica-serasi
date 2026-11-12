"""Fixture bersama. Koneksi uji tidak pernah melakukan commit, jadi data uji hilang saat rollback."""
import psycopg
import pytest
from psycopg.rows import dict_row

from db import _dsn


@pytest.fixture
def con():
    try:
        koneksi = psycopg.connect(_dsn(), row_factory=dict_row, connect_timeout=5)
    except psycopg.OperationalError as galat:
        pytest.fail(f"Basis data tidak dapat dihubungi. Jalankan 'docker compose up -d' lebih dulu. Rincian: {galat}")
    try:
        yield koneksi
    finally:
        koneksi.rollback()
        koneksi.close()
