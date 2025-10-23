# HYDA – Asistente de Delimitación Hidrológica

**HYDA (Hydrological Delimitation Assistant)** está diseñado para **asistir en la delimitación de límites hidrológicos** a partir de datos vectoriales de curvas de nivel.  
El sistema automatiza la identificación de divisorias y polígonos hidrológicos empleando información topográfica vectorial dentro del entorno QGIS.

---

## 🌎 Descripción general

HYDA ofrece un enfoque semiautomático para generar **divisorias de aguas y límites de cuencas hidrográficas** utilizando curvas de nivel.  
Mediante análisis geométrico y relacional de las curvas, permite delinear polígonos hidrológicos directamente en el lienzo de QGIS de manera interactiva.

### 🔍 Funcionalidades principales
- Delimitación interactiva de divisorias hidrológicas.
- Uso de **curvas de nivel vectoriales** como fuente principal.
- Generación paso a paso de **líneas divisorias** y **polígonos de cuenca**.
- Incorporación de **puntos auxiliares** y **puntos de conexión** para ajustes finos.
- Integración con herramientas de **snapping** y **índices espaciales** de QGIS para mayor precisión.
- Interfaz acoplable (dock) con retroalimentación visual en tiempo real.

---

## 🧭 Uso básico

1. Carga una capa de **curvas de nivel vectoriales** con su campo de elevaciones.
2. Abre el panel **HYDA** en QGIS y selecciona la capa topográfica y el campo de elevación.
3. Define **dos puntos iniciales** sobre el mapa para iniciar la delimitación.
4. Si es necesario, añade **puntos auxiliares** para extender o modificar la divisoria.
5. HYDA procesará automáticamente las curvas de nivel y generará el **polígono de cuenca** correspondiente.

---

## 🧠 Fundamento conceptual

El algoritmo de HYDA se basa en principios geomorfológicos y topográficos, evaluando la relación entre curvas de nivel para determinar líneas divisorias del flujo.  
El sistema:
- Analiza la jerarquía altimétrica y la proximidad entre curvas.  
- Detecta puntos de cresta y cambios de pendiente relevantes.  
- Construye líneas divisorias evitando cruces topológicos y autointersecciones.  

Este enfoque vectorial resulta especialmente útil en contextos donde no se dispone de un **Modelo Digital de Elevación (DEM)** o se requiere una representación **puramente vectorial** de la cuenca.

---

## 📁 Estructura del repositorio


