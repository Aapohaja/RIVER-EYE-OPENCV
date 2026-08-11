# Solar Outdoor Box — Design Spec

**Date:** 2026-06-12  
**Project:** River Eye — outdoor power enclosure

## Summary

Waterproof outdoor box untuk ESP32 + 4×18650 battery holder (4 sel sejajar 1 baris), dengan lubang kabel solar panel di dinding kanan yang dilindungi canopy setengah lingkaran tertutup kanan-kiri.

## Box

| Parameter | Value |
|-----------|-------|
| Outer | 160 × 90 × 55 mm |
| Wall / floor thickness | 3 mm |
| Inner cavity | 154 × 84 × 49 mm |
| Top | Open (tutup terpisah) |

Internal content (no mounting posts):
- ESP32 ~58×33mm
- 4×18650 holder (4 in a row) ~76×24mm

## Lid

| Parameter | Value |
|-----------|-------|
| Outer footprint | 160 × 90 mm |
| Plate thickness | 5 mm |
| Lip depth | 8 mm (masuk ke dalam box) |
| Lip wall thickness | 3 mm |
| O-ring groove | 2.5 mm wide × 2 mm deep, semua 4 sisi lip |
| Attachment | Press-fit (tidak ada screw) |

O-ring spec: Ø2mm cord, ID ≈ 148mm.

## Cable Entry + Rain Canopy

**Lubang kabel (PG7):**
- Dinding: kanan (x = 160mm)
- Posisi Y: center (45mm dari depan)
- Posisi Z: mid-height (27.5mm dari lantai)
- Diameter: 12mm (PG7 cable gland)

**Rain canopy:**
- Profil: setengah lingkaran (180° arc)
- Radius luar: 22mm
- Radius dalam: 17mm (tebal shell 5mm)
- Orientasi: melekat di dinding kanan, melengkung ke luar, opening menghadap ke bawah
- Lebar (Y direction): 80mm (menonjol 5mm ke luar dari sisi kiri dan kanan box, centered on hole)
- Side walls: flat plate 3mm menutup kedua ujung Y canopy → hujan dari samping terblokir
- Kabel masuk dari bawah melalui gap antara canopy bottom dan dinding kanan

## Material

PETG atau ABS (untuk outdoor), atau resin.

## Non-goals

- Tidak ada screw post di dalam box
- Tidak ada mounting bracket
- Tidak ada ventilation hole
- Tidak ada sensor bracket
