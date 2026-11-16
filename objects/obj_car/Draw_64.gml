var _cx = display_get_gui_width() - 110;
var _cy = display_get_gui_height() - 110;
var _r = 80;
var _dial_max = 8000;

// gear dial
draw_set_alpha(0.6);
draw_set_colour(c_black);
draw_circle(_cx, _cy, _r, false);
draw_set_alpha(1.0);

// increments every 1k rpm
draw_set_colour(c_white);
for (var _k=0; _k <= 8; _k++) {
    var _a = lerp(225, -45, _k * 0.125);
    draw_line_width(_cx + lengthdir_x(_r - 14, _a), _cy + lengthdir_y(_r -14, _a), 
                    _cx + lengthdir_x(_r - 4, _a), _cy + lengthdir_y(_r - 4, _a), 2);
}

// needle. red and jitters at the limiter
var _needle = lerp(225, -45, clamp(rpm / _dial_max, 0, 1));
draw_set_colour(c_white);
if (redlining) {
    _needle += random_range(-6, 6);
    draw_set_colour(c_red);
}
draw_line_width(_cx, _cy, _cx + lengthdir_x(_r - 10, _needle), _cy + lengthdir_y(_r -10, _needle), 4);

// gear name
var _name = (gear == 0) ? "R" : ((gear == 1) ? "N" : string(gear - 1));
draw_set_colour(c_white);
draw_set_halign(fa_center);  draw_set_valign(fa_middle);
draw_text_transformed(_cx, _cy + 38, _name, 2, 2, 0);
draw_set_halign(fa_left);    draw_set_valign(fa_top);