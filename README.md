# HYDA — Hydrological Delimitation Assistant

**HYDA** (Hydrological Delimitation Assistant) es un complemento para **QGIS** diseñado para agilizar y optimizar la delimitación de cuencas hidrográficas directamente sobre **curvas de nivel vectoriales**.  

---


## 🧭 Descripción técnica
HYDA automatiza parte del proceso de delimitación de cuencas utilizando la topología de curvas de nivel vectoriales.  
El usuario define los puntos de salida de la cuenca, y el complemento genera el polígono correspondiente siguiendo la estructura geométrica.  
Combina algoritmos geométricos con interacción visual, ofreciendo una herramienta semiautomática, precisa y flexible.

---

## 🖱️ Guía de usuario
1. Seleccionar la capa de **curvas de nivel vectoriales**.  
2. Seleccionar el campo de elevaciones donde se tienen registrados los valores correspondientes a las curvas de nivel.
3. Cargar Topografía.
4. Seleccionar la capa de destino, donde se almacenarán los polígonos creados.
5. Activar el botón **Inicio** y definir los dos puntos de salida de la cuenca.  
6. HYDA generará automáticamente el polígono de la divisoria.
7. Botones de selección, puntos directos y puntos auxiliares: estas herramientas permiten seleccionar y ajustar un polígono mediante la creación y manipulación de puntos secundarios, ofreciendo mayor control sobre la forma y precisión de la delimitación.
