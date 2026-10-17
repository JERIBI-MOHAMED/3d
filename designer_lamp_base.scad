// Electrical base for the twisted octagonal "DesignerLamp" shade (E27 ring socket)
// ---------------------------------------------------------------------------
// 3 printed parts (mm):
//   1. body   - octagonal hollow base + socket neck (lip with a 41 mm hole)
//   2. cap    - bottom cover, 4 x M3 countersunk screws, 4 rubber feet
//   3. clamp  - cable strain-relief bar (2 x M3x16 screwed from below through the saddle)
//
// The E27 ring socket goes up through the 41 mm lip from below, the shade's
// 45 mm bottom hole drops over the socket thread and the centering ring, and the
// socket ring is screwed on top: it clamps lip + shade plate together.
// Neck geometry (71 shoulder / 65 neck / 57 bore / 41 lip) and the sloped, support-free
// cavity ceiling are taken from the reference part obj_7_SOLID.
//
// Export one part:   openscad -D 'PART="body"' -o body.stl designer_lamp_base.scad
// PART = body | cap | clamp | plate (all parts, one print) | assembly | exploded | section
//
// Frame: Z = up, z = 0 is the underside of the body (the cap sits below it).

PART = "assembly";
$fn = 96;

// ---------------- shade (measured on DesignerLamp.3mf) ----------------
// octagon at the top of its 3 mm bottom plate, [angle deg, radius mm]
SHADE_POLAR = [[-165.5, 60.83], [-130, 70], [-94.5, 60.83], [-40, 50],
               [14.5, 60.83], [50, 70], [85.5, 60.83], [140, 50]];
SHADE_HOLE = 45;         // hole in the shade's bottom plate
SHADE_PLATE = 3;         // shade bottom plate thickness
SHADE_H = 165;           // total shade height
SHADE_WALL = 0.5;
SHADE_TWIST = 2.25;      // deg per mm, clockwise going up (one turn in 160 mm)

// ---------------- 1. body ----------------
MARGIN = 6;              // body outline = shade outline + MARGIN
BASE_H = 45;
WALL = 3;
TOP_T = 4;               // top plate around the bore
TOP_CHAMFER = 2;
CEIL_Z0 = 14;            // straight inner walls up to here, then a sloped ceiling up to the bore

SHOULDER_D = 71;         // neck, from the reference part
SHOULDER_H = 2;
SHOULDER_CH = 3;         // 45 deg chamfer 71 -> 65
NECK_D0 = 65;            // neck at its base
NECK_D1 = 61;            // neck at its top
NECK_TAPER = 9;          // 65 -> 61 over the last 9 mm, as on the reference
NECK_H = 20;             // body top -> neck top (= where the shade plate sits)
BORE_D = 57;             // room for the socket body and wires
SEAT_D = 47;             // 45 deg cone 57 -> 47, then flat seat for the socket shoulder
LIP_D = 41;              // E27 ring-socket thread (40 mm) + clearance
LIP_T = 5;               // lip + shade plate = 8 mm clamped by the socket ring
RING_D = SHADE_HOLE - 0.8;   // centering ring that enters the shade hole
RING_H = 2.5;            // < SHADE_PLATE so the socket ring presses on the shade

POST_D = 8;              // cap screw posts (vertices 1, 3, 5, 7)
POST_INSET = 1;          // post centre = vertex radius - POST_INSET
PILOT_D = 2.6;           // M3 self-tapping
PILOT_DEPTH = 14;

CABLE_EDGE = 2;          // outline edge (vertex i -> i+1) that gets the cable exit
CABLE_D = 7;
CABLE_Z = 10;
SADDLE_W = 26;           // strain-relief saddle along the wall
SADDLE_T = 8;            // saddle depth (away from the wall)
SADDLE_GAP = -0.5;       // saddle fused to the wall (slight overlap)
CLAMP_SCREW = 9;         // screw offset from the saddle centre

// ---------------- 2. cap ----------------
CAP_T = 3;
CAP_CHAMFER = 1.2;
CSK_D = 6.5;             // M3 countersink
SCREW_D = 3.4;
FOOT_D = 10.5;           // rubber feet recess (vertices 0, 2, 4, 6)
FOOT_DEPTH = 1.5;
FOOT_INSET = 3;

// ---------------- 3. clamp ----------------
CLAMP_T = 5;
HEAD_D = 6.5;            // M3 pan head recess under the saddle
HEAD_H = 2.2;
GROOVE_D = 5;            // squeezes a 6-7 mm round cable
CLAMP_DEPTH = SADDLE_T + SADDLE_GAP - 1;   // stops 0.5 mm short of the wall

// ---------------- derived ----------------
Z_TOP = BASE_H + NECK_H;              // neck top, shade plate underside
Z_LIP = Z_TOP - LIP_T;                // underside of the lip (socket seat)
Z_CONE = Z_LIP - (BORE_D - SEAT_D) / 2;
Z_CEIL = BASE_H - TOP_T;              // cavity ceiling

function pt(p) = [p[1] * cos(p[0]), p[1] * sin(p[0])];
SHADE_PTS = [for (p = SHADE_POLAR) pt(p)];
function vtx(i, dr = 0) = pt([SHADE_POLAR[i][0], SHADE_POLAR[i][1] + dr]);

E0 = SHADE_PTS[CABLE_EDGE];
E1 = SHADE_PTS[(CABLE_EDGE + 1) % 8];
EDGE_MID = (E0 + E1) / 2;
EDGE_DIR = (E1 - E0) / norm(E1 - E0);
EDGE_N = [EDGE_DIR[1], -EDGE_DIR[0]];               // outward (CCW polygon)
EDGE_ANG = atan2(EDGE_N[1], EDGE_N[0]);
WALL_IN = EDGE_MID + EDGE_N * (MARGIN - WALL);      // inner face of the wall
SADDLE_C = WALL_IN - EDGE_N * (SADDLE_GAP + SADDLE_T / 2);
SADDLE_TOP = CABLE_Z - CABLE_D / 2;

POSTS = [for (i = [1, 3, 5, 7]) vtx(i, -POST_INSET)];
FEET = [for (i = [0, 2, 4, 6]) vtx(i, -FOOT_INSET)];

// ---------------- helpers ----------------
module outline(off = 0) offset(r = off) polygon(SHADE_PTS);
module slab(off, z0, z1) translate([0, 0, z0]) linear_extrude(z1 - z0) outline(off);
// along the cable edge: x = along the wall, y = outward normal
module at_edge(c, z = 0) translate([c[0], c[1], z]) rotate(EDGE_ANG - 90) children();

// ---------------- 1. body ----------------
module body_shell() hull() {
    slab(MARGIN, 0, BASE_H - TOP_CHAMFER);
    slab(MARGIN - TOP_CHAMFER, BASE_H - 0.01, BASE_H);
}

module neck_outer() {
    translate([0, 0, BASE_H - 0.01]) {
        cylinder(d = SHOULDER_D, h = SHOULDER_H + 0.01);
        translate([0, 0, SHOULDER_H]) cylinder(d1 = SHOULDER_D, d2 = NECK_D0, h = SHOULDER_CH);
        cylinder(d = NECK_D0, h = NECK_H - NECK_TAPER + 0.01);
        translate([0, 0, NECK_H - NECK_TAPER]) cylinder(d1 = NECK_D0, d2 = NECK_D1, h = NECK_TAPER + 0.01);
    }
    // centering ring for the shade hole
    translate([0, 0, Z_TOP - 0.01]) cylinder(d = RING_D, h = RING_H + 0.01);
}

module neck_inner() {
    translate([0, 0, Z_CEIL - 1]) cylinder(d = BORE_D, h = Z_CONE - Z_CEIL + 1.01);
    translate([0, 0, Z_CONE]) cylinder(d1 = BORE_D, d2 = SEAT_D, h = Z_LIP - Z_CONE);
    translate([0, 0, Z_LIP - 1]) cylinder(d = LIP_D, h = LIP_T + RING_H + 2);
    translate([0, 0, Z_TOP + RING_H - 0.6]) cylinder(d1 = LIP_D, d2 = LIP_D + 1.4, h = 0.61);
}

module saddle() at_edge(SADDLE_C) difference() {
    translate([-SADDLE_W / 2, -SADDLE_T / 2, 0]) cube([SADDLE_W, SADDLE_T, SADDLE_TOP]);
    // shallow cable groove + screw holes, screwed from below with the cap off
    translate([0, 0, SADDLE_TOP + 1.5]) rotate([90, 0, 0]) cylinder(d = 6, h = SADDLE_T + 2, center = true);
    for (s = [-1, 1]) translate([s * CLAMP_SCREW, 0, -1]) {
        cylinder(d = SCREW_D, h = SADDLE_TOP + 2, $fn = 24);
        cylinder(d = HEAD_D, h = 1 + HEAD_H, $fn = 32);
    }
}

module cable_hole() at_edge(EDGE_MID + EDGE_N * MARGIN, CABLE_Z) rotate([90, 0, 0]) {   // local z = inwards
    translate([0, 0, -1]) cylinder(d = CABLE_D, h = WALL + 10);
    translate([0, 0, -0.01]) cylinder(d1 = CABLE_D + 2.4, d2 = CABLE_D, h = 1.21);
}

module cavity() hull() {
    slab(MARGIN - WALL, -1, CEIL_Z0);
    translate([0, 0, Z_CEIL]) cylinder(d = BORE_D, h = 0.01);
}

module body() difference() {
    union() {
        difference() {
            body_shell();
            cavity();
        }
        neck_outer();
        for (p = POSTS) translate(p) cylinder(d = POST_D, h = Z_CEIL + 0.01, $fn = 32);
        saddle();
    }
    neck_inner();
    cable_hole();
    for (p = POSTS) translate([p[0], p[1], -1]) cylinder(d = PILOT_D, h = PILOT_DEPTH + 1, $fn = 24);
}

// ---------------- 2. cap (printed as modelled, bottom face on the bed) ----------------
module cap() difference() {
    hull() {
        slab(MARGIN - CAP_CHAMFER, 0, 0.01);
        slab(MARGIN, CAP_CHAMFER, CAP_T);
    }
    for (p = POSTS) translate([p[0], p[1], -1]) {
        cylinder(d = SCREW_D, h = CAP_T + 2, $fn = 24);
        cylinder(d1 = CSK_D + 2, d2 = SCREW_D, h = 1 + (CSK_D + 2 - SCREW_D) / 2, $fn = 32);
    }
    for (p = FEET) translate([p[0], p[1], -1]) cylinder(d = FOOT_D, h = FOOT_DEPTH + 1, $fn = 48);
}

// ---------------- 3. clamp (printed flat, groove up) ----------------
module clamp() difference() {
    translate([-SADDLE_W / 2, -CLAMP_DEPTH / 2, 0]) cube([SADDLE_W, CLAMP_DEPTH, CLAMP_T]);
    translate([0, 0, CLAMP_T]) rotate([90, 0, 0]) cylinder(d = GROOVE_D, h = CLAMP_DEPTH + 2, center = true);
    for (s = [-1, 1]) translate([s * CLAMP_SCREW, 0, -1]) cylinder(d = PILOT_D, h = CLAMP_T + 2, $fn = 24);
}

// ---------------- reference volumes (previews only) ----------------
SHADE_COL = [0.34, 0.87, 0.24, 0.45];
module ghost_shade() translate([0, 0, Z_TOP]) {
    linear_extrude(SHADE_PLATE) difference() { outline(); circle(d = SHADE_HOLE); }
    translate([0, 0, SHADE_PLATE]) rotate(-SHADE_PLATE * SHADE_TWIST)
        linear_extrude(SHADE_H - SHADE_PLATE, twist = (SHADE_H - SHADE_PLATE) * SHADE_TWIST, slices = 120)
            difference() { outline(); offset(delta = -SHADE_WALL) outline(); }
}
module socket() {                                 // generic E27 ring socket
    color("white") {
        translate([0, 0, Z_LIP - 30]) cylinder(d = 40, h = 27);           // body + terminals
        translate([0, 0, Z_LIP - 3]) cylinder(d = 46, h = 3);             // shoulder on the seat
        translate([0, 0, Z_LIP]) cylinder(d = 39.6, h = 22);              // threaded sleeve
        translate([0, 0, Z_TOP + SHADE_PLATE]) difference() {             // ring
            cylinder(d = 52, h = 4); translate([0, 0, -1]) cylinder(d = 40, h = 6);
        }
    }
    color([1, 1, 0.85, 0.6]) hull() {                                      // A60 LED bulb
        translate([0, 0, Z_LIP + 2]) cylinder(d = 27, h = 25);
        translate([0, 0, Z_LIP + 70]) sphere(d = 60);
    }
}
module cable() color("white") {
    at_edge(EDGE_MID + EDGE_N * (MARGIN + 30), CABLE_Z - 1) rotate([90, 0, 0]) cylinder(d = 6, h = 30 + MARGIN + SADDLE_GAP + SADDLE_T);
    hull() {
        at_edge(SADDLE_C - EDGE_N * (SADDLE_T / 2), CABLE_Z - 1) sphere(d = 6);
        translate([0, 0, Z_LIP - 32]) sphere(d = 6);
    }
}
CLAMP_C = WALL_IN - EDGE_N * (0.5 + CLAMP_DEPTH / 2);
module placed_clamp(dz = 0) at_edge(CLAMP_C, SADDLE_TOP + 2 + dz) mirror([0, 0, 1]) translate([0, 0, -CLAMP_T]) clamp();

// ---------------- output ----------------
BASE_COL = "#56DF3D";
if (PART == "body") body();
else if (PART == "cap") cap();
else if (PART == "clamp") clamp();
else if (PART == "plate") {                                  // ~ 320 x 125 mm, fits the K2 Pro bed
    translate([-82, 0, 0]) body();
    translate([82, 0, 0]) cap();
    translate([0, -70, 0]) clamp();
}
else if (PART == "assembly") {
    color(BASE_COL) body();
    color(BASE_COL) translate([0, 0, -CAP_T]) cap();
    color(BASE_COL) placed_clamp();
    socket();
    cable();
    color(SHADE_COL) ghost_shade();
}
else if (PART == "exploded") {
    color(BASE_COL) body();
    color(BASE_COL) translate([0, 0, -CAP_T - 45]) cap();
    color(BASE_COL) placed_clamp(60);
    translate([0, 0, 25]) socket();
    color(SHADE_COL) translate([0, 0, 70]) ghost_shade();
}
else if (PART == "section") {             // printed parts cut through the socket axis and the cable exit
    difference() {
        union() {
            color(BASE_COL) body();
            color(BASE_COL) translate([0, 0, -CAP_T]) cap();
            color(BASE_COL) placed_clamp();
            color(SHADE_COL) intersection() { ghost_shade(); cylinder(r = 90, h = Z_TOP + 40); }
        }
        rotate(atan2(EDGE_MID[1], EDGE_MID[0])) translate([-200, 0, -10]) cube([400, 200, 400]);
    }
    socket();
    cable();
}
