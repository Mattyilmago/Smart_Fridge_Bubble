"""
YOLODetector: gestisce il riconoscimento prodotti usando YOLOv8.
Responsabilità:
- Caricamento modello YOLO
- Detection su immagini
- Aggregazione risultati da multiple camere
- Conteggio prodotti (quantità)
- Generazione JSON output
"""

from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter
from logger.logger import get_logger, log_error_for_server

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


class YOLODetector:
    """
    Gestisce il riconoscimento prodotti alimentari usando YOLOv8.
    Supporta modelli custom e conta automaticamente le quantità.
    """
    
    def __init__(self, model_path: str = "yolov8n.pt",
                 confidence_threshold: float = 0.5,
                 max_retries: int = 2):
        """
        Inizializza il detector YOLO.
        
        Args:
            model_path: Path del modello YOLO (.pt file)
            confidence_threshold: Soglia minima di confidence per detection (0-1)
            max_retries: Numero massimo di retry su errore detection
        """
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.max_retries = max_retries
        
        self.logger = get_logger('yolo')
        
        self.model: Optional[YOLO] = None
        self._is_initialized = False
        
        if not YOLO_AVAILABLE:
            self.logger.error("ultralytics YOLO not available - install with: pip install ultralytics")
        else:
            self.logger.info(f"YOLODetector initialized (model: {model_path}, confidence: {confidence_threshold})")
    
    def initialize(self) -> bool:
        """
        Carica il modello YOLO in memoria.
        
        Returns:
            bool: True se caricamento riuscito, False altrimenti
        """
        if not YOLO_AVAILABLE:
            self.logger.error("Cannot initialize: YOLO not available")
            return False
        
        try:
            self.logger.info(f"Loading YOLO model from {self.model_path}...")
            
            # Verifica che il modello esista
            if not self.model_path.exists():
                # Se il modello non esiste, scarica quello di default
                self.logger.warning(f"Model file not found at {self.model_path}")
                self.logger.info("Downloading default YOLOv8n model...")
                self.model_path = Path("yolov8n.pt")
            
            # Carica modello
            self.model = YOLO(str(self.model_path))
            
            # Test che il modello funzioni
            self.logger.info("Testing model...")
            # Crea immagine dummy per test
            import numpy as np
            dummy_image = np.zeros((640, 640, 3), dtype=np.uint8)
            _ = self.model(dummy_image, verbose=False)
            
            self._is_initialized = True
            self.logger.info("Model loaded and tested successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load YOLO model: {e}")
            error_data = log_error_for_server(
                'yolo',
                'ModelLoadError',
                f"Failed to load model from {self.model_path}",
                str(e)
            )
            return False
    
    def detect_products_from_images(self, image_paths: List[str]) -> List[Dict]:
        """
        Rileva prodotti da una lista di immagini (dalle multiple camere).
        Aggrega i risultati e conta le quantità.
        
        Args:
            image_paths: Lista di path delle immagini da analizzare
        
        Returns:
            List[Dict]: Lista prodotti nel formato:
                       [{"nomeProdotto": "X", "marchio": "Y", "taglia": "Z", "quantita": N}, ...]
        """
        if not self._is_initialized:
            self.logger.error("Detector not initialized. Call initialize() first.")
            return []
        
        if not image_paths:
            self.logger.warning("No images provided for detection")
            return []
        
        self.logger.info(f"Starting detection on {len(image_paths)} image(s)...")
        
        # Aggrega tutti i prodotti rilevati da tutte le immagini
        all_detected_products = []
        
        for img_path in image_paths:
            products = self._detect_from_single_image(img_path)
            all_detected_products.extend(products)
        
        # Conta quantità aggregate
        aggregated = self._aggregate_products(all_detected_products)
        
        self.logger.info(f"Detection complete: {len(aggregated)} unique product(s) found")
        return aggregated
    
    def _detect_from_single_image(self, image_path: str) -> List[Dict]:
        """
        Rileva prodotti da una singola immagine con retry.
        
        Args:
            image_path: Path dell'immagine
        
        Returns:
            List[Dict]: Lista prodotti rilevati (ogni detection è un item separato)
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Detecting from {Path(image_path).name} (attempt {attempt + 1}/{self.max_retries})")
                
                # Run inference
                results = self.model(
                    image_path,
                    conf=self.confidence_threshold,
                    verbose=False
                )
                
                # Estrai prodotti dalle detection
                products = []
                
                for result in results:
                    boxes = result.boxes
                    
                    for box in boxes:
                        # Estrai informazioni detection
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        class_name = result.names[class_id]
                        
                        # Crea dizionario prodotto
                        # NOTA: Per ora usiamo class_name come nomeProdotto
                        # Quando avrai un modello custom, qui potrai estrarre marchio/taglia
                        product = self._parse_product_info(class_name, confidence)
                        products.append(product)
                
                self.logger.debug(f"Found {len(products)} product(s) in {Path(image_path).name}")
                return products
                
            except Exception as e:
                self.logger.warning(f"Detection failed (attempt {attempt + 1}): {e}")
                
                # Se ultimo tentativo, logga errore per server
                if attempt == self.max_retries - 1:
                    error_data = log_error_for_server(
                        'yolo',
                        'DetectionError',
                        f"Failed to detect products from {image_path}",
                        str(e)
                    )
        
        return []
    
    def _parse_product_info(self, class_name: str, confidence: float) -> Dict:
        """
        Estrae informazioni prodotto dal nome della classe YOLO.
        
        NOTA: Con modello generico (COCO), le classi sono generiche tipo "bottle", "apple", ecc.
        Con un modello custom addestrato, class_name potrebbe essere "CocaCola_1.5L" e qui
        puoi fare parsing per estrarre marchio/taglia.
        
        Args:
            class_name: Nome classe riconosciuta da YOLO
            confidence: Confidence score della detection
        
        Returns:
            Dict: Informazioni prodotto
        """
        # ===== PARSING MODELLO GENERICO (COCO) =====
        # Classi COCO comuni per cibo: bottle, apple, orange, banana, sandwich, etc.
        
        # Per ora: mapping semplice nome classe → prodotto
        # TODO: Quando avrai modello custom, implementa parsing avanzato
        
        product = {
            'nomeProdotto': class_name.capitalize(),  # Es: "bottle" → "Bottle"
            'marchio': 'Generic',  # Placeholder - sostituire con parsing da modello custom
            'taglia': 'N/A',       # Placeholder
            'quantita': 1,         # Ogni detection conta come 1 item
            '_confidence': confidence  # Info interna (può essere utile per debug)
        }
        
        # ===== PARSING MODELLO CUSTOM (esempio futuro) =====
        # Esempio: class_name = "CocaCola_1.5L_Bottle"
        # Se il tuo modello custom usa convenzione tipo "Marchio_Taglia_Tipo":
        """
        parts = class_name.split('_')
        if len(parts) >= 2:
            product['marchio'] = parts[0]  # "CocaCola"
            product['taglia'] = parts[1]   # "1.5L"
            product['nomeProdotto'] = parts[-1] if len(parts) > 2 else parts[0]  # "Bottle"
        """
        
        return product
    
    def _aggregate_products(self, products: List[Dict]) -> List[Dict]:
        """
        Aggrega prodotti identici e conta le quantità.
        
        Args:
            products: Lista prodotti (con quantita=1 ciascuno)
        
        Returns:
            List[Dict]: Lista aggregata con quantità aggiornate
        """
        if not products:
            return []
        
        # Crea chiave univoca per ogni prodotto: (nome, marchio, taglia)
        # Usa Counter per contare occorrenze
        product_keys = []
        product_map = {}  # key → dizionario prodotto
        
        for product in products:
            key = (
                product['nomeProdotto'],
                product['marchio'],
                product['taglia']
            )
            product_keys.append(key)
            
            # Salva template del prodotto (senza quantità)
            if key not in product_map:
                product_map[key] = {
                    'nomeProdotto': product['nomeProdotto'],
                    'marchio': product['marchio'],
                    'taglia': product['taglia']
                }
        
        # Conta occorrenze
        counts = Counter(product_keys)
        
        # Crea lista aggregata
        aggregated = []
        for key, count in counts.items():
            product = product_map[key].copy()
            product['quantita'] = count
            aggregated.append(product)
        
        # Ordina per nome prodotto (opzionale, per output consistente)
        aggregated.sort(key=lambda p: p['nomeProdotto'])
        
        self.logger.debug(f"Aggregated {len(products)} detections into {len(aggregated)} unique products")
        return aggregated
    
    def create_products_json(self, products: List[Dict]) -> Dict:
        """
        Crea il JSON finale nel formato richiesto per il server.
        
        Args:
            products: Lista prodotti aggregati
        
        Returns:
            Dict: JSON nel formato {"prodotti": [...]}
        """
        # Rimuovi campi interni (es. _confidence) prima di generare JSON
        clean_products = []
        for product in products:
            clean = {
                'nomeProdotto': product['nomeProdotto'],
                'marchio': product['marchio'],
                'taglia': product['taglia'],
                'quantita': product['quantita']
            }
            clean_products.append(clean)
        
        return {'prodotti': clean_products}
    
    def get_model_info(self) -> Dict:
        """
        Ritorna informazioni sul modello caricato.
        
        Returns:
            Dict: Info modello (path, classi, ecc.)
        """
        if not self._is_initialized or not self.model:
            return {'error': 'Model not initialized'}
        
        try:
            return {
                'model_path': str(self.model_path),
                'num_classes': len(self.model.names),
                'class_names': list(self.model.names.values())[:10],  # Prime 10 classi
                'confidence_threshold': self.confidence_threshold
            }
        except:
            return {'error': 'Unable to retrieve model info'}
    
    def cleanup(self):
        """Libera risorse del modello."""
        if self.model:
            # YOLO di ultralytics non ha cleanup esplicito, 
            # ma possiamo rimuovere il riferimento per garbage collection
            self.model = None
            self.logger.info("YOLO model released")
        
        self._is_initialized = False