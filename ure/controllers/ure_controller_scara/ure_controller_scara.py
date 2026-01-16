from controller import Robot
import numpy as np

TIME_STEP = 32

WAITING, GRASPING, ROTATING, RELEASING, ROTATING_BACK = range(5)

robot = Robot()

counter = 0
state = WAITING
target_positions = [-1.88, -2.14, -2.38, -1.51]
speed = 1.0

# Hand motors
hand_motors = [robot.getDevice(f"finger_{i+1}_joint_1") for i in range(3)]
ur_motors = [
    robot.getDevice("shoulder_lift_joint"),
    robot.getDevice("elbow_joint"),
    robot.getDevice("wrist_1_joint"),
    robot.getDevice("wrist_2_joint")
]

for motor in ur_motors:
    motor.setVelocity(speed)

# Sensores DISTANCIA + CAMARA
distance_sensor = robot.getDevice("distance sensor")
distance_sensor.enable(TIME_STEP)

position_sensor = robot.getDevice("wrist_1_joint_sensor")
position_sensor.enable(TIME_STEP)

#  CAMARA para color
camera = robot.getDevice("color_sensor")
camera.enable(TIME_STEP)
camera.recognitionEnable(TIME_STEP)

print(" Brazo BLANCO - Solo agarra BLANCAS")

def is_white_can():
    """Detecta si la lata es BLANCA (HSV thresholds)"""
    image = camera.getImage()
    if image is None:
        return False
    
    # Extraer imagen RGB
    width = camera.getWidth()
    height = camera.getHeight()
    img_array = np.frombuffer(image, np.uint8).reshape((height, width, 4))
    rgb = img_array[:,:,0:3]
    
    # Promedio RGB - BLANCA si muy clara
    avg_color = np.mean(rgb, axis=(0,1))
    brightness = np.mean(avg_color)
    
    print(f"Color detectado: R={avg_color[0]:.1f} G={avg_color[1]:.1f} B={avg_color[2]:.1f} Brillo={brightness:.1f}")
    
    return brightness > 180  # ← BLANCA (ajusta según el color de las cajas)

while robot.step(TIME_STEP) != -1:
    if counter <= 0:
        if state == WAITING:
            if distance_sensor.getValue() < 500:
                #  SOLO agarra si es BLANCA
                if is_white_can():
                    state = GRASPING
                    counter = 8
                    print(" BLANCA detectada - Grasping")
                    for m in hand_motors:
                        m.setPosition(0.85)
                else:
                    print(" NEGRA detectada - Dejo pasar para brazo NEGRO")
                    # Se queda esperando la siguiente

        # ... resto de estados IGUALES al código anterior
        elif state == GRASPING:
            for i in range(4):
                ur_motors[i].setPosition(target_positions[i])
            print("Rotating arm")
            state = ROTATING

        elif state == ROTATING:
            if position_sensor.getValue() < -2.3:
                counter = 8
                print("Releasing can")
                state = RELEASING
                for m in hand_motors:
                    min_pos = m.getMinPosition()
                    m.setPosition(max(0.0, min_pos))

        elif state == RELEASING:
            for m in ur_motors:
                m.setPosition(0.0)
            print("Rotating arm back")
            state = ROTATING_BACK

        elif state == ROTATING_BACK:
            if position_sensor.getValue() > -0.1:
                state = WAITING
                print("Waiting can")

    counter -= 1
