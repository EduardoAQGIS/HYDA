# HYDA – Asistente de Delimitación Hidrológica

**HYDA (Hydrological Delimitation Assistant)** está diseñado para **asistir en la delimitación de límites hidrológicos** a partir de datos vectoriales de curvas de nivel.  
El sistema asiste en la identificación de divisorias empleando información topográfica vectorial dentro del entorno QGIS.

---

### 🔍 Funcionalidades
- Delimitación interactiva de divisorias hidrológicas.
- Uso de **curvas de nivel vectoriales** como fuente principal.
- Generación paso a paso de **líneas divisorias** y **polígonos de cuenca**.
- Incorporación de **puntos auxiliares** y **puntos de conexión** para ajustes finos.

---

## 💧 Uso

1. Selecciona la **capa de curvas de nivel** (tipo línea) que contenga las elevaciones.  
2. Elige el **campo de elevación** correspondiente dentro de esa capa.  
3. Presiona el botón **CARGAR** para inicializar la topografía.  
4. Selecciona una **capa de destino (poligonal)** donde se almacenarán los resultados generados.  
5. Usa los botones de delimitación del panel:
   - **INICIO:** define dos puntos iniciales para crear una nueva delimitación.  
   - **Seleccionar polígono:** permite elegir un polígono existente para editar o ampliar.  
   - **Puntos directos:** agrega conexiones manuales entre líneas divisorias.  
   - **Puntos auxiliares:** extiende o ajusta una delimitación ya creada.  
6. HYDA procesará automáticamente las curvas de nivel y generará el **polígono de cuenca** correspondiente en la capa de destino.  

---
