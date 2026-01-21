from controller import Robot
import sys

# Número total de motores usados
MOTOR_NUMBER = 7

# Nombres de los motores según el modelo en Webots
# Los seis primeros corresponden al brazo, el último a la pinza
MOTOR_NAMES = [
    "motor 1",
    "motor 2",
    "motor 3",
    "motor 4",
    "motor 5",
    "motor 6",
    "gripper::right",
]


class Rob3PickPlace:
    def __init__(self):
        # Instancia principal del robot
        self.robot = Robot()

        # Paso de simulación
        self.time_step = int(self.robot.getBasicTimeStep())

        # Lista de motores
        self.motors = [None] * MOTOR_NUMBER

        # Carga de dispositivos (motores) desde Webots
        for i, name in enumerate(MOTOR_NAMES):
            self.motors[i] = self._get_device_or_warn(name, i)

    def _get_device_or_warn(self, name: str, idx: int):
        """
        Intenta obtener un dispositivo por nombre.
        Si no existe, se avisa y se devuelve None.
        """
        try:
            dev = self.robot.getDevice(name)
            return dev
        except BaseException:
            print(f"[WARN] No existe el device '{name}' (motor index {idx}).")
            return None

    def step(self):
        """
        Avanza un paso de simulación.
        Si Webots termina la simulación, se sale del programa.
        """
        if self.robot.step(self.time_step) == -1:
            sys.exit(0)

    def passive_wait(self, sec: float):
        """
        Espera pasiva durante un tiempo dado (en segundos),
        avanzando la simulación sin hacer nada más.
        """
        start_time = self.robot.getTime()
        while start_time + sec > self.robot.getTime():
            self.step()

    def set_position(self, motor_index: int, position: float):
        """
        Envía una posición objetivo a un motor concreto.
        """
        m = self.motors[motor_index]
        if m is None:
            return
        try:
            m.setPosition(position)
        except BaseException as e:
            print(f"[ERROR] setPosition en motor {motor_index} falló:", e)

    def open_gripper(self):
        """
        Abre la pinza moviéndola a una posición abierta.
        """
        grip = self.motors[6]
        if grip is None:
            return
        try:
            grip.setPosition(0.5)
        except BaseException as e:
            print("[ERROR] open_gripper() falló:", e)

    def close_gripper(self):
        """
        Cierra la pinza aplicando un par negativo.
        """
        grip = self.motors[6]
        if grip is None:
            return
        try:
            grip.setTorque(-0.2)
        except BaseException as e:
            print("[ERROR] close_gripper() falló:", e)

    def run(self):
        """
        Secuencia principal de pick & place.
        El robot se mueve a una posición, agarra un objeto,
        lo traslada y lo suelta, repitiendo el ciclo.
        """
        while True:
            # Orientación inicial de la muñeca
            self.set_position(4, -1.95)
            self.passive_wait(0.5)

            # Preparación para el agarre
            self.set_position(1, 1.55)
            self.set_position(2, 1.12)
            self.open_gripper()
            self.passive_wait(2.0)

            # Alineación de la pinza con el objeto
            self.set_position(4, -1.09)
            self.passive_wait(2.0)

            # Cierre de la pinza para agarrar el objeto
            self.close_gripper()
            self.passive_wait(0.5)

            # Elevación del brazo tras el agarre
            self.set_position(1, -0.92)
            self.passive_wait(0.3)
            self.set_position(2, 1.88)
            self.set_position(4, 1.5)
            self.passive_wait(2.0)

            # Rotación del brazo hacia la zona de depósito
            self.set_position(0, -1.5708)
            self.passive_wait(1.0)

            # Posición previa a soltar el objeto
            self.set_position(4, -1.04)
            self.passive_wait(1.0)
            self.set_position(2, 1.12)
            self.set_position(1, 1.53)
            self.passive_wait(2.0)

            # Apertura de la pinza para soltar el objeto
            self.open_gripper()
            self.passive_wait(0.5)

            # Retirada del brazo
            self.set_position(4, -1.95)
            self.passive_wait(1.0)

            # Vuelta a la posición inicial
            self.set_position(1, 0.0)
            self.passive_wait(2.0)
            self.set_position(0, 0.0)
            self.passive_wait(2.0)


if __name__ == "__main__":
    Rob3PickPlace().run()
