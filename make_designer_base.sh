#!/bin/sh
# Export the DesignerLamp base STLs and preview PNGs (needs OpenSCAD; PNGs need a display or xvfb-run).
set -e
cd "$(dirname "$0")"
for P in body cap clamp plate; do openscad -q -D "PART=\"$P\"" -o "stl/designer_base_$P.stl" designer_lamp_base.scad; done
R="xvfb-run -a openscad -q --imgsize=1200,1000 --colorscheme=Tomorrow --autocenter --viewall"
$R -D 'PART="assembly"' --camera=0,0,0,62,0,-30,0 -o images/designer_base_assembly.png designer_lamp_base.scad
$R -D 'PART="exploded"' --camera=0,0,0,70,0,-30,0 -o images/designer_base_exploded.png designer_lamp_base.scad
$R -D 'PART="section"' --camera=0,0,0,80,0,110,0 -o images/designer_base_section.png designer_lamp_base.scad
$R -D 'PART="body"' --camera=0,0,0,50,0,-30,0 -o images/designer_base_body.png designer_lamp_base.scad
$R -D 'PART="body"' --camera=0,0,0,235,0,-20,0 -o images/designer_base_body_underside.png designer_lamp_base.scad
$R -D 'PART="cap"' --camera=0,0,0,200,0,-20,0 -o images/designer_base_cap_underside.png designer_lamp_base.scad
