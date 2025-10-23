# -*- coding: utf-8 -*-
"""
HYDA - Hydrological Delimitation Assistant
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QVariant
from qgis.PyQt.QtGui import QIcon, QCursor, QColor
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import (QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, 
                       QgsPointXY, QgsWkbTypes, QgsField, QgsSpatialIndex,
                       QgsVectorFileWriter, QgsRectangle, QgsMessageLog,
                       Qgis, QgsSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer,
                       QgsFillSymbol, QgsCoordinateTransform, QgsPointLocator)
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand
from .resources import *
from .HYDA_dialog import HYDADialog
import os.path
import math


class PuntoMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, callback, max_points=None):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self.max_points = max_points
        self.points = []
        
        self.rb = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        self.rb.setColor(QColor(0, 120, 255, 180))
        self.rb.setWidth(10)
        
        # Agregar indicador de snap
        from qgis.gui import QgsSnapIndicator
        self.snap_indicator = QgsSnapIndicator(canvas)
        
    def canvasMoveEvent(self, e):
        # Mostrar indicador de snap al mover el mouse
        match = self.canvas.snappingUtils().snapToMap(self.toMapCoordinates(e.pos()))
        self.snap_indicator.setMatch(match)
        
    def canvasPressEvent(self, e):
        # Obtener punto con snap
        match = self.canvas.snappingUtils().snapToMap(self.toMapCoordinates(e.pos()))
        
        if match.isValid():
            pt = match.point()
        else:
            pt = self.toMapCoordinates(e.pos())
        
        self.points.append(pt)
        self.rb.addPoint(pt)
        self.callback(pt)
        
        if self.max_points and len(self.points) >= self.max_points:
            self.canvas.unsetMapTool(self)
    
    def reset(self):
        self.points = []
        self.rb.reset(QgsWkbTypes.PointGeometry)
    
    def deactivate(self):
        super().deactivate()
        self.rb.reset(QgsWkbTypes.PointGeometry)
        self.snap_indicator.setMatch(QgsPointLocator.Match())

class PoligonoMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, callback, capa_poly):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self.capa_poly = capa_poly
        
        self.rb_hov = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self.rb_hov.setColor(QColor(255, 255, 0, 20))
        self.rb_hov.setWidth(1)
        self.rb_hov.setLineStyle(Qt.DashLine)
        
    def canvasMoveEvent(self, e):
        pt = self.toMapCoordinates(e.pos())
        pt_g = QgsGeometry.fromPointXY(pt)
        self.rb_hov.reset(QgsWkbTypes.PolygonGeometry)
        
        for feat in self.capa_poly.getFeatures():
            if feat.geometry().contains(pt_g):
                self.rb_hov.setToGeometry(feat.geometry(), None)
                break
        
    def canvasPressEvent(self, e):
        pt = self.toMapCoordinates(e.pos())
        pt_g = QgsGeometry.fromPointXY(pt)
        
        for feat in self.capa_poly.getFeatures():
            if feat.geometry().contains(pt_g):
                self.callback(feat)
                return
        
        QMessageBox.information(None, "Sin selección", "No se encontró ningún polígono en ese punto.")
    
    def deactivate(self):
        super().deactivate()
        self.rb_hov.reset(QgsWkbTypes.PolygonGeometry)


class HYDA:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', 'HYDA_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = self.tr(u'&HYDA')
        self.first_start = None
        
        self.capa_topo = None
        self.campo_elev = None
        self.curvas = {}
        self.idx_esp = None
        self.pts_ini = []
        self.pts_aux = []
        self.pts_conexion = []
        self.mt_ini = None
        self.mt_aux = None
        self.mt_conexion = None
        self.mt_sel = None
        self.capa_div = None
        self.res_lin = []
        self.poly_meta = {}
        self.poly_edit = None

    def tr(self, message):
        return QCoreApplication.translate('HYDA', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None,
                   whats_this=None, parent=None):
        
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.iface.addToolBarIcon(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        
        self.add_action(icon_path, text=self.tr(u'Hydrological Delimitation Assistant'),
                    callback=self.run, parent=self.iface.mainWindow())
        self.first_start = True

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&HYDA'), action)
            self.iface.removeToolBarIcon(action)
        
        if self.mt_ini:
            self.iface.mapCanvas().unsetMapTool(self.mt_ini)
        if self.mt_aux:
            self.iface.mapCanvas().unsetMapTool(self.mt_aux)
        if self.mt_conexion:
            self.iface.mapCanvas().unsetMapTool(self.mt_conexion)
        if self.mt_sel:
            self.iface.mapCanvas().unsetMapTool(self.mt_sel)

    def run(self):
        if self.first_start == True:
            self.first_start = False
            self.dlg = HYDADialog()
            
            self.dlg.topoLoaded.connect(self.on_topo_loaded)
            self.dlg.puntoInicialMode.connect(self.on_pto_ini_mode)
            self.dlg.puntoAuxiliarMode.connect(self.on_pto_aux_mode)
            self.dlg.puntoConexionMode.connect(self.on_pto_conexion_mode)
            self.dlg.seleccionarPoligonoMode.connect(self.on_sel_poly_mode)
            
            QgsProject.instance().layersRemoved.connect(lambda: self.dlg.actualizar_capas())
            QgsProject.instance().layersAdded.connect(lambda: self.dlg.actualizar_capas())
            
            # Añadir diálogo como dock widget
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dlg)
            
            # Hacer flotante y posicionar como QuickLabeling
            self.dlg.setFloating(True)
            self.dlg.move(1200, 200)
            
            optimal_size = self.dlg.widget().sizeHint()
            self.dlg.resize(400, optimal_size.height())
        else:
            self.dlg.show()

    def on_topo_loaded(self, capa, campo):
        QgsMessageLog.logMessage(f"Cargando topo: {capa.name()}", 'HYDA', Qgis.Info)
        self.capa_topo = capa
        self.campo_elev = campo
        self.cargar_curvas()
        
    def cargar_curvas(self):
        self.curvas = {}
        fid = 0
        
        QgsMessageLog.logMessage("Cargando curvas...", 'HYDA', Qgis.Info)
        
        for feat in self.capa_topo.getFeatures():
            try:
                elev = feat[self.campo_elev]
                if elev is None:
                    continue
                    
                geom = feat.geometry()
                
                if geom.isMultipart():
                    if geom.wkbType() == QgsWkbTypes.MultiLineString:
                        partes = geom.asMultiPolyline()
                        for parte in partes:
                            g_ind = QgsGeometry.fromPolylineXY(parte)
                            self.curvas[fid] = {'elevation': float(elev), 'geometry': g_ind}
                            fid += 1
                else:
                    self.curvas[fid] = {'elevation': float(elev), 'geometry': geom}
                    fid += 1
            except Exception as e:
                QgsMessageLog.logMessage(f"Error: {str(e)}", 'HYDA', Qgis.Warning)
                continue
        
        self.idx_esp = QgsSpatialIndex()
        for fid, curva in self.curvas.items():
            feat = QgsFeature()
            feat.setId(fid)
            feat.setGeometry(curva['geometry'])
            self.idx_esp.addFeature(feat)
        
        QgsMessageLog.logMessage(f"Curvas: {len(self.curvas)}", 'HYDA', Qgis.Info)

    def on_pto_ini_mode(self, activado):
        if activado:
            # Limpiar TODO al activar el botón
            self.pts_ini = []
            self.pts_aux = []
            self.pts_conexion = []
            self.poly_edit = None
            self.res_lin = []
            
            if self.mt_ini:
                try:
                    self.mt_ini.reset()
                except:
                    pass

            self.mt_ini = PuntoMapTool(self.iface.mapCanvas(), self.on_pto_ini_click, max_points=None)
            self.iface.mapCanvas().setMapTool(self.mt_ini)
            self.iface.mapCanvas().setCursor(Qt.CrossCursor)
        else:
            if self.mt_ini:
                try:
                    self.mt_ini.reset()
                    self.iface.mapCanvas().unsetMapTool(self.mt_ini)
                except:
                    pass
                self.iface.mapCanvas().setCursor(Qt.ArrowCursor)

    def on_pto_ini_click(self, pt):
        # Si ya hay 2 puntos previos, resetear para nueva pareja
        if len(self.pts_ini) >= 2:
            QgsMessageLog.logMessage("↻ Iniciando nueva delimitación", 'HYDA', Qgis.Info)
            self.pts_ini = []
            self.pts_aux = []
            self.pts_conexion = []
            self.poly_edit = None
            self.res_lin = []
            if self.mt_ini:
                try:
                    self.mt_ini.reset()  # Limpia los puntos rojos anteriores
                except:
                    pass
        
        self.pts_ini.append(pt)
        
        # Agregar punto rojo visual
        if self.mt_ini:
            self.mt_ini.rb.addPoint(pt)
        
        QgsMessageLog.logMessage(f"Pto ini {len(self.pts_ini)}: {pt.x():.2f}, {pt.y():.2f}", 'HYDA', Qgis.Info)
        
        # NUEVO: Actualizar estado según cantidad de puntos
        if len(self.pts_ini) == 1:
            self.dlg.actualizar_estado("Delimitando", mostrar_check=False, color="#0483AD")
        elif len(self.pts_ini) == 2:
            self.procesar_divisorias(modo='nuevo')
            self.dlg.habilitar_puntos_auxiliares()
            self.dlg.actualizar_estado("Delimitación creada", mostrar_check=True, color="#58AD03")

    def on_pto_aux_mode(self, activado):
        if activado:
            self.mt_aux = PuntoMapTool(self.iface.mapCanvas(), self.on_pto_aux_click, max_points=None)
            self.iface.mapCanvas().setMapTool(self.mt_aux)
            self.iface.mapCanvas().setCursor(Qt.CrossCursor)
        else:
            if self.mt_aux:
                self.iface.mapCanvas().unsetMapTool(self.mt_aux)
                self.iface.mapCanvas().setCursor(Qt.ArrowCursor)

    def on_pto_aux_click(self, pt):
        self.pts_aux.append(pt)
        QgsMessageLog.logMessage(f"Pto aux {len(self.pts_aux)}: {pt.x():.2f}, {pt.y():.2f}", 'HYDA', Qgis.Info)
        
        # Procesar con metodología de auxiliar incluyendo puntos directos previos
        if self.poly_edit is not None:
            self.procesar_con_auxiliar_y_directos(pt)
        else:
            if len(self.pts_ini) >= 2:
                self.procesar_con_auxiliar_y_directos(pt)

    def on_pto_conexion_mode(self, activado):
        if activado:
            self.mt_conexion = PuntoMapTool(self.iface.mapCanvas(), self.on_pto_conexion_click, max_points=None)
            self.iface.mapCanvas().setMapTool(self.mt_conexion)
            self.iface.mapCanvas().setCursor(Qt.CrossCursor)
        else:
            if self.mt_conexion:
                self.iface.mapCanvas().unsetMapTool(self.mt_conexion)
                self.iface.mapCanvas().setCursor(Qt.ArrowCursor)

    def on_pto_conexion_click(self, pt):
        """Maneja el clic para conexión directa"""
        if not self.res_lin or len(self.res_lin) < 2:
            QMessageBox.warning(self.dlg, "Advertencia", "Debe tener líneas de divisoria creadas primero")
            return
        
        # Encontrar la línea más cercana al punto clickeado
        d_min = float('inf')
        linea_cercana = None
        idx_linea = -1
        pt_conexion = None
        
        for i, linea in enumerate(self.res_lin):
            if len(linea['puntos']) < 2:
                continue
            
            geom_linea = QgsGeometry.fromPolylineXY(linea['puntos'])
            d = geom_linea.distance(QgsGeometry.fromPointXY(pt))
            
            if d < d_min:
                d_min = d
                linea_cercana = linea
                idx_linea = i
                # Obtener punto más cercano en la línea
                res = geom_linea.closestSegmentWithContext(pt)
                pt_conexion = res[1]
        
        if linea_cercana is None:
            QMessageBox.warning(self.dlg, "Advertencia", "No se encontró línea cercana")
            return
        
        QgsMessageLog.logMessage(f"Conexión directa | Línea {idx_linea+1} | Dist: {d_min:.1f}m", 'HYDA', Qgis.Info)
        
        # Agregar el punto de conexión a la lista de conexiones
        self.pts_conexion.append({
            'punto_click': pt,
            'punto_linea': pt_conexion,
            'linea_idx': idx_linea
        })
        
        # Modificar la línea para incluir la conexión directa
        puntos_linea = linea_cercana['puntos']
        idx_insertar = -1
        d_min_seg = float('inf')
        
        for j in range(len(puntos_linea) - 1):
            seg = QgsGeometry.fromPolylineXY([puntos_linea[j], puntos_linea[j+1]])
            d = seg.distance(QgsGeometry.fromPointXY(pt_conexion))
            if d < d_min_seg:
                d_min_seg = d
                idx_insertar = j + 1
        
        # Insertar conexión directa
        if idx_insertar > 0:
            # Truncar la línea hasta el punto de conexión
            nuevos_puntos = puntos_linea[:idx_insertar]
            nuevos_puntos.append(pt_conexion)
            nuevos_puntos.append(pt)
            
            # Actualizar la línea
            linea_cercana['puntos'] = nuevos_puntos
            linea_cercana['punto_final'] = pt
            linea_cercana['num_puntos'] = len(nuevos_puntos)
            linea_cercana['longitud'] = QgsGeometry.fromPolylineXY(nuevos_puntos).length()
            linea_cercana['conexion_directa'] = True
            
            QgsMessageLog.logMessage(f"✓ Conexión directa aplicada | Nuevos puntos: {len(nuevos_puntos)}", 'HYDA', Qgis.Info)
            
            # Actualizar estado
            self.dlg.actualizar_estado("Polígono modificado", mostrar_check=True, color="#1487F3")
            
            # Actualizar el polígono
            if self.poly_edit is not None:
                self.actualizar_poly_exist()
            else:
                self.crear_act_capas()

    def on_sel_poly_mode(self, activado):
        if activado:
            capa_d = self.dlg.get_capa_destino()
            
            if not capa_d or not capa_d.isValid():
                QMessageBox.warning(self.dlg, "Advertencia", "Debe seleccionar capa de salida")
                self.dlg.btn_seleccionar_poligono.setChecked(False)
                return
            
            self.mt_sel = PoligonoMapTool(self.iface.mapCanvas(), self.on_poly_sel, capa_d)
            self.iface.mapCanvas().setMapTool(self.mt_sel)
            self.iface.mapCanvas().setCursor(Qt.CrossCursor)
        else:
            if self.mt_sel:
                self.iface.mapCanvas().unsetMapTool(self.mt_sel)
                self.iface.mapCanvas().setCursor(Qt.ArrowCursor)

    def on_poly_sel(self, feat):
        fid = feat.id()
        QgsMessageLog.logMessage(f"Click poly FID: {fid} | Meta: {list(self.poly_meta.keys())}", 'HYDA', Qgis.Info)
        
        if fid not in self.poly_meta:
            QMessageBox.warning(self.dlg, "Polígono no válido",
                f"Este polígono (FID: {fid}) no fue creado con HYDA.\n"
                f"FIDs disponibles: {list(self.poly_meta.keys())}")
            return
        
        meta = self.poly_meta[fid]
        self.poly_edit = fid
        self.pts_ini = [meta['punto1'], meta['punto2']]
        self.pts_aux = meta['auxiliares'].copy()
        self.pts_conexion = meta.get('conexiones', []).copy()
        
        # Reconstruir las líneas de divisoria
        self.procesar_divisorias(modo='cargar')
        
        area_km2 = feat.geometry().area() / 1_000_000.0
        self.dlg.actualizar_info_poligono(fid, area_km2)
        QgsMessageLog.logMessage(f"Poly {fid} sel | Ini: 2 | Aux: {len(self.pts_aux)}", 'HYDA', Qgis.Info)

    def procesar_con_auxiliar_y_directos(self, pt_aux):
        """Procesa auxiliar considerando puntos directos previos"""
        if len(self.pts_ini) < 2:
            return
        
        if not self.curvas or not self.idx_esp:
            QMessageBox.warning(self.dlg, "Advertencia", "Debe cargar topografía")
            return
        
        QgsMessageLog.logMessage("="*60, 'HYDA', Qgis.Info)
        QgsMessageLog.logMessage(f"Proc auxiliar con directos", 'HYDA', Qgis.Info)
        
        try:
            from .hyda_processor import procesar_divisoria_individual, procesar_desde_auxiliar, crear_poligono_cuenca, recortar_lineas_en_cruce
            
            # Si ya existen líneas, trabajar sobre ellas
            if self.res_lin and len(self.res_lin) >= 2:
                # Encontrar la línea más cercana al punto auxiliar
                d_min = float('inf')
                lin_c = None
                idx_lin = -1
                
                for i, r in enumerate(self.res_lin):
                    if len(r['puntos']) < 2:
                        continue
                    pt_fin = r['punto_final']
                    d = pt_fin.distance(pt_aux)
                    if d < d_min:
                        d_min = d
                        lin_c = r
                        idx_lin = i
                
                if lin_c is not None:
                    # Obtener puntos de conexión directa pendientes para esta línea
                    pts_directos = []
                    for conexion in self.pts_conexion:
                        if conexion.get('linea_idx') == idx_lin:
                            pts_directos.append(conexion['punto_click'])
                    
                    # Agregar puntos directos a la línea
                    if pts_directos:
                        QgsMessageLog.logMessage(f"Agregando {len(pts_directos)} puntos directos", 'HYDA', Qgis.Info)
                        for pt_dir in pts_directos:
                            if pt_dir not in lin_c['puntos']:
                                lin_c['puntos'].append(pt_dir)
                    
                    # Agregar conexión directa al punto auxiliar
                    lin_c['puntos'].append(pt_aux)
                    QgsMessageLog.logMessage(f"L#{lin_c['numero']} cerc aux ({d_min:.1f}m)", 'HYDA', Qgis.Info)
                    
                    # Determinar otra línea para detección de cruces
                    otra_pts = None
                    if len(self.res_lin) >= 2:
                        otra_pts = self.res_lin[1]['puntos'] if idx_lin == 0 else self.res_lin[0]['puntos']
                    
                    # Continuar con metodología de auxiliar desde el punto auxiliar
                    r_cont = procesar_desde_auxiliar(pt_aux, self.idx_esp, self.curvas,
                        lin_c['elev_final'], lin_c['curvas_usadas'], otra_pts)
                    
                    if len(r_cont['puntos']) > 1:
                        lin_c['puntos'].extend(r_cont['puntos'][1:])
                        lin_c['elev_final'] = r_cont['elev_final']
                        lin_c['ganancia'] = lin_c['elev_final'] - lin_c['elev_inicial']
                        lin_c['num_puntos'] = len(lin_c['puntos'])
                        lin_c['salto_auxiliar'] = True
                        lin_c['razon'] = r_cont['razon']
                        lin_c['punto_final'] = r_cont['puntos'][-1] if r_cont['puntos'] else pt_aux
                        lin_c['longitud'] = QgsGeometry.fromPolylineXY(lin_c['puntos']).length()
                        QgsMessageLog.logMessage(f"✓ Ext: {r_cont['elev_inicial']}→{r_cont['elev_final']}m", 'HYDA', Qgis.Info)
                    else:
                        lin_c['salto_auxiliar'] = False
                        QgsMessageLog.logMessage("⚠ Sin curvas desde aux", 'HYDA', Qgis.Warning)
                    
                    # Actualizar estado
                    self.dlg.actualizar_estado("Delimitación modificada", mostrar_check=True, color="#24C2E2")
                    
                    # Actualizar polígono
                    if self.poly_edit is not None:
                        self.actualizar_poly_exist()
                    else:
                        self.crear_act_capas()
            
            QgsMessageLog.logMessage("="*60, 'HYDA', Qgis.Info)
            
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error: {str(e)}", 'HYDA', Qgis.Critical)
            QgsMessageLog.logMessage(traceback.format_exc(), 'HYDA', Qgis.Critical)
            QMessageBox.critical(self.dlg, "Error", f"Error:\n\n{str(e)}")

    def procesar_divisorias(self, modo='nuevo'):
        if len(self.pts_ini) < 2:
            return
        
        if not self.curvas or not self.idx_esp:
            QMessageBox.warning(self.dlg, "Advertencia", "Debe cargar topografía")
            return
        
        # Verificar capa de salida obligatoria
        capa_d = self.dlg.get_capa_destino()
        if not capa_d or not capa_d.isValid():
            QMessageBox.warning(self.dlg, "Advertencia", "Debe seleccionar una capa de salida")
            return
        
        QgsMessageLog.logMessage("="*60, 'HYDA', Qgis.Info)
        QgsMessageLog.logMessage(f"Proc div (modo: {modo})", 'HYDA', Qgis.Info)
        
        try:
            from .hyda_processor import procesar_divisoria_individual, procesar_desde_auxiliar, crear_poligono_cuenca
            
            res = []
            
            QgsMessageLog.logMessage("Proc L1", 'HYDA', Qgis.Info)
            r1 = procesar_divisoria_individual(self.pts_ini[0], self.idx_esp, self.curvas, 1, self.pts_aux, None)
            res.append(r1)
            QgsMessageLog.logMessage(f"L1: {r1['elev_inicial']}→{r1['elev_final']}m | {r1['longitud']/1000:.2f}km | Pts:{r1['num_puntos']}", 'HYDA', Qgis.Info)
            
            QgsMessageLog.logMessage("Proc L2", 'HYDA', Qgis.Info)
            r2 = procesar_divisoria_individual(self.pts_ini[1], self.idx_esp, self.curvas, 2, self.pts_aux, None)  # ← Cambio: None en vez de r1['puntos']
            res.append(r2)
            QgsMessageLog.logMessage(f"L2: {r2['elev_inicial']}→{r2['elev_final']}m | {r2['longitud']/1000:.2f}km | Pts:{r2['num_puntos']}", 'HYDA', Qgis.Info)
            
            # RECORTAR LÍNEAS EN EL CRUCE (agregado)
            from .hyda_processor import recortar_lineas_en_cruce
            
            pts1_orig = r1['puntos'].copy()
            pts2_orig = r2['puntos'].copy()
            
            pts1_rec, pts2_rec, pt_cruce = recortar_lineas_en_cruce(pts1_orig, pts2_orig)
            
            if pt_cruce:
                QgsMessageLog.logMessage(f"✂ Cruce detectado - L1: {len(pts1_orig)}→{len(pts1_rec)} pts | L2: {len(pts2_orig)}→{len(pts2_rec)} pts", 'HYDA', Qgis.Info)
                r1['puntos'] = pts1_rec
                r2['puntos'] = pts2_rec
                r1['num_puntos'] = len(pts1_rec)
                r2['num_puntos'] = len(pts2_rec)
                r1['longitud'] = QgsGeometry.fromPolylineXY(pts1_rec).length()
                r2['longitud'] = QgsGeometry.fromPolylineXY(pts2_rec).length()
                r1['punto_final'] = pts1_rec[-1]
                r2['punto_final'] = pts2_rec[-1]
            else:
                QgsMessageLog.logMessage("⚠ No se detectó cruce entre líneas", 'HYDA', Qgis.Warning)
            
            if len(self.pts_aux) > 0:
                QgsMessageLog.logMessage("Eval pto aux", 'HYDA', Qgis.Info)
                
                for pt_aux in self.pts_aux:
                    lin_c = None
                    d_min = float('inf')
                    idx_lin = -1
                    otra_pts = None
                    
                    for i, r in enumerate(res):
                        if len(r['puntos']) < 2:
                            continue
                        pt_fin = r['punto_final']
                        d = pt_fin.distance(pt_aux)
                        if d < d_min:
                            d_min = d
                            lin_c = r
                            idx_lin = i
                    
                    if lin_c is not None:
                        if len(res) >= 2:
                            otra_pts = res[1]['puntos'] if idx_lin == 0 else res[0]['puntos']
                        
                        QgsMessageLog.logMessage(f"L#{lin_c['numero']} cerc aux ({d_min:.1f}m)", 'HYDA', Qgis.Info)
                        lin_c['puntos'].append(pt_aux)
                        
                        r_cont = procesar_desde_auxiliar(pt_aux, self.idx_esp, self.curvas,
                            lin_c['elev_final'], lin_c['curvas_usadas'], otra_pts)
                        
                        if len(r_cont['puntos']) > 1:
                            lin_c['puntos'].extend(r_cont['puntos'][1:])
                            lin_c['elev_final'] = r_cont['elev_final']
                            lin_c['ganancia'] = lin_c['elev_final'] - lin_c['elev_inicial']
                            lin_c['num_puntos'] = len(lin_c['puntos'])
                            lin_c['salto_auxiliar'] = True
                            lin_c['razon'] = r_cont['razon']
                            lin_c['punto_final'] = r_cont['puntos'][-1] if r_cont['puntos'] else pt_aux
                            lin_c['longitud'] = QgsGeometry.fromPolylineXY(lin_c['puntos']).length()
                            QgsMessageLog.logMessage(f"✓ Ext: {r_cont['elev_inicial']}→{r_cont['elev_final']}m", 'HYDA', Qgis.Info)
                        else:
                            lin_c['salto_auxiliar'] = False
                            QgsMessageLog.logMessage("⚠ Sin curvas desde aux", 'HYDA', Qgis.Warning)
            
            self.res_lin = res
            
            if modo == 'editar' or modo == 'cargar':
                self.actualizar_poly_exist()
            else:
                self.crear_act_capas()
            
            QgsMessageLog.logMessage("="*60, 'HYDA', Qgis.Info)
            QgsMessageLog.logMessage("Divisorias OK", 'HYDA', Qgis.Info)
            
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error: {str(e)}", 'HYDA', Qgis.Critical)
            QgsMessageLog.logMessage(traceback.format_exc(), 'HYDA', Qgis.Critical)
            QMessageBox.critical(self.dlg, "Error", f"Error:\n\n{str(e)}")

    def actualizar_poly_exist(self):
        from .hyda_processor import crear_poligono_cuenca
        
        if self.poly_edit is None:
            QgsMessageLog.logMessage("No hay poly en edición", 'HYDA', Qgis.Warning)
            return
        
        capa_d = self.dlg.get_capa_destino()
        if not capa_d or not capa_d.isValid():
            QgsMessageLog.logMessage("Capa dest no válida", 'HYDA', Qgis.Warning)
            return
        
        if len(self.res_lin) < 2:
            QgsMessageLog.logMessage("No hay sufic líneas", 'HYDA', Qgis.Warning)
            return
        
        nuevo_p = crear_poligono_cuenca(self.res_lin[0]['puntos'], self.res_lin[1]['puntos'])
        
        if nuevo_p is None:
            return
        
        capa_d.startEditing()
        
        feat = capa_d.getFeature(self.poly_edit)
        if not feat.isValid():
            capa_d.rollBack()
            return
        
        capa_d.changeGeometry(self.poly_edit, nuevo_p)
        
        area_m2 = int(nuevo_p.area())
                
        if capa_d.fields().indexOf('Area_m2') != -1:
            capa_d.changeAttributeValue(self.poly_edit, capa_d.fields().indexOf('Area_m2'), area_m2)

        if capa_d.commitChanges():
            capa_d.triggerRepaint()
            self.poly_meta[self.poly_edit]['auxiliares'] = self.pts_aux.copy()
            self.poly_meta[self.poly_edit]['conexiones'] = self.pts_conexion.copy()
            QgsMessageLog.logMessage(f"✓ Poly {self.poly_edit} actualizado | Área: {area_m2} m²", 'HYDA', Qgis.Info)
        else:
            capa_d.rollBack()

    def crear_act_capas(self):
        from .hyda_processor import crear_poligono_cuenca
        
        if len(self.res_lin) < 2:
            QgsMessageLog.logMessage("No se pueden crear capas sin líneas", 'HYDA', Qgis.Warning)
            return

        poly_g = crear_poligono_cuenca(self.res_lin[0]['puntos'], self.res_lin[1]['puntos'])

        if poly_g is None:
            QgsMessageLog.logMessage("No se pudo crear poly cuenca", 'HYDA', Qgis.Warning)
            return

        capa_d = self.dlg.get_capa_destino()
        
        if not capa_d or not capa_d.isValid():
            QMessageBox.warning(self.dlg, "Advertencia", "Debe seleccionar una capa de salida válida")
            return

        area_m2 = int(poly_g.area())


        def aseg_campos(prov, layer):
            nuevos = []
            if layer.fields().indexOf('Area_m2') == -1:
                nuevos.append(QgsField('Area_m2', QVariant.Int))  # Int en vez de Double
            if nuevos:
                prov.addAttributes(nuevos)
                layer.updateFields()

        def set_atr(feat, layer):
            if layer.fields().indexOf('Area_m2') != -1:
                feat['Area_m2'] = area_m2

        try:
            if self.capa_topo and self.capa_topo.crs().isValid() and capa_d.crs().isValid() \
            and self.capa_topo.crs() != capa_d.crs():
                tr = QgsCoordinateTransform(self.capa_topo.crs(), capa_d.crs(), QgsProject.instance())
                poly_g.transform(tr)
        except Exception as e:
            QgsMessageLog.logMessage(f"Adv reproyec: {e}", 'HYDA', Qgis.Warning)

        prov_d = capa_d.dataProvider()
        aseg_campos(prov_d, capa_d)

        feat = QgsFeature(capa_d.fields())
        feat.setGeometry(poly_g)
        set_atr(feat, capa_d)

        capa_d.startEditing()
        ok = capa_d.addFeature(feat)
        
        if ok:
            if capa_d.commitChanges():
                capa_d.triggerRepaint()
                
                fids = [f.id() for f in capa_d.getFeatures()]
                if fids:
                    nuevo_fid = max(fids)
                    self.poly_meta[nuevo_fid] = {
                        'punto1': self.pts_ini[0],
                        'punto2': self.pts_ini[1],
                        'auxiliares': self.pts_aux.copy(),
                        'conexiones': self.pts_conexion.copy()
                    }
                    QgsMessageLog.logMessage(f"Poly agregado (FID: {nuevo_fid}) | Meta OK | Tot: {len(self.poly_meta)}", 'HYDA', Qgis.Info)
            else:
                QgsMessageLog.logMessage("Error commitChanges", 'HYDA', Qgis.Warning)
        else:
            capa_d.rollBack()
            QgsMessageLog.logMessage("No se pudo agregar poly", 'HYDA', Qgis.Warning)

    def limpiar_todo(self):
        self.pts_ini = []
        self.pts_aux = []
        self.pts_conexion = []
        self.poly_meta = {}
        self.poly_edit = None
        
        if self.mt_ini:
            self.mt_ini.reset()
            self.iface.mapCanvas().unsetMapTool(self.mt_ini)
        
        if self.mt_aux:
            self.mt_aux.reset()
            self.iface.mapCanvas().unsetMapTool(self.mt_aux)
        
        if self.mt_conexion:
            self.mt_conexion.reset()
            self.iface.mapCanvas().unsetMapTool(self.mt_conexion)
        
        if self.mt_sel:
            self.iface.mapCanvas().unsetMapTool(self.mt_sel)
            self.mt_sel = None
        
        self.iface.mapCanvas().setCursor(Qt.ArrowCursor)
        self.res_lin = []
        
        if self.capa_div:
            QgsProject.instance().removeMapLayer(self.capa_div.id())
            self.capa_div = None
        
        QgsMessageLog.logMessage("Plugin limpiado - listo", 'HYDA', Qgis.Info)
