if (mask == -1) {
    var _surf = surface_create(room_width, room_height);
    surface_set_target(_surf);
    draw_clear_alpha(c_black, 0);
    draw_tilemap(layer_tilemap_get_id(layer_get_id("Tiles_Track")), 0, 0);
    surface_reset_target();
    
    mask = buffer_create(room_width * room_height * 4, buffer_fixed, 1);
    buffer_get_surface(mask, _surf, 0);
    surface_free(_surf);
}