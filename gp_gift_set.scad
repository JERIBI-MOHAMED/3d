// GP (médecin généraliste) desk gift set
// ---------------------------------------------------------------
// 3 gifts, all parametric (mm):
//   1. nameplate      - flat plaque with raised name / title / ECG + slanted stand
//   2. pen cup        - round cup with a raised ECG line wrapped around it
//   3. stethoscope    - weighted tray base + post, heart on top to drape the stethoscope over
//
// Export one part:   openscad -D 'PART="plaque"' -o plaque.stl gp_gift_set.scad
// PART = plaque | plaque_stand | pencup | steth_base | steth_heart
//        nameplate | steth | set   (assembled preview views)

PART = "set";
NAME  = "Dr Prénom NOM";            // <- her name
TITLE = "Médecin Généraliste";      // or "General Practitioner"
FONT  = "Liberation Sans:style=Bold";
FONT2 = "Liberation Sans:style=Regular";

C_MAIN   = "white";                 // preview colours (main / accent filament)
C_ACCENT = "#d62828";
$fn = 72;

// ---------------- ECG trace (x 0..1, y in R-spike units) ----------------
ECG = [[0,0],[0.14,0],[0.19,0.13],[0.24,0],[0.32,0],[0.35,-0.15],[0.40,1],
       [0.45,-0.35],[0.48,0],[0.60,0],[0.68,0.22],[0.76,0],[1,0]];

function lerp(a, b, t) = a + (b - a) * t;
// split long segments so a polyline can be wrapped onto a cylinder
function resample(p, step) = concat(
    [for (i = [0:len(p) - 2]) let(a = p[i], b = p[i + 1], n = max(1, ceil(abs(b.x - a.x) / step)))
        for (j = [0:n - 1]) lerp(a, b, j / n)],
    [p[len(p) - 1]]);
// n beats of ECG mapped to x0..x1, baseline y0, spike height amp
function ecg_pts(x0, x1, y0, amp, n = 1) =
    [for (k = [0:n - 1]) for (q = ECG) [x0 + (k + q.x) * (x1 - x0) / n, y0 + q.y * amp]];

module stroke(pts, w) {
    for (i = [0:len(pts) - 2]) hull() { translate(pts[i]) circle(d = w, $fn = 16); translate(pts[i + 1]) circle(d = w, $fn = 16); }
}

// heart, tip at the origin, lobes up: width 1.71 s, height 1.56 s
module heart(s) {
    rotate(45) union() { square(s); translate([s / 2, s]) circle(d = s); translate([s, s / 2]) circle(d = s); }
}

// ======================= 1. nameplate =======================
PL_W = 170; PL_H = 64; PL_T = 4; PL_R = 6;
RELIEF = 1.2;                       // raised accent height (filament swap at PL_T)
RIM = 2.5;
NAME_SIZE = 12; TITLE_SIZE = 6.5;

ST_W = 140; ST_D = 30; ST_H = 12;   // plaque stand
LEAN = 15;                          // plaque lean-back angle
SLOT_D = 7; SLOT_CLR = 0.4;

module rounded_rect(w, h, r) { offset(r) square([w - 2 * r, h - 2 * r], center = true); }

module plaque_relief2d() {
    difference() { rounded_rect(PL_W, PL_H, PL_R); offset(-RIM) rounded_rect(PL_W, PL_H, PL_R); }
    translate([0, 15]) text(NAME, size = NAME_SIZE, font = FONT, halign = "center", valign = "center");
    translate([0, 1]) text(TITLE, size = TITLE_SIZE, font = FONT2, halign = "center", valign = "center");
    stroke(concat([[-72, -12]], ecg_pts(-62, 52, -12, 8, 2), [[60, -12]]), 1.6);
    translate([68, -17.5]) heart(6.8);
}

module plaque() {
    color(C_MAIN) linear_extrude(PL_T) rounded_rect(PL_W, PL_H, PL_R);
    color(C_ACCENT) translate([0, 0, PL_T - 0.01]) linear_extrude(RELIEF) plaque_relief2d();
}

// plaque frame: bottom edge on the slot floor, front face towards -Y, leaning back
module plaque_frame() {
    translate([0, 3, ST_H - SLOT_D]) rotate([90 - LEAN, 0, 0]) translate([0, 0, -PL_T]) children();
}

module plaque_stand() {
    color(C_MAIN) difference() {
        hull() for (x = [-1, 1], y = [-1, 1]) translate([x * (ST_W / 2 - 5), y * (ST_D / 2 - 5), 0]) {
            cylinder(r = 5, h = ST_H - 2); translate([0, 0, ST_H - 2]) cylinder(r1 = 5, r2 = 3, h = 2);
        }
        plaque_frame() translate([-PL_W, 0, -SLOT_CLR / 2]) cube([2 * PL_W, 40, PL_T + RELIEF + SLOT_CLR]);
    }
}

module nameplate() { plaque_stand(); plaque_frame() translate([0, PL_H / 2, 0]) plaque(); }

// ======================= 2. pen cup =======================
CUP_R = 36; CUP_H = 100; CUP_WALL = 2.4; CUP_FLOOR = 3;
CUP_ECG_Z = 52; CUP_ECG_AMP = 22; CUP_BEATS = 3;
CUP_FN = 160;

module pencup() {
    color(C_MAIN) difference() {
        union() {
            cylinder(r1 = CUP_R - 2, r2 = CUP_R, h = 2, $fn = CUP_FN);
            translate([0, 0, 2]) cylinder(r = CUP_R, h = CUP_H - 2, $fn = CUP_FN);
        }
        translate([0, 0, CUP_FLOOR]) cylinder(r = CUP_R - CUP_WALL, h = CUP_H, $fn = CUP_FN);
    }
    // raised ECG band, chord segments on the outer wall
    color(C_ACCENT) let(p = resample(ecg_pts(0, 360, CUP_ECG_Z, CUP_ECG_AMP, CUP_BEATS), 4))
        for (i = [0:len(p) - 2]) hull() for (q = [p[i], p[i + 1]])
            rotate([0, 0, q.x]) translate([CUP_R - 0.6, 0, q.y]) rotate([0, 90, 0]) cylinder(d = 2.6, h = 1.8, $fn = 12);
}

// ======================= 3. stethoscope stand =======================
SB_D = 110; SB_H = 10; SB_TRAY = 3;  // base with a shallow tray for the chest piece
POST_D = 22; POST_TOP = 160;         // post top height above the table
HEART_S = 52; HEART_RING = 9; HEART_T = 12;
TAB_W = 12; TAB_T = 8; TAB_L = 16; TAB_CLR = 0.4;

module steth_base() {
    color(C_MAIN) difference() {
        union() {
            cylinder(d1 = SB_D - 4, d2 = SB_D, h = 2);
            translate([0, 0, 2]) cylinder(d = SB_D, h = SB_H - 2);
            cylinder(d = POST_D, h = POST_TOP);
            translate([0, 0, SB_H - SB_TRAY]) cylinder(d1 = POST_D + 12, d2 = POST_D, h = 8);
        }
        difference() {
            translate([0, 0, SB_H - SB_TRAY]) cylinder(d = SB_D - 8, h = SB_TRAY + 1);
            cylinder(d = POST_D + 12, h = SB_H + 1);
        }
        // socket for the heart tab
        translate([-(TAB_W + TAB_CLR) / 2, HEART_T / 2 - TAB_T - TAB_CLR / 2, POST_TOP - TAB_L])
            cube([TAB_W + TAB_CLR, TAB_T + TAB_CLR, TAB_L + 1]);
    }
}

module steth_heart2d() {
    difference() { heart(HEART_S); offset(-HEART_RING) heart(HEART_S); }
    stroke(concat([[-39, 45]], ecg_pts(-30, 30, 45, 14), [[39, 45]]), 3.2);
}

// prints flat (lying on its side); tab glues into the post
module steth_heart() {
    color(C_ACCENT) {
        translate([0, 0, -HEART_T / 2]) linear_extrude(HEART_T) steth_heart2d();
        translate([-TAB_W / 2, -TAB_L, -HEART_T / 2]) cube([TAB_W, TAB_L + 6, TAB_T]);   // flush with the bed face
    }
}

module steth() { steth_base(); translate([0, 0, POST_TOP]) rotate([90, 0, 0]) steth_heart(); }

// ======================= views =======================
module desk() { color("#c8a27a") translate([-200, -110, -6]) cube([400, 230, 6]); }

if (PART == "plaque") plaque();
else if (PART == "plaque_stand") plaque_stand();
else if (PART == "pencup") pencup();
else if (PART == "steth_base") steth_base();
else if (PART == "steth_heart") translate([0, 0, HEART_T / 2]) steth_heart();
else if (PART == "nameplate") nameplate();
else if (PART == "steth") steth();
else if (PART == "set") {
    desk();
    translate([0, -55, 0]) nameplate();
    translate([-120, 40, 0]) pencup();
    translate([110, 45, 0]) steth();
}
