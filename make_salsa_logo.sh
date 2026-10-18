#!/bin/sh
# Export the "Salsa" logo STLs and preview PNGs (needs OpenSCAD; PNGs need a display or xvfb-run).
set -e
cd "$(dirname "$0")"
for ST in filled open; do
  openscad -q -D 'PART="logo_only"' -D "STYLE=\"$ST\"" -o "stl/salsa_logo_$ST.stl" salsa_logo_stand.scad
  openscad -q -D 'PART="logo"' -D "STYLE=\"$ST\"" -o "stl/salsa_logo_${ST}_with_tab.stl" salsa_logo_stand.scad
done
openscad -q -D 'PART="base"' -o stl/salsa_base.stl salsa_logo_stand.scad
R="xvfb-run -a openscad -q --imgsize=1200,800 --colorscheme=Tomorrow --autocenter --viewall"
for ST in filled open; do
  $R -D 'PART="logo_only"' -D "STYLE=\"$ST\"" --camera=0,0,0,0,0,0,0 --projection=o -o "images/salsa_logo_$ST.png" salsa_logo_stand.scad
  $R -D 'PART="logo_only"' -D "STYLE=\"$ST\"" --camera=0,0,0,35,0,-25,0 -o "images/salsa_logo_${ST}_3d.png" salsa_logo_stand.scad
  $R -D 'PART="assembly"' -D "STYLE=\"$ST\"" --camera=0,0,0,80,0,-25,0 -o "images/salsa_stand_$ST.png" salsa_logo_stand.scad
done
