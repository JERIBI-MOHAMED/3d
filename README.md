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

# Football crest keychains, 2 colors (`keychain/make_keychain.py`)

| | CS Sfaxien (`css`) | Club Africain (`ca`) | Brand of Sacrifice, Berserk (`brand`) | Esperance S. de Tunis (`est`) |
|---|---|---|---|---|
| Colors | black base + white relief | red base + white relief | black base + **red** relief | black base + white relief |
| Size | 41.5 x 60.9 x **4.0** mm | 41.9 x 60.9 x **4.2** mm | 32.1 x 59.5 x **4.2** mm | Ø50 crest, 52.4 x 60.9 x **4.2** mm |
| Base / relief | 3.2 mm / 0.8 mm (4 layers) | 3.2 mm / 1.0 mm (5 layers, so the red does not show pink through the white) | 3.2 mm / 1.0 mm | 3.2 mm / 1.0 mm (so the black does not grey the white) |
| Source | `keychain/cs_sfaxien_logo.svg` | `keychain/club_africain_logo.svg` | rebuilt in code from a hand-drawn reference (no SVG) | `keychain/esperance_tunis_logo.ai` (Illustrator 3 vectors) |
| Preview | `images/css_keychain_preview.png` | `images/ca_keychain_preview.png` | `images/brand_keychain_preview.png` | `images/est_keychain_preview.png` |

Each keychain is a colored base with a key-ring tab (4.5 mm hole) and the crest's details raised on top in the second color. The crests sit on their shield plus a 1.2 mm outline.
The Brand is a **cut-out**: the black base follows the symbol (1.5 mm outline), so the triangles inside the diamonds are open, and the ring tab overlaps the tip of the stem for strength.
Regenerate after changing the parameters at the top of the script:
`pip install shapely trimesh svgelements manifold3d mapbox_earcut matplotlib scipy && python3 keychain/make_keychain.py [css|ca|brand|est|est_flat|moon|sleep|mafia|flame|all]`

Files in `stl/`, `<p>` = `css`, `ca`, `brand` or `est`:

| File | Use |
|---|---|
| `<p>_keychain_2color.3mf` | **Opens already in two colors**: one object with two parts whose filaments are preset for the CFS (**1 = white 1A, 2 = black 1B, 4 = red 1D**). Sync the CFS first so the filament list matches. Otherwise, **One object, two parts** (`black_base`/`red_base` + `white_relief`/`red_relief`). Load it in Creality Print and give each part its own filament. |
| `<p>_keychain_<color>_base.stl` + `<p>_keychain_<color>_relief.stl` | The same two parts as STLs. Select both, drag them in together and answer **Yes** to "load as a single object with multiple parts". |
| `<p>_keychain_single_color.stl` | Everything merged, for a one-color print or a manual filament swap. |

Logo-specific fixes:
- CS Sfaxien: the Arabic text is 0.12 mm thicker per side than in the logo. Otherwise its strokes (about 0.2 mm) would be too thin for a 0.4 mm nozzle.
- Brand of Sacrifice: the drawing is a sketch with stippling, so the symbol is rebuilt from strokes (stem, X, upper arms, lower V) measured on the drawing. The red edges get a seeded "carved" roughness: a small wobble plus chips, at most 0.35 mm deep. The strokes stay about 1.5-2 mm wide; only the pointed tips are thinner. Change `seed` in `roughen()` for a different pattern.
- Esperance: built from the Illustrator file's vector shapes, parsed directly with no tracing, so every edge is exact. It's made black and white: yellow, gold, white and skin become white; black, grey and red become black. So the red stripes show as black stripes and the red crescents merge into the black ring. **The mascot comes from the print-ready STL** `keychain/esperance_tunis_mascot_source.stl` (in inches), whose line-art is drawn for a nozzle. Its raised lines are taken at their own size, with the feet just above "1919", and printed black on the white background, so the face is light and the eyes and smile are dark. There's a 0.6 mm white gap between the hat and the middle stripe. Black gaps narrower than 0.42 mm and white lines narrower than 0.34 mm are widened, each only by what it lacks. The original bottom text is far too condensed to print at 50 mm. So "ESPERANCE SPORTIVE DE TUNIS" is re-lettered in DejaVu Sans Bold (squeezed to 63 % width) along the whole bottom of the ring, 3.1 mm tall.
- Club Africain: the shapes are layered in the same order as the SVG. The stripes are cut to the shield shape (the SVG clip path), and the 8-unit stroke around it becomes a red band. At 50 mm every detail is at least 0.3 mm wide, so nothing is thickened.

## Printing on the Creality K2 SE (Creality Print, PLA, 0.4 nozzle)

Printer profile **Creality K2 SE 0.4 nozzle**. Print flat, logo facing **up**, on the smooth or textured PEI plate. No supports and no brim.

| Setting | Value |
|---|---|
| Process | **0.20 mm Standard**: base = 16 layers, so the color change falls exactly on a layer |
| First layer | 0.20 mm, slow (default) |
| Walls | 3, Arachne wall generator, "Detect thin walls" on |
| Top / bottom layers | 5 / 4 |
| Infill | 25 % gyroid (or 100 % for a very stiff keychain) |
| Outer wall speed | ~120 mm/s (keep "Slow down for small details" on, for the letters) |
| Seam | Aligned or back |
| Ironing (optional) | Top surfaces only. Gives a smoother, glossier white face |
| Temps (generic PLA) | Nozzle 220 °C, bed 55-60 °C (or just use your filament's preset, e.g. Hyper PLA) |
| Plate capacity | About 15 keychains per plate (copy the object and auto-arrange) |

**With a CFS (multicolor):** open `<p>_keychain_2color.3mf`. Set filament 1 = the base color (black/red) and filament 2 = the relief color (white, or red for the Brand). Assign the base part to 1 and the relief part to 2. There is only one color change per plate, so leave purge at default and set the prime tower small (or turn on "flush into infill").

**Without a CFS (one spool, one swap):** slice `<p>_keychain_single_color.stl` and open the preview. Drag the layer slider to **3.40 mm**: this is the first layer that only prints the raised details, and it's the same height for all the keychains. Right-click the **+** and choose **Add pause**. Start with the base color. When the printer pauses, unload, load the relief color, purge until the white comes out clean, then resume.
Keychains that share the same two colors can go on one plate (CS Sfaxien and Esperance = black→white, Club Africain = red→white, Brand = black→red). Otherwise use separate plates, or the CFS with black, red and white.

### Esperance keychain on the K2 SE, step by step (CFS: 1A = white, 1B = black)

1. Creality Print → open `stl/est_keychain_2color.3mf`. Printer **Creality K2 SE 0.4**, process **0.20mm Standard @Creality K2 SE**.
2. Filament panel → sync from the CFS → 1A white Hyper PLA, 1B black Hyper PLA.
3. Object list → right-click `black_base` → *Change filament* → **1B (black)**; right-click `white_relief` → **1A (white)**.
4. Process changes (everything else default):
   - Quality: wall generator **Arachne**, **Detect thin walls** on, seam **Aligned**
   - Strength: **3** walls, top **5** / bottom **4** layers, infill **25 % gyroid**
   - Speed: outer wall **100 mm/s** (fine mascot lines), **Slow down for small details** on
   - Others: **Ironing → Top surfaces** (smooth white face), no supports, no brim
   - Prime tower on (automatic), flush volumes at default or higher: black → white needs a full purge
5. Slice → Preview: black up to **3.20 mm**, white only from **3.40 mm**; the mascot's eyes and the letters should show as separate lines. Send print.
6. Without the CFS: slice `stl/est_keychain_single_color.stl`, add a **pause at 3.40 mm**, start in black, swap to white at the pause.

### Esperance keychain, flat top (`est_flat`, needs the CFS)

Same design, but the surface is **completely flat**: the white is inlaid 1.0 mm deep into a full-height black body (52.4 x 60.9 x 4.2 mm). Checked: the inlay fills the pockets exactly (areas match to 0.04 mm²), and both tops are at 4.2 mm.
Files: `stl/est_flat_keychain_2color.3mf` (parts `black_body` + `white_inlay`), or the two STLs `est_flat_keychain_black_body.stl` + `est_flat_keychain_white_inlay.stl`.
The top 5 layers hold both colors, so the filament changes on every one of those layers. That needs the CFS; a single pause cannot print it.

1. Open `stl/est_flat_keychain_2color.3mf`. Printer **K2 SE 0.4**, process **0.20mm Standard**. Sync the CFS: 1A white, 1B black.
2. Right-click `black_body` → **1B (black)**; right-click `white_inlay` → **1A (white)**.
3. Same process settings as above (Arachne, detect thin walls, 3 walls, top 5 / bottom 4, 25 % gyroid, outer wall 100 mm/s), plus:
   - **Prime tower on.** About 5 layers change color, so 5–6 swaps per plate.
   - Flushing volumes: black → white at least the default. White → black can be lower.
   - **Ironing → Topmost surface**: both colors are ironed in the same plane, which gives a smooth flat face.
4. Slice → Preview: black only up to 3.20 mm. From 3.40 to 4.20 mm, each layer prints black and white side by side. Send print.
5. Tip: print several on one plate. The swaps are per layer, not per keychain, so 10 keychains cost the same purge as one.

**Filament numbers in the 3MF files.** Each part is preset to a filament number: white = 1, black = 2, red = 4. This matches the CFS loaded as 1A white, 1B black, 1D red. If your slots differ, change the part's filament in the object list, or edit `FILAMENT` in `keychain/make_keychain.py` and regenerate. STL files cannot carry color, so use the 3MF.

### Moon keychain (`moon`)

Ø50 mm moon with the sigil, 52.4 x 60.9 x 4.2 mm: 3.2 mm black base, white raised 1.0 mm. Source: `keychain/moon_logo.webp`.
The sigil is drawn inverted in the image: black strokes on the light moon, white strokes where it crosses the dark maria. So it's kept as part of the image, not redrawn. Its 0.7-0.8 mm strokes print as they are.
The moon texture is cleaned to what a 0.4 mm nozzle prints: specks under 0.45 x 0.45 mm and lines thinner than 0.37 mm (either color) are dropped.
Print exactly like the raised Esperance keychain: `stl/moon_keychain_2color.3mf` opens with `black_base` on filament 2 (black) and `white_relief` on filament 1 (white). There's one change, at 3.40 mm.

### Sleep Token keychain (`sleep`), like the mockup

Rebuilt from the mockup photo `keychain/sleep_token_reference.jpg`. **38.7 x 53.7 x 3.6 mm**, with a **2.6 mm black base** and the white raised 1.0 mm (the mockup says ~54 x ~3.5 mm).
- Sigil: traced from its left half and mirrored, so it's exactly symmetric. The right roof runs to the moon's edge like the left one.
- Moon: the left crescent is two fitted circles. The textured moon on the right is traced, with craters kept down to printable size and a 0.6 mm black halo around the sigil.
- Black base: the disc plus a rounded lobe around the hanging spikes, a 1.5 mm outline and the ring tab (4.5 mm hole).

**K2 SE + CFS (1A white, 1B black):**
1. Open `stl/sleep_keychain_2color.3mf`. It's preset with `black_base` on filament 2 (black) and `white_relief` on filament 1 (white). Sync the CFS first.
2. Process **0.20mm Standard @Creality K2 SE**: Arachne walls, "Detect thin walls" on, 3 walls, top 5 / bottom 4 layers, 15-25 % gyroid, no supports, no brim. Ironing is optional (it adds time).
3. Preview: black up to **2.60 mm**, white only from **2.80 mm**. Note the color change is lower than the other keychains (3.40 mm) because the base is thinner. That's one filament change.
4. Without the CFS: slice `stl/sleep_keychain_single_color.stl`, add a **pause at 2.80 mm**, start in black and switch to white.

### Mafia keychain (`mafia`)

Ø50 mm black disc with the gangster bust from `keychain/mafia_reference.jpg`, 52.4 x 60.9 x 4.2 mm: 3.2 mm black base, white raised 1.0 mm.
The grey parts of the picture become the white relief. The figure is centered and scaled to 90 % of the disc, so a black margin stays around it. JPEG specks under 0.45 x 0.45 mm are dropped, and lines or gaps thinner than the nozzle are widened.
Print exactly like the raised Esperance keychain: `stl/mafia_keychain_2color.3mf` is preset with `black_base` on filament 2 and `white_relief` on filament 1. There's one change, at **3.40 mm**. Without the CFS: single-color STL with a pause at 3.40 mm.

### Flame devil keychain (`flame`)

Cut-out keychain from `keychain/flame_devil_reference.jpg`, 36.6 x 59.5 x 4.2 mm. The logo is 50 mm tall and raised 1.0 mm in **red** on a 3.2 mm **black** base that follows its outline (1.5 mm border, gaps between the logo's pieces filled). The ring tab overlaps the tallest flame tip.
`stl/flame_keychain_2color.3mf` is preset with `black_base` on filament 2 (black, 1B) and `red_relief` on filament 4 (red, 1D). There's one change, at **3.40 mm**. Without the CFS: single-color STL with a pause at 3.40 mm (black → red).
