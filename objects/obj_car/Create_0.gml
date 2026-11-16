image_speed = 0;    // no animation, 9 frames used as a lookup table

steer_input = 0;    // target steering angle [-1 .. +1]
steer       = 0;    // actual steering angle [-1 .. +1]
steer_rate  = 4;    // how fast steer can change (units / second)

throttle = 0;       // [0 .. 1]
brake = 0;          // [0 .. 1]
handbrake = false;
shift = 0;          // pulses [-1 .. +1] one frame

pad = 0;
gamepad_set_axis_deadzone(pad, 0.15);

specs = car_specs();
spec = specs[0]             // 0 hatch, 1 coupe, 2 wedge
sprite_index = spec.sprite;

gear = 1;                   // index into spec.gears, 1 = neutral
rpm = spec.idle;
redlining = false;

brake_power = 12;           // m/s^2 at full brake, about 1.2g of raw stopping power


// -------
// chassis
// -------
grip        = 1.2;          // lateral grip on aslphat in g, scaled by other surfaces
hand_grip   = 0.35;         // rear grip bias while handbrake        
hand_power  = 4;            // drag from handbrake, m/s^2
sliding_f   = false;        // true while an axle is past its grip budget
sliding_r   = false;

var _wheelbase = spec.front_axle - spec.rear_axle;          // px
com_x = spec.rear_axle + spec.front_weight * _wheelbase;    // mass centroid, px ahead of visual centroid
axle_f = spec.front_axle - com_x;                           // axle distances from mass centroid
axle_r = spec.rear_axle - com_x;
mass_f = phy_mass * spec.front_weight;                      // kg resting on each angle
mass_r = phy_mass - mass_f;

// rotational inertia of the two axle masses, measured from sprite centre in metres
var _inertia = mass_f * sqr(spec.front_axle * M_PER_PX) + mass_r * sqr(spec.rear_axle * M_PER_PX);
physics_mass_properties(phy_mass, com_x, 0, _inertia);


// -------
// track surfaces
// -------
surfaces = surface_table();
surf_f = SURF_ASPHALT;     // surface under each axel
surf_r = SURF_ASPHALT;
if (!instance_exists(obj_track)) instance_create_layer(0, 0, "Instances", obj_track);