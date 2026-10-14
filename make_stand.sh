#!/bin/sh
# Export the controller-stand STLs and preview PNGs (needs OpenSCAD; PNGs need a display or xvfb-run).
set -e
cd "$(dirname "$0")"
for P in block top door pin; do openscad -q -D "PART=\"$P\"" -o "stl/stand_$P.stl" controller_stand.scad; done
R="xvfb-run -a openscad -q --imgsize=1200,1000 --colorscheme=Tomorrow --autocenter --viewall"
$R -D 'PART="desk"' --camera=0,0,0,62,0,-35,0 -o images/stand_on_desk.png controller_stand.scad
$R -D 'PART="exploded"' --camera=0,0,0,70,0,-40,0 -o images/stand_exploded.png controller_stand.scad
$R -D 'PART="assembly"' -D DOOR_OPEN=95 --camera=0,0,0,75,0,-15,0 -o images/stand_door_open.png controller_stand.scad
$R -D 'PART="top"' --camera=0,0,0,235,0,-30,0 -o images/stand_top_underside.png controller_stand.scad
$R -D 'PART="block"' --camera=0,0,0,65,0,-60,0 -o images/stand_block.png controller_stand.scad
