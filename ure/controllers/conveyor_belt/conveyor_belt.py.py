from controller import Robot
import sys

def to_float(s: str, default: float) -> float:
    try:
        return float(s)
    except Exception:
        return default

robot = Robot()
TIME_STEP = int(robot.getBasicTimeStep())

# Argumentos pasados por Webots (controllerArgs):
# python.exe -u conveyor_belt.py <speed> <timer>
args = sys.argv[1:]

if len(args) != 2:
    raise RuntimeError(f"Se esperaban 2 argumentos (speed, timer). Recibidos: {args}")

speed = to_float(args[0], 0.2)
timer = to_float(args[1], 0.0)  # 0 = infinito

belt_motor = robot.getDevice("belt_motor")
if belt_motor is None:
    raise RuntimeError('No se encontró el dispositivo "belt_motor".')

belt_motor.setPosition(float("inf"))
belt_motor.setVelocity(speed)

while robot.step(TIME_STEP) != -1:
    if timer > 0.0 and robot.getTime() >= timer:
        belt_motor.setVelocity(0.0)
        robot.step(TIME_STEP)
        break
