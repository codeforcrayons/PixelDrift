

mask = -1;
gravel_map = layer_tilemap_get_id(layer_get_id("Tiles_Gravel"));

var _barrier_map = layer_tilemap_get_id(layer_get_id("Tiles_Barrier"));
var _size = tilemap_get_tile_width(_barrier_map);
for (var _row = 0; _row < tilemap_get_height(_barrier_map); _row++) {
    for (var _col = 0; _col < tilemap_get_width(_barrier_map); _col++) {
        if (tilemap_get(_barrier_map, _col, _row) > 0) {
            instance_create_layer(_col * _size, _row * _size, "Instances", obj_barrier);
        }
    }
}