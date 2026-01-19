from controller import Robot

TIME_STEP = 64
robot = Robot()

# --- CONFIGURACIÓN DE RUEDAS ---
wheels = []
wheelsNames = ['wheel1', 'wheel2', 'wheel3', 'wheel4'] # Solo las 2 ruedas de tu robot

for name in wheelsNames:
    wheel = robot.getDevice(name)
    wheel.setPosition(float('inf')) # Modo de rotación continua
    wheel.setVelocity(0.0)
    wheels.append(wheel)

# --- BUCLE PRINCIPAL ---
while robot.step(TIME_STEP) != -1:
    # Definir velocidad constante
    # Nota: Si va hacia atrás, cambia estos números a positivos (1.0)
    leftSpeed = -1.0
    rightSpeed = -1.0
    
    # Aplicar velocidad a las ruedas
    wheels[0].setVelocity(leftSpeed)
    wheels[1].setVelocity(rightSpeed)



