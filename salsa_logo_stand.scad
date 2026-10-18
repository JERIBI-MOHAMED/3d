// "Salsa" logo desk sign - script logo standing in a name base
// ---------------------------------------------------------------
// 2 printed parts (mm):
//   1. logo  - "Salsa" in script with a swash + heart; tab at the bottom plugs into the base
//              STYLE = "filled": logo raised on a backing plate (2 colours, swap at BACK_T)
//              STYLE = "open"  : logo outline only (1 colour)
//   2. base  - block with the name / title on the front face and a slot on top
//
// Export one part:   openscad -D 'PART="logo"' -D 'STYLE="open"' -o logo.stl salsa_logo_stand.scad
// PART = logo | base | assembly | logo_only (just the logo, no tab - no base needed)

use <fonts/GreatVibes-Regular.ttf>
use <fonts/DancingScript-VF.ttf>

PART  = "assembly";
STYLE = "filled";

LOGO_TEXT = "Salsa";
LINE1     = "Dr. Salsa";             // base, line 1
LINE2     = "Médecin Généraliste";   // base, line 2
LOGO_FONT = "Great Vibes";
BASE_FONT = "Dancing Script:style=Bold";

C_DARK  = "#5c1a2e";                 // burgundy
C_LIGHT = "#cbbfa9";                 // beige
$fn = 48;

// ---------------- logo ----------------
LOGO_SIZE = 40;                      // font size -> word about 117 x 50 (before LOGO_SCALE)
LOGO_DX   = -3.5;                    // centres the word (its glyph box is offset)
BASELINE  = 7;                       // text baseline above the swash
LOGO_SCALE = 1.2;                    // whole logo -> about 176 x 66
LOGO_SHIFT = [-7, -3.2];             // centres logo + heart, swash rests on the base
THICKEN   = 0.55;                    // grows the hairlines of the script font (printable >= 1.5 mm)
LOGO_T    = 5;                       // logo / backing thickness (= tab thickness)
RELIEF    = 1.6;                     // raised logo on the backing ("filled")
BACK_GROW = 5;                       // backing margin around the logo
BACK_CLOSE = 16;                     // closes letter counters in the backing

TAB_W = 96; TAB_D = 9;               // hidden tab under the logo
CLR   = 0.4;                         // slot clearance (total)

// ---------------- base ----------------
BASE_W = 200; BASE_D = 26; BASE_H = 36;
BASE_R = 1.5;
TEXT_RELIEF = 1.2;
LINE1_SIZE = 14; LINE2_SIZE = 8;
SLOT_DEPTH = TAB_D;

// ---------------- 2D helpers ----------------
function bez(p, t) = pow(1 - t, 3) * p[0] + 3 * pow(1 - t, 2) * t * p[1] + 3 * (1 - t) * pow(t, 2) * p[2] + pow(t, 3) * p[3];

// calligraphic stroke along a cubic bezier, width w0 -> w1 -> w0
module swash(p, w0, w1, n = 40) {
    for (i = [0:n - 1]) let(t0 = i / n, t1 = (i + 1) / n) hull() {
        translate(bez(p, t0)) circle(d = w0 + (w1 - w0) * sin(180 * t0));
        translate(bez(p, t1)) circle(d = w0 + (w1 - w0) * sin(180 * t1));
    }
}

module heart(s) {   // tip at the origin, lobes up
    rotate(45) union() { square(s); translate([s / 2, s]) circle(d = s); translate([s, s / 2]) circle(d = s); }
}
module heart_outline(s, w) { difference() { heart(s); offset(-w) heart(s); } }

// visible logo, y = 0 is the top of the base
module logo2d() {
    scale(LOGO_SCALE) translate(LOGO_SHIFT) logo2d_raw();
}

module logo2d_raw() {
    offset(THICKEN) translate([LOGO_DX, BASELINE]) text(LOGO_TEXT, size = LOGO_SIZE, font = LOGO_FONT, halign = "center");
    // swash under the word: crosses the letter feet so every letter is tied together
    swash([[-66, 15], [-42, -8], [20, 16], [58, 4]], 1.4, 4.2);
    swash([[56, 4.6], [62, 2], [66, 6], [68, 12]], 1.6, 2.2, 10);
    translate([69, 11]) rotate(-12) heart_outline(7, 1.8);
}

module tab2d() { translate([-TAB_W / 2, -TAB_D]) square([TAB_W, TAB_D + 0.01]); }   // hidden in the slot

module backing2d() {
    offset(-BACK_CLOSE) offset(BACK_CLOSE + BACK_GROW) logo2d();
}

// logo lying flat (print orientation): back face on z = 0
module logo_flat(tab = true) {
    if (STYLE == "filled") {
        color(C_DARK) linear_extrude(LOGO_T) union() {
            intersection() { backing2d(); translate([-200, 0]) square(400); }   // flat bottom on the base
            if (tab) tab2d();
        }
        color(C_LIGHT) translate([0, 0, LOGO_T - 0.01]) linear_extrude(RELIEF)
            intersection() { logo2d(); translate([-200, 0]) square(400); }
    } else {
        color(C_LIGHT) linear_extrude(LOGO_T) union() {
            intersection() { logo2d(); translate([-200, 0]) square(400); }
            if (tab) tab2d();
        }
    }
}

// ---------------- base ----------------
module base() {
    difference() {
        color(C_DARK) hull() for (x = [-1, 1], y = [-1, 1], z = [0, 1])
            translate([x * (BASE_W / 2 - BASE_R), y * (BASE_D / 2 - BASE_R), BASE_R + z * (BASE_H - 2 * BASE_R)]) sphere(BASE_R, $fn = 16);
        translate([-(TAB_W + CLR) / 2, -(LOGO_T + CLR) / 2, BASE_H - SLOT_DEPTH]) cube([TAB_W + CLR, LOGO_T + CLR, SLOT_DEPTH + 1]);
    }
    // name / title raised on the front face (print the base on its back to swap colour)
    color(C_LIGHT) translate([0, -BASE_D / 2 + 0.01, 0]) rotate([90, 0, 0]) linear_extrude(TEXT_RELIEF) {
        translate([0, BASE_H * 0.6]) text(LINE1, size = LINE1_SIZE, font = BASE_FONT, halign = "center", valign = "center");
        translate([0, BASE_H * 0.24]) text(LINE2, size = LINE2_SIZE, font = BASE_FONT, halign = "center", valign = "center");
    }
}

// base printed on its back: front face (with text) up
module base_print() { translate([0, 0, BASE_D / 2]) rotate([-90, 0, 0]) base(); }

module assembly() {
    base();
    // logo standing in the slot, front face towards -Y; its tab sits on the slot floor
    translate([0, LOGO_T / 2, BASE_H - SLOT_DEPTH + TAB_D]) rotate([90, 0, 0]) logo_flat();
}

if (PART == "logo") logo_flat();
else if (PART == "logo_only") logo_flat(tab = false);
else if (PART == "base") base_print();
else if (PART == "assembly") assembly();
