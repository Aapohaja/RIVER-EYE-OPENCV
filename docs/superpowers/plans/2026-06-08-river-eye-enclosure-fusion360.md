# River Eye Enclosure — Fusion 360 Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Buat satu file Python script yang ketika dijalankan di Fusion 360 Script Editor, otomatis menghasilkan model 3D enclosure River Eye siap print/fabrikasi — tahan cuaca, bisa dipasang di median jalan.

**Architecture:** Satu file `river_eye_enclosure.py`. Script membangun 2 component: `RiverEye_Box` (badan bawah) dan `RiverEye_Lid` (tutup). Semua geometri dibangun via Fusion 360 Python API menggunakan construction plane offsets untuk reliabilitas. Parameter dideklarasikan di awal sebagai variabel untuk kemudahan modifikasi.

**Tech Stack:** Fusion 360 Python API (`adsk.core`, `adsk.fusion`), Python 3.x

---

## File Structure

| File | Deskripsi |
|------|-----------|
| `river_eye_enclosure.py` | Script utama — semua geometri box dan lid |

---

## Catatan Penting sebelum Mulai

- Buka Fusion 360 → buat design baru kosong sebelum run script
- Tools → Scripts and Add-Ins → My Scripts → klik "+" → arahkan ke folder script
- Semua ukuran di script dalam **cm** (unit internal Fusion 360 API), bukan mm
- Jika ada error, pesan akan muncul di dialog box Fusion 360

---

### Task 1: Boilerplate, Parameter, dan Helper Functions

**Files:**
- Create: `C:\Users\aaron\OneDrive\Desktop\PCV\protel\river_eye_enclosure.py`

- [ ] **Step 1: Buat file script dengan seluruh parameter dan helper functions**

```python
import adsk.core, adsk.fusion, adsk.cam, traceback

def run(context):
    ui = None
    try:
        app  = adsk.core.Application.get()
        ui   = app.userInterface
        des  = app.activeProduct
        root = des.rootComponent

        # ── ALIASES ──────────────────────────────────────────────────────
        VI  = adsk.core.ValueInput.createByReal
        Pt  = adsk.core.Point3D.create
        Obj = adsk.core.ObjectCollection.create
        FO  = adsk.fusion.FeatureOperations
        ED  = adsk.fusion.ExtentDirections
        DED = adsk.fusion.DistanceExtentDefinition

        # ── PARAMETERS (semua dalam cm) ───────────────────────────────────
        BL, BW, BH = 12.0, 9.0, 8.0    # box outer: 120 × 90 × 80 mm
        WT          = 0.3                # 3 mm wall thickness

        LID_PLATE   = 0.7                # 7 mm top plate
        LID_LIP     = 0.8                # 8 mm lip (masuk ke dalam box)

        LIP_L  = BL - 2*WT - 0.05       # 11.35 cm (gap 0.25 mm per sisi)
        LIP_W  = BW - 2*WT - 0.05       # 8.35 cm
        LIP_X0 = (BL - LIP_L) / 2       # 0.325 cm
        LIP_Y0 = (BW - LIP_W) / 2       # 0.325 cm

        O_W, O_D = 0.25, 0.2            # O-ring groove: 2.5 mm lebar, 2 mm dalam

        PRL, PRW, PRD = 11.2, 6.2, 0.3  # solar panel recess 112 × 62 × 3 mm
        SP_X0 = (BL - PRL) / 2          # 0.4 cm
        SP_Y0 = (BW - PRW) / 2          # 1.4 cm

        PG7_R = 0.6                      # 6 mm radius = Ø12 mm (PG7)
        PG9_R = 0.8                      # 8 mm radius = Ø16 mm (PG9)

        BKT_L  = 4.0                     # 40 mm bracket length
        BKT_H  = 1.5                     # 15 mm bracket height
        BKT_T  = 0.5                     # 5 mm bracket thickness
        BKT_HR = 0.25                    # 2.5 mm hole radius = Ø5 mm

        VENT_R = 0.4                     # 4 mm radius = Ø8 mm
        VENT_Z = 1.0                     # 10 mm dari lantai
        BFL_W  = 3.0                     # 30 mm baffle width
        BFL_H  = 1.5                     # 15 mm baffle height
        BFL_T  = 0.5                     # 5 mm baffle thickness

        POST_RO  = 0.35                  # 3.5 mm outer radius
        POST_RI  = 0.175                 # 1.75 mm inner radius (M3)
        POST_H   = 1.1                   # 11 mm total (8 mm visible di atas lantai)
        POST_OFF = WT + 0.5              # 8 mm dari pojok luar

        SCREW_R = 0.175                  # 1.75 mm = M3 clearance

        posts = [
            (POST_OFF,        POST_OFF),
            (BL - POST_OFF,   POST_OFF),
            (BL - POST_OFF,   BW - POST_OFF),
            (POST_OFF,        BW - POST_OFF),
        ]

        # ── HELPERS ───────────────────────────────────────────────────────
        def offset_plane(comp, base, dist):
            pi = comp.constructionPlanes.createInput()
            pi.setByOffset(base, VI(dist))
            return comp.constructionPlanes.add(pi)

        def extrude_pos(comp, prof, dist, op=FO.NewBodyFeatureOperation):
            """Extrude in positive normal direction."""
            ei = comp.features.extrudeFeatures.createInput(prof, op)
            ei.setDistanceExtent(False, VI(dist))
            return comp.features.extrudeFeatures.add(ei)

        def extrude_neg(comp, prof, dist, op=FO.CutFeatureOperation):
            """Extrude in negative normal direction."""
            ei = comp.features.extrudeFeatures.createInput(prof, op)
            ei.setOneSideExtent(
                DED.create(VI(dist)), ED.NegativeExtentDirection)
            return comp.features.extrudeFeatures.add(ei)

        def rect_prof(comp, plane, x0, y0, x1, y1):
            """Sketch rectangle, return first profile."""
            sk = comp.sketches.add(plane)
            sk.sketchCurves.sketchLines.addTwoPointRectangle(
                Pt(x0, y0, 0), Pt(x1, y1, 0))
            return sk.profiles.item(0)

        def circle_prof(comp, plane, cx, cy, r):
            """Sketch circle, return profile."""
            sk = comp.sketches.add(plane)
            sk.sketchCurves.sketchCircles.addByCenterRadius(Pt(cx, cy, 0), r)
            return sk.profiles.item(0)

        def find_top_face(body, z_val, tol=0.005):
            """Find horizontal face at z=z_val (top face of extruded box)."""
            for f in body.faces:
                bb = f.boundingBox
                if (abs(bb.minPoint.z - z_val) < tol and
                        abs(bb.maxPoint.z - z_val) < tol):
                    return f
            return None

        # placeholder — tasks below fill in the rest
        ui.messageBox('Boilerplate OK')

    except:
        if ui:
            ui.messageBox('Error:\n{}'.format(traceback.format_exc()))
```

- [ ] **Step 2: Validasi syntax Python**

```powershell
python -c "import ast; ast.parse(open('river_eye_enclosure.py').read()); print('Syntax OK')"
```
Expected: `Syntax OK`

- [ ] **Step 3: Run di Fusion 360 → verifikasi dialog "Boilerplate OK" muncul**

Fusion 360 → Tools → Scripts and Add-Ins → Scripts → [+] → pilih `river_eye_enclosure.py` → Run

- [ ] **Step 4: Commit**

```bash
git add river_eye_enclosure.py
git commit -m "feat: add Fusion 360 enclosure script skeleton and parameters"
```

---

### Task 2: Main Box — Solid + Shell

**Files:**
- Modify: `river_eye_enclosure.py` — ganti baris `# placeholder` dengan kode di bawah

- [ ] **Step 1: Ganti `# placeholder — tasks below fill in the rest` dengan kode box**

```python
        # ═══════════════════════════════════════════════════════════════
        # MAIN BOX COMPONENT
        # ═══════════════════════════════════════════════════════════════
        boxOcc  = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        bC      = boxOcc.component
        bC.name = 'RiverEye_Box'

        XY = bC.xYConstructionPlane   # z=0, normal = +Z
        XZ = bC.xZConstructionPlane   # y=0, normal = +Y
        YZ = bC.yZConstructionPlane   # x=0, normal = +X

        # Solid box 120×90×80 mm
        boxFeat = extrude_pos(bC, rect_prof(bC, XY, 0, 0, BL, BW), BH)
        boxBody = boxFeat.bodies.item(0)

        # Shell: hapus top face, dinding 3 mm
        topFace = find_top_face(boxBody, BH)
        fc = Obj(); fc.add(topFace)
        si = bC.features.shellFeatures.createInput(fc, False)
        si.insideThickness = VI(WT)
        bC.features.shellFeatures.add(si)

        # placeholder2
        ui.messageBox('Box body OK')
```

- [ ] **Step 2: Run di Fusion 360 → verifikasi**

Harus muncul box hollow 120×90×80 mm dengan top terbuka. Cek di viewport: dinding 3mm, tidak ada tutup atas.

- [ ] **Step 3: Commit**

```bash
git add river_eye_enclosure.py
git commit -m "feat: add hollow box body with shell feature"
```

---

### Task 3: Cable Gland Holes

**Files:**
- Modify: `river_eye_enclosure.py` — ganti `# placeholder2`

- [ ] **Step 1: Tambah lubang cable gland kiri (PG7) dan kanan (PG9)**

```python
        # ── CABLE GLAND HOLES ────────────────────────────────────────────
        # Sketch pada YZ plane: sketch-X = global-Y, sketch-Y = global-Z
        yz_right = offset_plane(bC, YZ, BL)   # x=BL (kanan)
        hole_z   = BH * 0.5                   # center of wall height

        # Kiri (x=0): PG7 Ø12mm untuk sensor
        extrude_pos(bC,
            circle_prof(bC, YZ, BW/2, hole_z, PG7_R),
            WT + 0.05, FO.CutFeatureOperation)

        # Kanan (x=BL): PG9 Ø16mm untuk USB-C
        extrude_neg(bC,
            circle_prof(bC, yz_right, BW/2, hole_z, PG9_R),
            WT + 0.05)

        # placeholder3
        ui.messageBox('Cable gland holes OK')
```

- [ ] **Step 2: Run di Fusion 360 → verifikasi**

Harus ada 2 lubang bulat: Ø12mm di sisi kiri, Ø16mm di sisi kanan, keduanya di tengah ketinggian dinding (z=40mm).

- [ ] **Step 3: Commit**

```bash
git add river_eye_enclosure.py
git commit -m "feat: add PG7 and PG9 cable gland holes to box"
```

---

### Task 4: Mounting Brackets

**Files:**
- Modify: `river_eye_enclosure.py` — ganti `# placeholder3`

- [ ] **Step 1: Tambah 2 mounting bracket + lubang baut**

```python
        # ── MOUNTING BRACKETS (kiri dan kanan) ───────────────────────────
        bkt_y0 = (BW - BKT_L) / 2
        bkt_y1 = bkt_y0 + BKT_L
        bkt_z0 = BH/2 - BKT_H/2
        bkt_z1 = bkt_z0 + BKT_H

        # Kiri: bracket menonjol ke -X dari x=0
        extrude_neg(bC,
            rect_prof(bC, YZ, bkt_y0, bkt_z0, bkt_y1, bkt_z1),
            BKT_T, FO.JoinFeatureOperation)
        # Lubang baut Ø5mm di bracket kiri
        extrude_pos(bC,
            circle_prof(bC, offset_plane(bC, YZ, -BKT_T), BW/2, BH/2, BKT_HR),
            BKT_T + 0.05, FO.CutFeatureOperation)

        # Kanan: bracket menonjol ke +X dari x=BL
        extrude_pos(bC,
            rect_prof(bC, yz_right, bkt_y0, bkt_z0, bkt_y1, bkt_z1),
            BKT_T, FO.JoinFeatureOperation)
        # Lubang baut Ø5mm di bracket kanan
        extrude_neg(bC,
            circle_prof(bC, offset_plane(bC, YZ, BL + BKT_T), BW/2, BH/2, BKT_HR),
            BKT_T + 0.05)

        # placeholder4
        ui.messageBox('Mounting brackets OK')
```

- [ ] **Step 2: Run di Fusion 360 → verifikasi**

Harus ada 2 bracket 40×15mm menonjol di sisi kiri dan kanan, masing-masing dengan lubang Ø5mm di tengah untuk baut M5.

- [ ] **Step 3: Commit**

```bash
git add river_eye_enclosure.py
git commit -m "feat: add mounting brackets with M5 bolt holes"
```

---

### Task 5: Ventilation Hole + Baffle

**Files:**
- Modify: `river_eye_enclosure.py` — ganti `# placeholder4`

- [ ] **Step 1: Tambah lubang ventilasi dan baffle**

```python
        # ── VENTILATION HOLE + BAFFLE (dinding belakang y=BW) ────────────
        # XZ plane sketch: sketch-X = global-X, sketch-Y = global-Z
        back_plane = offset_plane(bC, XZ, BW)   # y=BW, normal = +Y

        # Lubang Ø8mm di tengah-X, 10mm dari lantai
        extrude_neg(bC,
            circle_prof(bC, back_plane, BL/2, VENT_Z, VENT_R),
            WT + 0.05)

        # Baffle: tudung 30mm lebar di atas lubang, menonjol +Y ke luar
        bfl_x0 = BL/2 - BFL_W/2
        bfl_x1 = BL/2 + BFL_W/2
        bfl_z0 = VENT_Z + VENT_R + 0.2   # 2mm di atas tepi atas lubang
        bfl_z1 = bfl_z0 + BFL_H
        extrude_pos(bC,
            rect_prof(bC, back_plane, bfl_x0, bfl_z0, bfl_x1, bfl_z1),
            BFL_T, FO.JoinFeatureOperation)

        # placeholder5
        ui.messageBox('Ventilation + baffle OK')
```

- [ ] **Step 2: Run di Fusion 360 → verifikasi**

Harus ada: lubang Ø8mm di dinding belakang (10mm dari lantai, tengah lebar box), dan tab/tudung 30×15mm di atasnya yang menonjol 5mm ke luar.

- [ ] **Step 3: Commit**

```bash
git add river_eye_enclosure.py
git commit -m "feat: add ventilation hole with rain baffle on back wall"
```

---

### Task 6: Internal Screw Posts

**Files:**
- Modify: `river_eye_enclosure.py` — ganti `# placeholder5`

- [ ] **Step 1: Tambah 4 screw post di pojok internal**

```python
        # ── INTERNAL SCREW POSTS (4 pojok) ───────────────────────────────
        for cx, cy in posts:
            # Silinder solid dari lantai, tinggi 11mm
            extrude_pos(bC,
                circle_prof(bC, XY, cx, cy, POST_RO),
                POST_H, FO.JoinFeatureOperation)
            # Lubang M3 (Ø3.5mm) menembus post
            extrude_pos(bC,
                circle_prof(bC, XY, cx, cy, POST_RI),
                POST_H + 0.05, FO.CutFeatureOperation)

        # placeholder6
        ui.messageBox('Box complete! Screw posts OK')
```

- [ ] **Step 2: Run di Fusion 360 → verifikasi**

Harus ada 4 silinder Ø7mm dengan lubang Ø3.5mm di tengahnya, di 4 pojok internal box (8mm dari masing-masing pojok luar).

- [ ] **Step 3: Commit**

```bash
git add river_eye_enclosure.py
git commit -m "feat: add 4 internal M3 screw posts at box corners"
```

---

### Task 7: Lid — Top Plate + Lip

**Files:**
- Modify: `river_eye_enclosure.py` — ganti `# placeholder6`

- [ ] **Step 1: Buat komponen lid dengan top plate dan lip**

```python
        # ═══════════════════════════════════════════════════════════════
        # LID COMPONENT
        # ═══════════════════════════════════════════════════════════════
        lidOcc  = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        lC      = lidOcc.component
        lC.name = 'RiverEye_Lid'

        LXY = lC.xYConstructionPlane   # z=0, normal = +Z
        LXZ = lC.xZConstructionPlane   # y=0, normal = +Y
        LYZ = lC.yZConstructionPlane   # x=0, normal = +X

        # Top plate: 120×90 × 7mm ke atas (z=0 → z=LID_PLATE)
        extrude_pos(lC,
            rect_prof(lC, LXY, 0, 0, BL, BW),
            LID_PLATE)

        # Lip: 113.5×83.5 × 8mm ke bawah (z=0 → z=-LID_LIP)
        extrude_neg(lC,
            rect_prof(lC, LXY, LIP_X0, LIP_Y0,
                      LIP_X0+LIP_L, LIP_Y0+LIP_W),
            LID_LIP, FO.JoinFeatureOperation)

        # placeholder7
        ui.messageBox('Lid body OK')
```

- [ ] **Step 2: Run di Fusion 360 → verifikasi**

Harus ada lid dengan top plate 120×90×7mm dan lip 113.5×83.5×8mm menggantung ke bawah dari tengah. Total tinggi = 15mm.

- [ ] **Step 3: Commit**

```bash
git add river_eye_enclosure.py
git commit -m "feat: add lid component with top plate and sealing lip"
```

---

### Task 8: O-Ring Groove

**Files:**
- Modify: `river_eye_enclosure.py` — ganti `# placeholder7`

- [ ] **Step 1: Potong alur O-ring di 4 sisi lip**

```python
        # ── O-RING GROOVE (4 sisi luar lip) ──────────────────────────────
        # Posisi vertikal: tengah lip = z = -(LID_LIP/2)
        oz0 = -(LID_LIP/2) - O_W/2    # batas bawah groove
        oz1 = -(LID_LIP/2) + O_W/2    # batas atas groove

        # Kiri (x=LIP_X0): potong ke dalam +X
        extrude_pos(lC,
            rect_prof(lC, offset_plane(lC, LYZ, LIP_X0),
                      LIP_Y0, oz0, LIP_Y0+LIP_W, oz1),
            O_D, FO.CutFeatureOperation)

        # Kanan (x=LIP_X0+LIP_L): potong ke dalam -X
        extrude_neg(lC,
            rect_prof(lC, offset_plane(lC, LYZ, LIP_X0+LIP_L),
                      LIP_Y0, oz0, LIP_Y0+LIP_W, oz1),
            O_D)

        # Depan (y=LIP_Y0): potong ke dalam +Y
        extrude_pos(lC,
            rect_prof(lC, offset_plane(lC, LXZ, LIP_Y0),
                      LIP_X0, oz0, LIP_X0+LIP_L, oz1),
            O_D, FO.CutFeatureOperation)

        # Belakang (y=LIP_Y0+LIP_W): potong ke dalam -Y
        extrude_neg(lC,
            rect_prof(lC, offset_plane(lC, LXZ, LIP_Y0+LIP_W),
                      LIP_X0, oz0, LIP_X0+LIP_L, oz1),
            O_D)

        # placeholder8
        ui.messageBox('O-ring groove OK')
```

- [ ] **Step 2: Run di Fusion 360 → verifikasi**

Harus ada alur 2.5mm × 2mm yang mengelilingi 4 sisi lip, di posisi tengah ketinggian lip. Alur ini tempat O-ring Ø2mm dipasang.

- [ ] **Step 3: Commit**

```bash
git add river_eye_enclosure.py
git commit -m "feat: add O-ring sealing groove to lid lip"
```

---

### Task 9: Solar Panel Recess + Cable Gland

**Files:**
- Modify: `river_eye_enclosure.py` — ganti `# placeholder8`

- [ ] **Step 1: Tambah recess solar panel dan lubang kabel**

```python
        # ── SOLAR PANEL RECESS + CABLE GLAND ─────────────────────────────
        top_plane = offset_plane(lC, LXY, LID_PLATE)   # permukaan atas lid

        # Recess solar panel 112×62×3mm, centered
        extrude_neg(lC,
            rect_prof(lC, top_plane, SP_X0, SP_Y0,
                      SP_X0+PRL, SP_Y0+PRW),
            PRD)

        # Lubang kabel solar panel PG7 (Ø12mm), menembus seluruh lid
        # Posisi: x=1.0cm, y=0.8cm (di depan recess, clear dari panel)
        extrude_neg(lC,
            circle_prof(lC, top_plane, 1.0, 0.8, PG7_R),
            LID_PLATE + LID_LIP + 0.05)

        # placeholder9
        ui.messageBox('Solar panel recess + gland OK')
```

- [ ] **Step 2: Run di Fusion 360 → verifikasi**

Harus ada:
- Cekungan 112×62×3mm di permukaan atas lid untuk solar panel
- Lubang Ø12mm (PG7) menembus seluruh ketebalan lid (15mm), di pojok depan-kiri lid, di luar area cekungan

- [ ] **Step 3: Commit**

```bash
git add river_eye_enclosure.py
git commit -m "feat: add solar panel recess and PG7 cable gland to lid"
```

---

### Task 10: Lid Screw Holes + Finalize

**Files:**
- Modify: `river_eye_enclosure.py` — ganti `# placeholder9` dan `ui.messageBox('Boilerplate OK')`

- [ ] **Step 1: Tambah 4 lubang sekrup lid dan pesan sukses**

Ganti `# placeholder9` dengan:

```python
        # ── LID SCREW HOLES (4 pojok, sejajar dengan screw posts di box) ─
        for cx, cy in posts:
            extrude_neg(lC,
                circle_prof(lC, top_plane, cx, cy, SCREW_R),
                LID_PLATE + LID_LIP + 0.05)

        # SELESAI
        ui.messageBox(
            'River Eye Enclosure berhasil dibuat!\n\n'
            'Components:\n'
            '  - RiverEye_Box  (120×90×80 mm)\n'
            '  - RiverEye_Lid  (120×90×15 mm)\n\n'
            'Catatan:\n'
            '  - Beli O-ring Ø2mm sesuai keliling lip\n'
            '  - Cable gland: PG7 (sensor + solar), PG9 (USB-C)\n'
            '  - Baut lid: M3 stainless\n'
            '  - Baut bracket: M5'
        )
```

- [ ] **Step 2: Hapus baris `ui.messageBox('Boilerplate OK')` yang sudah tidak dipakai**

- [ ] **Step 3: Validasi syntax final**

```powershell
python -c "import ast; ast.parse(open('river_eye_enclosure.py').read()); print('Syntax OK')"
```
Expected: `Syntax OK`

- [ ] **Step 4: Run full script di Fusion 360 → verifikasi semua fitur**

Checklist visual di Fusion 360:
- [ ] Box 120×90×80mm, dinding 3mm, top terbuka
- [ ] Lubang PG7 (Ø12mm) di sisi kiri, PG9 (Ø16mm) di sisi kanan
- [ ] 2 mounting bracket 40×15mm dengan lubang Ø5mm di sisi kiri-kanan
- [ ] Lubang ventilasi Ø8mm + baffle 30×15mm di dinding belakang
- [ ] 4 screw post Ø7mm (lubang Ø3.5mm) di pojok internal
- [ ] Lid dengan top plate 7mm + lip 8mm
- [ ] Alur O-ring 2.5×2mm mengelilingi lip
- [ ] Recess solar panel 112×62×3mm di permukaan atas lid
- [ ] Lubang PG7 (Ø12mm) di pojok lid untuk kabel solar
- [ ] 4 lubang M3 di pojok lid sejajar dengan screw posts

- [ ] **Step 5: Commit final**

```bash
git add river_eye_enclosure.py
git commit -m "feat: complete River Eye Fusion 360 enclosure script with all outdoor features"
```

---

---

## Opsional: Kemiringan 3° pada Lid (anti-genangan air)

Spec menyebut lid miring 3° agar air tidak menggenang di atas solar panel. Cara termudah di Fusion 360 setelah script selesai:

1. Buka komponen `RiverEye_Lid` di browser
2. Pilih top face lid (permukaan atas, termasuk solar panel recess)
3. **Modify → Draft** → pilih face sebagai "Pull Direction", atur angle = 3° ke arah depan (Y axis)
4. Ini tidak perlu dimasukkan ke script karena mudah dilakukan manual dan risiko salah arah jika diprogramkan.

---

## Bill of Materials (untuk fabrikasi)

| Item | Spec | Qty |
|------|------|-----|
| O-ring | Ø2mm, panjang sesuai keliling lip | 1 |
| Cable gland | PG7 (Ø12mm hole) | 2 |
| Cable gland | PG9 (Ø16mm hole) | 1 |
| Baut + mur | M3 × 12mm stainless | 4 |
| Baut + mur | M5 × 20mm stainless | 4 |
| Standoff | M3 × 15mm (brass/nylon) | 4 |
