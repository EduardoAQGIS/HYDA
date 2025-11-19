# HYDA - Hydrological Delimitation Assistant
<img width="80.4" height="93" alt="Imagen2" src="https://github.com/user-attachments/assets/dd9ddbac-9e6a-46dc-8f6a-143bf7648e21" />

**HYDA** (Hydrological Delimitation Assistant) es un complemento para **QGIS** diseñado para agilizar y optimizar la delimitación de cuencas hidrográficas directamente sobre **curvas de nivel**.  

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
   -<img width="21.7" height="26.8" alt="B" src="https://github.com/user-attachments/assets/d056c27f-bef2-4700-a37c-fdada5a0b8d1" /> Botón seleccionar: permite seleccionar el polígono a modificar.
   -<img width="21.9" height="26.9" alt="C" src="https://github.com/user-attachments/assets/df1bdf2b-ac6c-40c7-8dfc-0a59fa41e48f" /> Botón Puntos directos: crea puntos directamente en cualquier parte del polígono para modificar el recorrido (recomendado en áreas con cotas descendentes).
   -<img width="25.0" height="27.1" alt="D" src="https://github.com/user-attachments/assets/7404a3f5-b8e6-4db1-a2be-62618ef1781a" /> Botón Puntos auxiliares: crea un punto en una zona baja para que el recorrido continúe de manera ascendente hacia un pico no identificado previamente.


