from controller import Robot
import math

TIME_STEP = 32

# Máquina de estados simple para: observar -> buscar (scan) -> recoger -> dejar -> volver
BOOT, IDLE, OBSERVE, SCAN, PICK_WHITE, PICK_BLACK, MOVE_SHELF, PLACE_SHELF, RETURN_HOME = range(9)

robot = Robot()
state = BOOT
counter = 0
items_placed = 0

# Velocidades: arranque suave y luego normal
BOOT_SPEED = 0.35
RUN_SPEED  = 0.90

# Motores del UR (6 GDL) + motores de la pinza
motor_names = [
    "shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
    "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"
]
ur_motors = [robot.getDevice(n) for n in motor_names]

hand_motors = [
    robot.getDevice("finger_1_joint_1"),
    robot.getDevice("finger_2_joint_1"),
    robot.getDevice("finger_middle_joint_1"),
]

def set_all_speeds(v):
    """Fija la velocidad de todos los motores del brazo y la pinza."""
    for m in ur_motors:
        if m:
            m.setVelocity(v)
    for m in hand_motors:
        if m:
            m.setVelocity(v)

set_all_speeds(BOOT_SPEED)

# Poses (6 ejes)
# OBS_LIFT es el que más afecta a la "altura" del brazo (más negativo = más bajo en la mayoría de setups)
OBS_LIFT  = -1.55
OBS_ELBOW =  1.50
OBS_WR1   = -1.50

home_position = [0.0, -1.57, 0.0, -1.57, 0.0, 0.0]

# Pose de observación: baja y con la muñeca inclinada para ver la zona de cajas
observe_pose = [
    0.0,      
    OBS_LIFT,   
    OBS_ELBOW,  
    OBS_WR1,    
    -1.57,     
]

# Poses de pick 
white_pick_position = [-0.2, OBS_LIFT - 0.15, 1.35, OBS_WR1, -1.57, 0.0]
black_pick_position = [ 0.2, OBS_LIFT - 0.15, 1.35, OBS_WR1, -1.57, 0.0]

# Poses del estante / destino (se alternan en ciclo)
shelf_positions = [
    [3.14, -1.5, 1.0, -1.0, -1.57, 0.0],
    [3.14, -1.3, 0.8, -1.1, -1.57, 0.0],
    [3.14, -1.7, 1.2, -0.9, -1.57, 0.0],
]

# Barrido 360°
SCAN_PANS = [
    -3.14, -2.62, -2.09, -1.57, -1.05, -0.52,
     0.00,
     0.52,  1.05,  1.57,  2.09,  2.62,  3.14
]
SCAN_FRAMES = 10
scan_idx = 0

# Cámara con recognition
camera = robot.getDevice("color_sensor")
camera.enable(TIME_STEP)
camera.recognitionEnable(TIME_STEP)

def move_to_position(p):
    """Envía una pose objetivo (6 joints) al UR."""
    for i, v in enumerate(p):
        ur_motors[i].setPosition(v)

def open_gripper():
    """Abre la pinza."""
    for m in hand_motors:
        m.setPosition(m.getMinPosition() + 0.001)

def close_gripper():
    """Cierra la pinza."""
    for m in hand_motors:
        m.setPosition(0.85)

# Tags por recognitionColors (colores "marcadores" en el mundo)
WHITE_TAG = (1.0, 0.0, 1.0)  
BLACK_TAG = (0.0, 1.0, 1.0)  
def color_close(rgb, target, eps=0.15):
    """Comparación con tolerancia para evitar problemas de floats."""
    return (abs(rgb[0] - target[0]) < eps and
            abs(rgb[1] - target[1]) < eps and
            abs(rgb[2] - target[2]) < eps)

def normalize_colors(cols):
    """Normaliza el formato de getColors() a lista de tripletas (r,g,b)."""
    if cols is None:
        return []
    # Formato plano: [r,g,b]
    if len(cols) == 3 and isinstance(cols[0], (float, int)):
        return [(float(cols[0]), float(cols[1]), float(cols[2]))]
    # Formato lista: [[r,g,b], ...]
    out = []
    for c in cols:
        if isinstance(c, (list, tuple)) and len(c) >= 3:
            out.append((float(c[0]), float(c[1]), float(c[2])))
    return out

def find_tag(tag):
    """Devuelve True si la cámara ve algún objeto con el tag indicado."""
    for obj in camera.getRecognitionObjects():
        cols = normalize_colors(obj.getColors())
        for rgb in cols:
            if color_close(rgb, tag):
                return True
    return False

open_gripper()

while robot.step(TIME_STEP) != -1:
    if counter > 0:
        counter -= 1
        continue

    if state == BOOT:
        move_to_position(home_position)
        counter = 60
        state = RETURN_HOME
        continue

    if state == RETURN_HOME:
        set_all_speeds(RUN_SPEED)
        state = IDLE
        counter = 10
        continue

    if state == IDLE:
        move_to_position(observe_pose)
        counter = 15
        state = OBSERVE
        continue

    if state == OBSERVE:
        if find_tag(WHITE_TAG):
            move_to_position(white_pick_position)
            counter = 25
            state = PICK_WHITE
            continue

        if find_tag(BLACK_TAG):
            move_to_position(black_pick_position)
            counter = 25
            state = PICK_BLACK
            continue

        state = SCAN
        continue

    if state == SCAN:
        if find_tag(WHITE_TAG) or find_tag(BLACK_TAG):
            state = OBSERVE
            continue

        pan = SCAN_PANS[scan_idx]
        scan_pose = observe_pose.copy()
        scan_pose[0] = pan

        print(f"[{robot.getName()}] SCAN pan={pan:.2f}")
        move_to_position(scan_pose)

        counter = SCAN_FRAMES
        scan_idx = (scan_idx + 1) % len(SCAN_PANS)
        state = OBSERVE
        continue

    if state == PICK_WHITE:
        open_gripper()
        counter = 6
        close_gripper()
        counter = 20
        state = MOVE_SHELF
        continue

    if state == PICK_BLACK:
        open_gripper()
        counter = 6
        close_gripper()
        counter = 20
        state = MOVE_SHELF
        continue

    if state == MOVE_SHELF:
        pos = shelf_positions[items_placed % len(shelf_positions)]
        move_to_position(pos)
        counter = 70
        state = PLACE_SHELF
        continue

    if state == PLACE_SHELF:
        open_gripper()
        items_placed += 1
        move_to_position(home_position)
        counter = 60
        state = RETURN_HOME
        continue
