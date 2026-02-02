"""Image recognition package per Smart Fridge."""

from .camera_manager import CameraManager
from .yolo_detector import YOLODetector

__all__ = ['CameraManager', 'YOLODetector']