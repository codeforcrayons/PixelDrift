car_parse_input();

// steer rate limiter
var _dt = delta_time / 1000000;     // seconds since last frame
var _max_step = steer_rate * _dt;
steer += clamp(steer_input - steer, -_max_step, _max_step);

// lookup sprite frame for steering angle
image_index = round((steer + 1) * 4);

// -------
// gearbox
// -------
gear = clamp(gear + shift, 0, array_length(spec.gears) - 1);
var _ratio = spec.gears[gear] * spec.final_drive;

// -------
// forward speed. how much of the velocity matches the heading
// -------
var _fx = lengthdir_x(1, image_angle);
var _fy = lengthdir_y(1, image_angle);
var _fwd = phy_linear_velocity_x * _fx + phy_linear_velocity_y * _fy;   // px/s

// -------
// engine speed
// -------
if (_ratio == 0) {
    // neutral. engine disconnected, revs on its own
    var _target = lerp(spec.idle, spec.redline + 300, throttle);
    rpm = lerp(rpm, _target, 0.15);
} else {
    // in gear. the wheels turn the engine as they roll
    rpm = max(spec.idle, abs(_fwd * _ratio) * RPM_PER_SPEED);
}
redlining = rpm >= spec.redline;

// -------
// torque lookup. same idea as steering frame, but lerps each sample
// -------
var _i = clamp(rpm, 0, 7999) * 0.001;
var _lo = floor(_i);
var _torque = lerp(spec.torque[_lo], spec.torque[_lo + 1], frac(_i));

// -------
// drive with rev limiter
// -------
var _drive = 0;
if (!redlining) _drive = _torque * _ratio * ACCEL_PER_TORQUE * throttle * phy_mass;

// -------
// brake reverses accel + handbrake fades to 0 with velocity to prevent overshoot/oscillation
// -------
var _brake = clamp(_fwd / 20, -1, 1) * (brake_power * brake + hand_power * handbrake) * phy_mass;

// -------
// car's motion relative to its own frame (x forward, y right)
// -------
var _lateral = phy_linear_velocity_y * _fx - phy_linear_velocity_x *_fy;    // px/s, positive = right
var _spin = degtorad(phy_angular_velocity);                                 // rad/s, positive = clockwise
var _wx = dcos(steer * spec.max_steer);                                          // the direction the front wheels are pointing
var _wy = dsin(steer * spec.max_steer);

// ------
// grip budget per axle (N). weight on the axle * grip
// ------

//surface under each axle
surf_f = surface_at(x + _fx * spec.front_axle, y + _fy * spec.front_axle);
surf_r = surface_at(x + _fx * spec.rear_axle, y + _fy * spec.rear_axle);
var _sf = surfaces[surf_f];
var _sr = surfaces[surf_r];
phy_linear_damping = (_sf.linear + _sr.linear) / 2;
phy_angular_damping = (_sf.angular + _sr.angular) / 2;

// grip budget per axle
var _cap_f = mass_f * GRAVITY * grip * _sf.grip;
var _cap_r = mass_r * GRAVITY * grip * _sr.grip;
if (handbrake) _cap_r *= hand_grip;

// drive is split between the axles. anything over budget = wheelspin, lost
var _drive_f = clamp(_drive * spec.drive_front,       -_cap_f, _cap_f);
var _drive_r = clamp(_drive * (1 - spec.drive_front), -_cap_r, _cap_r);

// friction circle. grip spent on driving is not available laterally
var _lat_f = sqrt(sqr(_cap_f) - sqr(_drive_f));
var _lat_r = sqrt(sqr(_cap_r) - sqr(_drive_r));

// -------
// lateral slip at each axle (px/s). front is measured across the steered wheel
// -------
var _slip_f = (_lateral + _spin * axle_f) * _wx - _fwd * _wy;
var _slip_r = _lateral + _spin * axle_r;

// the push that would cancel the slip in one step, limited to the budget
var _step   = 1 / game_get_speed(gamespeed_fps);
var _push_f = clamp(-_slip_f * M_PER_PX * mass_f, -_lat_f * _step, _lat_f * _step);
var _push_r = clamp(-_slip_r * M_PER_PX * mass_r, -_lat_r * _step, _lat_r * _step);
sliding_f = abs(_push_f) >= _lat_f * _step;
sliding_r = abs(_push_r) >= _lat_r * _step;

// -------
// apply. (x, 0) is a point on the car's centre line, measured from the sprite centre
// -------
physics_apply_local_impulse(spec.front_axle, 0, -_push_f * _wy, _push_f * _wx);
physics_apply_local_impulse(spec.rear_axle,  0, 0, _push_r);
physics_apply_local_force(spec.front_axle, 0, _drive_f * _wx, _drive_f * _wy);
physics_apply_local_force(spec.rear_axle,  0, _drive_r, 0);
physics_apply_local_force(com_x, 0, -_brake, 0);

// temp: reset to spawn
if (keyboard_check_pressed(ord("R")) or gamepad_button_check_pressed(pad, gp_shoulderr)) {
    phy_position_x = xstart;
    phy_position_y = ystart;
    phy_rotation = 0;
    phy_linear_velocity_x = 0;
    phy_linear_velocity_y = 0;
    phy_angular_velocity = 0;
    gear = 1;
}