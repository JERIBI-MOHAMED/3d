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

# E27 base for the twisted octagonal "DesignerLamp" shade (`designer_lamp_base.scad`)

Parametric OpenSCAD base that fits the DesignerLamp shade (140 x 100 octagon, 3 mm bottom plate with a 45 mm hole)
and holds an **E27 ring socket** (threaded sleeve 40 mm + ring). The socket neck (71 shoulder / 65 neck / 57 bore /
41 lip) and the sloped, support-free inner ceiling come from the reference part `obj_7_SOLID`.
`./make_designer_base.sh` re-exports STLs + previews.

| Part | STL | Print |
|---|---|---|
| Body 130 x 133 x 67.5 (octagon 45 mm + neck 20 mm + centering ring) | `designer_base_body.stl` | upright, no supports, 0.2 mm, 3 walls, 15 % infill |
| Bottom cap 3 mm | `designer_base_cap.stl` | as exported (feet recesses on the bed) |
| Cable clamp 26 x 6.5 x 5 | `designer_base_clamp.stl` | flat, groove up |
| All parts on one bed (294 x 140, K2 Pro) | `designer_base_plate.stl` | |

Hardware: E27 socket with outer thread + ring, 2-core 0.75 mm2 cable with an inline switch and plug,
4 x M3x10 countersunk (cap), 2 x M3x16 pan head (clamp), 4 x rubber feet 10 mm. **LED bulb only** (shade walls 0.5 mm PLA).

Assembly
1. Feed the cable in through the side hole, lay it in the saddle groove, put the clamp on top (groove down) and screw
   the 2 M3x16 from below through the saddle. The cable must not pull out (strain relief).
2. Wire the socket (brown = live, blue = neutral), push it **from below** through the 41 mm lip until its shoulder
   sits on the seat.
3. Drop the shade over the socket thread: its 45 mm hole centers on the 44.2 mm ring and the plate rests on the neck.
4. Screw the socket ring on top: it clamps lip (5 mm) + shade plate (3 mm). Screw the cap on (4 x M3).

Fit checks (real shade mesh + OpenSCAD booleans): shade on the neck 0 interference and in contact (0.1 mm lower
collides), ring/hole clearance 0.33 mm per side, socket 0 interference with the lip/seat/bore, clamp 0 interference
with the wall, neck profile matches the reference within 0.05 mm (lip kept at 5 mm instead of 9.5). Steepest
inner-ceiling overhang ~58 deg in the two long corners; enable "support on build plate only" if your printer struggles.
