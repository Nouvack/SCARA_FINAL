from controller import Robot
import numpy as np

TIME_STEP = 32

WAITING, GRASPING, ROTATING, RELEASING, ROTATING_BACK = range(5)

robot = Robot()

# Margen para no pedir posiciones exactamente en el límite
EPS = 0.001  

counter = 0
state = WAITING
detected_color = None  

# Posiciones para cada canasta

white_basket_positions = [-1.2, -1.8, -1.3, 6 ]
black_basket_positions = [-2, -1.8, 0, 0]

speed = 1.0

# Devices: gripper + UR
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

# Sensors
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

print(f'[{robot.getName()}] Sistema de clasificación - Detecta BLANCAS y NEGRAS (modo ROI por imagen)')

# Ignorar primeros frames 
warmup_steps = 3

def clamp_with_eps(motor, pos):
    """Limita la posición al rango permitido del motor, dejando un margen EPS."""
    mn = motor.getMinPosition()
    mx = motor.getMaxPosition()
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

def detect_box_color():
    """
    Clasifica caja como blanca, negra o ninguna usando:
      - buffer BGRA de Webots,
      - ROI central para reducir fondo,
      - brillo (luma) + spread (canales parecidos -> blanco/negro).
    
    Returns:
        'white': caja blanca detectada
        'black': caja negra detectada
        None: no se detectó caja o color indeterminado
    """
    image = camera.getImage()
    if image is None:
        return None

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

    # Clasificación por umbrales
    if (brightness > 150.0) and (spread < 12.0):
        return 'white'
    elif (brightness < 80.0) and (spread < 15.0):
        return 'black'
    else:
        return None


# Main loop
while robot.step(TIME_STEP) != -1:
    if warmup_steps > 0:
        warmup_steps -= 1
        continue

    if counter <= 0:
        if state == WAITING:
            if distance_sensor.getValue() < 500:
                color = detect_box_color()
                if color == 'white':
                    detected_color = 'white'
                    state = GRASPING
                    counter = 8
                    print(f"[{robot.getName()}] BLANCA detectada - Grasping -> Canasta BLANCA")
                    close_gripper()
                elif color == 'black':
                    detected_color = 'black'
                    state = GRASPING
                    counter = 8
                    print(f"[{robot.getName()}] NEGRA detectada - Grasping -> Canasta NEGRA")
                    close_gripper()
                else:
                    print(f"[{robot.getName()}] Color indeterminado - Dejo pasar")

        elif state == GRASPING:
            # Seleccionar posiciones según el color detectado
            if detected_color == 'white':
                target_positions = white_basket_positions
            else:  # black
                target_positions = black_basket_positions
            
            for i in range(4):
                ur_motors[i].setPosition(target_positions[i])
            print(f"[{robot.getName()}] Rotating arm to {detected_color} basket")
            counter = 50  # Dar tiempo suficiente para que el brazo llegue a la canasta
            state = ROTATING

        elif state == ROTATING:
            # Esperar a que termine el movimiento (counter llegue a 0)
            print(f"[{robot.getName()}] Releasing can in {detected_color} basket")
            state = RELEASING
            open_gripper()

        elif state == RELEASING:
            counter = 15  # Esperar a que suelte la caja
            for m in ur_motors:
                m.setPosition(0.0)
            print(f"[{robot.getName()}] Rotating arm back")
            state = ROTATING_BACK

        elif state == ROTATING_BACK:
            # Esperar a que termine el movimiento de regreso
            state = WAITING
            detected_color = None
            print(f"[{robot.getName()}] Waiting can")

    counter -= 1
