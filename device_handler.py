"""
Device Handler Interface for Subnet Scanner

This module provides the base interface for device handlers,
which implement device-specific operations like log fetching and parsing.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from device_registry import DeviceRegistry


class DeviceHandler(ABC):
    """
    Base class for device handlers.
    Each device type should implement its own handler.
    """
    device_type = None
    
    def __init__(self, scanner):
        """
        Initialize the handler with a reference to the scanner
        
        Args:
            scanner: Scanner instance with methods like fetch_logs_from_ip
        """
        self.scanner = scanner
    
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
    

    
    @classmethod
    def register(cls):
        """
        Register this handler with the device registry
        """
        if cls.device_type:
            DeviceRegistry.register_handler(cls.device_type, cls)
