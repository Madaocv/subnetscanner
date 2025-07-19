"""
Device Manager for Subnet Scanner

This module integrates the device registry with the main scanner,
allowing for a gradual migration to the plugin architecture.
"""
from typing import Dict, Any
from device_registry import DeviceRegistry

# Optional imports of device handlers
# Handlers will be loaded automatically when imported in the main script
# These are here just for IDE completion and documentation
# The actual imports should be in the main script (z15_fan_broker.py)


class DeviceManager:
    """
    Manager for device type detection and operations.
    Acts as a bridge between the registry pattern and the existing code.
    """
    
    def __init__(self, scanner):
        """
        Initialize with reference to scanner instance
        
        Args:
            scanner: Scanner instance with existing methods
        """
        self.scanner = scanner
    
    def detect_device_type(self, ip: str, verbose: bool = False) -> Dict[str, Any]:
        """
        Detect device type using registered detectors
        
        Args:
            ip: IP address to check
            verbose: Whether to print verbose output
            
        Returns:
            Dictionary with device_type and source
        """
        # Try each detector in the registry
        for device_type, detector_func in DeviceRegistry.get_detectors().items():
            try:
                if detector_func(ip, self.scanner.username, self.scanner.password, self.scanner.timeout):
                    if verbose:
                        print(f"✓ Detected {device_type} device at {ip}")
                    return {"device_type": device_type, "device_type_source": "registry"}
            except Exception as e:
                if verbose:
                    print(f"Error during {device_type} detection for {ip}: {str(e)}")
        
        # If no detector found the device type, return unknown
        if verbose:
            print(f"? Unknown device type at {ip}")
        return {"device_type": "unknown", "device_type_source": None}
    
    def fetch_logs_from_device(self, ip: str, device_type: str, verbose: bool = False) -> Dict[str, Any]:
        """
        Fetch logs using the appropriate handler for the device type
        
        Args:
            ip: IP address to fetch logs from
            device_type: Type of device (e.g., "T21", "S21")
            verbose: Whether to print verbose output
            
        Returns:
            Dictionary with log information
        """
        # Get the appropriate handler for this device type
        handler_class = DeviceRegistry.get_handler(device_type)
        
        if handler_class:
            try:
                # Get model config for this device type from site config
                model_config = {}
                if hasattr(self.scanner, 'site_config') and 'models' in self.scanner.site_config:
                    # Get normalized device type for config lookup
                    normalized_type = DeviceRegistry.normalize_device_type(device_type)
                    model_config = self.scanner.site_config.get('models', {}).get(normalized_type, {})
                    
                # Create handler with model configuration
                handler = handler_class(self.scanner, model_config)
                
                if verbose:
                    print(f"Using {device_type} handler with model config {model_config} to fetch logs from {ip}")
                
                return handler.fetch_logs(ip)
            except Exception as e:
                if verbose:
                    print(f"Error using {device_type} handler for {ip}: {str(e)}")
                return {
                    "ip": ip,
                    "status": "error",
                    "message": f"Error using {device_type} handler: {str(e)}"
                }
        else:
            return {
                "ip": ip, 
                "status": "error",
                "message": f"No handler registered for device type: {device_type}"
            }
