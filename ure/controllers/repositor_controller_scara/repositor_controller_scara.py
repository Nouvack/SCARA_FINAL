"""repositor_controller_scara controller (imagen/ROI en vez de recognition)."""

from controller import Robot
import numpy as np

TIME_STEP = 32

# Estados
BOOT, IDLE, LOOKING_AT_WHITE, PICKING_FROM_WHITE, MOVING_TO_SHELF_WHITE, PLACING_ON_SHELF_WHITE, \
LOOKING_AT_BLACK, PICKING_FROM_BLACK, MOVING_TO_SHELF_BLACK, PLACING_ON_SHELF_BLACK, \
RETURNING_HOME, WAITING = range(12)

robot = Robot()
EPS = 0.001

counter = 0
state = BOOT
items_placed = 0

# Velocidad: arrancamos suave y luego subimos
BOOT_SPEED = 0.35
RUN_SPEED  = 0.90

# Posiciones (Formato: [Pan, Lift, Elbow, W1, W2, W3])
home_position = [0.0, -1.57, 0.0, -1.57, 0.0, 0.0]

# Canastas están FRENTE al robot móvil
# Canasta BLANCA (X=-0.15, ligeramente a la izquierda)
white_look_position = [-0.2, -1.0, 0.5, -1.0, -1.57, 0.0]
white_pick_position = [-0.2, -1.5, 1.2, -1.4, -1.57, 0.0]

# Canasta NEGRA (X=0.53, ligeramente a la derecha)
black_look_position = [0.2, -1.0, 0.5, -1.0, -1.57, 0.0]
black_pick_position = [0.2, -1.5, 1.2, -1.4, -1.57, 0.0]

shelf_positions = [
    [3.14, -1.5, 1.0, -1.0, -1.57, 0.0],
    [3.14, -1.3, 0.8, -1.1, -1.57, 0.0],
    [3.14, -1.7, 1.2, -0.9, -1.57, 0.0],
    [3.14, -1.5, 1.0, -1.0, -1.57, 0.0],
]

print(f'[{robot.getName()}] Inicializando controlador (ROI por imagen, 6 ejes)...')

# Pinza
hand_motors = [
    robot.getDevice("finger_1_joint_1"),
    robot.getDevice("finger_2_joint_1"),
    robot.getDevice("finger_middle_joint_1"),
]

# Brazo UR
motor_names = [
    "shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
    "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"
]
ur_motors = [robot.getDevice(name) for name in motor_names]
for i, m in enumerate(ur_motors):
    if not m:
        print(f"[{robot.getName()}] Error: Motor '{motor_names[i]}' no encontrado.")

def set_all_speeds(v):
    for m in ur_motors:
        if m: m.setVelocity(v)
    for m in hand_motors:
        if m: m.setVelocity(v)

set_all_speeds(BOOT_SPEED)

# Cámara (imagen)
camera = robot.getDevice("color_sensor")
if camera:
    camera.enable(TIME_STEP)
    print(f'[{robot.getName()}] Cámara activada (modo imagen).')
else:
    print(f'[{robot.getName()}] ADVERTENCIA: No se encontró cámara "color_sensor".')

# -----------------------
# Utilidades
# -----------------------
def clamp_with_eps(motor, pos):
    mn, mx = motor.getMinPosition(), motor.getMaxPosition()
    if mx == float("inf"):
        return max(mn + EPS, pos)
    return max(mn + EPS, min(mx - EPS, pos))

def close_gripper():
    target = 0.85
    for m in hand_motors:
        if m: m.setPosition(clamp_with_eps(m, target))

def open_gripper():
    for m in hand_motors:
        if m: m.setPosition(m.getMinPosition() + EPS)

def move_to_position(positions):
    for i, p in enumerate(positions):
        if i < len(ur_motors) and ur_motors[i]:
            ur_motors[i].setPosition(p)

def get_roi_stats():
    """
    Devuelve (brightness_mean, brightness_std) de un ROI central inferior.
    Ajusta el ROI si tu cámara apunta diferente.
    """
    if not camera:
        return None, None

    img = camera.getImage()
    if img is None:
        return None, None

    w = camera.getWidth()
    h = camera.getHeight()

    # ROI: parte inferior-central (suele capturar interior de cesta si miras hacia delante)
    x0 = int(w * 0.35)
    x1 = int(w * 0.65)
    y0 = int(h * 0.55)
    y1 = int(h * 0.90)

    # Extraer pixels (BGRA en Webots). Usamos API de cámara para sacar RGB por pixel.
    # Nota: esto no es lo más rápido, pero es simple y suficiente para empezar.
    vals = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            r = camera.imageGetRed(img, w, x, y)
            g = camera.imageGetGreen(img, w, x, y)
            b = camera.imageGetBlue(img, w, x, y)
            # brillo simple
            vals.append((r + g + b) / 3.0)

    if not vals:
        return None, None

    arr = np.array(vals, dtype=np.float32)
    return float(arr.mean()), float(arr.std())

def basket_has_object():
    """
    Heurística:
    - Si hay una lata/objeto, normalmente sube la variación (std) o cambia el brillo medio.
    - Ajusta umbrales según tu escena.
    """
    mean_b, std_b = get_roi_stats()
    if mean_b is None:
        return False

    # DEBUG útil - HABILITADO para ver valores
    print(f'[{robot.getName()}] ROI mean={mean_b:.1f} std={std_b:.1f}')

    # Umbral base por variación:
    # - si std es muy bajo, suele ser superficie uniforme (cesta vacía / fondo plano)
    # - si std sube, hay bordes/objeto dentro
    return std_b > 3.0  # Reducido de 6.0 a 3.0 para ser más sensible

# -----------------------
# Bucle principal
# -----------------------
open_gripper()

while robot.step(TIME_STEP) != -1:
    if counter > 0:
        counter -= 1
        continue

    # --- BOOT: ir a home y estabilizar ---
    if state == BOOT:
        print(f'[{robot.getName()}] BOOT -> yendo a HOME para estabilizar...')
        move_to_position(home_position)
        counter = 80
        state = RETURNING_HOME
        continue

    # --- IDLE -> mirar blanca ---
    if state == IDLE:
        print(f'[{robot.getName()}] -> Revisando Cesta BLANCA...')
        move_to_position(white_look_position)
        counter = 45
        state = LOOKING_AT_WHITE
        continue

    # --- LOOK BLANCA ---
    if state == LOOKING_AT_WHITE:
        if basket_has_object():
            print(f'[{robot.getName()}] Objeto probable en BLANCA. Bajando para recoger...')
            move_to_position(white_pick_position)
            counter = 35
            state = PICKING_FROM_WHITE
        else:
            print(f'[{robot.getName()}] Cesta BLANCA parece vacía. Pasando a NEGRA...')
            move_to_position(black_look_position)
            counter = 55
            state = LOOKING_AT_BLACK
        continue

    if state == PICKING_FROM_WHITE:
        close_gripper()
        counter = 25
        state = MOVING_TO_SHELF_WHITE
        continue

    if state == MOVING_TO_SHELF_WHITE:
        shelf_pos = shelf_positions[items_placed % len(shelf_positions)]
        print(f'[{robot.getName()}] Llevando al estante (desde BLANCA)...')
        move_to_position(shelf_pos)
        counter = 70
        state = PLACING_ON_SHELF_WHITE
        continue

    if state == PLACING_ON_SHELF_WHITE:
        open_gripper()
        items_placed += 1
        print(f'[{robot.getName()}] Colocado. Ahora reviso NEGRA...')
        move_to_position(black_look_position)
        counter = 55
        state = LOOKING_AT_BLACK
        continue

    # --- LOOK NEGRA ---
    if state == LOOKING_AT_BLACK:
        if basket_has_object():
            print(f'[{robot.getName()}] Objeto probable en NEGRA. Bajando para recoger...')
            move_to_position(black_pick_position)
            counter = 35
            state = PICKING_FROM_BLACK
        else:
            print(f'[{robot.getName()}] Cesta NEGRA parece vacía. Me quedo esperando...')
            # Evita vaivén: no vuelvas a home cada vez
            state = WAITING
            counter = 120
        continue

    if state == PICKING_FROM_BLACK:
        close_gripper()
        counter = 25
        state = MOVING_TO_SHELF_BLACK
        continue

    if state == MOVING_TO_SHELF_BLACK:
        shelf_pos = shelf_positions[items_placed % len(shelf_positions)]
        print(f'[{robot.getName()}] Llevando al estante (desde NEGRA)...')
        move_to_position(shelf_pos)
        counter = 70
        state = PLACING_ON_SHELF_BLACK
        continue

    if state == PLACING_ON_SHELF_BLACK:
        open_gripper()
        items_placed += 1
        print(f'[{robot.getName()}] Colocado. Volviendo a HOME...')
        move_to_position(home_position)
        counter = 70
        state = RETURNING_HOME
        continue

    if state == RETURNING_HOME:
        # Ya estabilizado: subimos velocidad “normal”
        set_all_speeds(RUN_SPEED)
        state = IDLE
        counter = 25
        continue

    if state == WAITING:
        # después de esperar, vuelve a revisar desde blanca otra vez
        print(f'[{robot.getName()}] Esperando completado. Revisando canastas nuevamente...')
        move_to_position(white_look_position)
        counter = 45
        state = LOOKING_AT_WHITE
        continue
