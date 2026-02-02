"""
AdsWidget: widget per visualizzare pubblicità tramite iframe web.
Usa QWebEngineView per renderizzare contenuti web.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtCore import QUrl
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    
from config import DEFAULT_ADS_URL


class AdsWidget(QWidget):
    """
    Widget per visualizzare pubblicità da URL.
    Wrappa QWebEngineView per mostrare iframe/pagine web.
    """
    
    def __init__(self, parent=None):
        """Inizializza il widget pubblicità."""
        super().__init__(parent)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura layout e webview."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Usa WebView se disponibile, altrimenti usa un placeholder
        if WEBENGINE_AVAILABLE:
            # WebView per mostrare contenuti web
            self.web_view = QWebEngineView()
            
            # Carica URL di default
            self.load_url(DEFAULT_ADS_URL)
            
            layout.addWidget(self.web_view)
        else:
            # Placeholder se WebEngine non è disponibile
            label = QLabel("Ads Area\n(WebEngine not available)")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: #2b2b2b; color: #888; font-size: 18px;")
            layout.addWidget(label)
            
        self.setLayout(layout)
    
    def load_url(self, url: str):
        """
        Carica un nuovo URL nel webview.
        
        Args:
            url: URL da caricare (completo con http:// o https://)
        """
        if not WEBENGINE_AVAILABLE:
            print("[AdsWidget] WebEngine not available, skipping URL load")
            return
            
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        print(f"[AdsWidget] Loading URL: {url}")
        self.web_view.setUrl(QUrl(url))
    
    def load_html(self, html: str):
        """
        Carica HTML direttamente (utile per contenuti dinamici).
        
        Args:
            html: Stringa HTML da renderizzare
        """
        self.web_view.setHtml(html)