#macro SURF_ASPHALT 0
#macro SURF_GRASS 1
#macro SURF_GRAVEL 2

function surface_table(){
    return [
        { name: "asphalt", grip: 1.0, linear: 0.025, angular: 0.05 },
        { name: "grass", grip: 0.5, linear: 0.6, angular: 0.02 },       // slips, drags, spins
        { name: "gravel", grip: 1.2, linear: 1.5, angular: 2.0 }        // grabs, slows, resists rotation
    ];
}

// reads track masks to determine which surface is under a room position
function surface_at(_x, _y) {
    if (obj_track.mask == -1) return SURF_ASPHALT;
        
    _x = clamp(floor(_x), 0, room_width - 1);
    _y = clamp(floor(_y), 0, room_height - 1);
    
    var _alpha = buffer_peek(obj_track.mask, (_x + _y * room_width) * 4 + 3, buffer_u8);
    if (_alpha > 127) return SURF_ASPHALT;
        
    if (tilemap_get_at_pixel(obj_track.gravel_map, _x, _y) > 0) return SURF_GRAVEL;
        
    return SURF_GRASS;
}