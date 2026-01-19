from controller import Robot

TIME_STEP = 64
robot = Robot()

wheelsNames = ['wheel1', 'wheel2', 'wheel3', 'wheel4']
wheels = []

for name in wheelsNames:
    wheel = robot.getDevice(name)
    wheel.setPosition(float('inf'))  # rotación continua
    wheel.setVelocity(0.0)
    wheels.append(wheel)

while robot.step(TIME_STEP) != -1:
    # Lado izquierdo: wheel1 y wheel3
    leftSpeed = -1.0
    # Lado derecho: wheel2 y wheel4
    rightSpeed = -1.0

    wheels[0].setVelocity(leftSpeed)   # wheel1
    wheels[2].setVelocity(leftSpeed)   # wheel3
    wheels[1].setVelocity(rightSpeed)  # wheel2
    wheels[3].setVelocity(rightSpeed)  # wheel4
