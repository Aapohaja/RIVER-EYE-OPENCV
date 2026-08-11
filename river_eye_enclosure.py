import adsk.core, adsk.fusion, traceback

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

        # ── PARAMETERS (all in cm — Fusion 360 internal unit) ────────────
        BL, BW, BH = 12.0, 9.0, 8.0    # box outer: 120 × 90 × 80 mm
        WT          = 0.3               # 3 mm wall thickness

        LID_PLATE   = 0.7               # 7 mm top plate height
        LID_LIP     = 0.8               # 8 mm lip depth (fits inside box)

        LIP_L  = BL - 2*WT - 0.05      # 11.35 cm (0.25 mm gap per side)
        LIP_W  = BW - 2*WT - 0.05      # 8.35 cm
        LIP_X0 = (BL - LIP_L) / 2      # 0.325 cm from left edge
        LIP_Y0 = (BW - LIP_W) / 2      # 0.325 cm from front edge

        O_W, O_D = 0.25, 0.2           # O-ring groove: 2.5 mm wide, 2 mm deep

        PRL, PRW, PRD = 11.2, 6.2, 0.3 # solar panel recess: 112×62×3 mm
        SP_X0 = (BL - PRL) / 2         # 0.4 cm
        SP_Y0 = (BW - PRW) / 2         # 1.4 cm

        PG7_R = 0.6                     # 6 mm radius = Ø12 mm (PG7 cable gland)
        PG9_R = 0.8                     # 8 mm radius = Ø16 mm (PG9 cable gland)

        BKT_L  = 4.0                    # 40 mm mounting bracket length
        BKT_H  = 1.5                    # 15 mm mounting bracket height
        BKT_T  = 0.5                    # 5 mm bracket thickness
        BKT_HR = 0.25                   # 2.5 mm hole radius = Ø5 mm

        VENT_R = 0.4                    # 4 mm radius = Ø8 mm vent hole
        VENT_Z = 1.0                    # 10 mm from floor
        BFL_W  = 3.0                    # 30 mm baffle width
        BFL_H  = 1.5                    # 15 mm baffle height
        BFL_T  = 0.5                    # 5 mm baffle protrusion

        POST_RO  = 0.35                 # 3.5 mm outer radius of screw post
        POST_RI  = 0.175                # 1.75 mm inner radius = Ø3.5 mm (M3 heat-set insert bore)
        POST_H   = 1.1                  # 11 mm total post height (8 mm visible above floor)
        POST_OFF = WT + 0.5             # 8 mm from outer box corner

        SCREW_R = 0.175                 # 1.75 mm = M3 clearance hole in lid

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
            """Extrude in positive normal direction of the sketch plane."""
            ei = comp.features.extrudeFeatures.createInput(prof, op)
            ei.setDistanceExtent(False, VI(dist))
            return comp.features.extrudeFeatures.add(ei)

        def extrude_neg(comp, prof, dist, op=FO.CutFeatureOperation):
            """Extrude in negative normal direction of the sketch plane."""
            ei = comp.features.extrudeFeatures.createInput(prof, op)
            ei.setOneSideExtent(
                DED.create(VI(dist)), ED.NegativeExtentDirection)
            return comp.features.extrudeFeatures.add(ei)

        def rect_prof(comp, plane, x0, y0, x1, y1):
            """Sketch a rectangle and return its profile."""
            sk = comp.sketches.add(plane)
            sk.sketchCurves.sketchLines.addTwoPointRectangle(
                Pt(x0, y0, 0), Pt(x1, y1, 0))
            return sk.profiles.item(0)

        def circle_prof(comp, plane, cx, cy, r):
            """Sketch a circle and return its profile."""
            sk = comp.sketches.add(plane)
            sk.sketchCurves.sketchCircles.addByCenterRadius(Pt(cx, cy, 0), r)
            return sk.profiles.item(0)

        def find_top_face(body, z_val, tol=0.005):
            """Find the horizontal face at z=z_val (used to locate top face for shell)."""
            for f in body.faces:
                bb = f.boundingBox
                if (abs(bb.minPoint.z - z_val) < tol and
                        abs(bb.maxPoint.z - z_val) < tol):
                    return f
            return None

        # ═══════════════════════════════════════════════════════════════════
        # MAIN BOX COMPONENT
        # Box outer: 120×90×80 mm, wall: 3 mm, top open
        # ═══════════════════════════════════════════════════════════════════
        boxOcc  = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        bC      = boxOcc.component
        bC.name = 'RiverEye_Box'

        XY = bC.xYConstructionPlane   # z=0, normal = +Z
        XZ = bC.xZConstructionPlane   # y=0, normal = +Y
        YZ = bC.yZConstructionPlane   # x=0, normal = +X

        # Task 2: Solid box + shell
        boxFeat = extrude_pos(bC, rect_prof(bC, XY, 0, 0, BL, BW), BH)
        boxBody = boxFeat.bodies.item(0)

        topFace = find_top_face(boxBody, BH)
        if topFace is None:
            raise RuntimeError('find_top_face: no face at z={}cm'.format(BH))
        fc = Obj()
        fc.add(topFace)
        si = bC.features.shellFeatures.createInput(fc, False)
        si.insideThickness = VI(WT)
        bC.features.shellFeatures.add(si)

        # Task 3: Cable gland holes
        yz_right = offset_plane(bC, YZ, BL)
        hole_z   = BH * 0.5

        # Left wall (x=0): PG7 Ø12mm for water level sensor
        extrude_pos(bC,
            circle_prof(bC, YZ, BW/2, hole_z, PG7_R),
            WT + 0.05, FO.CutFeatureOperation)

        # Right wall (x=BL): PG9 Ø16mm for USB-C access
        extrude_neg(bC,
            circle_prof(bC, yz_right, BW/2, hole_z, PG9_R),
            WT + 0.05)

        # Task 4: Mounting brackets (left and right)
        bkt_y0 = (BW - BKT_L) / 2
        bkt_y1 = bkt_y0 + BKT_L
        bkt_z0 = BH/2 - BKT_H/2
        bkt_z1 = bkt_z0 + BKT_H

        # Left bracket: protrudes -X from x=0
        extrude_neg(bC,
            rect_prof(bC, YZ, bkt_y0, bkt_z0, bkt_y1, bkt_z1),
            BKT_T, FO.JoinFeatureOperation)
        # Left bracket bolt hole Ø5mm
        extrude_pos(bC,
            circle_prof(bC, offset_plane(bC, YZ, -BKT_T), BW/2, BH/2, BKT_HR),
            BKT_T + 0.05, FO.CutFeatureOperation)

        # Right bracket: protrudes +X from x=BL
        extrude_pos(bC,
            rect_prof(bC, yz_right, bkt_y0, bkt_z0, bkt_y1, bkt_z1),
            BKT_T, FO.JoinFeatureOperation)
        # Right bracket bolt hole Ø5mm
        extrude_neg(bC,
            circle_prof(bC, offset_plane(bC, YZ, BL + BKT_T), BW/2, BH/2, BKT_HR),
            BKT_T + 0.05)

        # Task 5: Ventilation hole + rain baffle (back wall y=BW)
        back_plane = offset_plane(bC, XZ, BW)

        # Vent hole Ø8mm, 10mm from floor
        extrude_neg(bC,
            circle_prof(bC, back_plane, BL/2, VENT_Z, VENT_R),
            WT + 0.05)

        # Baffle tab above vent hole, protrudes +Y outward
        bfl_x0 = BL/2 - BFL_W/2
        bfl_x1 = BL/2 + BFL_W/2
        bfl_z0 = VENT_Z + VENT_R + 0.2   # 2 mm above top of vent hole
        bfl_z1 = bfl_z0 + BFL_H
        extrude_pos(bC,
            rect_prof(bC, back_plane, bfl_x0, bfl_z0, bfl_x1, bfl_z1),
            BFL_T, FO.JoinFeatureOperation)

        # Task 6: Internal screw posts at 4 corners
        floor_inner = offset_plane(bC, XY, WT)
        for cx, cy in posts:
            extrude_pos(bC,
                circle_prof(bC, XY, cx, cy, POST_RO),
                POST_H, FO.JoinFeatureOperation)
            extrude_pos(bC,
                circle_prof(bC, floor_inner, cx, cy, POST_RI),
                POST_H - WT + 0.05, FO.CutFeatureOperation)

        # ═══════════════════════════════════════════════════════════════════
        # LID COMPONENT
        # Lid total: 120×90×15 mm (7mm plate + 8mm lip)
        # ═══════════════════════════════════════════════════════════════════
        lidOcc  = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        lC      = lidOcc.component
        lC.name = 'RiverEye_Lid'

        LXY = lC.xYConstructionPlane   # z=0, normal = +Z
        LXZ = lC.xZConstructionPlane   # y=0, normal = +Y
        LYZ = lC.yZConstructionPlane   # x=0, normal = +X

        # Task 7: Top plate (upward) + lip (downward)
        extrude_pos(lC,
            rect_prof(lC, LXY, 0, 0, BL, BW),
            LID_PLATE)
        extrude_neg(lC,
            rect_prof(lC, LXY, LIP_X0, LIP_Y0,
                      LIP_X0 + LIP_L, LIP_Y0 + LIP_W),
            LID_LIP, FO.JoinFeatureOperation)

        # Task 8: O-ring groove on all 4 sides of lip
        # Groove centered at mid-depth of lip: z = -(LID_LIP/2)
        oz0 = -(LID_LIP / 2) - O_W / 2
        oz1 = -(LID_LIP / 2) + O_W / 2

        # Left lip face (x=LIP_X0): cut +X
        extrude_pos(lC,
            rect_prof(lC, offset_plane(lC, LYZ, LIP_X0),
                      LIP_Y0, oz0, LIP_Y0 + LIP_W, oz1),
            O_D, FO.CutFeatureOperation)

        # Right lip face (x=LIP_X0+LIP_L): cut -X
        extrude_neg(lC,
            rect_prof(lC, offset_plane(lC, LYZ, LIP_X0 + LIP_L),
                      LIP_Y0, oz0, LIP_Y0 + LIP_W, oz1),
            O_D)

        # Front lip face (y=LIP_Y0): cut +Y
        extrude_pos(lC,
            rect_prof(lC, offset_plane(lC, LXZ, LIP_Y0),
                      LIP_X0, oz0, LIP_X0 + LIP_L, oz1),
            O_D, FO.CutFeatureOperation)

        # Back lip face (y=LIP_Y0+LIP_W): cut -Y
        extrude_neg(lC,
            rect_prof(lC, offset_plane(lC, LXZ, LIP_Y0 + LIP_W),
                      LIP_X0, oz0, LIP_X0 + LIP_L, oz1),
            O_D)

        # Task 9: Solar panel recess + solar cable gland hole
        top_plane = offset_plane(lC, LXY, LID_PLATE)

        # Solar panel recess 112×62×3mm, centered on lid top
        extrude_neg(lC,
            rect_prof(lC, top_plane, SP_X0, SP_Y0,
                      SP_X0 + PRL, SP_Y0 + PRW),
            PRD)

        # PG7 cable gland hole Ø12mm for solar panel cable
        # Position: x=1.0cm, y=0.8cm (in front of solar panel recess, clear of it)
        extrude_neg(lC,
            circle_prof(lC, top_plane, 2.5, 0.5, PG7_R),
            LID_PLATE + LID_LIP + 0.05)

        # Task 10: Lid M3 screw holes (aligned with box screw posts)
        for cx, cy in posts:
            extrude_neg(lC,
                circle_prof(lC, top_plane, cx, cy, SCREW_R),
                LID_PLATE + LID_LIP + 0.05)

        ui.messageBox(
            'River Eye Enclosure berhasil dibuat!\n\n'
            'Components:\n'
            '  - RiverEye_Box  (120 x 90 x 80 mm)\n'
            '  - RiverEye_Lid  (120 x 90 x 15 mm)\n\n'
            'Hardware yang perlu dibeli:\n'
            '  - O-ring: Ø2mm, panjang sesuai keliling lip\n'
            '  - Cable gland PG7 x2 (sensor + solar cable)\n'
            '  - Cable gland PG9 x1 (USB-C)\n'
            '  - Baut M3 x 12mm stainless x4 (lid)\n'
            '  - Baut M5 x 20mm stainless x4 (bracket ke median)\n'
            '  - Standoff M3 x 15mm x4 (ESP32 di atas battery)'
        )

    except:
        if ui:
            ui.messageBox('Error:\n{}'.format(traceback.format_exc()))
