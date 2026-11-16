function car_parse_input(){
    // keyboard inputs
    var _steer      = keyboard_check(vk_right) - keyboard_check(vk_left);
    var _throttle   = keyboard_check(vk_up);
    var _brake      = keyboard_check(vk_down);
    var _hand       = keyboard_check(vk_space);
    var _shift      = keyboard_check_pressed(ord("X")) - keyboard_check_pressed(ord("Z"));
    
    // gamepad inputs win control if values are greater
    if (gamepad_is_connected(pad)) {
        var _stick = gamepad_axis_value(pad, gp_axislh);
        if (abs(_stick) > abs(_steer)) _steer = _stick; 
        
        _throttle   = max(_throttle, gamepad_button_value(pad, gp_shoulderrb));     // right trigger 
        _brake      = max(_brake, gamepad_button_value(pad, gp_shoulderlb));        // left trigger
        _hand       = _hand || gamepad_button_check(pad, gp_face1);                 // A 
        _shift      += gamepad_button_check_pressed(pad, gp_face3)                  // X +
                     - gamepad_button_check_pressed(pad, gp_face2);                 // B -
    }
    
    steer_input = _steer;
    throttle = _throttle;
    brake = _brake;
    handbrake = _hand;
    shift = clamp(_shift, -1, 1);
}