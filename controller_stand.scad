// Desk-grommet controller stand with hidden cable compartment
// ---------------------------------------------------------------
// 4 printed parts (mm):
//   1. insert block  - goes INTO the desk opening, held by barbed flex clips
//   2. top stand     - sits ON the desk, plugs onto the block, holds the controller
//   3. cable door    - hinged front door of the cable compartment
//   4. hinge pin     - holds the door (or use a 2.5 mm steel rod / nail)
//
// Export one part:   openscad -D 'PART="block"' -o block.stl controller_stand.scad
// PART = block | top | door | pin | plate (all parts, one print) | assembly | exploded
//
// Frame: X = width (52), Y = depth (front = -Y, door side), Z = up.
// Assembly z = 0 is the desk surface.

PART = "assembly";
DOOR_OPEN = 0;           // door angle in the assembly views (deg)
$fn = 72;

// ---------------- global fit ----------------
CLR = 0.25;              // sliding clearance per side (block neck <-> top socket)

// ---------------- 1. insert block ----------------
BLK_X = 43.2;            // across the 44 mm opening
BLK_Y = 39.2;            // along the opening ("mounting length")
BLK_H = 50;              // total height incl. neck
BLK_WALL = 2.4;
BLK_R = 1.5;             // corner radius
NECK_H = 6;              // neck that plugs into the top part
NECK_WALL = 1.6;
BOTTOM_LIP = 2;          // inward stiffening lip at the bottom (cables still pass)
BOTTOM_LIP_H = 2;

CLIP_W = 14;             // desk clip (barbed flex tongue) width
CLIP_Z0 = 4;             // root (anchored) height from block bottom
CLIP_Z1 = 34;            // free end height
CLIP_SLIT = 1.2;
CLIP_PROUD = 1.6;        // max barb height -> 1.2 mm grip in a 44 mm opening
CLIP_TEETH = 8;

SNAP_W = 12;             // neck snap tongue width
SNAP_SLIT = 1.0;
SNAP_LEN = 12;           // tongue length from the neck top downwards
SNAP_BUMP = 0.7;         // bump height

// ---------------- 2. top stand ----------------
TOP_X = 52;
TOP_Y = 48;
TOP_H = 68;
TOP_R = 3;
BASE_H = 23;             // height of the box under the cradle

UPRIGHT_T = 7;           // thickness of each cradle wall
UPRIGHT_Y = 44;          // depth of each cradle wall
U_W = 32;                // controller slot width (DualSense lower body)
U_BOTTOM = 46;           // height of the bottom of the U slot
HORN_R = 2.5;            // rounding of the horn tips

// cable compartment
COMP_FLOOR = 6;          // compartment floor (front strip) height
COMP_BACK_Y = -10;       // y of the compartment back wall
OPEN_X = 46.6;           // door opening width  (door 46 + 2 x 0.3)
OPEN_TOP = 20.6;         // door opening top    (door 14 + clearances)

CABLES = 3;
CABLE_PITCH = 12;
KEY_D = 10;              // round part (USB-C head seat)
KEY_SLOT = 6;            // cable groove width
KEY_TOP = 19.6;          // top of the Ø10 seat
KEY_DEPTH = 5;           // pocket depth into the back wall
CABLE_MOUTH = 3.6;       // lips at the groove mouth (cable clicks in); 6 = no lips
KEY_R = 1;               // fillet at the seat/groove shoulder

// ---------------- 3. door ----------------
DOOR_L = 46;
DOOR_H = 14;
DOOR_T = 2.5;
KNUCKLE_D = 5;           // hinge tube along the bottom edge
DOOR_GAP = 0.3;          // gap under the hinge tube
LATCH_X = 18;            // latch bumps at +/- this x
LATCH_W = 4;
LATCH_H = 0.6;           // bump height (more = firmer click)
NOTCH_W = 5;             // cable exit notches in the door top edge
NOTCH_D = 4;

// ---------------- 4. hinge pin ----------------
PIN_D = 2.5;
PIN_HOLE_DOOR = 2.9;     // door spins freely
PIN_HOLE_IN = 2.7;       // entry side wall (right, +X)
PIN_HOLE_PRESS = 2.4;    // far side wall (left, -X): press fit
PIN_HEAD_D = 4.5;
PIN_HEAD_T = 1.0;

// ---------------- derived ----------------
NECK_X = BLK_X - 2 * (BLK_WALL - NECK_WALL);   // 41.6
NECK_Y = BLK_Y - 2 * (BLK_WALL - NECK_WALL);   // 37.6
IN_X = BLK_X - 2 * BLK_WALL;                   // 38.4
IN_Y = BLK_Y - 2 * BLK_WALL;                   // 34.4
BODY_H = BLK_H - NECK_H;                       // 44
SOCK_X = NECK_X + 2 * CLR;
SOCK_Y = NECK_Y + 2 * CLR;
SOCK_H = NECK_H + 0.3;
SNAP_ZC = BODY_H + NECK_H / 2;                 // bump centre height on the block

HINGE_Y = -TOP_Y / 2 + DOOR_T;                 // hinge axis (top-part frame)
HINGE_Z = COMP_FLOOR + DOOR_GAP + KNUCKLE_D / 2;
DOOR_Z0 = COMP_FLOOR + DOOR_GAP;
PIN_X0 = -TOP_X / 2 + 0.7;                     // pin tip (0.7 mm inside left face)
PIN_X1 = TOP_X / 2 - PIN_HEAD_T;               // shank end / head start
PIN_LEN = PIN_X1 - PIN_X0;

function cable_x(i) = (i - (CABLES - 1) / 2) * CABLE_PITCH;

module rrect(x, y, h, r) {
    linear_extrude(h) offset(r = r) square([x - 2 * r, y - 2 * r], center = true);
}

// profile in the (x, z) plane extruded along y
module xz_extrude(w) { rotate([90, 0, 0]) linear_extrude(w, center = true) children(); }
// profile in the (y, z) plane extruded along x
module yz_extrude(w) { rotate([90, 0, 90]) linear_extrude(w, center = true) children(); }

// =================================================================
// 1. INSERT BLOCK (printed upright, z = 0 at its bottom)
// =================================================================
module clip_teeth_profile() {           // x = outward from the wall face, y = z
    L = CLIP_Z1 - CLIP_Z0;
    e = function(z) CLIP_PROUD * (z - CLIP_Z0) / L;
    pts = concat(
        [[0, CLIP_Z0]],
        [for (k = [1 : CLIP_TEETH]) let(z = CLIP_Z0 + k * L / CLIP_TEETH)
            each [[e(z), z], [k == CLIP_TEETH ? 0 : 0.55 * e(z), z]]]
    );
    polygon(concat(pts, [[-0.5, CLIP_Z1], [-0.5, CLIP_Z0]]));   // embedded 0.5 in the wall
}

module snap_bump_profile() {
    z = SNAP_ZC;
    polygon([[-0.5, z - 1.7], [0, z - 1.7], [SNAP_BUMP, z - 0.5], [SNAP_BUMP, z + 0.1], [0, z + 1.3], [-0.5, z + 1.3]]);
}

module block() {
    difference() {
        union() {
            rrect(BLK_X, BLK_Y, BODY_H, BLK_R);
            rrect(NECK_X, NECK_Y, BLK_H, BLK_R);
            for (s = [-1, 1]) {
                // barbed desk clips
                translate([s * BLK_X / 2, 0, 0]) mirror([s < 0 ? 1 : 0, 0, 0])
                    xz_extrude(CLIP_W - 1) clip_teeth_profile();
                // neck snap bumps
                translate([s * NECK_X / 2, 0, 0]) mirror([s < 0 ? 1 : 0, 0, 0])
                    xz_extrude(SNAP_W - 2) snap_bump_profile();
            }
        }
        // through bore (open top and bottom for the cables)
        translate([0, 0, -1]) rrect(IN_X, IN_Y, BLK_H + 2, 0.6);
        for (s = [-1, 1]) {
            // U-slit freeing the desk clip tongue (anchored at the bottom)
            for (t = [-1, 1])
                translate([s * BLK_X / 2, t * (CLIP_W + CLIP_SLIT) / 2, (CLIP_Z0 + CLIP_Z1 + CLIP_SLIT) / 2])
                    cube([2 * BLK_WALL + 2 * CLIP_PROUD + 2, CLIP_SLIT, CLIP_Z1 - CLIP_Z0 + CLIP_SLIT], center = true);
            translate([s * BLK_X / 2, 0, CLIP_Z1 + CLIP_SLIT / 2])
                cube([2 * BLK_WALL + 2 * CLIP_PROUD + 2, CLIP_W + 2 * CLIP_SLIT, CLIP_SLIT], center = true);
            // slits freeing the neck snap tongue (open at the top)
            for (t = [-1, 1])
                translate([s * BLK_X / 2, t * (SNAP_W + SNAP_SLIT) / 2, BLK_H - SNAP_LEN / 2 + 0.5])
                    cube([2 * BLK_WALL + 4, SNAP_SLIT, SNAP_LEN + 1], center = true);
        }
    }
    // bottom stiffening lip
    difference() {
        rrect(IN_X + 0.2, IN_Y + 0.2, BOTTOM_LIP_H, 0.6);
        translate([0, 0, -1]) rrect(IN_X - 2 * BOTTOM_LIP, IN_Y - 2 * BOTTOM_LIP, BOTTOM_LIP_H + 2, 0.6);
    }
}

// =================================================================
// 2. TOP STAND (printed upright, z = 0 = desk surface)
// =================================================================
module upright_profile() {             // 2D in (y, z)
    offset(r = -1.5) offset(r = 1.5)    // fillet the U bottom corners
    offset(r = HORN_R) offset(r = -HORN_R)   // round the horn tips
    difference() {
        translate([-UPRIGHT_Y / 2, BASE_H - 6]) square([UPRIGHT_Y, TOP_H - BASE_H + 6]);
        translate([0, U_BOTTOM + U_W / 2]) circle(d = U_W);
        translate([-U_W / 2, U_BOTTOM + U_W / 2]) square([U_W, TOP_H]);
    }
}

module keyhole_2d(slot) {              // 2D in (x, z), centred on x = 0
    offset(r = -KEY_R) offset(r = KEY_R) union() {
        translate([0, KEY_TOP - KEY_D / 2]) circle(d = KEY_D);
        translate([-slot / 2, -1]) square([slot, KEY_TOP - KEY_D / 2 + 1]);
    }
}

module socket_groove_profile() {       // x outward from the socket wall, y = z
    polygon([[-0.1, 1.2], [0.9, 2.2], [0.9, 3.4], [-0.1, 4.6]]);
}

module top_stand() {
    difference() {
        union() {
            rrect(TOP_X, TOP_Y, BASE_H, TOP_R);
            for (s = [-1, 1])
                translate([s * (TOP_X / 2 - UPRIGHT_T / 2), 0, 0]) yz_extrude(UPRIGHT_T) upright_profile();
        }
        // socket for the block neck
        translate([0, 0, -1]) rrect(SOCK_X, SOCK_Y, SOCK_H + 1, BLK_R + CLR);
        // snap grooves (block bumps click in here)
        for (s = [-1, 1])
            translate([s * SOCK_X / 2, 0, 0]) mirror([s < 0 ? 1 : 0, 0, 0])
                xz_extrude(SOCK_Y - 2) socket_groove_profile();
        // cable compartment (open at the front for the door, open below into the block)
        translate([-OPEN_X / 2, -TOP_Y / 2 - 1, COMP_FLOOR])
            cube([OPEN_X, COMP_BACK_Y + TOP_Y / 2 + 1, OPEN_TOP - COMP_FLOOR]);
        // hinge channel for the door tube
        translate([0, HINGE_Y, HINGE_Z]) rotate([0, 90, 0])
            cylinder(r = KNUCKLE_D / 2 + 0.3, h = OPEN_X, center = true);
        // pin holes: right = entry with counterbore, left = press fit
        translate([0, HINGE_Y, HINGE_Z]) rotate([0, 90, 0]) {
            translate([0, 0, OPEN_X / 2 - 0.1]) cylinder(d = PIN_HOLE_IN, h = 10);
            translate([0, 0, PIN_X1]) cylinder(d = PIN_HEAD_D + 0.5, h = 10);
            translate([0, 0, -TOP_X / 2 - 1]) cylinder(d = PIN_HOLE_PRESS, h = TOP_X / 2 - OPEN_X / 2 + 1.1);
        }
        // latch grooves in the opening ceiling
        for (s = [-1, 1])
            translate([s * LATCH_X - (LATCH_W + 1) / 2, -TOP_Y / 2 + 0.35, OPEN_TOP - 0.1])
                cube([LATCH_W + 1, 1.8, LATCH_H + 0.1]);
        // finger scoop above the door
        translate([0, -TOP_Y / 2, OPEN_TOP]) rotate([90, 0, 0]) cylinder(r = 5, h = 7, center = true);
        // keyhole cable pockets in the back wall
        for (i = [0 : CABLES - 1]) translate([cable_x(i), 0, 0]) {
            translate([0, COMP_BACK_Y + 1.2 + KEY_DEPTH / 2, 0]) xz_extrude(KEY_DEPTH) keyhole_2d(KEY_SLOT);
            translate([0, COMP_BACK_Y + 1.2 / 2, 0]) xz_extrude(1.2 + 0.2) keyhole_2d(CABLE_MOUTH);
        }
    }
}

// =================================================================
// 3. DOOR (local frame: outer face y = 0, bottom of hinge tube z = 0)
// =================================================================
module door() {
    difference() {
        union() {
            translate([-DOOR_L / 2, 0, KNUCKLE_D / 2]) cube([DOOR_L, DOOR_T, DOOR_H - KNUCKLE_D / 2]);
            translate([0, DOOR_T, KNUCKLE_D / 2]) rotate([0, 90, 0]) cylinder(d = KNUCKLE_D, h = DOOR_L, center = true);
            // snap latch bumps on the top edge
            for (s = [-1, 1]) translate([s * LATCH_X, 0, DOOR_H]) rotate([90, 0, 90])
                linear_extrude(LATCH_W, center = true)
                    polygon([[0.35, -0.3], [0.35, 0], [0.95, LATCH_H], [1.55, LATCH_H], [2.15, 0], [2.15, -0.3]]);
        }
        translate([0, DOOR_T, KNUCKLE_D / 2]) rotate([0, 90, 0]) cylinder(d = PIN_HOLE_DOOR, h = DOOR_L + 2, center = true);
        // cable exit notches
        for (i = [0 : CABLES - 1])
            translate([cable_x(i) - NOTCH_W / 2, -1, DOOR_H - NOTCH_D]) cube([NOTCH_W, DOOR_T + 2, NOTCH_D + 1]);
        // grip line on the outer face
        translate([-8, -0.01, DOOR_H - NOTCH_D - 2.6]) cube([16, 0.5, 0.8]);
    }
}

// =================================================================
// 4. HINGE PIN (lying along x, flat on the bed)
// =================================================================
module pin_body() rotate([0, 90, 0]) union() {     // along +x from the tip
    translate([0, 0, 0.8]) cylinder(d = PIN_D, h = PIN_LEN - 0.8);
    cylinder(d1 = PIN_D - 0.6, d2 = PIN_D, h = 0.8);            // lead-in
    translate([0, 0, PIN_LEN]) cylinder(d = PIN_HEAD_D, h = PIN_HEAD_T);
}

module hinge_pin() {                    // printed lying down on a 0.25 mm flat
    fz = PIN_D / 2 - 0.25;
    translate([0, 0, fz]) difference() {
        pin_body();
        translate([-1, -5, -10 - fz]) cube([PIN_LEN + PIN_HEAD_T + 2, 10, 10]);
    }
}

// =================================================================
// placement helpers (assembled positions)
// =================================================================
module placed_block(dz = 0) translate([0, 0, -BODY_H + dz]) block();
module placed_door(open = 0, dy = 0) translate([0, -TOP_Y / 2 + dy, DOOR_Z0])
    translate([0, DOOR_T, KNUCKLE_D / 2]) rotate([open, 0, 0]) translate([0, -DOOR_T, -KNUCKLE_D / 2]) door();
module placed_pin(dx = 0) translate([PIN_X0 + dx, HINGE_Y, HINGE_Z]) pin_body();

if (PART == "block") block();
else if (PART == "top") top_stand();
else if (PART == "door") rotate([90, 0, 0]) door();          // outer face on the bed
else if (PART == "pin") hinge_pin();
else if (PART == "plate") {                                  // everything on one bed (~110 x 110 mm)
    translate([-28, 18, 0]) top_stand();
    translate([30, 18, 0]) block();
    translate([0, -22, 0]) rotate([90, 0, 0]) door();
    for (i = [0, 1]) translate([-PIN_LEN / 2, -46 - 8 * i, 0]) hinge_pin();   // 1 spare pin
}
else if (PART == "assembly") {
    color("dimgray") top_stand();
    color("gray") placed_block();
    color("steelblue") placed_door(DOOR_OPEN);
    color("silver") placed_pin();
} else if (PART == "a_block") placed_block();
else if (PART == "a_door") placed_door(DOOR_OPEN);
else if (PART == "a_pin") placed_pin();
else if (PART == "desk") {
    color("dimgray") top_stand();
    color("gray") placed_block();
    color("steelblue") placed_door(DOOR_OPEN);
    color("silver") placed_pin();
    // preview only: 19 mm desk with a 100 x 44 opening
    color("burlywood", 0.45) translate([0, 0, -19]) difference() {
        translate([-90, -60, 0]) cube([180, 160, 19]);
        translate([-22, -BLK_Y / 2 - 0.4, -1]) cube([44, 100, 21]);
    }
}
else if (PART == "exploded") {
    color("dimgray") top_stand();
    color("gray") placed_block(-35);
    color("steelblue") placed_door(0, -25);
    color("silver") placed_pin(40);
}
