# -*- coding: utf-8 -*-
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QDockWidget, QWidget, QComboBox, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QFrame
from qgis.PyQt.QtCore import pyqtSignal, Qt, QSize
from qgis.PyQt.QtGui import QIcon, QPainter, QColor
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes
import os

class HYDADialog(QDockWidget):
    
    topoLoaded = pyqtSignal(object, str)
    puntoInicialMode = pyqtSignal(bool)
    puntoAuxiliarMode = pyqtSignal(bool)
    puntoConexionMode = pyqtSignal(bool)
    seleccionarPoligonoMode = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super(HYDADialog, self).__init__(parent)
        self.plugin_dir = os.path.dirname(__file__)
        self.capa_topo = None
        self.campo_elev = None
        self.capa_dest = None
        self.poly_sel_fid = None
        self.setupUi()
        
    def setupUi(self):
        self.setWindowTitle("HYDA - Hydrological Delimitation Assistant")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Configurar como flotante inicialmente
        self.setFloating(True)
        
        # Establecer ancho mínimo inicial
        self.setMinimumWidth(400)
        self.resize(400, 420)
        
        main_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(15, 15, 15, 10)
        
        # Estilo general - colores por defecto de plugins QGIS
        main_widget.setStyleSheet("""
            QDockWidget {
                font-size: 8pt;
            }
            QFrame {
                background-color: #EDEDED;
                border: 1px solid #D3D3D3;
                border-radius: 0px;
                padding: 5px;
            }
            QLabel {
                border: none;
                background-color: transparent;
                padding: 0px;
                margin: 0px;
            }
            QPushButton {
                padding: 5px;
                background-color: #e0e0e0;
                border: 1px solid #a0a0a0;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QPushButton:disabled {
                color: #a0a0a0;
                background-color: #f0f0f0;
            }
        """)
        
        # BLOQUE 1: Cargar Topografía
        lbl_topo_titulo = QLabel("<b>Topografía</b>")
        lbl_topo_titulo.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(lbl_topo_titulo)
        
        frame1 = QFrame()
        frame1_layout = QVBoxLayout()
        frame1_layout.setSpacing(3)
        frame1_layout.setContentsMargins(5, 5, 5, 5)
        
        lbl_capa = QLabel("Curvas de Nivel:")
        lbl_capa.setContentsMargins(0, 0, 0, 0)
        frame1_layout.addWidget(lbl_capa)
        
        self.combo_capa_topo = QComboBox()
        self.combo_capa_topo.currentIndexChanged.connect(self.on_capa_topo_changed)
        frame1_layout.addWidget(self.combo_capa_topo)
        
        lbl_elev = QLabel("Campo de Elevaciones:")
        lbl_elev.setContentsMargins(0, 5, 0, 0)
        frame1_layout.addWidget(lbl_elev)
        
        self.combo_campo_elev = QComboBox()
        frame1_layout.addWidget(self.combo_campo_elev)
        
        self.btn_cargar_topo = QPushButton("CARGAR")
        self.btn_cargar_topo.clicked.connect(self.cargar_topografia)
        self.btn_cargar_topo.setContentsMargins(0, 8, 0, 0)
        self.btn_cargar_topo.setStyleSheet("""
            QPushButton {
                background-color: #78909C;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #407072;
            }
            QPushButton:pressed {
                background-color: #2e5052;
            }
        """)
        frame1_layout.addWidget(self.btn_cargar_topo)
        
        frame1.setLayout(frame1_layout)
        layout.addWidget(frame1)
        
        # BLOQUE 2: Salida
        lbl_salida_titulo = QLabel("<b>Salida</b>")
        lbl_salida_titulo.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(lbl_salida_titulo)
        
        frame2 = QFrame()
        frame2_layout = QVBoxLayout()
        frame2_layout.setSpacing(3)
        frame2_layout.setContentsMargins(5, 5, 5, 5)
        
        lbl_salida = QLabel("Seleccionar capa de destino:")
        lbl_salida.setContentsMargins(0, 0, 0, 0)
        frame2_layout.addWidget(lbl_salida)
        
        self.combo_capa_dest = QComboBox()
        frame2_layout.addWidget(self.combo_capa_dest)
        
        frame2.setLayout(frame2_layout)
        layout.addWidget(frame2)
        
        # BLOQUE 3: Delimitación
        lbl_delim_titulo = QLabel("<b>Delimitación</b>")
        lbl_delim_titulo.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(lbl_delim_titulo)
        
        frame3 = QFrame()
        frame3_layout = QVBoxLayout()
        frame3_layout.setSpacing(5)
        frame3_layout.setContentsMargins(5, 5, 5, 5)
        
        # Fila con los 4 botones - justificados
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        # Botón A - Inicio (2.5x más ancho)
        icon_a = QIcon(os.path.join(self.plugin_dir, 'A.png'))
        self.btn_puntos_iniciales = QPushButton(icon_a, "")
        self.btn_puntos_iniciales.setText(" INICIO")
        self.btn_puntos_iniciales.setCheckable(True)
        self.btn_puntos_iniciales.setEnabled(False)
        self.btn_puntos_iniciales.clicked.connect(self.toggle_puntos_iniciales)
        self.btn_puntos_iniciales.setToolTip("Haga clic en el mapa para crear 2 puntos iniciales")
        self.btn_puntos_iniciales.setIconSize(QSize(30, 30))
        self.btn_puntos_iniciales.setMinimumHeight(40)
        self.btn_puntos_iniciales.setMinimumWidth(115)
        self.btn_puntos_iniciales.setStyleSheet("""
            QPushButton {
                font-size: 8.5pt;
                font-weight: bold;
                color: white;
                background-color: #0483AD;
                border: 1px solid #a0a0a0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #047092;
            }
            QPushButton:pressed {
                background-color: #24C2E2;
            }
            QPushButton:disabled {
                color: #a0a0a0;
                background-color: #f0f0f0;
            }
            QPushButton:checked {
                background-color: #1BAECB;
                border: 2px solid #1BAECB;
            }
        """)
        buttons_layout.addWidget(self.btn_puntos_iniciales)
        
        # Botón B - Seleccionar Polígono
        icon_b = QIcon(os.path.join(self.plugin_dir, 'B.png'))
        self.btn_seleccionar_poligono = QPushButton(icon_b, "")
        self.btn_seleccionar_poligono.setCheckable(True)
        self.btn_seleccionar_poligono.setEnabled(False)
        self.btn_seleccionar_poligono.clicked.connect(self.toggle_seleccionar_poligono)
        self.btn_seleccionar_poligono.setToolTip("Seleccionar polígono")
        self.btn_seleccionar_poligono.setIconSize(QSize(30, 30))
        self.btn_seleccionar_poligono.setFixedSize(40, 40)
        self.btn_seleccionar_poligono.setStyleSheet("""
            QPushButton {
                border-radius: 4px;
                background-color: #F2F2F2;
            }
            QPushButton:checked {
                background-color: #FFF7EB;
                border: 2px solid #FF9800;
            }
        """)
        buttons_layout.addWidget(self.btn_seleccionar_poligono)
        
        # Botón C - Puntos Directos
        icon_c = QIcon(os.path.join(self.plugin_dir, 'C.png'))
        self.btn_puntos_conexion = QPushButton(icon_c, "")
        self.btn_puntos_conexion.setCheckable(True)
        self.btn_puntos_conexion.setEnabled(False)
        self.btn_puntos_conexion.clicked.connect(self.toggle_puntos_conexion)
        self.btn_puntos_conexion.setToolTip("Puntos directos")
        self.btn_puntos_conexion.setIconSize(QSize(30, 30))
        self.btn_puntos_conexion.setFixedSize(40, 40)
        self.btn_puntos_conexion.setStyleSheet("""
            QPushButton {
                border-radius: 4px;
                background-color: #F2F2F2;
            }
            QPushButton:checked {
                background-color: #E2F1FE;
                border: 2px solid #1487F3;
            }
        """)
        buttons_layout.addWidget(self.btn_puntos_conexion)
        
        # Botón D - Puntos Auxiliares
        icon_d = QIcon(os.path.join(self.plugin_dir, 'D.png'))
        self.btn_puntos_auxiliares = QPushButton(icon_d, "")
        self.btn_puntos_auxiliares.setCheckable(True)
        self.btn_puntos_auxiliares.setEnabled(False)
        self.btn_puntos_auxiliares.clicked.connect(self.toggle_puntos_auxiliares)
        self.btn_puntos_auxiliares.setToolTip("Puntos auxiliares")
        self.btn_puntos_auxiliares.setIconSize(QSize(30, 30))
        self.btn_puntos_auxiliares.setFixedSize(40, 40)
        self.btn_puntos_auxiliares.setStyleSheet("""
            QPushButton {
                border-radius: 4px;
                background-color: #F2F2F2;
            }
            QPushButton:checked {
                background-color: #EDFAFD;
                border: 2px solid #24C2E2;
            }
        """)
        buttons_layout.addWidget(self.btn_puntos_auxiliares)
        
        # Sin addStretch() para que los botones se distribuyan
        frame3_layout.addLayout(buttons_layout)
        
        frame3.setLayout(frame3_layout)
        layout.addWidget(frame3)
        
        layout.addStretch()
        
        # Label de estado al final con check
        estado_layout = QHBoxLayout()
        estado_layout.setContentsMargins(0, 0, 0, 0)
        estado_layout.setSpacing(3)
        
        self.lbl_check = QLabel("✓")
        self.lbl_check.setStyleSheet("color: #4CAF50; font-size: 10pt; font-weight: bold;")
        self.lbl_check.setVisible(False)
        estado_layout.addWidget(self.lbl_check)
        
        self.lbl_estado = QLabel("Listo para delimitar")
        self.lbl_estado.setStyleSheet("color: #666666; font-style: italic; font-size: 7pt;")
        self.lbl_estado.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        estado_layout.addWidget(self.lbl_estado)
        
        estado_layout.addStretch()
        layout.addLayout(estado_layout)
        
        main_widget.setLayout(layout)
        self.setWidget(main_widget)
        
        # Actualizar capas al iniciar
        self.actualizar_capas()
        
    def actualizar_capas(self):
        curr_topo = self.combo_capa_topo.currentText()
        curr_dest = self.combo_capa_dest.currentText()
        
        self.combo_capa_topo.clear()
        self.combo_capa_dest.clear()
        
        layers = QgsProject.instance().mapLayers().values()
        
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):
                if layer.geometryType() == QgsWkbTypes.LineGeometry:
                    self.combo_capa_topo.addItem(layer.name(), layer)
        
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):
                if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    self.combo_capa_dest.addItem(layer.name(), layer)
        
        idx = self.combo_capa_topo.findText(curr_topo)
        if idx >= 0:
            self.combo_capa_topo.setCurrentIndex(idx)
            
        idx = self.combo_capa_dest.findText(curr_dest)
        if idx >= 0:
            self.combo_capa_dest.setCurrentIndex(idx)
    
    def on_capa_topo_changed(self):
        self.combo_campo_elev.clear()
        
        capa = self.combo_capa_topo.currentData()
        if capa:
            for field in capa.fields():
                if field.type() in [2, 3, 4, 6]:
                    self.combo_campo_elev.addItem(field.name())
    
    def cargar_topografia(self):
        capa = self.combo_capa_topo.currentData()
        campo = self.combo_campo_elev.currentText()
        
        if not capa:
            QMessageBox.warning(self, "Advertencia", "Seleccione una capa de topografía")
            return
        
        if not campo:
            QMessageBox.warning(self, "Advertencia", "Seleccione un campo de elevación")
            return
        
        self.actualizar_estado("Cargando topografía", mostrar_check=False)
        
        self.capa_topo = capa
        self.campo_elev = campo
        
        self.actualizar_estado("Topografía cargada", mostrar_check=True, color="#4CAF50")
        self.btn_puntos_iniciales.setEnabled(True)
        self.btn_seleccionar_poligono.setEnabled(True)
        
        self.topoLoaded.emit(capa, campo)
    
    def toggle_puntos_iniciales(self):
        if self.btn_puntos_iniciales.isChecked():
            # Al activar Inicio, resetear puntos auxiliares y conexiones
            from . import HYDA as hyda_module
            plugin = None
            
            # Buscar la instancia del plugin
            for obj in QtWidgets.QApplication.instance().allWidgets():
                if hasattr(obj, 'pts_aux') and hasattr(obj, 'pts_conexion'):
                    plugin = obj
                    break
            
            # Si encontramos el plugin, resetear sus puntos
            if plugin and hasattr(plugin, 'pts_aux'):
                plugin.pts_aux = []
                plugin.pts_conexion = []
                plugin.poly_edit = None
            
            # Desactivar otros modos
            if self.btn_puntos_auxiliares.isChecked():
                self.btn_puntos_auxiliares.setChecked(False)
                self.puntoAuxiliarMode.emit(False)
            
            if self.btn_puntos_conexion.isChecked():
                self.btn_puntos_conexion.setChecked(False)
                self.puntoConexionMode.emit(False)
            
            if self.btn_seleccionar_poligono.isChecked():
                self.btn_seleccionar_poligono.setChecked(False)
                self.seleccionarPoligonoMode.emit(False)
            
            self.actualizar_estado("Delimitando", mostrar_check=False, color="#7CB342")
            self.puntoInicialMode.emit(True)
        else:
            self.puntoInicialMode.emit(False)
    
    def toggle_seleccionar_poligono(self):
        if self.btn_seleccionar_poligono.isChecked():
            # Desactivar otros modos
            if self.btn_puntos_iniciales.isChecked():
                self.btn_puntos_iniciales.setChecked(False)
                self.puntoInicialMode.emit(False)
            
            if self.btn_puntos_auxiliares.isChecked():
                self.btn_puntos_auxiliares.setChecked(False)
                self.puntoAuxiliarMode.emit(False)
            
            if self.btn_puntos_conexion.isChecked():
                self.btn_puntos_conexion.setChecked(False)
                self.puntoConexionMode.emit(False)
            
            self.actualizar_estado("Seleccionar polígono", mostrar_check=False, color="#FF9800")
            self.seleccionarPoligonoMode.emit(True)
        else:
            self.seleccionarPoligonoMode.emit(False)
            self.poly_sel_fid = None
    
    def toggle_puntos_auxiliares(self):
        if self.btn_puntos_auxiliares.isChecked():
            # Desactivar otros modos
            if self.btn_puntos_iniciales.isChecked():
                self.btn_puntos_iniciales.setChecked(False)
                self.puntoInicialMode.emit(False)
            
            if self.btn_puntos_conexion.isChecked():
                self.btn_puntos_conexion.setChecked(False)
                self.puntoConexionMode.emit(False)
            
            if self.btn_seleccionar_poligono.isChecked():
                self.btn_seleccionar_poligono.setChecked(False)
                self.seleccionarPoligonoMode.emit(False)
            
            self.actualizar_estado("Modificando delimitación", mostrar_check=False, color="#24C2E2")
            self.puntoAuxiliarMode.emit(True)
        else:
            self.puntoAuxiliarMode.emit(False)
    
    def toggle_puntos_conexion(self):
        if self.btn_puntos_conexion.isChecked():
            # Desactivar otros modos
            if self.btn_puntos_iniciales.isChecked():
                self.btn_puntos_iniciales.setChecked(False)
                self.puntoInicialMode.emit(False)
            
            if self.btn_puntos_auxiliares.isChecked():
                self.btn_puntos_auxiliares.setChecked(False)
                self.puntoAuxiliarMode.emit(False)
            
            if self.btn_seleccionar_poligono.isChecked():
                self.btn_seleccionar_poligono.setChecked(False)
                self.seleccionarPoligonoMode.emit(False)
            
            self.actualizar_estado("Agregar puntos directos", mostrar_check=False, color="#1487F3")
            self.puntoConexionMode.emit(True)
        else:
            self.puntoConexionMode.emit(False)
    
    def actualizar_estado(self, mensaje, mostrar_check=False, color="#666666"):
        """Actualiza el mensaje de estado"""
        self.lbl_estado.setText(mensaje)
        self.lbl_estado.setStyleSheet(f"color: {color}; font-style: italic; font-size: 7pt;")
        
        if mostrar_check:
            self.lbl_check.setStyleSheet(f"color: {color}; font-size: 12pt; font-weight: bold;")
            self.lbl_check.setVisible(True)
        else:
            self.lbl_check.setVisible(False)
    
    def actualizar_info_poligono(self, fid, area_km2=None):
        """Actualiza la información del polígono seleccionado"""
        self.poly_sel_fid = fid
        
        if fid is not None:
            self.btn_seleccionar_poligono.setChecked(False)
            self.btn_puntos_auxiliares.setEnabled(True)
            self.btn_puntos_conexion.setEnabled(True)
            self.actualizar_estado("Polígono seleccionado", mostrar_check=True, color="#FF9800")
    
    def habilitar_puntos_auxiliares(self):
        """Habilita los botones de edición"""
        self.btn_puntos_auxiliares.setEnabled(True)
        self.btn_puntos_conexion.setEnabled(True)
    
    def desactivar_modo_puntos_iniciales(self):
        """Desactiva el modo de puntos iniciales"""
        if self.btn_puntos_iniciales.isChecked():
            self.btn_puntos_iniciales.setChecked(False)
            self.actualizar_estado("Delimitación creada", mostrar_check=True, color="#7CB342")
    
    def showEvent(self, event):
        """Se ejecuta cuando se muestra el diálogo"""
        super().showEvent(event)
        self.actualizar_capas()
    
    def closeEvent(self, event):
        """Se ejecuta cuando se cierra el diálogo - resetear todo"""
        # Desactivar todos los modos
        if self.btn_puntos_iniciales.isChecked():
            self.btn_puntos_iniciales.setChecked(False)
            self.puntoInicialMode.emit(False)
        
        if self.btn_puntos_auxiliares.isChecked():
            self.btn_puntos_auxiliares.setChecked(False)
            self.puntoAuxiliarMode.emit(False)
        
        if self.btn_puntos_conexion.isChecked():
            self.btn_puntos_conexion.setChecked(False)
            self.puntoConexionMode.emit(False)
        
        if self.btn_seleccionar_poligono.isChecked():
            self.btn_seleccionar_poligono.setChecked(False)
            self.seleccionarPoligonoMode.emit(False)
        
        # Resetear variables
        self.capa_topo = None
        self.campo_elev = None
        self.poly_sel_fid = None
        
        # Aceptar el evento de cierre
        event.accept()
    
    def get_capa_destino(self):
        """Retorna la capa de destino seleccionada"""
        return self.combo_capa_dest.currentData()