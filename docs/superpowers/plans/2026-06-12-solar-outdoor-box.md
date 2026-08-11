# Solar Outdoor Box — Fusion 360 Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `solar_box.py` — a single Fusion 360 Python script that generates a waterproof outdoor enclosure (box + press-fit lid + semicircular rain canopy) for an ESP32 + 4×18650 battery holder.

**Architecture:** One `run(context)` function. Geometry built sequentially: box shell → lid plate → lid lip → O-ring groove × 4 faces → PG7 hole → canopy crescent profile → canopy extrusion. Follows patterns from `river_eye_enclosure.py` (same helper functions). No internal screw posts. No sensor bracket. No ventilation.

**Tech Stack:** Fusion 360 Python API (`adsk.core`, `adsk.fusion`), `math` (for `math.pi`)

**Reference file:** `C:\Users\aaron\OneDrive\Desktop\PCV\protel\river_eye_enclosure\river_eye_enclosure.py`

---

### Task 1: Scaffold — imports, parameters, and helpers

**Files:**
- Create: `C:\Users\aaron\OneDrive\Desktop\PCV\protel\solar_box.py`

- [ ] **Step 1: Create the file with scaffold**

```python
import adsk.core, adsk.fusion, adsk.cam, traceback, math

def run(context):
    ui = None
    try:
        app  = adsk.core.Application.get()
        ui   = app.userInterface
        des  = app.activeProduct
        root = des.rootComponent

        VI  = adsk.core.ValueInput.createByReal
        Pt  = adsk.core.Point3D.create
        FO  = adsk.fusion.FeatureOperations
        ED  = adsk.fusion.ExtentDirections
        DED = adsk.fusion.DistanceExtentDefinition

        # ── PARAMETERS (all in cm) ────────────────────────────────
        BL, BW, BH = 16.0, 9.0, 5.5      # Box outer: 160×90×55mm
        WT         = 0.3                   # Wall + floor thickness: 3mm

        LID_PLATE  = 0.5                   # Lid plate: 5mm
        LID_LIP    = 0.8                   # Lid lip depth: 8mm
        LIP_CLR    = 0.05                  # 0.5mm fit clearance
        LIP_L      = BL - 2*WT - LIP_CLR
        LIP_W      = BW - 2*WT - LIP_CLR
        LIP_X0     = (BL - LIP_L) / 2
        LIP_Y0     = (BW - LIP_W) / 2
        O_W, O_D   = 0.25, 0.2            # O-ring groove: 2.5mm wide, 2mm deep

        PG7_R      = 0.6                   # PG7 hole radius: 6mm (Ø12mm)
        PG7_Y      = BW / 2               # centered in Y
        PG7_Z      = BH / 2               # mid-height

        CANO_RO    = 2.2                   # Canopy outer radius: 22mm
        CANO_RI    = 1.7                   # Canopy inner radius: 17mm (5mm thick)
        CANO_HW    = 4.0                   # Canopy half-width: 40mm (total 80mm in Y)

        LX = BL + 3.0                      # Lid X offset (placed right of box)

        # ── PLANE HELPERS ────────────────────────────────────────
        def yp(comp, x):
            """YZ-type plane at global X=x. sketch_x→Y, sketch_y→-Z"""
            if abs(x) < 1e-5:
                return comp.yZConstructionPlane
            pi = comp.constructionPlanes.createInput()
            pi.setByOffset(comp.yZConstructionPlane, VI(x))
            return comp.constructionPlanes.add(pi)

        def xp(comp, y):
            """XZ-type plane at global Y=y. sketch_x→X, sketch_y→Z"""
            if abs(y) < 1e-5:
                return comp.xZConstructionPlane
            pi = comp.constructionPlanes.createInput()
            pi.setByOffset(comp.xZConstructionPlane, VI(y))
            return comp.constructionPlanes.add(pi)

        def zp(comp, z):
            """XY-type plane at global Z=z."""
            pi = comp.constructionPlanes.createInput()
            pi.setByOffset(comp.xYConstructionPlane, VI(z))
            return comp.constructionPlanes.add(pi)

        XY = root.xYConstructionPlane

        # ── SKETCH HELPERS ────────────────────────────────────────
        def rect(comp, plane, x0, y0, x1, y1):
            sk = comp.sketches.add(plane)
            sk.sketchCurves.sketchLines.addTwoPointRectangle(Pt(x0,y0,0), Pt(x1,y1,0))
            return sk.profiles.item(0)

        def circ(comp, plane, cx, cy, r):
            sk = comp.sketches.add(plane)
            sk.sketchCurves.sketchCircles.addByCenterRadius(Pt(cx,cy,0), r)
            return sk.profiles.item(0)

        def circ_yz(comp, plane, gy, gz, r):
            """Circle on a yp-plane. sketch_y = -global_Z."""
            return circ(comp, plane, gy, -gz, r)

        def rect_yz(comp, plane, gy0, gz0, gy1, gz1):
            """Rectangle on a yp-plane. sketch_y = -global_Z."""
            return rect(comp, plane, gy0, -gz1, gy1, -gz0)

        # ── EXTRUDE HELPERS ───────────────────────────────────────
        def new_body(comp, prof, dist):
            ei = comp.features.extrudeFeatures.createInput(prof, FO.NewBodyFeatureOperation)
            ei.setDistanceExtent(False, VI(dist))
            return comp.features.extrudeFeatures.add(ei)

        def join_pos(comp, prof, dist):
            ei = comp.features.extrudeFeatures.createInput(prof, FO.JoinFeatureOperation)
            ei.setDistanceExtent(False, VI(dist))
            return comp.features.extrudeFeatures.add(ei)

        def join_neg(comp, prof, dist):
            ei = comp.features.extrudeFeatures.createInput(prof, FO.JoinFeatureOperation)
            ei.setOneSideExtent(DED.create(VI(dist)), ED.NegativeExtentDirection)
            return comp.features.extrudeFeatures.add(ei)

        def join_sym(comp, prof, half_dist):
            """Symmetric extrude ±half_dist (total = 2×half_dist)."""
            ei = comp.features.extrudeFeatures.createInput(prof, FO.JoinFeatureOperation)
            ei.setSymmetricExtent(VI(half_dist), False)
            return comp.features.extrudeFeatures.add(ei)

        def cut_pos(comp, prof, dist, body):
            ei = comp.features.extrudeFeatures.createInput(prof, FO.CutFeatureOperation)
            ei.setDistanceExtent(False, VI(dist))
            ei.participantBodies = [body]
            return comp.features.extrudeFeatures.add(ei)

        def cut_neg(comp, prof, dist, body):
            ei = comp.features.extrudeFeatures.createInput(prof, FO.CutFeatureOperation)
            ei.setOneSideExtent(DED.create(VI(dist)), ED.NegativeExtentDirection)
            ei.participantBodies = [body]
            return comp.features.extrudeFeatures.add(ei)

        def find_top_face(body, z_val, tol=0.005):
            for f in body.faces:
                bb = f.boundingBox
                if abs(bb.minPoint.z - z_val) < tol and abs(bb.maxPoint.z - z_val) < tol:
                    return f
            return None

        # (box, lid, canopy code goes in Tasks 2-5)

    except:
        if ui:
            ui.messageBox('Error:\n{}'.format(traceback.format_exc()))
```

- [ ] **Step 2: Commit scaffold**

```bash
git add "OneDrive/Desktop/PCV/protel/solar_box.py"
git commit -m "feat: scaffold solar_box.py with parameters and helpers"
```

---

### Task 2: Box body and shell

**Files:**
- Modify: `C:\Users\aaron\OneDrive\Desktop\PCV\protel\solar_box.py` (inside `run()`, after helpers)

- [ ] **Step 1: Add box body + shell after the helpers block**

Replace the `# (box, lid, canopy code goes in Tasks 2-5)` comment with:

```python
        # =================================================================
        # BOX  (x: 0→BL,  y: 0→BW,  z: 0→BH)
        # =================================================================
        boxFeat = new_body(root, rect(root, XY, 0, 0, BL, BW), BH)
        boxBody = boxFeat.bodies.item(0)
        boxBody.name = 'SolarBox_Box'

        # Shell: remove top face, 3mm wall
        topFace = find_top_face(boxBody, BH)
        if topFace is None:
            raise RuntimeError('find_top_face: no face at z={}'.format(BH))
        fc = adsk.core.ObjectCollection.create()
        fc.add(topFace)
        si = root.features.shellFeatures.createInput(fc, False)
        si.insideThickness = VI(WT)
        root.features.shellFeatures.add(si)
```

- [ ] **Step 2: Load script into Fusion 360 and run**

In Fusion 360: **Tools → Add-Ins → Scripts and Add-Ins → Add** → select `solar_box.py` → **Run**.

Expected: a hollow open-top box 160×90×55mm appears at origin.

- [ ] **Step 3: Commit**

```bash
git add "OneDrive/Desktop/PCV/protel/solar_box.py"
git commit -m "feat: add box body and shell to solar_box.py"
```

---

### Task 3: Lid — plate, lip, O-ring groove

**Files:**
- Modify: `C:\Users\aaron\OneDrive\Desktop\PCV\protel\solar_box.py`

- [ ] **Step 1: Add lid body after the box shell code**

```python
        # =================================================================
        # LID  placed right of box at x=LX
        # Plate: 5mm  |  Lip: 8mm down (fits inside box opening)
        # =================================================================
        lidFeat = new_body(root, rect(root, XY, LX, 0, LX+BL, BW), LID_PLATE)
        lidBody = lidFeat.bodies.item(0)
        lidBody.name = 'SolarBox_Lid'

        # Lip: extrude -Z from bottom of plate
        join_neg(root,
                 rect(root, XY, LX+LIP_X0, LIP_Y0,
                      LX+LIP_X0+LIP_L, LIP_Y0+LIP_W),
                 LID_LIP)

        # O-ring groove: 2.5mm wide × 2mm deep, mid-depth of lip on all 4 outer faces
        oz0 = -(LID_LIP/2) - O_W/2   # -0.525 cm from lid top
        oz1 = -(LID_LIP/2) + O_W/2   # -0.275 cm from lid top

        # Left lip face  (x = LX+LIP_X0): cut_pos → +X into lip
        cut_pos(root,
                rect_yz(root, yp(root, LX+LIP_X0),
                        LIP_Y0, oz0, LIP_Y0+LIP_W, oz1),
                O_D, lidBody)

        # Right lip face (x = LX+LIP_X0+LIP_L): cut_neg → -X into lip
        cut_neg(root,
                rect_yz(root, yp(root, LX+LIP_X0+LIP_L),
                        LIP_Y0, oz0, LIP_Y0+LIP_W, oz1),
                O_D, lidBody)

        # Front lip face (y = LIP_Y0): cut_pos → +Y into lip
        cut_pos(root,
                rect(root, xp(root, LIP_Y0),
                     LX+LIP_X0, oz0, LX+LIP_X0+LIP_L, oz1),
                O_D, lidBody)

        # Back lip face  (y = LIP_Y0+LIP_W): cut_neg → -Y into lip
        cut_neg(root,
                rect(root, xp(root, LIP_Y0+LIP_W),
                     LX+LIP_X0, oz0, LX+LIP_X0+LIP_L, oz1),
                O_D, lidBody)
```

- [ ] **Step 2: Run in Fusion 360**

Expected: lid appears to the right of the box. Lip visible underneath. O-ring groove (2.5×2mm) visible as a continuous channel around all 4 outer faces of the lip.

- [ ] **Step 3: Commit**

```bash
git add "OneDrive/Desktop/PCV/protel/solar_box.py"
git commit -m "feat: add lid with lip and O-ring groove"
```

---

### Task 4: PG7 cable hole in right wall

**Files:**
- Modify: `C:\Users\aaron\OneDrive\Desktop\PCV\protel\solar_box.py`

- [ ] **Step 1: Cut PG7 hole after the lid code**

```python
        # =================================================================
        # PG7 CABLE HOLE — right wall (x=BL), Y-center, Z-mid-height
        # Ø12mm (radius 0.6cm), cut through 3mm wall thickness
        # yp(BL): normal = +X → cut_neg = -X direction (into right wall) ✓
        # =================================================================
        cut_neg(root,
                circ_yz(root, yp(root, BL), PG7_Y, PG7_Z, PG7_R),
                WT + 0.05,
                boxBody)
```

- [ ] **Step 2: Run in Fusion 360**

Expected: a 12mm-diameter hole visible in the center of the right wall (x=BL face), centered at Y=45mm, Z=27.5mm.

- [ ] **Step 3: Commit**

```bash
git add "OneDrive/Desktop/PCV/protel/solar_box.py"
git commit -m "feat: add PG7 cable hole in right wall"
```

---

### Task 5: Rain canopy — semicircle + side walls

**Files:**
- Modify: `C:\Users\aaron\OneDrive\Desktop\PCV\protel\solar_box.py`

The canopy is a crescent-shaped prism:
- Cross-section (XZ plane at Y=BW/2): outer semicircle R=2.2cm + inner R=1.7cm + 2 closing lines at x=BL
- Extruded symmetrically ±4cm in Y → total 80mm width
- End faces (at Y=BW/2±4cm) act as solid side walls → rain from the side is blocked
- Opening faces -Z (downward): cable enters from below

- [ ] **Step 1: Add canopy after PG7 hole code**

```python
        # =================================================================
        # RAIN CANOPY — semicircle hood over PG7 hole
        # Profile in XZ plane at Y=BW/2 (xp plane, sketch_x→X, sketch_y→Z)
        # Outer arc: R=CANO_RO=2.2cm, Inner arc: R=CANO_RI=1.7cm
        # Both semicircles centered at (BL, PG7_Z) = (16, 2.75)
        # Arc goes OUTWARD (+X), opening faces -Z (downward)
        # Extruded ±CANO_HW=4cm in Y → 80mm wide with closed end walls
        # =================================================================
        canopy_sk = root.sketches.add(xp(root, BW/2))
        arcs  = canopy_sk.sketchCurves.sketchArcs
        lines = canopy_sk.sketchCurves.sketchLines

        cx, cz = BL, PG7_Z

        # Outer semicircle: from (BL, PG7_Z+CANO_RO) CW→through (BL+CANO_RO,PG7_Z)→(BL, PG7_Z-CANO_RO)
        # addByCenterStartSweep: negative sweep = CW in sketch plane
        arcs.addByCenterStartSweep(
            Pt(cx, cz, 0),
            Pt(cx, cz + CANO_RO, 0),
            -math.pi
        )

        # Inner semicircle: from (BL, PG7_Z-CANO_RI) CW→through (BL+CANO_RI,PG7_Z)→(BL, PG7_Z+CANO_RI)
        arcs.addByCenterStartSweep(
            Pt(cx, cz, 0),
            Pt(cx, cz - CANO_RI, 0),
            -math.pi
        )

        # Closing lines at x=BL (wall face): top gap and bottom gap
        lines.addByTwoPoints(
            Pt(cx, cz + CANO_RI, 0),
            Pt(cx, cz + CANO_RO, 0)
        )
        lines.addByTwoPoints(
            Pt(cx, cz - CANO_RO, 0),
            Pt(cx, cz - CANO_RI, 0)
        )

        # Get crescent profile (the only closed region in this sketch)
        if canopy_sk.profiles.count == 0:
            raise RuntimeError('Canopy sketch: no closed profile found. Check arc directions.')
        canopy_prof = canopy_sk.profiles.item(0)

        # Extrude symmetrically ±CANO_HW — joins to box body
        join_sym(root, canopy_prof, CANO_HW)
```

- [ ] **Step 2: Run in Fusion 360**

Expected:
- A curved hood protrudes from the right wall of the box
- The hood is a thick C-shape (5mm shell, 22mm radius) opening downward
- Width = 80mm in Y (centered on box), flat end walls at both Y ends
- The PG7 hole is visible inside the hood

If `profiles.count == 0`, the sketch curves didn't form a closed loop — check that arc endpoints exactly match line endpoints (they must share the same coordinate values).

- [ ] **Step 3: Add final message box and commit**

After `join_sym(...)`, add:

```python
        # =================================================================
        # DONE
        # =================================================================
        ui.messageBox(
            'Solar Outdoor Box selesai!\n\n'
            'SolarBox_Box   160×90×55mm  (3mm wall)\n'
            'SolarBox_Lid   160×90×13mm  (plate 5mm + lip 8mm)\n'
            '  O-ring groove 2.5×2mm, press-fit\n\n'
            'PG7 Ø12mm  —  right wall, center Y/Z\n'
            'Rain Canopy  —  R22mm semicircle, 80mm wide\n'
            '  side walls tertutup, opening facing DOWN\n\n'
            'Hardware:\n'
            '  O-ring Ø2mm cord, ID≈148mm  ×1\n'
            '  PG7 cable gland  ×1'
        )
```

```bash
git add "OneDrive/Desktop/PCV/protel/solar_box.py"
git commit -m "feat: add semicircle rain canopy with closed side walls"
```

---

## Self-Review

**Spec coverage:**
- ✅ Box 160×90×55mm, 3mm wall — Task 2
- ✅ Lid press-fit, O-ring groove all 4 sides — Task 3
- ✅ PG7 Ø12mm right wall center — Task 4
- ✅ Canopy semicircle R22mm, 5mm thick — Task 5
- ✅ Canopy 80mm wide, side walls closed — Task 5 (extrude ±4cm = closed ends)
- ✅ No screw posts, no sensor bracket, no ventilation — not in any task ✓

**Placeholder scan:** No TBDs. All code blocks complete.

**Type consistency:**
- `boxBody` created in Task 2, used in Task 4 `cut_neg` — ✓
- `LX`, `LIP_X0`, `LIP_Y0`, `LIP_L`, `LIP_W` defined in Task 1, used in Task 3 — ✓
- `PG7_Y`, `PG7_Z`, `PG7_R` defined in Task 1, used in Task 4 — ✓
- `CANO_RO`, `CANO_RI`, `CANO_HW` defined in Task 1, used in Task 5 — ✓
- `join_sym()` defined in Task 1, used in Task 5 — ✓

**Known edge case:** Fusion 360's `addByCenterStartSweep` with sweep=-π creates arcs that touch at start/end. If the profile is not detected (`profiles.count == 0`), the arc endpoints may be floating-point mismatched with line endpoints. Fix: use `Pt(cx, cz+CANO_RO, 0)` exactly for both the arc end and the line start — same coordinates, same `Pt()` call values.
