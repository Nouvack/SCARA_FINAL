"""repositor_controller_scara controller."""

from controller import Robot
import numpy as np

TIME_STEP = 32

# Estados de la máquina de estados
IDLE, LOOKING_AT_WHITE, PICKING_FROM_WHITE, MOVING_TO_SHELF_WHITE, PLACING_ON_SHELF_WHITE, \
LOOKING_AT_BLACK, PICKING_FROM_BLACK, MOVING_TO_SHELF_BLACK, PLACING_ON_SHELF_BLACK, \
RETURNING_HOME = range(10)

robot = Robot()

# Margen para evitar límites exactos
EPS = 0.001

counter = 0
state = IDLE
items_placed = 0
speed = 1.0

# Posiciones (Formato: [Pan, Lift, Elbow, W1, W2, W3])
home_position = [0.0, -1.57, 0.0, -1.57, 0.0, 0.0]

# Posiciones Cesta BLANCA (Izquierda/Frente)
# Pan ~0.5 (izquierda), Lift levanta, Elbow flexiona
white_look_position = [1.0, -1.8, 1.2, -1.0, -1.57, 0.0] 
white_pick_position = [1.0, -2.0, 1.3, -0.9, -1.57, 0.0]

# Posiciones Cesta NEGRA (Derecha/Frente)
# Pan ~-0.5 (derecha)
black_look_position = [-1.0, -1.8, 1.2, -1.0, -1.57, 0.0]
black_pick_position = [-1.0, -2.0, 1.3, -0.9, -1.57, 0.0]

# Posiciones Estante (Atrás - Pan ~3.14)
shelf_positions = [
    [3.14, -1.5, 1.0, -1.0, -1.57, 0.0],
    [3.14, -1.3, 0.8, -1.1, -1.57, 0.0],
    [3.14, -1.7, 1.2, -0.9, -1.57, 0.0],
    [3.14, -1.5, 1.0, -1.0, -1.57, 0.0],
]

# -----------------------
# Inicialización
# -----------------------
print(f'[{robot.getName()}] Inicializando controlador inteligente (6 ejes)...')

hand_motors = [
    robot.getDevice("finger_1_joint_1"),
    robot.getDevice("finger_2_joint_1"),
    robot.getDevice("finger_middle_joint_1"),
]
for m in hand_motors:
    if m: m.setVelocity(speed)

# Usamos los 6 motores del UR3e para movimiento completo
motor_names = [
    "shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
    "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"
]
ur_motors = [robot.getDevice(name) for name in motor_names]

for m in ur_motors:
    if m: m.setVelocity(speed)
    else: print(f"Error: Motor no encontrado en la lista.")

# Cámara IMPRESCINDIBLE para esta tarea
camera = robot.getDevice("color_sensor")
if camera:
    camera.enable(TIME_STEP)
    camera.recognitionEnable(TIME_STEP)
    print(f'[{robot.getName()}] Cámara y reconocimiento activados.')
else:
    print(f'[{robot.getName()}] ADVERTENCIA: No se encontró cámara "color_sensor".')

# -----------------------
# Funciones
# -----------------------
def check_basket_content():
    """Retorna True si la cámara detecta objetos reconocimiento."""
    if not camera: return True
    
    number_of_objects = camera.getRecognitionNumberOfObjects()
    print(f'[{robot.getName()}] Veo {number_of_objects} objetos.')
    return number_of_objects > 0

def clamp_with_eps(motor, pos):
    mn, mx = motor.getMinPosition(), motor.getMaxPosition()
    if mx == float("inf"): return max(mn + EPS, pos)
    return max(mn + EPS, min(mx - EPS, pos))

def close_gripper():
    target = 0.85
    for m in hand_motors:
        if m: m.setPosition(clamp_with_eps(m, target))

def open_gripper():
    for m in hand_motors:
        if m: m.setPosition(m.getMinPosition() + EPS)

def move_to_position(positions):
    """Mueve los 6 motores a las posiciones indicadas."""
    for i, p in enumerate(positions):
        if i < len(ur_motors) and ur_motors[i]:
            ur_motors[i].setPosition(p)

# -----------------------
# Bucle Principal
# -----------------------
open_gripper()

while robot.step(TIME_STEP) != -1:
    if counter <= 0:
        # --- Lógica Cesta BLANCA ---
        if state == IDLE:
            print(f'[{robot.getName()}] -> Revisando Cesta BLANCA...')
            state = LOOKING_AT_WHITE
            move_to_position(white_look_position)
            counter = 40

        elif state == LOOKING_AT_WHITE:
            # Aquí el robot está "mirando"
            # Verificamos si hay algo
            if check_basket_content():
                print(f'[{robot.getName()}] ¡Objeto detectado en Blanca! Iniciando recogida.')
                state = PICKING_FROM_WHITE
                move_to_position(white_pick_position)
                counter = 30
            else:
                print(f'[{robot.getName()}] Cesta Blanca vacía. Pasando a Negra.')
                state = LOOKING_AT_BLACK # Saltar recogida
                move_to_position(black_look_position)
                counter = 50

        elif state == PICKING_FROM_WHITE:
            close_gripper()
            # Pequeña espera para asegurar agarre antes de mover
            state = MOVING_TO_SHELF_WHITE
            counter = 20 # Tiempo de cierre

        elif state == MOVING_TO_SHELF_WHITE:
            shelf_pos = shelf_positions[items_placed % len(shelf_positions)]
            print(f'[{robot.getName()}] Llevando al estante...')
            move_to_position(shelf_pos)
            state = PLACING_ON_SHELF_WHITE
            counter = 60

        elif state == PLACING_ON_SHELF_WHITE:
            open_gripper()
            items_placed += 1
            state = LOOKING_AT_BLACK # Siguiente cesta
            print(f'[{robot.getName()}] Objeto colocado. Vamos a Cesta NEGRA.')
            move_to_position(black_look_position)
            counter = 50

        # --- Lógica Cesta NEGRA ---
        elif state == LOOKING_AT_BLACK:
            # Estado de observación para negra
            if check_basket_content():
                print(f'[{robot.getName()}] ¡Objeto detectado en Negra! Iniciando recogida.')
                state = PICKING_FROM_BLACK
                move_to_position(black_pick_position)
                counter = 30
            else:
                print(f'[{robot.getName()}] Cesta Negra vacía. Volviendo a inicio.')
                state = RETURNING_HOME
                move_to_position(home_position)
                counter = 50

        elif state == PICKING_FROM_BLACK:
            close_gripper()
            state = MOVING_TO_SHELF_BLACK
            counter = 20

        elif state == MOVING_TO_SHELF_BLACK:
            shelf_pos = shelf_positions[items_placed % len(shelf_positions)]
            print(f'[{robot.getName()}] Llevando al estante...')
            move_to_position(shelf_pos)
            state = PLACING_ON_SHELF_BLACK
            counter = 60
        
        elif state == PLACING_ON_SHELF_BLACK:
            open_gripper()
            items_placed += 1
            print(f'[{robot.getName()}] Ciclo terminado. Volviendo a Home.')
            state = RETURNING_HOME
            move_to_position(home_position)
            counter = 50

        elif state == RETURNING_HOME:
            state = IDLE
            counter = 20

    counter -= 1

