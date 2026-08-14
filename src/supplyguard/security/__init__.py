"""Onion-architecture security primitives (L2/L3: sanitization + injection)."""

from .injection_detector import InjectionDetector, InjectionScanOutput

__all__ = ["InjectionDetector", "InjectionScanOutput"]
