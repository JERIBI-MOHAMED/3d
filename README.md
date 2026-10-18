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

# GP desk gift set (`gp_gift_set.scad`)

Parametric OpenSCAD gift set for a general practitioner (médecin généraliste). Set `NAME` / `TITLE`
at the top of the file (or `-D 'NAME="Dr ..."'`), then `./make_gp_gifts.sh` re-exports STLs + previews.

| Gift | STL | Print |
|---|---|---|
| Nameplate plaque 170 x 64 x 4 (+1.2 raised name, title, ECG, heart, rim) | `gp_plaque.stl` | flat, no supports; filament swap at 4.0 mm (white -> red) |
| Nameplate stand 140 x 30 x 12, plaque leans back 15 deg | `gp_plaque_stand.stl` | flat, no supports |
| Pen cup Ø72 x 100 with raised ECG band | `gp_pencup.stl` | upright, no supports; paint the ECG (acrylic marker) or use multi-colour |
| Stethoscope stand: Ø110 tray base + Ø22 post, 160 mm | `gp_steth_base.stl` | upright, no supports, 20-30 % infill |
| Stethoscope heart (52 mm, ECG brace, glue-in tab) | `gp_steth_heart.stl` | flat, no supports; glue the tab into the post |

Fit checks (boolean): heart tab / post socket and plaque / stand slot have 0 interference.
