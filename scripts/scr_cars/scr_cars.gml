// magic numbers for unit sanity
// treat as global tuning parameters
#macro RPM_PER_SPEED 5          // engine rpm per (px/s * final gear ratio)
#macro ACCEL_PER_TORQUE 0.01   // m/s^2 per (torque * final gear ratio)
#macro M_PER_PX 0.1             // must match "pixels to meters" in the room's physics settings
#macro GRAVITY 9.8               // m/s^2

// torque curves
function car_specs(){
    return [
        {   // AWD hatch. short wheelbase, revvy, close gears
            sprite: spr_car_hatch,
            idle: 900, redline: 7500,
            //        0k  1k  2k   3k   4k   5k   6k   7k   8k      rpm
            torque: [ 70, 95, 120, 145, 175, 200, 195, 165, 100 ],
            //        R   N   1    2    3    4     5                gear
            gears: [-3.3, 0, 3.3, 2.5, 2.0, 1.6, 1.0 ],
            final_drive: 3.0,
            max_steer: 78,                          // front wheel angle at full lock, degrees
            front_axle: 12, rear_axle: -12,         // wheelbase relative to center
            front_weight: 0.58, drive_front: 0.5    // weight and drive distribution
        },
        {   // FR coupe. big midrange, short redline
            sprite: spr_car_coupe,
            idle: 800, redline: 6500,
            torque: [100, 140, 180, 205, 205, 200, 185, 155, 110 ],
            gears: [-3.2, 0, 3.0, 2.0, 1.8, 1.4, 1.0 ],
            final_drive: 4.1,
            max_steer: 65,
            front_axle: 16, rear_axle: -14,
            front_weight: 0.52, drive_front: 0
        },
        {   // MR wedge. torque rises gradually
            sprite: spr_car_wedge,
            idle: 1000, redline: 7800,
            torque: [ 60, 80, 100, 125, 150, 180, 205, 220, 205 ],
            gears:  [-3.4, 0, 3.2, 2.6, 2.2, 1.8, 1.4 ],
            final_drive: 4.1,
            max_steer: 52,
            front_axle: 17, rear_axle: -17,
            front_weight: 0.44,
            drive_front: 0
        }
    ];
}