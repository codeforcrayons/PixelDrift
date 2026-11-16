draw_self();
if (keyboard_check(ord("T")) or gamepad_button_check(pad, gp_shoulderl)) {
    var _ax = lengthdir_x(1, image_angle);
    var _ay = lengthdir_y(1, image_angle);
    draw_set_colour(sliding_f ? c_red : c_lime);
    draw_circle(x + _ax * spec.front_axle, y + _ay * spec.front_axle, 4, false);
    draw_set_colour(sliding_r ? c_red : c_lime);
    draw_circle(x + _ax * spec.rear_axle,  y + _ay * spec.rear_axle,  4, false);
    draw_set_colour(c_yellow);
    draw_circle(phy_com_x, phy_com_y, 2, false);      // where Box2D thinks the mass is
    draw_set_colour(c_white);
    draw_text(x + 30, y - 30, surfaces[surf_f].name + " / " + surfaces[surf_r].name);
    draw_set_colour(c_white);
}