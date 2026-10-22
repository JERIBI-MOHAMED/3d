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

Silver ribbon loop with gold stripes holding a gold ball with a raised Africa map, on a flared foot.
Shape measured on a reference photo (all sizes in units of the ball diameter `BALL_D`, default 65 mm):
assembled it stands **~258 mm** tall, 93 mm wide. Run headless with `blender -b -P trophy_blender.py -- ./stl`
(or `pip install bpy` and `python3 trophy_blender.py -- ./stl`).

| Part | STL | Size (mm) | Print |
|---|---|---|---|
| Foot with D-shaped spigot | `trophy_base.stl` | Ø75 x 87 | upright, no supports, silver |
| Collar ring | `trophy_ring.stl` | Ø30 x 4.2 | flat, gold |
| Ribbon loop | `trophy_body.stl` | 93 x 28 x 169 | upright on the neck, no supports, **brim 8 mm**, silver |
| Ball, one piece | `trophy_ball.stl` | Ø65 | tree supports under the bottom, gold |
| Ball, split (no supports) | `trophy_ball_top.stl` + `trophy_ball_bottom.stl` | Ø65 x 33 each | flat face down, gold |

Gold stripes are raised 0.8 mm above the silver ones, so a gold paint marker (or a silk-gold
filament change at the layer where they start) gives the two-tone look.

Assembly: ring over the spigot, body onto the spigot (the flat faces the back, so the V faces front).
Split ball: glue the halves with 2 pieces of 1.75 mm filament in the alignment holes.
Slide the ball into the loop from the front, then push a 1.75 mm filament pin (~15 mm: 7 mm arm + 8 mm ball) through each
arm's outer edge into the ball and trim flush.
Fit checks: ball 0.3 mm clear of the arms everywhere (slides in from the front), pin channels straight
through both arms into 8 mm holes in the ball, spigot 0.3 mm clearance in the socket.
