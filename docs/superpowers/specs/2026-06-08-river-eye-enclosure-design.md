# River Eye Enclosure — Design Spec
**Date:** 2026-06-08  
**Project:** River Eye (PROTEL flood monitoring)  
**Goal:** Fusion 360 Python API script yang auto-generate model 3D enclosure untuk node monitoring ketinggian air — siap deployment outdoor di tepi jalan (iklim tropis Indonesia).

---

## Komponen yang Harus Masuk

| Komponen | Dimensi | Posisi |
|---|---|---|
| 4×18650 Battery Holder | 90 × 70 × 22 mm | Tengah lantai box |
| ESP32 DevKit USB-C | 54 × 28 × 10 mm | Di atas battery holder (standoff 15mm) |
| Water Level Sensor PCB | ~30 × 60 × 2 mm | Menembus sisi kiri via cable gland slot |
| Solar Panel | 110 × 60 mm | Recess di atas lid |

---

## Dimensi

### Main Box (badan bawah)
- **Outer:** 120 × 90 × 80 mm
- **Wall thickness:** 3 mm
- **Internal:** 114 × 84 × 77 mm
- **Top:** terbuka (dipasang lid)
- **Mounting brackets:** 2 bracket di sisi panjang, masing-masing 40×10×5mm dengan lubang baut Ø5mm

### Lid (tutup atas)
- **Outer:** 120 × 90 × 15 mm
- **Lip:** masuk 8mm ke dalam box (diperdalam dari 5mm untuk O-ring)
- **O-ring groove:** alur 2.5mm × 2mm di keliling lip (untuk O-ring Ø2mm, IP54 minimum)
- **Solar panel recess:** 112 × 62 × 3 mm di permukaan atas lid, centered
- **Kemiringan:** permukaan lid miring 3° ke salah satu sisi agar air tidak menggenang di atas solar panel

---

## Opening / Penetrasi (semua via cable gland)

| Lubang | Ukuran Hole | Posisi | Fungsi |
|---|---|---|---|
| Sensor cable gland | Ø 12 mm (PG7) | Sisi kiri, H=40mm dari lantai, centered | Masukkan kabel sensor (bukan PCB langsung) |
| USB-C access gland | Ø 16 mm (PG9) | Sisi kanan, H=40mm dari lantai | Akses USB-C via kabel ekstensi / gland |
| Solar cable gland | Ø 12 mm (PG7) | Sisi depan lid | Kabel dari solar panel ke dalam box |
| Screw holes lid | Ø 3.5 mm | 4 pojok lid | Kunci lid dengan baut M3 stainless |
| Screw posts box | Ø 3.5 mm, tinggi 8mm | 4 pojok internal box | Pasangan screw hole lid |

> **Catatan perubahan dari desain sebelumnya:** Sensor PCB tidak lagi menembus langsung lewat slot. Sebagai gantinya, kabel sensor keluar via PG7 cable gland — lebih waterproof dan mudah diganti.

---

## Ventilasi (anti-panas)

- **1 lubang ventilasi** di sisi belakang box bawah, Ø 8mm
- **Baffle / overhang** di luar lubang ventilasi: tonjolan 10mm ke atas dari dinding (seperti tudung) agar udara bisa masuk tapi air tidak
- Posisi: H=10mm dari lantai (sirkulasi konveksi — udara dingin masuk bawah, panas keluar via celah lid)

---

## Mounting Bracket

- 2 bracket menyatu dengan dinding samping box (left & right)
- Dimensi tiap bracket: 40 × 15 mm, tebal 5mm
- Lubang: Ø 5mm, untuk baut M5 ke struktur median jalan
- Posisi: H=40mm dari lantai (tengah-tengah dinding)

---

## Internal Layout

```
Top view (internal 114 × 84 mm):
┌──────────────────────────────────────┐
│         margin ~12mm tiap sisi       │
│  ┌────────────────────────────────┐  │
│  │     4×18650 Battery Holder     │  │  ← centered
│  │         90 × 70 mm             │  │
│  │   [ESP32 di atas, standoff]    │  │
│  └────────────────────────────────┘  │
│PG7←                           →vent  │
└──────────────────────────────────────┘

Side view:
┌──────────────────────┐  ← lid (15mm) + O-ring groove
│  [solar panel recess]│
├══════════════════════╡  ← lid lip 8mm ke dalam box
│  ESP32 (standoff)    │
│  ─────────────────── │
│  4×18650 holder      │
│                      │
└──────────────────────┘
│      bracket →  ●    │  ← mounting bracket Ø5mm
```

---

## Output Script

- **Format:** Fusion 360 Python API script (`.py`)
- **Cara pakai:** Fusion 360 → Tools → Scripts and Add-ins → Run Script
- **Output:** 2 component (Main Box + Lid) di active design
- **Unit:** mm
- **Parametrik:** Dimensi utama sebagai variabel di awal script

---

## Tidak Termasuk (Out of Scope)

- O-ring fisik (beli terpisah, O-ring Ø2mm sesuai keliling lip)
- Cable gland fisik PG7/PG9 (beli terpisah, standard metric)
- Conformal coating untuk PCB
- Cat / surface finish
- Internal PCB standoff untuk ESP32 (pakai standoff M3 off-the-shelf)
