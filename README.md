PixelDrift is a 2D top-down racing game made with GameMaker Studio 2. 

The physics system simulates a body with two points of contact over a surface, roughly representing the combined wheels at each axle of the car. 
Both axles can transfer linear drive from the engine, and the front axle handles lateral forces for steering.
The engine is represented as a torque curve, and the car derives torque at the wheel through a sequential 5-speed gearbox.

Three cars exist: an AWD hatch, a front-engine RWD coupe, and a mid-engine RWD wedge. 
Car specifications are stored in a table in `scr_cars.gml` and may be extended for more models: 
- RPM range
- torque curve
- gear ratios
- steering angle
- wheelbase
- weight bias 
- drive bias

Still to do:
Telemetry and scorekeeping
Sound and visual effects
Rumble feedback
GUI and menus
