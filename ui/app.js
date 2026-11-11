"use strict";
const API = "/api/v1";

/* ---------- Menu ---------- */
const MENU = [
  { label: "Dashboard Monitoring", rute: "#/" },
  { label: "Referensi", anak: [
      { label: "Referensi Wilayah", rute: "#/wilayah" },
      { label: "Referensi KDKMP", rute: "#/koperasi" },
      { label: "Data BAST", rute: "#/bast" } ] },
  { label: "Proses Internal", anak: [
      { label: "Komponen Aset Desa", rute: "#/komponen" } ] },
  { label: "Pemantauan", anak: [
      { label: "Riwayat Pengiriman", rute: "#/riwayat" } ] },
];

/* ---------- Fungsi bantu (dipakai semua halaman) ---------- */
function esc(teks) {      // cegah teks dari database ditafsirkan sebagai HTML
  return String(teks ?? "").replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function api(jalur, param = {}) {
  const url = new URL(API + jalur, location.origin);
  for (const [k, v] of Object.entries(param)) {
    if (v !== "" && v != null) url.searchParams.set(k, v);
  }
  let r;
  try { r = await fetch(url); }
  catch (e) { throw new Error("Tidak dapat menghubungi server. Pastikan aplikasi berjalan."); }
  if (!r.ok) {
    const e = new Error(r.status === 404 ? "Data tidak ditemukan." : "Server menjawab galat " + r.status + ".");
    e.status = r.status;
    throw e;
  }
  return r.json();
}

// Uang dari server berupa teks desimal ("1580000000.00"). Diformat dengan teks, tanpa float, agar tidak ada pembulatan.
function rupiah(teks) {
  if (teks == null || teks === "") return "-";
  const [bulat, desimal = "00"] = String(teks).split(".");
  const kelompok = bulat.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return "Rp " + kelompok + (/^0+$/.test(desimal) ? "" : "." + desimal);
}

function badge(teks, jenis = "biru") {
  return `<span class="badge badge-${jenis}">${esc(teks)}</span>`;
}

function kepala(judul, sub) {
  return `<div class="kepala"><div><h1>${esc(judul)}</h1><p>${esc(sub)}</p></div></div>`;
}

/* ---------- Router sederhana berbasis #hash ---------- */
const HALAMAN = {};                       // nama rute -> async fungsi(param) yang mengembalikan HTML
function daftar(nama, fungsi) { HALAMAN[nama] = fungsi; }

function gambarMenu(rute) {
  const aktif = (r) => (r === "#/" ? rute === "" : r === "#/" + rute);
  document.getElementById("menu").innerHTML = MENU.map(m => {
    if (!m.anak) {
      return `<div class="tab-item ${aktif(m.rute) ? "aktif" : ""}"><a class="tab-tombol" href="${m.rute}">${esc(m.label)}</a></div>`;
    }
    const anakAktif = m.anak.some(a => aktif(a.rute));
    const isi = m.anak.map(a => `<a href="${a.rute}" class="${aktif(a.rute) ? "aktif" : ""}">${esc(a.label)}</a>`).join("");
    return `<div class="tab-item ${anakAktif ? "aktif" : ""}"><button class="tab-tombol ada-menu" type="button">${esc(m.label)}</button>
            <div class="tab-anak">${isi}</div></div>`;
  }).join("");
}

async function tampil() {
  const bagian = location.hash.replace(/^#\/?/, "").split("/");
  const nama = bagian[0] || "";
  const param = decodeURIComponent(bagian.slice(1).join("/"));
  const wadah = document.getElementById("halaman");
  gambarMenu(nama);
  window.scrollTo(0, 0);
  const fungsi = HALAMAN[nama];
  if (!fungsi) { wadah.innerHTML = `<div class="galat">Halaman tidak dikenal.</div>`; return; }
  wadah.innerHTML = `<div class="memuat">Memuat…</div>`;
  try {
    const hasil = await fungsi(param);                // teks HTML, atau {html, pasang} untuk halaman interaktif
    if (typeof hasil === "string") { wadah.innerHTML = hasil; }
    else { wadah.innerHTML = hasil.html; await hasil.pasang(wadah); }
  } catch (e) { wadah.innerHTML = `<div class="galat">${esc(e.message)}</div>`; }
}
window.addEventListener("hashchange", tampil);

/* ---------- Halaman: Dashboard Monitoring ---------- */
daftar("", async () => {
  const sumber = [
    ["Referensi Wilayah (desa)", "/ref-wilayah", "#/wilayah"],
    ["Koperasi", "/koperasi", "#/koperasi"],
    ["Reviu BAST", "/reviu-bast", "#/bast"],
    ["Komponen Aset Desa", "/komponen-aset-desa", "#/komponen"],
    ["Pengiriman Data (batch)", "/batches", "#/riwayat"],
  ];
  const hasil = await Promise.all(sumber.map(s => api(s[1], { per_page: 1 })));
  const kartu = sumber.map((s, i) =>
    `<a class="angka" href="${s[2]}"><div class="angka-nilai">${hasil[i].total}</div><div class="angka-label">${esc(s[0])}</div></a>`).join("");
  return kepala("Dashboard Monitoring", "Ringkasan data yang tersimpan di purwarupa ICA Serasi") +
         `<div class="angka-baris">${kartu}</div>`;
});

/* ---------- Bantu untuk halaman daftar dan detail (C3) ---------- */
const STATE = {};    // filter dan nomor halaman tiap daftar; tetap ada setelah membuka detail lalu kembali

// kolom: [{judul, isi: (baris) => HTML, kelas}]. isi() mengembalikan HTML, jadi teks dari database wajib lewat esc().
function tabel(kolom, baris, kosong = "Tidak ada data.") {
  if (!baris.length) return `<div class="kosong">${esc(kosong)}</div>`;
  const kepalaTabel = kolom.map(k => `<th class="${k.kelas || ""}">${esc(k.judul)}</th>`).join("");
  const isi = baris.map(b => `<tr>${kolom.map(k => `<td class="${k.kelas || ""}">${k.isi(b)}</td>`).join("")}</tr>`).join("");
  return `<div class="tabel-bungkus"><table class="tabel"><thead><tr>${kepalaTabel}</tr></thead><tbody>${isi}</tbody></table></div>`;
}

function paginasi(total, page, perPage) {
  const jumlah = Math.max(1, Math.ceil(total / perPage));
  const dari = total ? (page - 1) * perPage + 1 : 0;
  const sampai = Math.min(total, page * perPage);
  return `<div class="paginasi"><span>Menampilkan ${dari}–${sampai} dari ${total}</span>
    <span><button class="tombol-kecil" type="button" data-hal="${page - 1}" ${page <= 1 ? "disabled" : ""}>Sebelumnya</button>
    <span class="hal-info">Halaman ${page} / ${jumlah}</span>
    <button class="tombol-kecil" type="button" data-hal="${page + 1}" ${page >= jumlah ? "disabled" : ""}>Berikutnya</button></span></div>`;
}

function pilihan(opsi, nilai, kosong) {   // opsi: [[nilai, label], ...]
  return `<option value="">${esc(kosong)}</option>` +
    opsi.map(([v, l]) => `<option value="${esc(v)}" ${v === nilai ? "selected" : ""}>${esc(l)}</option>`).join("");
}

function persen(teks) {                   // "25.000000" -> "25", "33.333334" tetap
  const t = String(teks ?? "");
  return t.includes(".") ? t.replace(/\.?0+$/, "") : t;
}

function profil(pasangan) {               // pasangan: [[label, HTML nilai], ...]
  return `<div class="profil">${pasangan.map(([l, v]) =>
    `<div><div class="profil-label">${esc(l)}</div><div class="profil-nilai">${v}</div></div>`).join("")}</div>`;
}

function kepalaDetail(judul, sub, kembali) {
  return `<div class="kepala"><a class="tombol-kembali" href="${kembali}">Kembali</a>
          <div><h1>${esc(judul)}</h1><p>${esc(sub)}</p></div></div>`;
}

function tombolDetail(rute) { return `<a class="tombol-detail" href="${rute}">Detail</a>`; }

/* Halaman daftar generik: kartu filter + tabel + penomoran halaman */
function halamanDaftar(cfg) {
  return async () => {
    const s = (STATE[cfg.kunci] ??= { provinsi: "", kabkota: "", tipe: "", dari: "", sampai: "", q: "", page: 1 });
    const provinsi = (await api("/opsi/provinsi")).items;
    const tipeHtml = cfg.tipe
      ? `<label>Tipe Koperasi<select id="f-tipe">${pilihan([["KDMP", "KDMP"], ["KKMP", "KKMP"]], s.tipe, "Semua")}</select></label>` : "";
    const tanggalHtml = cfg.tanggal
      ? `<label>Dari Tanggal<input type="date" id="f-dari" value="${esc(s.dari)}"></label>
         <label>Sampai Tanggal<input type="date" id="f-sampai" value="${esc(s.sampai)}"></label>` : "";
    const html = kepala(cfg.judul, cfg.sub) +
      `<div class="kartu filter">
         <label>Provinsi<select id="f-prov">${pilihan(provinsi.map(p => [p.kode_provinsi, p.nama_provinsi]), s.provinsi, "Semua")}</select></label>
         <label>Kabupaten/Kota<select id="f-kab" disabled></select></label>
         ${tipeHtml}
         ${tanggalHtml}
         <label class="lebar">${esc(cfg.labelCari)}<input id="f-q" type="search" placeholder="${esc(cfg.placeholder)}" value="${esc(s.q)}"></label>
         <button class="tombol" id="f-cari" type="button">Cari</button>
         ${cfg.csv ? `<button class="tombol tombol-sekunder" id="f-unduh" type="button">Unduh CSV</button>` : ""}
       </div>
       <div class="kartu tabel-kartu" id="hasil"><div class="memuat">Memuat…</div></div>`;
    return { html, pasang: (wadah) => pasangDaftar(cfg, s, wadah) };
  };
}

async function pasangDaftar(cfg, s, wadah) {
  const $ = (pilih) => wadah.querySelector(pilih);
  const selKab = $("#f-kab");
  async function isiKabkota() {
    if (!s.provinsi) { selKab.innerHTML = pilihan([], "", "Pilih provinsi dulu"); selKab.disabled = true; return; }
    const d = (await api("/opsi/kabkota", { kode_provinsi: s.provinsi })).items;
    selKab.innerHTML = pilihan(d.map(k => [k.kode_kabkota, k.nama_kabkota]), s.kabkota, "Semua");
    selKab.disabled = false;
  }
  const parameter = () => ({ q: s.q, kode_provinsi: s.provinsi, kode_kabkota: s.kabkota, jenis_koperasi: s.tipe,
                              dari_tanggal: s.dari, sampai_tanggal: s.sampai });
  async function muat() {
    const kotak = $("#hasil");
    try {
      const d = await api(cfg.jalur, { page: s.page, per_page: cfg.perPage || 15, ...parameter() });
      kotak.innerHTML = tabel(cfg.kolom, d.items, "Tidak ada data yang cocok dengan filter.") + paginasi(d.total, d.page, d.per_page);
      kotak.querySelectorAll("[data-hal]").forEach(t =>
        t.addEventListener("click", () => { s.page = Number(t.dataset.hal); muat(); }));
    } catch (e) { kotak.innerHTML = `<div class="galat">${esc(e.message)}</div>`; }
  }
  $("#f-prov").addEventListener("change", async (e) => { s.provinsi = e.target.value; s.kabkota = ""; s.page = 1; await isiKabkota(); muat(); });
  selKab.addEventListener("change", (e) => { s.kabkota = e.target.value; s.page = 1; muat(); });
  const selTipe = $("#f-tipe");
  if (selTipe) selTipe.addEventListener("change", (e) => { s.tipe = e.target.value; s.page = 1; muat(); });
  const selDari = $("#f-dari"), selSampai = $("#f-sampai");
  if (selDari) selDari.addEventListener("change", (e) => { s.dari = e.target.value; s.page = 1; muat(); });
  if (selSampai) selSampai.addEventListener("change", (e) => { s.sampai = e.target.value; s.page = 1; muat(); });
  const cari = () => { s.q = $("#f-q").value.trim(); s.page = 1; muat(); };
  $("#f-cari").addEventListener("click", cari);
  $("#f-q").addEventListener("keydown", (e) => { if (e.key === "Enter") cari(); });
  if (cfg.csv) pasangUnduh($("#f-unduh"), () => ambilSemua(cfg.jalur, parameter()), cfg.csv.berkas, kolomCsv(...cfg.csv.kolom));  
  await isiKabkota();
  await muat();
}

/* ---------- Halaman: Referensi Wilayah ---------- */
const daftarWilayah = halamanDaftar({
  kunci: "wilayah", judul: "Referensi Wilayah", sub: "Data referensi desa/kelurahan beserta kecamatan, kabupaten/kota, dan provinsi",
  jalur: "/ref-wilayah", tipe: false, csv: { berkas: "referensi_wilayah.csv", kolom: ["kode_desa_kelurahan", "nama_desa_kelurahan",
    "kode_kecamatan", "nama_kecamatan", "kode_kabkota", "nama_kabkota", "kode_provinsi", "nama_provinsi"] }, labelCari: "Cari Wilayah", placeholder: "Nama/kode desa atau kecamatan…",
  kolom: [
    { judul: "Kode Desa/Kelurahan", kelas: "kode", isi: b => esc(b.kode_desa_kelurahan) },
    { judul: "Nama Desa/Kelurahan", isi: b => `<b>${esc(b.nama_desa_kelurahan)}</b>` },
    { judul: "Kecamatan", isi: b => esc(b.nama_kecamatan) },
    { judul: "Kabupaten/Kota", isi: b => esc(b.nama_kabkota) },
    { judul: "Provinsi", isi: b => esc(b.nama_provinsi) },
    { judul: "Aksi", kelas: "kanan", isi: b => tombolDetail("#/wilayah/" + encodeURIComponent(b.kode_desa_kelurahan)) },
  ],
});

async function detailWilayah(kode) {
  const w = await api("/ref-wilayah/" + encodeURIComponent(kode));
  let kop = null;                          // satu desa paling banyak punya satu baris koperasi
  try { kop = await api("/ref-kdkmp/" + encodeURIComponent(kode)); }
  catch (e) { if (e.status !== 404) throw e; }
  const komponen = (await api("/komponen-aset-desa", { kode_desa_kelurahan: kode, per_page: 100 })).items;

  const kartuProfil = `<div class="kartu"><h2>Profil Wilayah</h2>${profil([
    ["Kode Desa/Kelurahan", `<span class="kode">${esc(w.kode_desa_kelurahan)}</span>`],
    ["Nama Desa/Kelurahan", `<b>${esc(w.nama_desa_kelurahan)}</b>`],
    ["Kecamatan", `${esc(w.nama_kecamatan)} (${esc(w.kode_kecamatan)})`],
    ["Kabupaten/Kota", `${esc(w.nama_kabkota)} (${esc(w.kode_kabkota)})`],
    ["Provinsi", `${esc(w.nama_provinsi)} (${esc(w.kode_provinsi)})`],
  ])}</div>`;
  const kartuKomponen = `<div class="kartu"><h2>Komponen Aset Desa</h2>` + tabel([
    { judul: "Koperasi", isi: b => esc(b.nama_koperasi) },
    { judul: "Sumber BAST", kelas: "kode", isi: b => esc(b.nomor_reviu_bast) },
    { judul: "Porsi", kelas: "kanan", isi: b => persen(b.porsi_kepemilikan) + "%" },
    { judul: "Bangunan", kelas: "kanan", isi: b => rupiah(b.nilai_bast_bangunan_desa) },
    { judul: "Sarpras", kelas: "kanan", isi: b => rupiah(b.nilai_bast_sarana_prasarana_desa) },
    { judul: "Kendaraan", kelas: "kanan", isi: b => rupiah(b.nilai_bast_kendaraan_desa) },
    { judul: "Total Desa", kelas: "kanan", isi: b => `<b>${rupiah(b.total_nilai_desa)}</b>` },
  ], komponen, "Tidak ada data komponen aset desa untuk wilayah ini.") + `</div>`;
  const kartuKoperasi = `<div class="kartu"><h2>Koperasi Terkait (KDKMP)</h2>` + (kop
    ? profil([
        ["Nama Koperasi", `<a href="#/koperasi/${encodeURIComponent(kop.nomor_induk_koperasi)}">${esc(kop.nama_koperasi)}</a>`],
        ["NIK", `<span class="kode">${esc(kop.nomor_induk_koperasi)}</span>`],
        ["Tipe", badge(kop.jenis_koperasi)],
        ["Porsi Kepemilikan", persen(kop.porsi_kepemilikan) + "%"],
      ])
    : `<div class="kosong">Tidak ada koperasi terkait di wilayah ini.</div>`) + `</div>`;
  const kartuTagihan = `<div class="kartu"><h2>Statistik Tagihan</h2>
    <div class="kosong">Di luar cakupan purwarupa (Modul 7).</div></div>`;
  return kepalaDetail("Detail Wilayah: " + w.nama_desa_kelurahan,
                      "Informasi profil referensi wilayah, relasi KDKMP, dan rincian komponen aset", "#/wilayah") +
    `<div class="dua-kolom"><div>${kartuProfil}${kartuKomponen}</div><div>${kartuKoperasi}${kartuTagihan}</div></div>`;
}
daftar("wilayah", (kode) => (kode ? detailWilayah(kode) : daftarWilayah()));

/* ---------- Halaman: Referensi KDKMP (satu baris per koperasi) ---------- */
const STRUKTUR = { 1: "Tunggal", 2: "Bersama" };
const labelStatus = (s) => (s === "AKTIF" ? badge("Aktif", "hijau") : badge(s, "abu"));

const daftarKoperasi = halamanDaftar({
  kunci: "koperasi", judul: "Referensi KDKMP", sub: "Data referensi KDMP dan KKMP aktif lintas wilayah",
  jalur: "/koperasi", tipe: true, csv: { berkas: "referensi_kdkmp.csv", kolom: ["nomor_induk_koperasi", "nama_koperasi",
    "jenis_koperasi", "struktur_kepemilikan", "status", "jumlah_desa", "total_porsi", "nama_kabkota", "nama_provinsi"] }, labelCari: "Cari Koperasi", placeholder: "Nama/NIK koperasi…",
  kolom: [
    { judul: "NIK", kelas: "kode", isi: b => esc(b.nomor_induk_koperasi) },
    { judul: "Nama Koperasi", isi: b => esc(b.nama_koperasi) },
    { judul: "Wilayah Pemilik", isi: b => b.jumlah_desa > 1
        ? `<span title="${esc(b.wilayah_pemilik)}">${b.jumlah_desa} desa</span>` : esc(b.wilayah_pemilik) },
    { judul: "Kab/Kota", isi: b => esc(b.nama_kabkota) },
    { judul: "Tipe", isi: b => badge(b.jenis_koperasi) },
    { judul: "Kepemilikan", isi: b => badge(STRUKTUR[b.struktur_kepemilikan] || "-", "abu") },
    { judul: "Status", isi: b => labelStatus(b.status) },
    { judul: "Aksi", kelas: "kanan", isi: b => tombolDetail("#/koperasi/" + encodeURIComponent(b.nomor_induk_koperasi)) },
  ],
});

async function detailKoperasi(nik) {
  const d = await api("/koperasi/" + encodeURIComponent(nik));
  const p = d.profil;
  const kartuProfil = `<div class="kartu"><h2>Profil KDKMP</h2>${profil([
    ["Nomor Induk Koperasi (NIK)", `<span class="kode">${esc(p.nomor_induk_koperasi)}</span>`],
    ["Nama Koperasi", `<b>${esc(p.nama_koperasi)}</b>`],
    ["Tipe Koperasi", badge(p.jenis_koperasi)],
    ["Status Koperasi", labelStatus(p.status)],
    ["Struktur Kepemilikan", esc(STRUKTUR[p.struktur_kepemilikan] || "-")],
    ["Kabupaten/Kota", esc(p.nama_kabkota)],
    ["Provinsi", esc(p.nama_provinsi)],
    ["Jumlah Desa Pemegang Porsi", String(p.jumlah_desa)],
  ])}</div>`;
  const utuh = persen(p.total_porsi) === "100";
  const kartuDesa = `<div class="kartu"><h2>Daftar Desa/Kelurahan Pemegang Porsi</h2>` + tabel([
    { judul: "Kode Desa", kelas: "kode", isi: b => esc(b.kode_desa_kelurahan) },
    { judul: "Nama Desa/Kelurahan", isi: b => `<b>${esc(b.nama_desa_kelurahan)}</b>` },
    { judul: "Kecamatan", isi: b => esc(b.nama_kecamatan) },
    { judul: "Kab/Kota", isi: b => esc(b.nama_kabkota) },
    { judul: "Provinsi", isi: b => esc(b.nama_provinsi) },
    { judul: "Porsi Kepemilikan", kelas: "kanan", isi: b => `${persen(b.porsi_kepemilikan)}%
        <span class="bar"><span style="width:${Math.min(100, Number(b.porsi_kepemilikan))}%"></span></span>` },
  ], d.desa) +
    `<div class="${utuh ? "cocok" : "galat"} total-porsi">Total porsi kepemilikan: ${esc(persen(p.total_porsi))}% ${utuh ? "Cocok" : "Tidak 100%"}</div></div>`;
  const reviu = d.riwayat_reviu.length
    ? d.riwayat_reviu.map(r => `<div class="reviu-item">
        <div class="baris-nilai"><a class="kode" href="#/bast/${encodeURIComponent(r.uuid_reviu_bast)}"><b>${esc(r.nomor_reviu_bast)}</b></a>
          <span>${esc(r.tanggal_reviu_bast)}</span></div>
        <div class="baris-nilai"><span>Bangunan:</span><span>${rupiah(r.nilai_bast_bangunan_kdkmp)}</span></div>
        <div class="baris-nilai"><span>Sarana &amp; Prasarana:</span><span>${rupiah(r.nilai_bast_sarana_prasarana_kdkmp)}</span></div>
        <div class="baris-nilai"><span>Kendaraan:</span><span>${rupiah(r.nilai_bast_kendaraan_kdkmp)}</span></div>
        <div class="baris-nilai total"><span>Total Nilai BAST (jenis ${esc(r.jenis_reviu_bast)}):</span><span>${rupiah(r.nilai_reviu_bast)}</span></div></div>`).join("")
    : `<div class="kosong">Belum ada reviu BAST.</div>`;
  const kartuReviu = `<div class="kartu"><h2>Riwayat Reviu BAST</h2>${reviu}</div>`;
  const kartuTagihan = `<div class="kartu"><h2>Summary Tagihan</h2>
    <div class="kosong">Di luar cakupan purwarupa (Modul 7).</div></div>`;
  return kepalaDetail("Detail Koperasi: " + p.nama_koperasi,
                      "Informasi profil referensi KDKMP, desa pemegang porsi, reviu BAST, dan ringkasan tagihan", "#/koperasi") +
    `<div class="dua-kolom"><div>${kartuProfil}${kartuDesa}</div><div>${kartuReviu}${kartuTagihan}</div></div>`;
}
daftar("koperasi", (nik) => (nik ? detailKoperasi(nik) : daftarKoperasi()));

/* ---------- Hitung uang tanpa float (C4) ---------- */
// Uang diubah ke bilangan bulat dalam sen (BigInt), dijumlahkan, lalu dikembalikan ke teks.
function keSen(teks) {                    // "1260000000.00" -> 126000000000n
  const [bulat, desimal = ""] = String(teks ?? "0").split(".");
  return BigInt(bulat + (desimal + "00").slice(0, 2));
}
function dariSen(sen) {                   // 126000000000n -> "1260000000.00"
  const s = (sen < 0n ? -sen : sen).toString().padStart(3, "0");
  return (sen < 0n ? "-" : "") + s.slice(0, -2) + "." + s.slice(-2);
}

/* ---------- Halaman: Data BAST ---------- */
const daftarBast = halamanDaftar({
  kunci: "bast", judul: "Data BAST", sub: "Reviu BAST yang diterima dari sistem sumber",
  jalur: "/reviu-bast", tipe: true, tanggal: true, csv: { berkas: "reviu_bast.csv", kolom: ["nomor_reviu_bast",
    "tanggal_reviu_bast", "nomor_induk_koperasi", "nama_koperasi", "jenis_koperasi", "nama_kabkota", "nama_provinsi",
    "jenis_reviu_bast", "nilai_reviu_bast", "nilai_bast_bangunan_kdkmp", "nilai_bast_sarana_prasarana_kdkmp",
    "nilai_bast_kendaraan_kdkmp"] }, labelCari: "Cari Reviu BAST", placeholder: "Nomor reviu, nama koperasi, atau NIK…",
  kolom: [
    { judul: "Nomor Reviu BAST", kelas: "kode", isi: b => esc(b.nomor_reviu_bast) },
    { judul: "Tanggal", isi: b => esc(b.tanggal_reviu_bast) },
    { judul: "Koperasi", isi: b => `${esc(b.nama_koperasi)}<div class="kode redup">${esc(b.nomor_induk_koperasi)}</div>` },
    { judul: "Kab/Kota", isi: b => esc(b.nama_kabkota) },
    { judul: "Tipe", isi: b => badge(b.jenis_koperasi) },
    { judul: "Jenis Reviu", isi: b => esc(b.jenis_reviu_bast) },
    { judul: "Nilai Reviu BAST", kelas: "kanan", isi: b => `<b>${rupiah(b.nilai_reviu_bast)}</b>` },
    { judul: "Aksi", kelas: "kanan", isi: b => tombolDetail("#/bast/" + encodeURIComponent(b.uuid_reviu_bast)) },
  ],
});

async function detailBast(uuid) {
  const r = await api("/reviu-bast/" + encodeURIComponent(uuid));
  // Alokasi per desa: API belum punya filter uuid, jadi ambil per koperasi lalu saring di sini.
  const alokasi = (await api("/komponen-aset-desa", { nomor_induk_koperasi: r.nomor_induk_koperasi, per_page: 100 }))
    .items.filter(k => k.uuid_reviu_bast === r.uuid_reviu_bast);

  const kartuProfil = `<div class="kartu"><h2>Profil Reviu BAST</h2>${profil([
    ["Nomor Reviu BAST", `<span class="kode">${esc(r.nomor_reviu_bast)}</span>`],
    ["Tanggal Reviu BAST", esc(r.tanggal_reviu_bast)],
    ["Koperasi", `<a href="#/koperasi/${encodeURIComponent(r.nomor_induk_koperasi)}">${esc(r.nama_koperasi)}</a>`],
    ["NIK", `<span class="kode">${esc(r.nomor_induk_koperasi)}</span>`],
    ["Tipe Koperasi", badge(r.jenis_koperasi)],
    ["Jenis Reviu BAST", esc(r.jenis_reviu_bast)],
    ["Kecamatan", esc(r.nama_kecamatan)],
    ["Kabupaten/Kota", esc(r.nama_kabkota)],
    ["Provinsi", esc(r.nama_provinsi)],
  ])}</div>`;

  // Verifikasi: jumlah tiga komponen harus sama dengan nilai reviu (aturan R3-06), dihitung dalam sen.
  const komponen = [["Bangunan", r.nilai_bast_bangunan_kdkmp],
                    ["Sarana dan Prasarana", r.nilai_bast_sarana_prasarana_kdkmp],
                    ["Kendaraan", r.nilai_bast_kendaraan_kdkmp]];
  const jumlah = komponen.reduce((a, [, v]) => a + keSen(v), 0n);
  const seimbang = jumlah === keSen(r.nilai_reviu_bast);
  const kartuVerifikasi = `<div class="kartu"><h2>Verifikasi Nilai Komponen</h2>` +
    komponen.map(([l, v]) => `<div class="baris-nilai"><span>${esc(l)}</span><span>${rupiah(v)}</span></div>`).join("") +
    `<div class="baris-nilai total"><span>Jumlah tiga komponen</span><span>${rupiah(dariSen(jumlah))}</span></div>
     <div class="baris-nilai total"><span>Nilai Reviu BAST</span><span>${rupiah(r.nilai_reviu_bast)}</span></div>
     <div class="${seimbang ? "cocok" : "galat"} total-porsi">${seimbang
        ? "Cocok dan seimbang"
        : "Tidak seimbang, selisih " + esc(rupiah(dariSen(keSen(r.nilai_reviu_bast) - jumlah)))}</div></div>`;

  // Alokasi per desa dan selisih pembulatan terhadap nilai reviu (aturan D5: ROUND 2 desimal per komponen per desa).
  let isiAlokasi;
  if (!alokasi.length) {
    isiAlokasi = `<div class="kosong">Belum ada alokasi komponen untuk reviu ini.</div>`;
  } else {
    const totalDesa = alokasi.reduce((a, k) => a + keSen(k.total_nilai_desa), 0n);
    const selisih = keSen(r.nilai_reviu_bast) - totalDesa;
    const mutlak = selisih < 0n ? -selisih : selisih;
    const wajar = mutlak <= BigInt(2 * alokasi.length);      // paling banyak 2 sen per desa akibat pembulatan
    const catatan = selisih === 0n
      ? `<div class="cocok total-porsi">Jumlah seluruh desa: ${rupiah(dariSen(totalDesa))}. Tidak ada selisih.</div>`
      : `<div class="${wajar ? "catatan" : "galat"} total-porsi">Jumlah seluruh desa: ${rupiah(dariSen(totalDesa))}.
           Selisih terhadap Nilai Reviu BAST: ${rupiah(dariSen(selisih))}
           ${wajar ? "(akibat pembulatan dua desimal per komponen per desa)" : "(melebihi batas pembulatan)"}</div>`;
    isiAlokasi = tabel([
      { judul: "Kode Desa", kelas: "kode", isi: k => esc(k.kode_desa_kelurahan) },
      { judul: "Nama Desa/Kelurahan", isi: k => `<b>${esc(k.nama_desa_kelurahan)}</b>` },
      { judul: "Porsi", kelas: "kanan", isi: k => persen(k.porsi_kepemilikan) + "%" },
      { judul: "Bangunan", kelas: "kanan", isi: k => rupiah(k.nilai_bast_bangunan_desa) },
      { judul: "Sarpras", kelas: "kanan", isi: k => rupiah(k.nilai_bast_sarana_prasarana_desa) },
      { judul: "Kendaraan", kelas: "kanan", isi: k => rupiah(k.nilai_bast_kendaraan_desa) },
      { judul: "Total Desa", kelas: "kanan", isi: k => `<b>${rupiah(k.total_nilai_desa)}</b>` },
    ], alokasi) + catatan;
  }
  const kartuAlokasi = `<div class="kartu"><h2>Alokasi Komponen ke Desa</h2>${isiAlokasi}</div>`;

  return kepalaDetail("Detail Reviu BAST: " + r.nomor_reviu_bast,
                      "Profil reviu, verifikasi nilai komponen, dan alokasi ke desa pemegang porsi", "#/bast") +
    `<div class="dua-kolom"><div>${kartuProfil}</div><div>${kartuVerifikasi}</div></div>${kartuAlokasi}`;
}
daftar("bast", (uuid) => (uuid ? detailBast(uuid) : daftarBast()));

/* ---------- Halaman: Komponen Aset KDKMP per Desa ---------- */
const daftarKomponen = halamanDaftar({
  kunci: "komponen", judul: "Komponen Aset KDKMP per Desa",
  sub: "Nilai komponen aset setiap desa pemegang porsi, dihitung otomatis dari reviu BAST",
  jalur: "/komponen-aset-desa", tipe: true, csv: { berkas: "komponen_aset_desa.csv", kolom: ["kode_desa_kelurahan",
    "nama_desa_kelurahan", "nama_koperasi", "nomor_reviu_bast", "porsi_kepemilikan", "nilai_bast_bangunan_desa",
    "nilai_bast_sarana_prasarana_desa", "nilai_bast_kendaraan_desa", "total_nilai_desa"] }, labelCari: "Cari Komponen", placeholder: "Nama desa, nama koperasi, atau nomor reviu…",
  kolom: [
    { judul: "Kode Desa", kelas: "kode", isi: k => esc(k.kode_desa_kelurahan) },
    { judul: "Nama Desa/Kelurahan", isi: k => `<b>${esc(k.nama_desa_kelurahan)}</b>` },
    { judul: "Koperasi", kelas: "nowrap", isi: k => esc(k.nama_koperasi) },
    { judul: "Sumber BAST", kelas: "kode", isi: k => `<a href="#/bast/${encodeURIComponent(k.uuid_reviu_bast)}">${esc(k.nomor_reviu_bast)}</a>` },
    { judul: "Porsi", kelas: "kanan", isi: k => persen(k.porsi_kepemilikan) + "%" },
    { judul: "Bangunan", kelas: "kanan", isi: k => rupiah(k.nilai_bast_bangunan_desa) },
    { judul: "Sarpras", kelas: "kanan", isi: k => rupiah(k.nilai_bast_sarana_prasarana_desa) },
    { judul: "Kendaraan", kelas: "kanan", isi: k => rupiah(k.nilai_bast_kendaraan_desa) },
    { judul: "Total Desa", kelas: "kanan", isi: k => `<b>${rupiah(k.total_nilai_desa)}</b>` },
  ],
});
daftar("komponen", () => daftarKomponen());

/* ---------- Unduh CSV (C5) ---------- */
const PEMISAH = ";";    // Excel berbahasa Indonesia memakai titik koma; ganti "," bila perlu

async function ambilSemua(jalur, param = {}) {      // gabungkan semua halaman (API membatasi 100 baris per permintaan)
  let semua = [], page = 1, ada = true;
  while (ada) {
    const d = await api(jalur, { ...param, page, per_page: 100 });
    semua = semua.concat(d.items);
    ada = d.items.length > 0 && semua.length < d.total;
    page++;
  }
  return semua;
}

function kolomCsv(...nama) { return nama.map(n => [n, b => b[n]]); }   // ["a","b"] -> [["a", b => b.a], ["b", b => b.b]]

function selCsv(nilai) {
  let t = nilai == null ? "" : (typeof nilai === "object" ? JSON.stringify(nilai) : String(nilai));
  if (/^[=+\-@\t\r]/.test(t)) t = "'" + t;          // cegah teks dibaca Excel sebagai rumus
  return /["\n\r;,]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
}

function unduhCsv(namaBerkas, kolom, baris) {       // kolom: [[judul, (b) => nilai], ...]
  const isi = [kolom.map(k => selCsv(k[0])).join(PEMISAH)]
    .concat(baris.map(b => kolom.map(k => selCsv(k[1](b))).join(PEMISAH))).join("\r\n");
  const blob = new Blob(["\uFEFF" + isi], { type: "text/csv;charset=utf-8" });   // \uFEFF: agar Excel membaca UTF-8
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = namaBerkas;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// Pasang tombol unduh: ambil semua data dulu, lalu buat berkas. Tombol dinonaktifkan selama proses.
function pasangUnduh(tombol, ambil, namaBerkas, kolom) {
  const teksAsal = tombol.textContent;
  tombol.addEventListener("click", async () => {
    tombol.disabled = true; tombol.textContent = "Menyiapkan...";
    try { unduhCsv(namaBerkas, kolom, await ambil()); }
    catch (e) { alert(e.message); }
    finally { tombol.disabled = false; tombol.textContent = teksAsal; }
  });
}

/* ---------- Halaman: Riwayat Pengiriman dan Error Log ---------- */
const DATASET = { ref_wilayah: "Referensi Wilayah", ref_kdkmp: "Referensi KDKMP", reviu_bast: "Reviu BAST" };
const KODE_ERROR = ["W1-01", "K2-01", "K2-02", "K2-03", "K2-04", "K2-05", "R3-01", "R3-02", "R3-03", "R3-04", "R3-05", "R3-06", "R3-07"];

function waktu(teks) {                    // "2026-11-11 02:57:23.9+00:00" -> "11 Nov 2026, 09.57.23 WIB"
  const t = String(teks ?? "");
  const m = t.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})(?:\.\d+)?(Z|[+-]\d{2}(?::?\d{2})?)?/);
  if (!m) return t;
  let zona = m[3] || "Z";
  if (/^[+-]\d{2}$/.test(zona)) zona += ":00";
  const d = new Date(`${m[1]}T${m[2]}${zona}`);
  if (isNaN(d)) return t;
  return d.toLocaleString("id-ID", { timeZone: "Asia/Jakarta", day: "2-digit", month: "short", year: "numeric",
                                     hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }) + " WIB";
}

function statusBatch(b) {
  if (b.baris_ditolak === 0) return badge("Diterima semua", "hijau");
  if (b.baris_diterima === 0) return badge("Ditolak semua", "merah");
  return badge("Sebagian ditolak", "kuning");
}

async function halamanRiwayat() {
  const s = (STATE.riwayat ??= { dataset: "", page: 1 });
  const html = kepala("Riwayat Pengiriman dan Error Log", "Catatan setiap kiriman data dari sistem sumber beserta baris yang ditolak") +
    `<div class="kartu filter">
       <label>Dataset<select id="f-dataset">${pilihan(Object.entries(DATASET), s.dataset, "Semua")}</select></label>
       <button class="tombol" id="f-unduh" type="button">Unduh CSV</button>
     </div>
     <div class="kartu tabel-kartu" id="hasil"><div class="memuat">Memuat…</div></div>`;
  return { html, pasang: (wadah) => pasangRiwayat(s, wadah) };
}

async function pasangRiwayat(s, wadah) {
  const kotak = wadah.querySelector("#hasil");
  const kolom = [
    { judul: "Waktu Diterima", isi: b => esc(waktu(b.diterima_pada)) },
    { judul: "ID Batch", kelas: "kode", isi: b => `<span title="${esc(b.batch_id)}">${esc(b.batch_id.slice(0, 8))}</span>` },
    { judul: "Dataset", isi: b => esc(DATASET[b.dataset] || b.dataset) },
    { judul: "Pengirim", isi: b => esc(b.pengirim) },
    { judul: "Total Baris", kelas: "kanan", isi: b => esc(b.total_baris) },
    { judul: "Diterima", kelas: "kanan", isi: b => esc(b.baris_diterima) },
    { judul: "Ditolak", kelas: "kanan", isi: b => esc(b.baris_ditolak) },
    { judul: "Status", isi: b => statusBatch(b) },
    { judul: "Aksi", kelas: "kanan", isi: b => b.baris_ditolak > 0
        ? `<a class="tombol-detail" href="#/riwayat/${encodeURIComponent(b.batch_id)}">Lihat Error</a>`
        : `<span class="redup">Tidak ada error</span>` },
  ];
  async function muat() {
    try {
      const d = await api("/batches", { page: s.page, per_page: 15, dataset: s.dataset });
      kotak.innerHTML = tabel(kolom, d.items, "Belum ada pengiriman.") + paginasi(d.total, d.page, d.per_page);
      kotak.querySelectorAll("[data-hal]").forEach(t =>
        t.addEventListener("click", () => { s.page = Number(t.dataset.hal); muat(); }));
    } catch (e) { kotak.innerHTML = `<div class="galat">${esc(e.message)}</div>`; }
  }
  wadah.querySelector("#f-dataset").addEventListener("change", (e) => { s.dataset = e.target.value; s.page = 1; muat(); });
  pasangUnduh(wadah.querySelector("#f-unduh"), () => ambilSemua("/batches", { dataset: s.dataset }), "riwayat_pengiriman.csv", [
    ["batch_id", b => b.batch_id], ["diterima_pada", b => b.diterima_pada], ["dataset", b => b.dataset],
    ["pengirim", b => b.pengirim], ["total_baris", b => b.total_baris], ["baris_diterima", b => b.baris_diterima],
    ["baris_ditolak", b => b.baris_ditolak],
  ]);
  await muat();
}

async function detailRiwayat(id) {
  await api("/batches/" + encodeURIComponent(id) + "/errors", { per_page: 1 });      // 404 bila batch tidak ada
  // API belum punya GET /batches/{id}, jadi ringkasan dicari dari daftar batch.
  const b = (await ambilSemua("/batches")).find(x => x.batch_id === id);
  const s = (STATE["err-" + id] ??= { kode: "", page: 1 });

  const ringkasan = b ? profil([
    ["ID Batch", `<span class="kode">${esc(b.batch_id)}</span>`],
    ["Dataset", esc(DATASET[b.dataset] || b.dataset)],
    ["Pengirim", esc(b.pengirim)],
    ["Waktu Diterima", esc(waktu(b.diterima_pada))],
    ["Total Baris", esc(b.total_baris)],
    ["Baris Diterima", esc(b.baris_diterima)],
    ["Baris Ditolak", esc(b.baris_ditolak)],
    ["Status", statusBatch(b)],
  ]) : profil([["ID Batch", `<span class="kode">${esc(id)}</span>`]]);
  const catatanWilayah = b && b.dataset === "ref_wilayah" && b.baris_ditolak > 0
    ? `<div class="catatan total-porsi">Pada Referensi Wilayah, satu baris cacat menolak seluruh batch (W1-01). Error log hanya mencatat baris yang cacat.</div>` : "";

  const html = kepalaDetail("Error Log Batch " + id.slice(0, 8), "Rincian baris yang ditolak pada pengiriman ini", "#/riwayat") +
    `<div class="kartu"><h2>Ringkasan Pengiriman</h2>${ringkasan}${catatanWilayah}</div>
     <div class="kartu filter">
       <label>Kode Error<select id="f-kode">${pilihan(KODE_ERROR.map(k => [k, k]), s.kode, "Semua")}</select></label>
       <button class="tombol" id="f-unduh" type="button">Unduh CSV</button>
     </div>
     <div class="kartu tabel-kartu" id="hasil"><div class="memuat">Memuat…</div></div>`;
  return { html, pasang: (wadah) => pasangDetailRiwayat(id, s, wadah) };
}

async function pasangDetailRiwayat(id, s, wadah) {
  const kotak = wadah.querySelector("#hasil");
  const jalur = "/batches/" + encodeURIComponent(id) + "/errors";
  const kolom = [
    { judul: "Baris Ke", kelas: "kanan", isi: e => esc(e.nomor_baris) },
    { judul: "Kode Error", isi: e => badge(e.kode_error, "merah") },
    { judul: "Field", kelas: "kode", isi: e => esc(e.field || "-") },
    { judul: "Pesan", isi: e => esc(e.pesan) },
    { judul: "Data Baris", isi: e => `<details class="data-baris"><summary>Lihat</summary><pre>${esc(JSON.stringify(e.data_baris, null, 2))}</pre></details>` },
  ];
  async function muat() {
    try {
      const d = await api(jalur, { page: s.page, per_page: 15, kode_error: s.kode });
      kotak.innerHTML = tabel(kolom, d.items, "Tidak ada error yang cocok dengan filter.") + paginasi(d.total, d.page, d.per_page);
      kotak.querySelectorAll("[data-hal]").forEach(t =>
        t.addEventListener("click", () => { s.page = Number(t.dataset.hal); muat(); }));
    } catch (e) { kotak.innerHTML = `<div class="galat">${esc(e.message)}</div>`; }
  }
  wadah.querySelector("#f-kode").addEventListener("change", (e) => { s.kode = e.target.value; s.page = 1; muat(); });
  pasangUnduh(wadah.querySelector("#f-unduh"), () => ambilSemua(jalur, { kode_error: s.kode }), "error_log_" + id.slice(0, 8) + ".csv", [
    ["nomor_baris", e => e.nomor_baris], ["kode_error", e => e.kode_error], ["field", e => e.field],
    ["pesan", e => e.pesan], ["data_baris", e => e.data_baris],
  ]);
  await muat();
}
daftar("riwayat", (id) => (id ? detailRiwayat(id) : halamanRiwayat()));

tampil();