"""
Device Registry for Subnet Scanner

This module provides a registry for device type detectors and handlers,
allowing for a flexible plugin architecture to support multiple device types.
"""
from typing import Dict, Any, Callable, Type


class DeviceRegistry:
    """
    Registry for device detectors and handlers.
    Serves as a central registry for all supported device types.
    """
    _detectors = {}
    _handlers = {}
    
    @classmethod
    def register_detector(cls, device_type: str, detector_func: Callable):
        """
        Register a detector function for a specific device type
        
        Args:
            device_type: Name of the device type (e.g., "T21", "S21")
            detector_func: Function that detects if a device is of this type
        """
        cls._detectors[device_type] = detector_func
        
    @classmethod
    def register_handler(cls, device_type: str, handler_class: Type):
        """
        Register a handler class for a specific device type
        
        Args:
            device_type: Name of the device type (e.g., "T21", "S21")
            handler_class: Class that handles operations for this device type
        """
        cls._handlers[device_type] = handler_class
    
    @classmethod
    def get_detectors(cls):
        """Get all registered device detectors"""
        return cls._detectors
    
    @classmethod
    def reorder_detectors(cls, preferred_order=None):
        """
        Reorder detectors to prioritize specific device types first
        
        Args:
            preferred_order: List of device types in order of detection priority
                            (types listed first will be checked first)
        """
        if not preferred_order:
            return
            
        # Make a copy of the current detectors
        current_detectors = dict(cls._detectors)
        
        # Clear the detectors
        cls._detectors = {}
        
        # Add detectors back in preferred order
        for device_type in preferred_order:
            if device_type in current_detectors:
                cls._detectors[device_type] = current_detectors.pop(device_type)
        
        # Add remaining detectors
        for device_type, detector in current_detectors.items():
            cls._detectors[device_type] = detector
        
    @classmethod
    def get_handler(cls, device_type: str):
        """Get handler for specific device type"""
        return cls._handlers.get(device_type)
        
    @classmethod
    def normalize_device_type(cls, device_type: str) -> str:
        """
        Normalize device type string to a standardized format
        
        This method extracts the main model from a potentially longer device type string,
        ensuring consistent representation across the application.
        
        Args:
            device_type: The raw device type string
            
        Returns:
            Normalized device type string
        """
        if device_type == "unknown":
            return "unknown"
            
        # Extract the main model from full device type string
        # Check for specific device types first (more specific before less specific)
        if "Z15j" in device_type:
            return "Z15j"
        elif "Z15" in device_type:
            return "Z15"
        elif "T21" in device_type:
            return "T21"
        elif "S21 Pro" in device_type or "S21Pro" in device_type:  # For S21 Pro devices
            return "S21 Pro"
        elif "S21+" in device_type:  # For S21+ devices
            return "S21+"
        else:
            # For any other models, extract the model number (e.g., Antminer XXX -> XXX)
            import re
            model_match = re.search(r'Antminer\s+([A-Z]\d+[\+]*)', device_type)
            if model_match:
                return model_match.group(1)
            else:
                # Use the full string if we can't extract a specific model
                return device_type
