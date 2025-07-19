"""
Device Handler Interface for Subnet Scanner

This module provides the base interface for device handlers,
which implement device-specific operations like log fetching and parsing.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from device_registry import DeviceRegistry


class DeviceHandler(ABC):
    """
    Base class for device handlers.
    Each device type should implement its own handler.
    """
    device_type = None
    
    def __init__(self, scanner, model_config=None):
        """
        Initialize the handler with a reference to the scanner and model configuration
        
        Args:
            scanner: Scanner instance with methods like fetch_logs_from_ip
            model_config: Configuration for this device model from site config
        """
        self.scanner = scanner
        self.model_config = model_config or {}
    
    @abstractmethod
    def fetch_logs(self, ip: str) -> Dict[str, Any]:
        """
        Fetch logs from this device type
        
        Args:
            ip: IP address of the device
            
        Returns:
            Dictionary with log information
        """
        pass
    
    def get_log_endpoint(self) -> str:
        """
        Return the endpoint URL used for logs
        
        Returns:
            String with the endpoint path
        """
        # Default implementation, can be overridden
        return "/cgi-bin/get_kernel_log.cgi"
    
    @abstractmethod
    def parse_logs(self, log_content: str) -> Dict[str, Any]:
        """
        Parse logs in the device-specific format
        
        Args:
            log_content: Raw log content as string
            
        Returns:
            Parsed log information as dictionary
        """
        pass
        
    def normalize_message(self, message: str) -> str:
        """
        Normalize error messages for consistent grouping
        
        This method should be implemented by device-specific handlers to normalize
        error messages and group similar errors together.
        
        Args:
            message: Original error message
            
        Returns:
            Normalized message for grouping
        """
        # Default implementation returns the original message unchanged
        return message
    
    def get_expected_fans_from_config(self) -> int:
        """
        Get expected number of fans from model configuration
        
        Returns:
            Number of expected fans according to site configuration
        """
        # Get fan count from model configuration, with fallback to default value
        return self.model_config.get('fans', 2)  # Default to 2 fans if not specified
    
    @classmethod
    def register(cls):
        """
        Register this handler with the device registry
        """
        if cls.device_type:
            DeviceRegistry.register_handler(cls.device_type, cls)
