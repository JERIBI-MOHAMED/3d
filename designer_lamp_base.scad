// Round "puck" base for the twisted octagonal "DesignerLamp" shade (E27 ring socket)
// ---------------------------------------------------------------------------
// 4 printed parts (mm):
//   1. body    - D150 x 37 puck, 45 deg bevelled top, 41 mm socket hole (printed upside down)
//   2. cap     - 2 mm bottom cover with honeycomb vents, 4 x M3 countersunk screws, 4 rubber feet
//   3. clamp   - cable strain-relief bar, 2 x M3x16 screwed from below into the saddle
//   4. bushing - flanged centering washer: centers the shade's 45 mm hole on the socket thread
//
// The E27 ring socket (fully threaded, 2 rings) goes through the 41 mm hole: one ring
// under the top plate, then bushing + shade on top, then the second ring clamps it all.
// Socket handling (41 mm lip, ring clamp) taken from the reference part obj_7_SOLID.
//
// Export one part:   openscad -D 'PART="body"' -o body.stl designer_lamp_base.scad
// PART = body | cap | clamp | bushing | plate (all parts, one print) | assembly | exploded | section
//        a_body | a_bushing (parts in assembly position, for fit checks)
//
// Frame: Z = up, z = 0 is the underside of the body (the cap sits below it).
// The cable leaves at the back (-Y).

PART = "assembly";
$fn = 128;

// ---------------- shade (measured on DesignerLamp.3mf) ----------------
// octagon at the top of its 3 mm bottom plate, [angle deg, radius mm] (previews only)
SHADE_POLAR = [[-165.5, 60.83], [-130, 70], [-94.5, 60.83], [-40, 50],
               [14.5, 60.83], [50, 70], [85.5, 60.83], [140, 50]];
SHADE_HOLE = 45;         // hole in the shade's bottom plate
SHADE_PLATE = 3;         // shade bottom plate thickness
SHADE_H = 165;
SHADE_WALL = 0.5;
SHADE_TWIST = 2.25;      // deg per mm, clockwise going up (one turn in 160 mm)

// ---------------- 1. body ----------------
BASE_D = 150;
BASE_H = 37;             // + CAP_T = 40 total
BEVEL = 5;               // 45 deg bevel -> flat top of BASE_D - 2 * BEVEL = 140 (shade foot: 133)
WALL = 1.8;              // = 2 + 2 perimeters, no infill between them
TOP_T = 1.6;             // = 3 bottom + 5 top layers at 0.2: fully solid, no slow internal bridge layer
LIP_T = 5;               // socket boss under the plate = lip clamped by the socket rings
LIP_BOSS_D = 60;
RIBS = 6;                // stiffening ribs under the thin plate, boss -> wall
RIB_T = 1.8;
RIB_H = 6;
LIP_D = 41;              // E27 ring-socket thread (40 mm) + clearance

POST_D = 8;              // cap screw posts, fused to the wall
POST_R = BASE_D / 2 - WALL - POST_D / 2 + 0.5;
POST_ANG = [45, 135, 225, 315];
PILOT_D = 2.6;           // M3 self-tapping
PILOT_DEPTH = 14;

CABLE_D = 7;
CABLE_Z = 10;
SADDLE_W = 26;           // strain-relief block hanging from the top plate, behind the cable exit
SADDLE_T = 8.5;          // radial depth (incl. 0.5 mm into the wall)
SADDLE_BOT = CABLE_Z + CABLE_D / 2;
CLAMP_SCREW = 9;         // screw offset from the cable axis

// ---------------- 2. cap ----------------
CAP_T = 1.6;             // fully solid at 0.2 mm layers, as the top plate
CAP_CHAMFER = 1;
CSK_D = 6.5;             // M3 countersink
SCREW_D = 3.4;
FOOT_D = 10.5;           // rubber feet recess
FOOT_DEPTH = 0.8;
FOOT_R = 58;
FOOT_ANG = [0, 90, 180, 270];
VENT_R = 50;             // honeycomb vents inside this radius (saves filament, cools the socket)
VENT_HEX = 10;           // hole across flats (finger-safe, < 12 mm)
VENT_RIB = 2.4;

// ---------------- 3. clamp ----------------
CLAMP_T = 5;
CLAMP_DEPTH = 7;
GROOVE_D = 5;            // squeezes a 6-7 mm round cable
HEAD_D = 6.5;            // M3 pan head recess
HEAD_H = 2.2;

// ---------------- 4. bushing ----------------
FLANGE_D = 58;
FLANGE_T = 1.5;
SLEEVE_D = SHADE_HOLE - 0.8;   // enters the shade hole
SLEEVE_H = 2.5;                // < SHADE_PLATE so the top ring presses on the shade
BUSH_BORE = 40.6;              // on the socket thread

// ---------------- derived ----------------
Z_TOP = BASE_H;                       // top face of the body
Z_CEIL = BASE_H - TOP_T;              // underside of the top plate
Z_LIP = BASE_H - LIP_T;               // underside of the socket boss
Z_SHADE = Z_TOP + FLANGE_T;           // shade plate underside
R_IN = BASE_D / 2 - WALL;
SCREW_Y = -(R_IN - 5);                // radial position of the clamp screws (cable side)

function pt(p) = [p[1] * cos(p[0]), p[1] * sin(p[0])];
SHADE_PTS = [for (p = SHADE_POLAR) pt(p)];

// ---------------- 1. body ----------------
module body_shell() {
    cylinder(d = BASE_D, h = BASE_H - BEVEL + 0.01);
    translate([0, 0, BASE_H - BEVEL]) cylinder(d1 = BASE_D, d2 = BASE_D - 2 * BEVEL, h = BEVEL);
}

module saddle() difference() {
    translate([-SADDLE_W / 2, -R_IN - 0.5, SADDLE_BOT]) cube([SADDLE_W, SADDLE_T, Z_CEIL - SADDLE_BOT + 0.01]);
    // cable groove + pilot holes, both on the free (lower) face
    translate([0, 0, SADDLE_BOT - 1.5]) rotate([90, 0, 0]) cylinder(d = 6, h = 2 * BASE_D, center = true);
    for (s = [-1, 1]) translate([s * CLAMP_SCREW, SCREW_Y, SADDLE_BOT - 1]) cylinder(d = PILOT_D, h = 11, $fn = 24);
}

module cable_hole() translate([0, -BASE_D / 2, CABLE_Z]) rotate([-90, 0, 0]) {   // local z = inwards
    translate([0, 0, -1]) cylinder(d = CABLE_D, h = WALL + 4, $fn = 48);
    translate([0, 0, -0.01]) cylinder(d1 = CABLE_D + 2.4, d2 = CABLE_D, h = 1.21, $fn = 48);
}

module cavity(grow = 0) {
    translate([0, 0, -1]) cylinder(r = R_IN + grow, h = BASE_H - BEVEL + 1);
    translate([0, 0, BASE_H - BEVEL - 0.01])                             // follows the outer bevel
        cylinder(r1 = R_IN + grow, r2 = R_IN + grow - (Z_CEIL - BASE_H + BEVEL), h = Z_CEIL - BASE_H + BEVEL + 0.01);
}

module body() difference() {
    union() {
        difference() {
            body_shell();
            cavity();
        }
        translate([0, 0, Z_LIP]) cylinder(d = LIP_BOSS_D, h = LIP_T - TOP_T + 0.01);
        intersection() {                            // inner features stay inside the wall (bevel)
            union() {
                for (a = POST_ANG) rotate(a) translate([POST_R, 0, 0]) cylinder(d = POST_D, h = Z_CEIL + 0.01, $fn = 32);
                for (i = [0:RIBS - 1]) rotate(i * 360 / RIBS)
                    translate([LIP_BOSS_D / 2 - 1, -RIB_T / 2, Z_CEIL - RIB_H]) cube([R_IN - LIP_BOSS_D / 2 + 2, RIB_T, RIB_H + 0.01]);
                saddle();
            }
            cavity(0.5);
        }
    }
    translate([0, 0, -1]) cylinder(d = LIP_D, h = BASE_H + 2);
    translate([0, 0, Z_TOP - 0.6]) cylinder(d1 = LIP_D, d2 = LIP_D + 1.4, h = 0.61);   // vs elephant foot
    cable_hole();
    for (a = POST_ANG) rotate(a) translate([POST_R, 0, -1]) cylinder(d = PILOT_D, h = PILOT_DEPTH + 1, $fn = 24);
}

// ---------------- 2. cap (printed as modelled, bottom face on the bed) ----------------
module cap() difference() {
    hull() {
        cylinder(d = BASE_D - 2 * CAP_CHAMFER, h = 0.01);
        translate([0, 0, CAP_CHAMFER]) cylinder(d = BASE_D, h = CAP_T - CAP_CHAMFER);
    }
    for (a = POST_ANG) rotate(a) translate([POST_R, 0, -1]) {
        cylinder(d = SCREW_D, h = CAP_T + 2, $fn = 24);
        cylinder(d1 = CSK_D + 2, d2 = SCREW_D, h = 1 + (CSK_D + 2 - SCREW_D) / 2, $fn = 32);
    }
    for (a = FOOT_ANG) rotate(a) translate([FOOT_R, 0, -1]) cylinder(d = FOOT_D, h = FOOT_DEPTH + 1, $fn = 48);
    translate([0, 0, -1]) linear_extrude(CAP_T + 2) vents();
}

module vents() {                          // hex grid, only whole cells inside VENT_R
    p = VENT_HEX + VENT_RIB;
    d = VENT_HEX / cos(30);
    for (j = [-8:8], i = [-8:8]) let(c = [(i + (j % 2) / 2) * p, j * p * sin(60)])
        if (norm(c) + d / 2 <= VENT_R) translate(c) rotate(30) circle(d = d, $fn = 6);
}

// ---------------- 3. clamp (printed flat, groove up) ----------------
module clamp() difference() {
    translate([-SADDLE_W / 2, -CLAMP_DEPTH / 2, 0]) cube([SADDLE_W, CLAMP_DEPTH, CLAMP_T]);
    translate([0, 0, CLAMP_T]) rotate([90, 0, 0]) cylinder(d = GROOVE_D, h = CLAMP_DEPTH + 2, center = true);
    for (s = [-1, 1]) translate([s * CLAMP_SCREW, 0, -1]) {
        cylinder(d = SCREW_D, h = CLAMP_T + 2, $fn = 24);
        cylinder(d = HEAD_D, h = 1 + HEAD_H, $fn = 32);
    }
}
module placed_clamp(dz = 0) translate([0, SCREW_Y, CABLE_Z - CABLE_D / 2 + 1 - CLAMP_T - dz]) clamp();

// ---------------- 4. bushing (printed flange down) ----------------
module bushing() difference() {
    union() {
        cylinder(d = FLANGE_D, h = FLANGE_T);
        cylinder(d = SLEEVE_D, h = FLANGE_T + SLEEVE_H);
    }
    translate([0, 0, -1]) cylinder(d = BUSH_BORE, h = FLANGE_T + SLEEVE_H + 2);
}
module placed_bushing(dz = 0) translate([0, 0, Z_TOP + dz]) bushing();

// ---------------- reference volumes (previews only) ----------------
SHADE_COL = [1, 0.93, 0.8, 0.5];
module outline(off = 0) offset(r = off) polygon(SHADE_PTS);
module ghost_shade() translate([0, 0, Z_SHADE]) {
    linear_extrude(SHADE_PLATE) difference() { outline(); circle(d = SHADE_HOLE); }
    translate([0, 0, SHADE_PLATE]) rotate(-SHADE_PLATE * SHADE_TWIST)
        linear_extrude(SHADE_H - SHADE_PLATE, twist = (SHADE_H - SHADE_PLATE) * SHADE_TWIST, slices = 120)
            difference() { outline(); offset(delta = -SHADE_WALL) outline(); }
}
module ring(z) translate([0, 0, z]) difference() { cylinder(d = 52, h = 4); translate([0, 0, -1]) cylinder(d = 40, h = 6); }
module socket() {                                 // fully threaded E27 socket with 2 rings
    color("white") {
        translate([0, 0, 14]) cylinder(d = 40, h = Z_TOP + 26 - 14);
        ring(Z_LIP - 4.02);                                               // under the socket boss
        ring(Z_SHADE + SHADE_PLATE + 0.01);                               // on the shade
    }
    color([1, 1, 0.85, 0.6]) hull() {                                      // A60 LED bulb
        translate([0, 0, Z_TOP + 6]) cylinder(d = 27, h = 25);
        translate([0, 0, Z_TOP + 76]) sphere(d = 60);
    }
}
module cable() color("white") {
    translate([0, -BASE_D / 2 - 30, CABLE_Z]) rotate([-90, 0, 0]) cylinder(d = 6, h = 30 + WALL + SADDLE_T + 2, $fn = 24);
    hull() {
        translate([0, -R_IN + SADDLE_T + 1, CABLE_Z]) sphere(d = 6, $fn = 24);
        translate([0, 0, 12]) sphere(d = 6, $fn = 24);
    }
}

// ---------------- output ----------------
BASE_COL = "#55565c";
module print_body() translate([0, 0, Z_TOP]) rotate([180, 0, 0]) body();   // top face on the bed
if (PART == "body") print_body();
else if (PART == "cap") cap();
else if (PART == "clamp") clamp();
else if (PART == "bushing") bushing();
else if (PART == "a_body") body();
else if (PART == "a_bushing") placed_bushing();
else if (PART == "plate") {                                  // 310 x 238 mm, fits the K2 Pro bed (350 x 350)
    translate([-80, 0, 0]) print_body();
    translate([80, 0, 0]) cap();
    translate([0, 100, 0]) clamp();
    translate([0, -105, 0]) bushing();
}
else if (PART == "assembly") {
    color(BASE_COL) { body(); translate([0, 0, -CAP_T]) cap(); placed_clamp(); }
    color("#e8e2d6") placed_bushing();
    socket();
    cable();
    color(SHADE_COL) ghost_shade();
}
else if (PART == "exploded") {
    color(BASE_COL) { body(); translate([0, 0, -CAP_T - 40]) cap(); placed_clamp(25); }
    color("#e8e2d6") placed_bushing(30);
    translate([0, 0, 60]) socket();
    color(SHADE_COL) translate([0, 0, 95]) ghost_shade();
}
else if (PART == "section") {             // printed parts cut through the socket axis and the cable exit
    difference() {
        union() {
            color(BASE_COL) { body(); translate([0, 0, -CAP_T]) cap(); placed_clamp(); }
            color("#e8e2d6") placed_bushing();
            color(SHADE_COL) intersection() { ghost_shade(); cylinder(r = 90, h = Z_SHADE + 30); }
        }
        translate([0, -200, -10]) cube([200, 400, 400]);
    }
    socket();
    cable();
}
