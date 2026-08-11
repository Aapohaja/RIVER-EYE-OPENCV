import adsk.core, adsk.fusion, traceback, math

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
        CANO_D     = 2.2                   # Canopy depth (extrude outward +X): 22mm

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
        fc = Obj(); fc.add(topFace)
        si = root.features.shellFeatures.createInput(fc, False)
        si.insideThickness = VI(WT)
        root.features.shellFeatures.add(si)

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

        # =================================================================
        # LID TOP FEATURES — cut from top face (z = LID_PLATE)
        # =================================================================
        tp = zp(root, LID_PLATE)

        # Solar cable PG7 Ø12mm — centered on lid
        cut_neg(root,
                circ(root, tp, LX+BL/2, BW/2, PG7_R),
                LID_PLATE + LID_LIP + 0.05, lidBody)

        # =================================================================
        # PG7 CABLE HOLE — right wall (x=BL), Y-center, Z-mid-height
        # Ø12mm (radius 0.6cm), cut through 3mm wall thickness
        # yp(BL): normal = +X → cut_neg = -X direction (into right wall) ✓
        # =================================================================
        cut_neg(root,
                circ_yz(root, yp(root, BL), PG7_Y, PG7_Z, PG7_R),
                WT + 0.05,
                boxBody)

        # =================================================================
        # RAIN CANOPY — upper-half crescent hood over PG7 hole
        # Profile on yp(BL) plane (right wall face, normal = +X outward)
        #   sketch_x → global_Y,  sketch_y → -global_Z
        # Crescent covers global_Z ≥ PG7_Z (upper half only)
        # Bottom is OPEN → cable enters from below
        # Extruded +X outward by CANO_D depth
        # =================================================================
        canopy_sk = root.sketches.add(yp(root, BL))
        arcs  = canopy_sk.sketchCurves.sketchArcs
        lines = canopy_sk.sketchCurves.sketchLines

        cy =  BW / 2    # sketch_x center = global_Y
        cz = -PG7_Z     # sketch_y center = -global_Z

        # Outer arc: left end → CCW over top → right end  (+π = CCW viewed from +X)
        arcs.addByCenterStartSweep(
            Pt(cy, cz, 0),
            Pt(cy - CANO_RO, cz, 0),
            math.pi
        )

        # Inner arc: left end → CCW over top → right end
        arcs.addByCenterStartSweep(
            Pt(cy, cz, 0),
            Pt(cy - CANO_RI, cz, 0),
            math.pi
        )

        # Closing lines at Z=PG7_Z (horizontal centerline = the open bottom edge)
        lines.addByTwoPoints(Pt(cy - CANO_RO, cz, 0), Pt(cy - CANO_RI, cz, 0))
        lines.addByTwoPoints(Pt(cy + CANO_RI, cz, 0), Pt(cy + CANO_RO, cz, 0))

        if canopy_sk.profiles.count == 0:
            raise RuntimeError('Canopy sketch: no closed profile found.')
        canopy_prof = canopy_sk.profiles.item(0)

        # Extrude outward (+X) — joins to box body
        join_pos(root, canopy_prof, CANO_D)

        # =================================================================
        # DONE
        # =================================================================
        ui.messageBox(
            'Solar Outdoor Box selesai!\n\n'
            'SolarBox_Box   160×90×55mm  (3mm wall)\n'
            'SolarBox_Lid   160×90×13mm  (plate 5mm + lip 8mm)\n'
            '  O-ring groove 2.5×2mm, press-fit\n'
            '  PG7 Ø12mm solar cable hole (tengah lid)\n\n'
            'PG7 Ø12mm  —  right wall, center Y/Z (kabel sensor)\n'
            'Rain Canopy  —  upper-half crescent, depth 22mm\n'
            '  menutup atas dan samping, bawah TERBUKA (kabel masuk dari bawah)\n\n'
            'Hardware:\n'
            '  O-ring Ø2mm cord, ID≈148mm  ×1\n'
            '  PG7 cable gland  ×2  (wall + lid)'
        )

    except:
        if ui:
            ui.messageBox('Error:\n{}'.format(traceback.format_exc()))
