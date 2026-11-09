-- =====================================================================
-- Purwarupa ICA Serasi, skema basis data Modul 1 sampai 5
-- Sumber utama : DPPL SIKD Serasi V5.04, Bab 4.2 Kamus Data (mengikuti UR V5.04)
-- Target       : PostgreSQL 14 atau lebih baru
-- Catatan      : Kolom bertanda [DPPL-DUPLIKAT] sengaja diduplikasi dari tabel lain
--                karena DPPL merancangnya begitu. Purwarupa meniru rancangan itu
--                apa adanya supaya rancangan DPPL yang diuji, bukan versi perbaikan.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Pencatatan pengiriman (tidak ada di DPPL, ditambahkan khusus purwarupa)
-- ---------------------------------------------------------------------
CREATE TABLE batch_log (
    batch_id        UUID PRIMARY KEY,
    dataset         VARCHAR(30)  NOT NULL
                    CHECK (dataset IN ('ref_wilayah', 'ref_kdkmp', 'reviu_bast')),
    pengirim        VARCHAR(50)  NOT NULL DEFAULT 'SIMKOPDES',
    total_baris     INTEGER      NOT NULL CHECK (total_baris >= 0),
    baris_diterima  INTEGER      NOT NULL CHECK (baris_diterima >= 0),
    baris_ditolak   INTEGER      NOT NULL CHECK (baris_ditolak >= 0),
    diterima_pada   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CHECK (baris_diterima + baris_ditolak = total_baris)
);

CREATE TABLE error_log (
    id              BIGSERIAL PRIMARY KEY,
    batch_id        UUID         NOT NULL REFERENCES batch_log (batch_id),
    nomor_baris     INTEGER      NOT NULL CHECK (nomor_baris >= 1),
    kode_error      VARCHAR(10)  NOT NULL,
    field           VARCHAR(60),
    pesan           TEXT         NOT NULL,
    data_baris      JSONB,
    dibuat_pada     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_error_log_batch ON error_log (batch_id, nomor_baris);

-- ---------------------------------------------------------------------
-- Modul 1: ref_wilayah (DPPL 4.2 butir 1)
-- Diterima utuh (bulk), tanpa validasi substansi dan tanpa partial acceptance.
-- ---------------------------------------------------------------------
CREATE TABLE ref_wilayah (
    kode_desa_kelurahan VARCHAR(10)  PRIMARY KEY,
    nama_desa_kelurahan VARCHAR(150) NOT NULL,
    kode_kecamatan      VARCHAR(10)  NOT NULL,
    nama_kecamatan      VARCHAR(100) NOT NULL,
    kode_kabkota        VARCHAR(4)   NOT NULL,
    nama_kabkota        VARCHAR(150) NOT NULL,
    kode_provinsi       VARCHAR(2)   NOT NULL,
    nama_provinsi       VARCHAR(100) NOT NULL,
    diterima_pada       TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_ref_wilayah_kecamatan ON ref_wilayah (kode_kecamatan);
CREATE INDEX ix_ref_wilayah_kabkota   ON ref_wilayah (kode_kabkota);

-- ---------------------------------------------------------------------
-- Modul 2: ref_kdkmp (DPPL 4.2 butir 2)
-- PK tunggal kode_desa_kelurahan: satu desa satu baris (DPPL menegaskannya).
-- NIKOP boleh berulang antarbaris bila struktur_kepemilikan = BERSAMA.
-- Kode jenis_koperasi: sumber (DPPL dan UR) hanya menyebut "1 digit: KDMP atau KKMP"
-- tanpa memetakan angkanya, jadi purwarupa menyimpan teks 'KDMP' atau 'KKMP'.
-- ---------------------------------------------------------------------
CREATE TABLE ref_kdkmp (
    kode_desa_kelurahan  VARCHAR(10)   PRIMARY KEY
                         REFERENCES ref_wilayah (kode_desa_kelurahan),
    nama_desa_kelurahan  VARCHAR(150)  NOT NULL,   -- [DPPL-DUPLIKAT] dari ref_wilayah
    kode_kecamatan       VARCHAR(10)   NOT NULL,   -- [DPPL-DUPLIKAT]
    nama_kecamatan       VARCHAR(100)  NOT NULL,   -- [DPPL-DUPLIKAT]
    kode_kabkota         VARCHAR(4)    NOT NULL,   -- [DPPL-DUPLIKAT]
    nama_kabkota         VARCHAR(150)  NOT NULL,   -- [DPPL-DUPLIKAT]
    kode_provinsi        VARCHAR(2)    NOT NULL,   -- [DPPL-DUPLIKAT]
    nama_provinsi        VARCHAR(100)  NOT NULL,   -- [DPPL-DUPLIKAT]
    nomor_induk_koperasi VARCHAR(30)   NOT NULL,
    nama_koperasi        VARCHAR(255)  NOT NULL,
    -- 1 = TUNGGAL, 2 = BERSAMA. DPPL menandainya "Tidak*" (kemungkinan kelalaian);
    -- UR V5.04 menandainya wajib, jadi purwarupa mewajibkannya.
    struktur_kepemilikan SMALLINT      NOT NULL CHECK (struktur_kepemilikan IN (1, 2)),
    -- Skala 0 sampai 100 (UR V5.04). Presisi 6 desimal.
    porsi_kepemilikan    NUMERIC(9,6)  NOT NULL
                         CHECK (porsi_kepemilikan > 0 AND porsi_kepemilikan <= 100),
    jenis_koperasi       VARCHAR(4)    NOT NULL CHECK (jenis_koperasi IN ('KDMP', 'KKMP')),
    status               VARCHAR(10)   NOT NULL DEFAULT 'AKTIF' CHECK (status = 'AKTIF'),
    batch_id             UUID          REFERENCES batch_log (batch_id),
    diterima_pada        TIMESTAMPTZ   NOT NULL DEFAULT now()
);
-- Bukan UNIQUE, karena NIKOP boleh berulang bila BERSAMA.
CREATE INDEX ix_ref_kdkmp_nikop ON ref_kdkmp (nomor_induk_koperasi);

-- ---------------------------------------------------------------------
-- Tabel acuan jenis reviu (DPPL menyebut FK ke ref_jenis_reviu_BAST)
-- ---------------------------------------------------------------------
CREATE TABLE ref_jenis_reviu_bast (
    kode_jenis  SMALLINT    PRIMARY KEY CHECK (kode_jenis BETWEEN 1 AND 4),
    nama_jenis  VARCHAR(30) NOT NULL
);
INSERT INTO ref_jenis_reviu_bast (kode_jenis, nama_jenis) VALUES
    (1, 'Gabungan'),
    (2, 'Bangunan'),
    (3, 'Sarana Prasarana'),
    (4, 'Kendaraan');

-- ---------------------------------------------------------------------
-- Modul 3: reviu_bast (DPPL 4.2 butir 3). Append-only.
-- Catatan desain: DPPL menyatakan nomor_induk_koperasi sebagai FK ke ref_kdkmp,
-- tetapi NIKOP tidak unik di ref_kdkmp (BERSAMA), sehingga PostgreSQL tidak
-- dapat membuat FK fisik. Keberadaan NIKOP diperiksa di lapisan aplikasi.
-- ---------------------------------------------------------------------
CREATE TABLE reviu_bast (
    uuid_reviu_bast      UUID          PRIMARY KEY,
    nomor_induk_koperasi VARCHAR(30)   NOT NULL,
    nama_koperasi        VARCHAR(255)  NOT NULL,   -- [DPPL-DUPLIKAT] dari ref_kdkmp
    jenis_koperasi       VARCHAR(4)    NOT NULL CHECK (jenis_koperasi IN ('KDMP', 'KKMP')),
    kode_kecamatan       VARCHAR(10)   NOT NULL,   -- [DPPL-DUPLIKAT]
    nama_kecamatan       VARCHAR(100),             -- [DPPL-DUPLIKAT], tidak wajib di DPPL
    kode_kabkota         VARCHAR(4)    NOT NULL,   -- [DPPL-DUPLIKAT]
    nama_kabkota         VARCHAR(150),             -- [DPPL-DUPLIKAT], tidak wajib di DPPL
    kode_provinsi        VARCHAR(2)    NOT NULL,   -- [DPPL-DUPLIKAT]
    nama_provinsi        VARCHAR(100),             -- [DPPL-DUPLIKAT], tidak wajib di DPPL
    nomor_reviu_bast     VARCHAR(60)   NOT NULL,
    tanggal_reviu_bast   DATE          NOT NULL,
    jenis_reviu_bast     SMALLINT      NOT NULL DEFAULT 1
                         REFERENCES ref_jenis_reviu_bast (kode_jenis),
    nilai_reviu_bast     NUMERIC(15,2) NOT NULL
                         CHECK (nilai_reviu_bast >= 0 AND nilai_reviu_bast <= 3000000000),
    nilai_bast_bangunan_kdkmp         NUMERIC(15,2) NOT NULL CHECK (nilai_bast_bangunan_kdkmp >= 0),
    nilai_bast_sarana_prasarana_kdkmp NUMERIC(15,2) NOT NULL CHECK (nilai_bast_sarana_prasarana_kdkmp >= 0),
    nilai_bast_kendaraan_kdkmp        NUMERIC(15,2) NOT NULL CHECK (nilai_bast_kendaraan_kdkmp >= 0),
    batch_id             UUID          REFERENCES batch_log (batch_id),
    diterima_pada        TIMESTAMPTZ   NOT NULL DEFAULT now(),
    -- "unik per NIKOP per jenis reviu" (DPPL 4.2 butir 3)
    UNIQUE (nomor_induk_koperasi, jenis_reviu_bast),
    -- Kriteria 4 Modul 3: tiga komponen harus sama dengan nilai total
    CHECK (nilai_bast_bangunan_kdkmp + nilai_bast_sarana_prasarana_kdkmp
           + nilai_bast_kendaraan_kdkmp = nilai_reviu_bast)
);
CREATE INDEX ix_reviu_bast_nikop ON reviu_bast (nomor_induk_koperasi);

-- ---------------------------------------------------------------------
-- Modul 4: komponen_aset_desa (DPPL 4.2 butir 4). Turunan otomatis.
-- DPPL tidak menetapkan PK. Purwarupa memakai PK komposit
-- (kode_desa_kelurahan, uuid_reviu_bast), selaras dengan basis_permohonan_bank.
-- Rumus (porsi berskala 0..100): nilai_desa = ROUND(porsi / 100 * nilai_nikop, 2)
-- ---------------------------------------------------------------------
CREATE TABLE komponen_aset_desa (
    kode_desa_kelurahan  VARCHAR(10)   NOT NULL REFERENCES ref_kdkmp (kode_desa_kelurahan),
    uuid_reviu_bast      UUID          NOT NULL REFERENCES reviu_bast (uuid_reviu_bast),
    nama_desa_kelurahan  VARCHAR(255),             -- [DPPL-DUPLIKAT]
    kode_kecamatan       VARCHAR(10)   NOT NULL,   -- [DPPL-DUPLIKAT]
    nama_kecamatan       VARCHAR(100),             -- [DPPL-DUPLIKAT]
    kode_kabkota         VARCHAR(4)    NOT NULL,   -- [DPPL-DUPLIKAT]
    nama_kabkota         VARCHAR(150),             -- [DPPL-DUPLIKAT]
    kode_provinsi        VARCHAR(2)    NOT NULL,   -- [DPPL-DUPLIKAT]
    nama_provinsi        VARCHAR(100),             -- [DPPL-DUPLIKAT]
    nomor_induk_koperasi VARCHAR(30)   NOT NULL,
    nama_koperasi        VARCHAR(255),             -- [DPPL-DUPLIKAT]
    struktur_kepemilikan SMALLINT      CHECK (struktur_kepemilikan IN (1, 2)),   -- [DPPL-DUPLIKAT]
    porsi_kepemilikan    NUMERIC(9,6)  NOT NULL,   -- [DPPL-DUPLIKAT]
    jenis_koperasi       VARCHAR(4)    NOT NULL CHECK (jenis_koperasi IN ('KDMP', 'KKMP')),
    nilai_reviu_bast     NUMERIC(15,2) NOT NULL,   -- tingkat NIKOP [DPPL-DUPLIKAT]
    nilai_reviu_bast_desa NUMERIC(15,2) NOT NULL,  -- hasil kalkulasi
    jenis_reviu_bast     SMALLINT      NOT NULL REFERENCES ref_jenis_reviu_bast (kode_jenis),
    tanggal_reviu_bast   DATE          NOT NULL,
    nilai_bast_bangunan_kdkmp         NUMERIC(15,2) NOT NULL,   -- tingkat NIKOP
    nilai_bast_sarana_prasarana_kdkmp NUMERIC(15,2) NOT NULL,
    nilai_bast_kendaraan_kdkmp        NUMERIC(15,2) NOT NULL,
    nilai_bast_bangunan_desa          NUMERIC(15,2) NOT NULL,   -- hasil kalkulasi
    nilai_bast_sarana_prasarana_desa  NUMERIC(15,2) NOT NULL,
    nilai_bast_kendaraan_desa         NUMERIC(15,2) NOT NULL,
    dibentuk_pada        TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (kode_desa_kelurahan, uuid_reviu_bast)
);
CREATE INDEX ix_komponen_aset_nikop ON komponen_aset_desa (nomor_induk_koperasi);

-- ---------------------------------------------------------------------
-- Modul 5: basis_permohonan_bank (DPPL 4.2 butir 5). Turunan otomatis.
-- DPPL menulis porsi_kepemilikan DECIMAL(5,2) di tabel ini, sedangkan di tabel lain
-- DECIMAL(9,6). Purwarupa memakai (9,6) agar tidak kehilangan presisi.
-- nilai_reviu_bast_desa diambil dari komponen_aset_desa (Modul 4), tidak dihitung ulang.
-- ---------------------------------------------------------------------
CREATE TABLE basis_permohonan_bank (
    kode_desa_kelurahan  VARCHAR(10)   NOT NULL REFERENCES ref_kdkmp (kode_desa_kelurahan),
    uuid_reviu_bast      UUID          NOT NULL REFERENCES reviu_bast (uuid_reviu_bast),
    nama_desa_kelurahan  VARCHAR(255),             -- [DPPL-DUPLIKAT]
    kode_kecamatan       VARCHAR(10)   NOT NULL,
    nama_kecamatan       VARCHAR(100),
    kode_kabkota         VARCHAR(4)    NOT NULL,
    nama_kabkota         VARCHAR(150),
    kode_provinsi        VARCHAR(2)    NOT NULL,
    nama_provinsi        VARCHAR(100),
    nomor_induk_koperasi VARCHAR(30)   NOT NULL,
    nama_koperasi        VARCHAR(255),
    struktur_kepemilikan SMALLINT      NOT NULL CHECK (struktur_kepemilikan IN (1, 2)),
    porsi_kepemilikan    NUMERIC(9,6)  NOT NULL,
    jenis_koperasi       VARCHAR(4)    NOT NULL CHECK (jenis_koperasi IN ('KDMP', 'KKMP')),
    nomor_reviu_bast     VARCHAR(60)   NOT NULL,
    nilai_reviu_bast     NUMERIC(15,2) NOT NULL,
    jenis_reviu_bast     SMALLINT      NOT NULL REFERENCES ref_jenis_reviu_bast (kode_jenis),
    tanggal_reviu_bast   DATE          NOT NULL,
    nilai_reviu_bast_desa NUMERIC(15,2) NOT NULL,
    dibentuk_pada        TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (kode_desa_kelurahan, uuid_reviu_bast)
);
CREATE INDEX ix_basis_permohonan_nikop ON basis_permohonan_bank (nomor_induk_koperasi);
