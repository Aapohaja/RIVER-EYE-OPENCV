import adsk.core, adsk.fusion, traceback

def run(context):
    ui = None
    try:
        app  = adsk.core.Application.get()
        ui   = app.userInterface
        des  = app.activeProduct
        root = des.rootComponent

        VI  = adsk.core.ValueInput.createByReal
        Pt  = adsk.core.Point3D.create
        Obj = adsk.core.ObjectCollection.create
        FO  = adsk.fusion.FeatureOperations
        ED  = adsk.fusion.ExtentDirections
        DED = adsk.fusion.DistanceExtentDefinition

        # ── PARAMETERS (all in cm) ────────────────────────────────────────
        BL, BW, BH = 12.0, 9.0, 8.0
        WT         = 0.3
        LID_PLATE    = 0.5    # 5 mm plate
        LID_LIP      = 0.7    # 7 mm lip  → total 12 mm
        LID_OVERHANG = 0.6    # 6 mm overhang ke kiri (melindungi sensor)
        LIP_L  = BL - 2*WT - 0.05
        LIP_W  = BW - 2*WT - 0.05
        LIP_X0 = (BL - LIP_L) / 2
        LIP_Y0 = (BW - LIP_W) / 2
        O_W, O_D   = 0.25, 0.2
        PRL, PRW, PRD = 11.2, 6.2, 0.2    # recess 2mm (plate 5mm → 3mm sisa)
        SP_X0 = (BL - PRL) / 2
        SP_Y0 = (BW - PRW) / 2
        PG7_R  = 0.6
        PG9_R  = 0.8
        BKT_L, BKT_H, BKT_T = 4.0, 1.5, 0.5
        BKT_HR = 0.25
        VENT_R = 0.4
        VENT_Z = 1.0
        BFL_W, BFL_H, BFL_T = 3.0, 1.5, 0.5
        POST_RO  = 0.35
        POST_RI  = 0.175
        POST_H   = 1.1
        POST_OFF = WT + 0.5
        SCREW_R  = 0.175
        LX = BL + 3.0

        posts = [
            (POST_OFF,        POST_OFF),
            (BL - POST_OFF,   POST_OFF),
            (BL - POST_OFF,   BW - POST_OFF),
            (POST_OFF,        BW - POST_OFF),
        ]

        # ── PLANE HELPERS ─────────────────────────────────────────────────
        # YZ-type plane at x (offset from yZConstructionPlane).
        # Empirically: sketch_x → global_Y,  sketch_y → global_(-Z)
        # So to hit global z=Z, pass sketch_y = -Z
        def yp(comp, x):
            if abs(x) < 1e-5:
                return comp.yZConstructionPlane
            pi = comp.constructionPlanes.createInput()
            pi.setByOffset(comp.yZConstructionPlane, VI(x))
            return comp.constructionPlanes.add(pi)

        # XZ-type plane at y (offset from xZConstructionPlane).
        # sketch_x → global_X,  sketch_y → global_Z  (no inversion)
        # Normal = +Y  →  pos = +Y, neg = -Y
        def xp(comp, y):
            if abs(y) < 1e-5:
                return comp.xZConstructionPlane
            pi = comp.constructionPlanes.createInput()
            pi.setByOffset(comp.xZConstructionPlane, VI(y))
            return comp.constructionPlanes.add(pi)

        # XY-type plane at z (normal = +Z → pos = +Z up, neg = -Z down)
        def zp(comp, z):
            pi = comp.constructionPlanes.createInput()
            pi.setByOffset(comp.xYConstructionPlane, VI(z))
            return comp.constructionPlanes.add(pi)

        XY = root.xYConstructionPlane

        # ── SKETCH HELPERS ────────────────────────────────────────────────
        def rect(comp, plane, x0, y0, x1, y1):
            sk = comp.sketches.add(plane)
            sk.sketchCurves.sketchLines.addTwoPointRectangle(Pt(x0,y0,0), Pt(x1,y1,0))
            return sk.profiles.item(0)

        def circ(comp, plane, cx, cy, r):
            sk = comp.sketches.add(plane)
            sk.sketchCurves.sketchCircles.addByCenterRadius(Pt(cx,cy,0), r)
            return sk.profiles.item(0)

        # On yp-planes: sketch_y = -global_Z, so to target global z=Z use sketch_y=-Z
        def circ_yz(comp, plane, global_y, global_z, r):
            """Circle on a yp-plane. Pass actual global Y and Z."""
            return circ(comp, plane, global_y, -global_z, r)

        def rect_yz(comp, plane, gy0, gz0, gy1, gz1):
            """Rectangle on a yp-plane. Pass actual global Y and Z ranges."""
            # negating Z: sketch_y0=-gz1, sketch_y1=-gz0 (swap keeps correct order)
            return rect(comp, plane, gy0, -gz1, gy1, -gz0)

        # ── EXTRUDE HELPERS ───────────────────────────────────────────────
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

        def cut_pos(comp, prof, dist, body):
            """Cut body in positive-normal direction."""
            ei = comp.features.extrudeFeatures.createInput(prof, FO.CutFeatureOperation)
            ei.setDistanceExtent(False, VI(dist))
            ei.participantBodies = [body]
            return comp.features.extrudeFeatures.add(ei)

        def cut_neg(comp, prof, dist, body):
            """Cut body in negative-normal direction."""
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

        # =================================================================
        # BOX  (x:0->BL  y:0->BW  z:0->BH)
        # =================================================================
        boxFeat = new_body(root, rect(root, XY, 0, 0, BL, BW), BH)
        boxBody = boxFeat.bodies.item(0)
        boxBody.name = 'RiverEye_Box'

        topFace = find_top_face(boxBody, BH)
        if topFace is None:
            raise RuntimeError('find_top_face: no face at z={}'.format(BH))
        fc = Obj(); fc.add(topFace)
        si = root.features.shellFeatures.createInput(fc, False)
        si.insideThickness = VI(WT)
        root.features.shellFeatures.add(si)

        # ── SENSOR BRACKET (L-shape, external left wall) ─────────────────
        # Sensor PCB 59×20mm dipasang di luar pada bracket ini
        SB_W     = 2.5    # 25mm lebar bracket (Y), cukup untuk sensor 20mm
        SB_T     = 0.2    # 2mm tebal bracket (protrudes -X dari dinding kiri)
        SB_ABOVE = 0.5    # 5mm di atas lantai box (area attachment ke dinding)
        SB_BELOW = 6.5    # 65mm di bawah lantai (lebih panjang dari sensor 59mm)
        SB_Y0    = (BW - SB_W) / 2   # centered in Y

        # Lubang kabel sensor Ø5mm di dinding kiri (kabel masuk ke dalam box)
        cut_pos(root, circ_yz(root, yp(root, 0), BW/2, 0.4, 0.25), WT+0.05, boxBody)

        # Bracket plate: join ke dinding kiri, extrude -X (keluar)
        join_neg(root, rect_yz(root, yp(root, 0), SB_Y0, -SB_BELOW, SB_Y0+SB_W, SB_ABOVE), SB_T)

        # 2× lubang M3 di bracket untuk baut sensor PCB
        sb_outer = yp(root, -SB_T)   # muka luar bracket di x=-SB_T
        cut_pos(root, circ_yz(root, sb_outer, BW/2,  0.0,       0.175), SB_T+0.05, boxBody)
        cut_pos(root, circ_yz(root, sb_outer, BW/2, -SB_BELOW+0.5, 0.175), SB_T+0.05, boxBody)

        # USB-C PG9 Ø16mm on RIGHT wall (x=BL)
        # yp at BL, normal=+X → cut_neg = -X direction (into right wall) ✓
        cut_neg(root, circ_yz(root, yp(root, BL), BW/2, BH*0.5, PG9_R), WT+0.05, boxBody)

        # Mounting brackets
        by0 = (BW - BKT_L) / 2     # 2.5 cm
        by1 = by0 + BKT_L           # 6.5 cm
        bz0 = BH/2 - BKT_H/2       # 3.25 cm
        bz1 = bz0 + BKT_H           # 4.75 cm

        # Left bracket protrudes -X: join_neg on yp(0) ✓
        join_neg(root, rect_yz(root, yp(root, 0), by0, bz0, by1, bz1), BKT_T)
        cut_pos(root, circ_yz(root, yp(root, -BKT_T), BW/2, BH/2, BKT_HR), BKT_T+0.05, boxBody)

        # Right bracket protrudes +X: join_pos on yp(BL) ✓
        join_pos(root, rect_yz(root, yp(root, BL), by0, bz0, by1, bz1), BKT_T)
        cut_neg(root, circ_yz(root, yp(root, BL+BKT_T), BW/2, BH/2, BKT_HR), BKT_T+0.05, boxBody)

        # Ventilation hole + rain baffle on BACK wall (y=BW)
        # xp normal=+Y → cut_neg = -Y (into back wall) ✓, join_pos = +Y (outward) ✓
        bp = xp(root, BW)
        cut_neg(root, circ(root, bp, BL/2, VENT_Z, VENT_R), WT+0.05, boxBody)

        bx0 = BL/2 - BFL_W/2
        bx1 = BL/2 + BFL_W/2
        bfz0 = VENT_Z + VENT_R + 0.2
        bfz1 = bfz0 + BFL_H
        join_pos(root, rect(root, bp, bx0, bfz0, bx1, bfz1), BFL_T)

        # Screw posts (4 corners, bore starts at z=WT to keep floor solid)
        fi = zp(root, WT)
        for cx, cy in posts:
            join_pos(root, circ(root, XY, cx, cy, POST_RO), POST_H)
            cut_pos(root, circ(root, fi, cx, cy, POST_RI), POST_H-WT+0.05, boxBody)

        # =================================================================
        # LID  (total 12mm: 5mm plate + 7mm lip)
        # Overhang 6mm ke kiri → x: LX-LID_OVERHANG → LX+BL
        # Placed 3cm right of box  (LX = BL+3.0 = 15cm)
        # =================================================================
        lidFeat = new_body(root, rect(root, XY, LX-LID_OVERHANG, 0, LX+BL, BW), LID_PLATE)
        lidBody = lidFeat.bodies.item(0)
        lidBody.name = 'RiverEye_Lid'

        # Lip: join_neg → -Z direction from z=0 ✓
        join_neg(root, rect(root, XY, LX+LIP_X0, LIP_Y0, LX+LIP_X0+LIP_L, LIP_Y0+LIP_W), LID_LIP)

        # O-ring groove (2.5mm wide × 2mm deep on all 4 sides of lip)
        oz0 = -(LID_LIP/2) - O_W/2   # ≈ -0.525 cm
        oz1 = -(LID_LIP/2) + O_W/2   # ≈ -0.275 cm

        # Left lip face x=LX+LIP_X0: cut_pos=+X into lip
        # (lip starts at LX+LIP_X0, overhang area LX-OVERHANG to LX+LIP_X0 is solid plate only)
        cut_pos(root, rect_yz(root, yp(root, LX+LIP_X0),
                LIP_Y0, oz0, LIP_Y0+LIP_W, oz1), O_D, lidBody)
        # Right lip face x=LX+LIP_X0+LIP_L: cut_neg=-X into lip ✓
        cut_neg(root, rect_yz(root, yp(root, LX+LIP_X0+LIP_L),
                LIP_Y0, oz0, LIP_Y0+LIP_W, oz1), O_D, lidBody)
        # Front lip face y=LIP_Y0: xp normal=+Y, cut_pos=+Y into lip ✓
        cut_pos(root, rect(root, xp(root, LIP_Y0),
                LX+LIP_X0, oz0, LX+LIP_X0+LIP_L, oz1), O_D, lidBody)
        # Back lip face y=LIP_Y0+LIP_W: cut_neg=-Y into lip ✓
        cut_neg(root, rect(root, xp(root, LIP_Y0+LIP_W),
                LX+LIP_X0, oz0, LX+LIP_X0+LIP_L, oz1), O_D, lidBody)

        # Solar panel recess + cable gland + screw holes (cut from lid top)
        tp = zp(root, LID_PLATE)

        cut_neg(root, rect(root, tp, LX+SP_X0, SP_Y0, LX+SP_X0+PRL, SP_Y0+PRW), PRD, lidBody)
        cut_neg(root, circ(root, tp, LX+2.5, 0.5, PG7_R), LID_PLATE+LID_LIP+0.05, lidBody)

        for cx, cy in posts:
            cut_neg(root, circ(root, tp, LX+cx, cy, SCREW_R), LID_PLATE+LID_LIP+0.05, lidBody)

        ui.messageBox(
            'River Eye Enclosure selesai!\n\n'
            'RiverEye_Box  120x90x80mm\n'
            'RiverEye_Lid  126x90x12mm  (overhang 6mm kiri, di kanan box)\n'
            'Sensor Bracket  2mm plate, 65mm di bawah lantai\n\n'
            'Hardware:\n'
            '  O-ring Ø2mm, PG7 x2, PG9 x1\n'
            '  Baut M3x12 x4, M5x20 x4\n'
            '  Standoff M3x15 x4'
        )

    except:
        if ui:
            ui.messageBox('Error:\n{}'.format(traceback.format_exc()))
