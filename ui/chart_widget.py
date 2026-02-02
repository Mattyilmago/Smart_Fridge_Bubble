"""
ChartWidget: widget riutilizzabile per visualizzare grafici a linea.
Mostra storico temporale con linea media tratteggiata.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis, QAreaSeries
from PyQt6.QtCore import Qt, QDateTime, QMargins
from PyQt6.QtGui import QPen, QColor, QFont, QPainter, QBrush
from datetime import datetime, timedelta
from typing import List, Optional
from data.data_manager import DataPoint
from config import (CHART_COLORS, CHART_X_AXIS_LABEL_INTERVAL, 
                   CHART_ANIMATION_DURATION, HISTORY_HOURS,
                   TEMPERATURE_THRESHOLDS, TEMPERATURE_ZONE_COLORS)


class ChartWidget(QWidget):
    """
    Widget per visualizzare grafico a linea con storico temporale.
    Features:
    - Linea principale con dati
    - Linea tratteggiata per la media
    - Asse X temporale (etichette ogni ora)
    - Asse Y auto-scaling
    - Label valore corrente
    """
    
    def __init__(self, title: str, unit: str, line_color: str, average_line_color: str, 
                 enable_temp_zones: bool = False, parent=None):
        """
        Inizializza il widget grafico.
        
        Args:
            title: Titolo del grafico (es. "Temperature")
            unit: Unità di misura (es. "°C")
            line_color: Colore linea principale (hex)
            average_line_color: Colore linea media (hex)
            enable_temp_zones: Se True, mostra zone colorate temperatura (verde/gialla/rossa)
            parent: Widget padre
        """
        super().__init__(parent)
        
        self.title = title
        self.unit = unit
        self.line_color = line_color
        self.average_line_color = average_line_color
        self.enable_temp_zones = enable_temp_zones
        
        # Liste per le serie delle zone (solo se abilitate)
        self.zone_series = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura layout e componenti UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Label valore corrente (grande, in alto)
        self.current_value_label = QLabel("-- " + self.unit)
        self.current_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        self.current_value_label.setFont(font)
        self.current_value_label.setStyleSheet(f"color: {self.line_color};")
        
        # Crea chart
        self.chart = QChart()
        self.chart.setTitle(self.title)
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.setAnimationDuration(CHART_ANIMATION_DURATION)
        self.chart.legend().hide()
        
        # Tema scuro
        self.chart.setBackgroundBrush(QColor(CHART_COLORS['background']))
        self.chart.setTitleBrush(QColor(CHART_COLORS['text']))
        
        # Crea zone temperatura colorate (se abilitate)
        if self.enable_temp_zones:
            self._create_temperature_zones()
        
        # Serie dati principale
        self.data_series = QLineSeries()
        pen = QPen(QColor(self.line_color))
        pen.setWidth(2)
        self.data_series.setPen(pen)
        self.chart.addSeries(self.data_series)
        
        # Serie media (linea tratteggiata)
        self.average_series = QLineSeries()
        avg_pen = QPen(QColor(self.average_line_color))
        avg_pen.setWidth(2)
        avg_pen.setStyle(Qt.PenStyle.DashLine)  # Linea tratteggiata
        self.average_series.setPen(avg_pen)
        self.chart.addSeries(self.average_series)
        
        # Asse X (tempo relativo)
        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("Time Ago")
        self.axis_x.setLabelsColor(QColor(CHART_COLORS['text']))
        self.axis_x.setLabelsVisible(True)
        self.axis_x.setLabelsAngle(-45)
        self.axis_x.setGridLineColor(QColor(CHART_COLORS['grid']))
        self.axis_x.setGridLineVisible(True)
        self.axis_x.setTickCount(7)
        self.axis_x.setReverse(True)  # Inverte l'asse: 0 a destra, valori crescenti a sinistra
        
        # Font per le label dell'asse X
        axis_font = QFont()
        axis_font.setPointSize(9)
        self.axis_x.setLabelsFont(axis_font)
        
        # Asse Y (valore)
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText(self.unit)
        self.axis_y.setLabelsColor(QColor(CHART_COLORS['text']))
        self.axis_y.setLabelsVisible(True)  # Assicura visibilità label
        self.axis_y.setGridLineColor(QColor(CHART_COLORS['grid']))
        self.axis_y.setGridLineVisible(True)
        self.axis_y.setTickCount(6)
        self.axis_y.setLabelsFont(axis_font)
        self.axis_y.setLabelFormat("%.1f")  # Massimo 1 decimali
        
        # Collega assi alle serie
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.data_series.attachAxis(self.axis_x)
        self.data_series.attachAxis(self.axis_y)
        self.average_series.attachAxis(self.axis_x)
        self.average_series.attachAxis(self.axis_y)
        
        # Collega assi alle zone temperatura (se abilitate)
        if self.enable_temp_zones:
            for zone_area, _, _ in self.zone_series:
                zone_area.attachAxis(self.axis_x)
                zone_area.attachAxis(self.axis_y)
        
        # Chart view con margini per le label
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Margini del chart per dare spazio alle label
        self.chart.setMargins(QMargins(10, 10, 10, 30))  # Extra spazio in basso per label ruotate
        
        # Aggiungi al layout
        layout.addWidget(self.current_value_label)
        layout.addWidget(self.chart_view)
        
        self.setLayout(layout)
    
    def _create_temperature_zones(self):
        """
        Crea le zone colorate di background per il grafico temperatura.
        - Verde: 0 - 6°C (safe)
        - Gialla: 6 - 8°C (warning)
        - Rossa: >8°C (danger)
        """
        # Zone boundaries
        safe_max = TEMPERATURE_THRESHOLDS['safe_max']
        warning_max = TEMPERATURE_THRESHOLDS['warning_max']
        
        # Zona VERDE (0 - 6°C)
        safe_lower = QLineSeries()
        safe_lower.append(0, 0)  # Placeholder, verrà aggiornato dinamicamente
        safe_lower.append(1, 0)
        
        safe_upper = QLineSeries()
        safe_upper.append(0, safe_max)
        safe_upper.append(1, safe_max)
        
        safe_area = QAreaSeries(safe_upper, safe_lower)
        safe_color = QColor(TEMPERATURE_ZONE_COLORS['safe'])
        safe_color.setAlpha(TEMPERATURE_ZONE_COLORS['zone_opacity'])
        safe_area.setBrush(QBrush(safe_color))
        safe_area.setPen(QPen(Qt.PenStyle.NoPen))  # Senza bordo
        self.chart.addSeries(safe_area)
        self.zone_series.append((safe_area, safe_lower, safe_upper))
        
        # Zona GIALLA (6 - 8°C)
        warning_lower = QLineSeries()
        warning_lower.append(0, safe_max)
        warning_lower.append(1, safe_max)
        
        warning_upper = QLineSeries()
        warning_upper.append(0, warning_max)
        warning_upper.append(1, warning_max)
        
        warning_area = QAreaSeries(warning_upper, warning_lower)
        warning_color = QColor(TEMPERATURE_ZONE_COLORS['warning'])
        warning_color.setAlpha(TEMPERATURE_ZONE_COLORS['zone_opacity'])
        warning_area.setBrush(QBrush(warning_color))
        warning_area.setPen(QPen(Qt.PenStyle.NoPen))
        self.chart.addSeries(warning_area)
        self.zone_series.append((warning_area, warning_lower, warning_upper))
        
        # Zona ROSSA (>8°C)
        danger_lower = QLineSeries()
        danger_lower.append(0, warning_max)
        danger_lower.append(1, warning_max)
        
        danger_upper = QLineSeries()
        danger_upper.append(0, warning_max + 10)  # Placeholder alto
        danger_upper.append(1, warning_max + 10)
        
        danger_area = QAreaSeries(danger_upper, danger_lower)
        danger_color = QColor(TEMPERATURE_ZONE_COLORS['danger'])
        danger_color.setAlpha(TEMPERATURE_ZONE_COLORS['zone_opacity'])
        danger_area.setBrush(QBrush(danger_color))
        danger_area.setPen(QPen(Qt.PenStyle.NoPen))
        self.chart.addSeries(danger_area)
        self.zone_series.append((danger_area, danger_lower, danger_upper))
        
        print(f"[ChartWidget-{self.title}] Temperature zones created")
    
    def _update_temperature_zones(self, max_value: float, min_y: float, max_y: float):
        """
        Aggiorna le coordinate X delle zone temperatura per coprire tutto il grafico.
        
        Args:
            max_value: Valore massimo asse X (tempo più vecchio)
            min_y: Valore minimo asse Y
            max_y: Valore massimo asse Y
        """
        if not self.enable_temp_zones or not self.zone_series:
            return
        
        safe_max = TEMPERATURE_THRESHOLDS['safe_max']
        warning_max = TEMPERATURE_THRESHOLDS['warning_max']
        
        # Helper per aggiornare una zona
        def update_zone(zone_idx, y_lower, y_upper):
            _, lower_series, upper_series = self.zone_series[zone_idx]
            lower_series.clear()
            lower_series.append(0, y_lower)
            lower_series.append(max_value, y_lower)
            upper_series.clear()
            upper_series.append(0, y_upper)
            upper_series.append(max_value, y_upper)
        
        # Aggiorna le tre zone: verde, gialla, rossa
        update_zone(0, min_y, safe_max)        # Verde: min → 6°C
        update_zone(1, safe_max, warning_max)  # Gialla: 6°C → 8°C
        update_zone(2, warning_max, max_y)     # Rossa: 8°C → max
    
    def update_chart(self, data_points: List[DataPoint], average: float):
        """
        Aggiorna il grafico con nuovi dati.
        
        Args:
            data_points: Lista di DataPoint da visualizzare
            average: Valore medio da mostrare come linea tratteggiata
        """
        if not data_points:
            print(f"[ChartWidget-{self.title}] No data points to display")
            return
        
        # Aggiorna label valore corrente
        current_value = data_points[-1].value
        self.current_value_label.setText(f"{current_value:.1f} {self.unit}")
        print(f"[ChartWidget-{self.title}] Updated with {len(data_points)} points, current: {current_value:.1f}{self.unit}")
        
        # Clear serie esistenti
        self.data_series.clear()
        self.average_series.clear()
        
        # Usa il punto più recente come riferimento (tempo = 0)
        most_recent_time = data_points[-1].timestamp
        oldest_data_time = data_points[0].timestamp
        
        # Calcola la differenza temporale totale in secondi
        total_seconds = (most_recent_time - oldest_data_time).total_seconds()
        
        # Determina unità base in base al superamento delle soglie naturali
        if total_seconds >= 3600:  # >= 1 ora (3600s)
            time_unit, final_divisor = 'h', 3600
        elif total_seconds >= 60:  # >= 1 minuto (60s)
            time_unit, final_divisor = 'm', 60
        else:  # < 1 minuto
            time_unit, final_divisor = 's', 1
        
        # Calcola il range massimo nell'unità scelta
        max_value = total_seconds / final_divisor
        display_unit = time_unit
        
        print(f"[ChartWidget-{self.title}] Using {time_unit}, range: {max_value:.1f}{time_unit}")
        
        # Aggiungi punti dati
        for point in data_points:
            time_ago = (most_recent_time - point.timestamp).total_seconds() / final_divisor
            self.data_series.append(time_ago, point.value)
        
        # Imposta formato label asse X
        label_formats = {'s': '%.0fs', 'm': '%.1fm', 'h': '%.1fh'}
        self.axis_x.setLabelFormat(label_formats[display_unit])
        
        # Aggiungi linea media
        self.average_series.append(0, average)
        self.average_series.append(max_value, average)
        
        # Aggiorna range asse X
        self.axis_x.setRange(0, max_value)
        
        # Auto-scale asse Y con margine e intervallo minimo
        if data_points:
            values = [p.value for p in data_points]
            min_val = min(values + [average])
            max_val = max(values + [average])
            range_val = max_val - min_val
            
            # Assicura un range minimo per evitare tick duplicati con 1 decimale
            # Con 6 tick, ogni tick deve avere almeno 0.1 di differenza
            # Quindi il range minimo è 6 * 0.1 = 0.6
            min_range = 0.6
            if range_val < min_range:
                # Espandi il range centrandolo sul valore medio
                center = (min_val + max_val) / 2
                min_val = center - min_range / 2
                max_val = center + min_range / 2
            else:
                # Aggiungi margine del 10%
                margin = range_val * 0.1
                min_val = min_val - margin
                max_val = max_val + margin
            
            self.axis_y.setRange(min_val, max_val)
            
            # Aggiorna zone temperatura se abilitate
            if self.enable_temp_zones:
                self._update_temperature_zones(max_value, min_val, max_val)