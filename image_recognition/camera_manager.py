"""
CameraManager: gestisce acquisizione immagini dalle GoPro USB.
Responsabilità:
- Discovery automatico dispositivi video
- Cattura foto da multiple camere
- Salvataggio immagini con timestamp
- Gestione errori e retry
"""

import cv2
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple
from logger.logger import get_logger, log_error_for_server


class CameraManager:
    """
    Gestisce l'acquisizione di immagini da webcam USB (GoPro).
    Supporta multiple camere e retry automatico.
    """
    
    def __init__(self, image_dir: str = "captured_images", 
                 resolution: Tuple[int, int] = (1280, 720),
                 warmup_frames: int = 5,
                 max_retries: int = 3):
        """
        Inizializza il gestore camere.
        
        Args:
            image_dir: Directory dove salvare le immagini catturate
            resolution: Risoluzione immagini (width, height)
            warmup_frames: Numero di frame da scartare prima della cattura (per stabilizzare)
            max_retries: Numero massimo di retry per cattura fallita
        """
        self.image_dir = Path(image_dir)
        self.image_dir.mkdir(exist_ok=True)
        
        self.resolution = resolution
        self.warmup_frames = warmup_frames
        self.max_retries = max_retries
        
        self.logger = get_logger('camera')
        
        # Lista dispositivi video disponibili
        self.camera_devices: List[int] = []
        
        # Cache oggetti VideoCapture (MANTENIAMO APERTI per evitare problemi disconnessione)
        self._captures = {}
        
        self.logger.info(f"CameraManager initialized (resolution: {resolution[0]}x{resolution[1]})")
    
    def discover_cameras(self) -> int:
        """
        Scopre automaticamente i dispositivi video disponibili.
        Testa /dev/video0, /dev/video1, ... fino a trovare quelli funzionanti.
        
        Returns:
            int: Numero di camere trovate
        """
        self.logger.info("Discovering video devices...")
        self.camera_devices.clear()
        
        # Testa fino a 31 dispositivi (su Raspberry con molti device interni serve range più ampio)
        # Salta dispositivi interni noti del Raspberry Pi
        skip_devices = [10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 31]  # bcm2835 devices
        
        for device_id in range(31):
            # Salta dispositivi interni del Raspberry
            if device_id in skip_devices:
                continue
                
            try:
                # Usa backend V4L2 esplicito (migliore per USB su Linux)
                cap = cv2.VideoCapture(device_id, cv2.CAP_V4L2)
                
                if cap.isOpened():
                    # Imposta risoluzione prima di testare
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                    
                    # Scarta primi frame di warmup
                    for _ in range(3):
                        cap.read()
                    
                    # Testa se riesce effettivamente a leggere un frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        self.camera_devices.append(device_id)
                        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        self.logger.info(f"Found camera at /dev/video{device_id} ({actual_w}x{actual_h})")
                    else:
                        self.logger.debug(f"Device {device_id} opened but cannot read frames")
                
                cap.release()
            except Exception as e:
                self.logger.debug(f"Error testing device {device_id}: {e}")
        
        if not self.camera_devices:
            self.logger.error("No video devices found!")
        else:
            self.logger.info(f"Discovery complete: {len(self.camera_devices)} camera(s) found")
        
        return len(self.camera_devices)
    
    def initialize_cameras(self) -> bool:
        """
        Inizializza e apre tutte le camere scoperte.
        Le mantiene aperte per evitare problemi di disconnessione.
        
        Returns:
            bool: True se tutte inizializzate, False altrimenti
        """
        if not self.camera_devices:
            self.logger.error("No cameras discovered. Run discover_cameras() first.")
            return False
        
        self.logger.info("Initializing cameras...")
        all_ok = True
        
        for device_id in self.camera_devices:
            try:
                cap = cv2.VideoCapture(device_id, cv2.CAP_V4L2)
                
                if not cap.isOpened():
                    self.logger.error(f"Failed to open /dev/video{device_id}")
                    all_ok = False
                    continue
                
                # Imposta risoluzione
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                
                # Warmup iniziale
                for _ in range(3):
                    cap.read()
                
                # Salva nella cache
                self._captures[device_id] = cap
                self.logger.info(f"Camera /dev/video{device_id} initialized and ready")
                
            except Exception as e:
                self.logger.error(f"Error initializing /dev/video{device_id}: {e}")
                all_ok = False
        
        return all_ok
    
    def capture_images(self, label: str = "fridge") -> List[str]:
        """
        Cattura immagini da tutte le camere disponibili.
        
        Args:
            label: Etichetta per i nomi file (es. "fridge" -> "fridge_cam0_20240101_120000.jpg")
        
        Returns:
            List[str]: Lista dei path delle immagini catturate con successo
        """
        if not self.camera_devices:
            self.logger.error("No cameras available. Run discover_cameras() first.")
            return []
        
        captured_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for device_id in self.camera_devices:
            image_path = self._capture_from_device(device_id, label, timestamp)
            if image_path:
                captured_files.append(image_path)
        
        self.logger.info(f"Captured {len(captured_files)}/{len(self.camera_devices)} images")
        return captured_files
    
    def _capture_from_device(self, device_id: int, label: str, timestamp: str) -> Optional[str]:
        """
        Cattura singola immagine da un dispositivo specifico usando la cache.
        
        Args:
            device_id: ID del dispositivo video
            label: Etichetta per nome file
            timestamp: Timestamp per nome file
        
        Returns:
            Optional[str]: Path dell'immagine salvata o None se fallito
        """
        # Usa camera dalla cache se disponibile
        if device_id in self._captures:
            cap = self._captures[device_id]
        else:
            # Se non in cache, prova ad aprirla
            self.logger.warning(f"Camera {device_id} not in cache, opening now...")
            cap = cv2.VideoCapture(device_id, cv2.CAP_V4L2)
            if not cap.isOpened():
                self.logger.error(f"Cannot open /dev/video{device_id}")
                return None
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self._captures[device_id] = cap
        
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Capturing from /dev/video{device_id} (attempt {attempt + 1}/{self.max_retries})")
                
                # Warmup: scarta primi frame per stabilizzare esposizione/bilanciamento bianco
                self.logger.debug(f"Warming up camera (discarding {self.warmup_frames} frames)...")
                for _ in range(self.warmup_frames):
                    cap.read()
                
                # Cattura frame
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    raise RuntimeError("Failed to capture frame")
                
                # Salva immagine
                filename = f"{label}_cam{device_id}_{timestamp}.jpg"
                filepath = self.image_dir / filename
                
                cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                
                self.logger.info(f"Image saved: {filepath}")
                return str(filepath)
                
            except Exception as e:
                self.logger.warning(f"Capture failed (attempt {attempt + 1}): {e}")
                
                # Se ultimo tentativo, logga errore per server
                if attempt == self.max_retries - 1:
                    error_data = log_error_for_server(
                        'camera',
                        'CameraCaptureError',
                        f"Failed to capture from /dev/video{device_id} after {self.max_retries} attempts",
                        str(e)
                    )
        
        return None
    
    def test_cameras(self) -> bool:
        """
        Testa che tutte le camere scoperte funzionino correttamente.
        Utile per diagnostica all'avvio.
        
        Returns:
            bool: True se tutte le camere funzionano, False altrimenti
        """
        if not self.camera_devices:
            self.logger.error("No cameras to test. Run discover_cameras() first.")
            return False
        
        self.logger.info("Testing all cameras...")
        all_ok = True
        
        for device_id in self.camera_devices:
            cap = cv2.VideoCapture(device_id, cv2.CAP_V4L2)
            
            if not cap.isOpened():
                self.logger.error(f"Camera /dev/video{device_id}: FAILED (cannot open)")
                all_ok = False
                continue
            
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                self.logger.info(f"Camera /dev/video{device_id}: OK (resolution: {frame.shape[1]}x{frame.shape[0]})")
            else:
                self.logger.error(f"Camera /dev/video{device_id}: FAILED (cannot read frame)")
                all_ok = False
        
        return all_ok
    
    def cleanup(self):
        """Libera risorse (chiude eventuali capture aperte)."""
        for cap in self._captures.values():
            try:
                cap.release()
            except:
                pass
        
        self._captures.clear()
        self.logger.info("Camera cleanup complete")
    
    def get_camera_count(self) -> int:
        """
        Ritorna il numero di camere disponibili.
        
        Returns:
            int: Numero di camere
        """
        return len(self.camera_devices)
    
    def get_latest_images(self, max_age_seconds: int = 60) -> List[str]:
        """
        Ritorna le immagini catturate più recenti.
        Utile per recuperare le immagini dopo la cattura per passarle a YOLO.
        
        Args:
            max_age_seconds: Età massima delle immagini in secondi (default: 60s)
        
        Returns:
            List[str]: Lista path immagini recenti
        """
        if not self.image_dir.exists():
            return []
        
        now = datetime.now()
        recent_images = []
        
        for img_file in self.image_dir.glob("*.jpg"):
            # Timestamp da nome file: fridge_cam0_20240101_120000.jpg
            try:
                parts = img_file.stem.split('_')
                if len(parts) >= 4:
                    timestamp_str = f"{parts[-2]}_{parts[-1]}"
                    img_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    age = (now - img_time).total_seconds()
                    if age <= max_age_seconds:
                        recent_images.append(str(img_file))
            except:
                continue
        
        return sorted(recent_images)  # Ordina per nome (quindi per timestamp)