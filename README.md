# Clasificación de Objetos con Robot SCARA en Webots

## Descripción del proyecto

Este proyecto se basa en el mundo de ejemplo **`ure.wbt`** de **Universal Robots** dentro del simulador **Webots**, el cual incluye un robot **SCARA**.

En su versión original, el robot tiene como objetivo principal **apilar objetos idénticos**, específicamente **latas**, siguiendo una lógica simple y repetitiva.

## Modificación propuesta

La modificación planteada amplía la funcionalidad original del sistema. En lugar de trabajar con un único tipo de objeto, el robot será capaz de **clasificar dos tipos diferentes de objetos** que llegan de manera continua.

Para lograr esto, se incorporan:

* **Sensores** para la detección de los objetos.
* **Cámaras** para identificar el tipo de objeto.
* **Lógica de control** que permita tomar decisiones en función de la información obtenida.

El robot deberá reconocer correctamente cada objeto y **separarlo según su tipo**, depositándolo en la ubicación correspondiente.

## Objetivo

El objetivo principal es demostrar cómo, a partir de un ejemplo base, se puede extender el comportamiento de un robot industrial simulado para realizar tareas más complejas, combinando **visión artificial**, **sensado** y **control robótico**.

## Tecnologías utilizadas

* Webots
* Universal Robots (ejemplo `ure.wbt`)
* Robot SCARA
* Sensores y cámaras virtuales

---

Proyecto orientado a la experimentación y aprendizaje en robótica y automatización dentro de entornos simulados.
