from controller import Robot

TIME_STEP = 64
robot = Robot()

# Init wheels
wheelsNames = ['wheel1', 'wheel2', 'wheel3', 'wheel4']
wheels = []

for name in wheelsNames:
    wheel = robot.getDevice(name)
    wheel.setPosition(float('inf'))
    wheel.setVelocity(0.0)
    wheels.append(wheel)

# The robot base should remain STATIONARY
# The arm will do all the work checking baskets
while robot.step(TIME_STEP) != -1:
    # Keep all wheels stopped
    for wheel in wheels:
        wheel.setVelocity(0.0)
