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

# Hand on a thin stick with a twist lock (`sign/make_twist_lock.py`)

`sign/twist_lock.3mf` (Creality K2 SE project, both parts on one plate) / `sign/stick.stl`: the original hand
(35 mm, scale 0.35) gets a round cuff under the wrist with a socket, and a separate 6 mm stick has two lugs at its top
(preview: `images/twist_lock_preview.png`). Regenerate with `python3 sign/make_twist_lock.py original_hand.3mf sign`
(it also writes `hand_socket.stl`, 66 MB, not committed). Needs `pip install manifold3d trimesh pymeshfix`.

- Assembly: push the stick into the cuff with the lugs in the two slots, then turn it **~90 deg** (counter-clockwise
  looking down on the hand) until it clicks over the bump. Turn back to take it apart.
- Hand 18.5 x 15.4 x 41 mm, printed upright on the cuff (tree supports for the fingers, 4 mm brim). The socket itself
  needs no supports (45 deg ceilings).
- Stick 6 mm x 130 mm (120 mm visible), printed lying down on its flat side, no supports.
- Fit checks (boolean): 0 interference sliding in and at 90 deg; the lug rides over the 0.25 mm bump between ~35 and
  65 deg (the click); it stops at ~93 deg and cannot be pulled out when locked. 0.2 mm clearance; if it is too tight on
  your printer, raise `CLEAR` (or `DETENT_IN` for a softer click).

# Stop sign paddle with the hand (`sign/make_stop_sign.py`)

`sign/stop_sign.3mf` (Creality K2 SE project) / `sign/stop_sign.stl`: a red octagon stop sign with a white border, the
middle-finger hand in white relief where "STOP" would be, and a handle (preview: `images/stop_sign_preview.png`).
Regenerate with `python3 sign/make_stop_sign.py original_hand.3mf sign` (sizes at the top of the script).

- Sign 130 mm flat to flat, 5 mm plate, border and hand raised up to 6 mm. Handle 22 x 11 mm, 100 mm long, with a wide
  neck into the sign. Whole paddle 210 x 206 mm on the bed (turned 46 deg to fit), 11 mm tall. No supports needed.
- Print flat as placed (back of the sign on the bed). Load **red**; the 3MF already has a **colour change at 5.2 mm**,
  where the printer pauses so you swap to **white** for the border and the hand. The handle's top half also comes out
  white. In the preview, check that the colour change is on the layer right above the red plate.
