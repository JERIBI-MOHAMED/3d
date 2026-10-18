#!/bin/sh
# Export the GP gift-set STLs and preview PNGs (needs OpenSCAD; PNGs need a display or xvfb-run).
# Set her name first: edit NAME in gp_gift_set.scad, or add  -D 'NAME="Dr ..."'  to the commands below.
set -e
cd "$(dirname "$0")"
for P in plaque plaque_stand pencup steth_base steth_heart; do openscad -q -D "PART=\"$P\"" -o "stl/gp_$P.stl" gp_gift_set.scad; done
R="xvfb-run -a openscad -q --imgsize=1200,900 --colorscheme=Tomorrow --autocenter --viewall"
$R -D 'PART="set"' --camera=0,0,0,60,0,-20,0 -o images/gp_set.png gp_gift_set.scad
$R -D 'PART="nameplate"' --camera=0,0,0,78,0,-10,0 -o images/gp_nameplate.png gp_gift_set.scad
$R -D 'PART="pencup"' --camera=0,0,0,75,0,-25,0 -o images/gp_pencup.png gp_gift_set.scad
$R -D 'PART="steth"' --camera=0,0,0,80,0,-25,0 -o images/gp_stethoscope_stand.png gp_gift_set.scad
