from controller import Robot
import numpy as np

TIME_STEP = 32

WAITING, GRASPING, ROTATING, RELEASING, ROTATING_BACK = range(5)

robot = Robot()

# Margen pequeño para no pedir posiciones exactamente en el límite
EPS = 1e-4

counter = 0
state = WAITING
target_positions = [-1.88, -2.14, -2.38, -1.51]
speed = 1.0

# -----------------------
# Devices: gripper + UR
# -----------------------
hand_motors = [
    robot.getDevice("finger_1_joint_1"),
    robot.getDevice("finger_2_joint_1"),
    robot.getDevice("finger_middle_joint_1"),
]
for m in hand_motors:
    if m is None:
        raise RuntimeError("Falta un motor del gripper: finger_1_joint_1 / finger_2_joint_1 / finger_middle_joint_1")

ur_motors = [
    robot.getDevice("shoulder_lift_joint"),
    robot.getDevice("elbow_joint"),
    robot.getDevice("wrist_1_joint"),
    robot.getDevice("wrist_2_joint"),
]
for m in ur_motors:
    if m is None:
        raise RuntimeError("Falta un motor del UR: shoulder_lift_joint / elbow_joint / wrist_1_joint / wrist_2_joint")
    m.setVelocity(speed)

# -----------------------
# Sensors
# -----------------------
distance_sensor = robot.getDevice("distance sensor")
if distance_sensor is None:
    raise RuntimeError('No se encontró el sensor "distance sensor".')
distance_sensor.enable(TIME_STEP)

position_sensor = robot.getDevice("wrist_1_joint_sensor")
if position_sensor is None:
    raise RuntimeError('No se encontró el sensor "wrist_1_joint_sensor".')
position_sensor.enable(TIME_STEP)

camera = robot.getDevice("color_sensor")
if camera is None:
    raise RuntimeError('No se encontró la cámara "color_sensor".')
camera.enable(TIME_STEP)

print(f'[{robot.getName()}] Brazo BLANCO - Solo agarra BLANCAS (modo ROI por imagen)')

# Ignorar primeros frames 
warmup_steps = 3

def clamp_with_eps(motor, pos):
    """Limita la posición al rango permitido del motor, dejando un margen EPS."""
    mn = motor.getMinPosition()
    mx = motor.getMaxPosition()
    # Algunos motores pueden tener mx = inf, pero en grippers normalmente es finito
    if mx == float("inf"):
        return max(mn + EPS, pos)
    return max(mn + EPS, min(mx - EPS, pos))

def close_gripper():
    """Cierra el gripper a una posición objetivo, con clamp para evitar límites exactos."""
    target = 0.85
    for m in hand_motors:
        m.setPosition(clamp_with_eps(m, target))

def open_gripper():
    """Abre el gripper hasta su mínimo permitido, con margen EPS."""
    for m in hand_motors:
        m.setPosition(m.getMinPosition() + EPS)

def is_white_can():
    """
    Clasifica blanca vs negra usando:
      - buffer BGRA de Webots,
      - ROI central para reducir fondo,
      - brillo (luma) + spread (canales parecidos -> blanco).
    """
    image = camera.getImage()
    if image is None:
        return False

    w, h = camera.getWidth(), camera.getHeight()

    # Webots: BGRA
    img = np.frombuffer(image, np.uint8).reshape((h, w, 4))
    bgr = img[:, :, :3]

    # ROI central 
    x0, x1 = int(w * 0.35), int(w * 0.65)
    y0, y1 = int(h * 0.35), int(h * 0.65)
    roi = bgr[y0:y1, x0:x1, :]

    B = roi[:, :, 0].astype(np.float32)
    G = roi[:, :, 1].astype(np.float32)
    R = roi[:, :, 2].astype(np.float32)

    brightness = 0.2126 * R.mean() + 0.7152 * G.mean() + 0.0722 * B.mean()
    spread = (np.abs(R - G).mean() + np.abs(R - B).mean() + np.abs(G - B).mean()) / 3.0

    print(f"[{robot.getName()}] ROI bright={brightness:.1f} spread={spread:.1f} (R={R.mean():.1f} G={G.mean():.1f} B={B.mean():.1f})")

    # Umbrales iniciales 
    return (brightness > 150.0) and (spread < 12.0)


# -----------------------
# Main loop
# -----------------------
while robot.step(TIME_STEP) != -1:
    if warmup_steps > 0:
        warmup_steps -= 1
        continue

    if counter <= 0:
        if state == WAITING:
            if distance_sensor.getValue() < 500:
                if is_white_can():
                    state = GRASPING
                    counter = 8
                    print(f"[{robot.getName()}] BLANCA detectada - Grasping")
                    close_gripper()
                else:
                    print(f"[{robot.getName()}] NEGRA detectada - Dejo pasar")

        elif state == GRASPING:
            for i in range(4):
                ur_motors[i].setPosition(target_positions[i])
            print(f"[{robot.getName()}] Rotating arm")
            state = ROTATING

        elif state == ROTATING:
            if position_sensor.getValue() < -2.3:
                counter = 8
                print(f"[{robot.getName()}] Releasing can")
                state = RELEASING
                open_gripper()

        elif state == RELEASING:
            for m in ur_motors:
                m.setPosition(0.0)
            print(f"[{robot.getName()}] Rotating arm back")
            state = ROTATING_BACK

        elif state == ROTATING_BACK:
            if position_sensor.getValue() > -0.1:
                state = WAITING
                print(f"[{robot.getName()}] Waiting can")

    counter -= 1
