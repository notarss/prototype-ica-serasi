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

function kepala(ikon, judul, sub) {
  return `<div class="kepala"><div class="kepala-ikon">${ikon}</div>
          <div><h1>${esc(judul)}</h1><p>${esc(sub)}</p></div></div>`;
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
    return `<div class="tab-item ${anakAktif ? "aktif" : ""}"><button class="tab-tombol" type="button">${esc(m.label)} ▾</button>
            <div class="tab-anak">${isi}</div></div>`;
  }).join("");
}

async function tampil() {
  const bagian = location.hash.replace(/^#\/?/, "").split("/");
  const nama = bagian[0] || "";
  const param = decodeURIComponent(bagian.slice(1).join("/"));
  const wadah = document.getElementById("halaman");
  gambarMenu(nama);
  const fungsi = HALAMAN[nama];
  if (!fungsi) { wadah.innerHTML = `<div class="galat">Halaman tidak dikenal.</div>`; return; }
  wadah.innerHTML = `<div class="memuat">Memuat…</div>`;
  try { wadah.innerHTML = await fungsi(param); }
  catch (e) { wadah.innerHTML = `<div class="galat">${esc(e.message)}</div>`; }
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
  return kepala("▦", "Dashboard Monitoring", "Ringkasan data yang tersimpan di purwarupa ICA Serasi") +
         `<div class="angka-baris">${kartu}</div>`;
});

/* ---------- Halaman lain: diisi pada tahap berikutnya ---------- */
const BELUM = {
  wilayah:   ["⌖", "Referensi Wilayah", "Tahap C3"],
  koperasi:  ["▣", "Referensi KDKMP", "Tahap C3"],
  bast:      ["▤", "Data BAST", "Tahap C4"],
  komponen:  ["▥", "Komponen Aset KDKMP per Desa", "Tahap C4"],
  riwayat:   ["≣", "Riwayat Pengiriman dan Error Log", "Tahap C5"],
};
for (const [nama, [ikon, judul, tahap]] of Object.entries(BELUM)) {
  daftar(nama, async () => kepala(ikon, judul, "Halaman ini dibuat pada " + tahap) +
                           `<div class="kartu"><div class="kosong">Belum dibuat.</div></div>`);
}

tampil();