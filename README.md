# Twisted textured lamp (Blender)

Run `lamp_blender.py` in Blender (Scripting tab > Open > Run Script) or headless:
`blender -b -P lamp_blender.py -- ./stl`

Parts (mm): `lamp_shade.stl`, `lamp_base.stl`, `lamp_cap.stl` (already generated in `stl/`).
All dimensions are parameters at the top of the script.

Print notes
- Shade: upright, no supports, 0.4 mm nozzle, 0.2 mm layers, 2-3 perimeters, 0% infill, white/natural PLA or PETG (translucent). Prefer a cool LED bulb (PLA softens ~60 C).
- Base: upright. Cap: flat on the bed. 4 x M3x16 screws (self-tapping in 2.6 mm pilot holes).
- E14 holder fits the 36 mm hole (set `SOCKET_HOLE` for E27). Cable exits through the side slot.
- Set `TEXTURE = False` for a light, smooth shade.

# Ribbed jar with bayonet lid (`jar_blender.py`)

Open: align the lid ribs with the lug marks, push down, turn **30 deg clockwise** to lock; reverse to open.
Mechanism checked by boolean interference tests: lid drops straight when aligned, turns freely over 30 deg,
hard stop at the end, cannot be lifted once locked. Tune `TWIST_DEG`, `CLEARANCE` for your printer.

# Desk-grommet controller stand with cable compartment (`controller_stand.scad`)

Parametric OpenSCAD model (all sizes at the top of the file). `./make_stand.sh` re-exports STLs + previews.

| Part | STL | Print |
|---|---|---|
| Insert block 43.2 x 39.2 x 50 (goes into the 44 mm desk opening) | `stand_block.stl` | upright, no supports, PETG preferred (clips flex) |
| Top stand 52 x 48 x 68 (sits on the desk, holds the controller) | `stand_top.stl` | upright, no supports (2 short bridges) |
| Cable door 46 x 14 x 2.5 | `stand_door.stl` | outer face on the bed |
| Hinge pin Ø2.5 x 50.3 + head | `stand_pin.stl` | lying on its flat, 100 % infill (print 2) |
| **All parts on one bed** (107 x 97 mm, fits any Creality) | `stand_all_in_one_plate.stl` / `.3mf` | 1 top + 1 block + 1 door + 2 pins, already oriented |

Assembly: door into the front opening, pin from the right side (head side) through wall + door tube,
press into the left wall. Snap the block's neck into the socket under the top (2 clicks), then push
the whole stand into the desk opening until the top sits on the desk; the barbed clips grip the
opening walls (any desk thickness). Cables come up through the block and park in the 3 keyhole
pockets behind the door; they exit through the door's top notches.
Fit checks (boolean): block/top 0 interference when seated, door swings freely 10-100 deg
(latch click at ~5 deg), pin press-fits only in the left wall, clips bite 1.2 mm into a 44 mm opening.

# African club trophy replica (`trophy_blender.py`)

Silver vase-shaped body whose teardrop opening is cut through it front to back; the two arms are
thick gold-striped shells that cradle a gold ball with a raised Africa map; flared silver foot.
Shape measured on a turntable video (front view: widths and opening, side view: depth), all sizes
in units of the ball diameter derived from `HEIGHT`: assembled it stands **210 mm** tall,
61 x 45 mm (ball Ø48.4). Change `HEIGHT` for another size. Run headless with
`blender -b -P trophy_blender.py -- ./stl` (or `pip install bpy` and `python3 trophy_blender.py -- ./stl`).

| Part | STL | Size (mm) | Print |
|---|---|---|---|
| Foot with D-shaped spigot | `trophy_base.stl` | Ø56 x 71 | upright, no supports, silver |
| Collar ring | `trophy_ring.stl` | Ø25.6 x 4.2 | flat, gold |
| Body, front + back halves | `trophy_body_front.stl` + `trophy_body_back.stl` | 61 x 23 x 140 each | lying flat on the cut face, no supports |
| Ball, split (no supports) | `trophy_ball_top.stl` + `trophy_ball_bottom.stl` | Ø48.4 x 25 each | flat face down, gold |
| Ball, one piece | `trophy_ball.stl` | Ø48.4 | tree supports under the bottom, gold |
| Whole body (reference) | `trophy_body.stl` | 61 x 45 x 140 | not for printing: the ball can't go in |

Gold stripes are raised 0.8 mm above the silver ones, so a gold paint marker (or the two-colour
plate below) gives the two-tone look.

Assembly: glue the ball halves (2 pieces of 1.75 mm filament in the alignment holes). Put 5 pieces
of 1.75 mm filament, 7 mm long, in the back half's alignment holes, lay the ball in the back half's
seats (the Africa map facing front and up), glue the front half on (CA or epoxy) - the opening is
narrower than the ball, so the ball is held for good. Then ring over the spigot and the body onto
the spigot (the flat faces the back, so the V faces front).
Fit checks: ball 0.3 mm clear of its seats, the Africa relief 4 mm clear of the arms, the opening
22.3 mm half-width above and below the ball (radius 24.2) so it can't fall out, the ball lays into
the back half without touching it, ≥ 9.5 mm of material above every alignment hole, spigot 0.3 mm
clearance in the socket.

## Creality K2 SE project (`stl/trophy_k2se.3mf`)

Open in **Creality Print 6 or 7** (File > Open project, accept loading the project settings).
Printer `Creality K2 SE 0.4 nozzle`, process `0.16mm Standard`, filament 1 = **silver silk**,
filament 2 = **gold silk** (`CR-Silk` profile, 220 °C nozzle / 60 °C bed). Load them in CFS slots 1 and 2.

| Plate | Parts | Filament |
|---|---|---|
| 1 | ball top + ball bottom (flat side down, 0.12 mm layers) + ring | gold |
| 2 | base + body halves (stripes painted afterwards with a gold paint pen) | silver |
| 3 | body halves with the gold stripes printed (CFS) | silver + gold |

Settings changed from the K2 SE system preset (marked as changed, so they survive loading):
3 walls (Arachne), gyroid 15 %, outer wall 120 mm/s (silk shine), seam at the back,
hole compensation +0.1 mm (pin and ring fits), purge into infill. No supports anywhere.

Print the body halves of plate 2 (silver, then a gold paint pen) or of plate 3, not both.
Plate 3 needs ~140 filament changes (the curved arms carry gold on every layer of the halves),
about 11 h of changes and ~90 g of purge at the K2 SE's 135 s per change.
`k2se_3mf.py` writes the project; `k2se_settings.json` is the K2 SE system profile flattened from
Creality Print's official profiles.
