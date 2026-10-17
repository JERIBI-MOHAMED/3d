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

# Round E27 base for the twisted octagonal "DesignerLamp" shade (`designer_lamp_base.scad`)

Parametric OpenSCAD "puck" base, D150 x 40 mm with a 45 deg bevelled top (flat top D140), for the DesignerLamp shade
(foot max D133, 3 mm bottom plate with a 45 mm hole). The socket handling comes from the reference part `obj_7_SOLID`:
an **E27 ring socket** through a 41 mm hole, with the shade clamped by the socket ring. `./make_designer_base.sh`
re-exports STLs + previews.

| Part | STL | Print |
|---|---|---|
| Body D150 x 37 (5 mm top plate, 41 mm socket hole) | `designer_base_body.stl` | exported **upside down** (top face on the bed): no supports, 3 walls, 15 % infill |
| Bottom cap D150 x 3 | `designer_base_cap.stl` | as exported (feet recesses on the bed) |
| Cable clamp 26 x 7 x 5 | `designer_base_clamp.stl` | flat, groove up |
| Centering bushing D58 / D44.2 x 4 | `designer_base_bushing.stl` | flange down |
| All parts on one bed (310 x 238, K2 Pro) | `designer_base_plate.stl` | |

Hardware: **fully threaded E27 socket with 2 rings** (40 mm thread), 2-core 0.75 mm2 cable with an inline switch and
plug, 4 x M3x10 countersunk (cap), 2 x M3x16 pan head (clamp), 4 x rubber feet 10 mm. **LED bulb only** (shade walls
0.5 mm PLA).

Assembly
1. Feed the cable in through the rear hole, lay it in the groove under the saddle, put the clamp under it (groove up)
   and screw the 2 M3x16 upwards into the saddle. The cable must not pull out (strain relief).
2. Wire the socket (brown = live, blue = neutral), screw one ring on its thread and push it **from below** through
   the 41 mm hole so that ring sits under the top plate.
3. Slide the bushing (flange down) over the thread, then the shade: its 45 mm hole centers on the bushing sleeve.
4. Screw the second ring on top: it clamps top plate (5) + bushing flange (1.5) + shade plate (3). Screw the cap on.

Fit checks (real shade mesh + OpenSCAD booleans): shade 0 interference with body and bushing and in contact
(0.1 mm lower collides), sleeve/hole clearance 0.32 mm per side, shade foot fully on the D140 top, socket 0
interference with the hole, clamp 0 interference with the wall. Printed upside down the body has no overhang
steeper than 45 deg except the 7 mm cable hole ceiling.
