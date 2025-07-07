"""
S19j Pro Device Handler for Subnet Scanner

This module provides implementation for S19j Pro devices,
including detection logic and log handling via socket communication.
"""
import requests
from typing import Dict, Any, List
from requests.auth import HTTPDigestAuth

from device_socket_based_handler import SocketBasedHandler
from device_registry import DeviceRegistry


class S19jProHandler(SocketBasedHandler):
    """Handler for S19j Pro devices"""
    device_type = "S19j Pro"
    

    
    def fetch_logs(self, ip: str) -> Dict[str, Any]:
        """
        Fetch logs from S19j Pro device using socket API
        
        Args:
            ip: IP address of the device
            
        Returns:
            Dictionary with fan status information
        """
        # Base result including device type info
        result = {
            "ip": ip,
            "status": "success",
            "device_type": "S19j Pro",
            "device_type_source": "registry"
        }
        
        try:
            # Send the stats command to get fan information
            stats = self.send_socket_command(ip, "stats", timeout=self.scanner.timeout)
            
            if "error" in stats:
                raise Exception(stats["error"])
            
            # Extract device type from STATS section if available
            miner_type = self.get_device_type_from_stats(stats)
            if miner_type:
                result["miner_type"] = miner_type
            
            # Extract fan status using the base class method
            failed_fans, fan_data, error_msg = self.extract_fan_status(stats)
            
            if error_msg:
                result["status"] = "error"
                result["message"] = error_msg
                result["error_type"] = "fan_data_error"
                return result
            
            # Add fan status information
            if failed_fans > 0:
                result["message"] = self.get_default_fan_message(failed_fans)
            else:
                # All fans are OK - return empty message to ignore successful checks
                result["message"] = ""
                result["ignore_success"] = True
            
            # Store raw fan data for reference
            result["fan_data"] = fan_data
                
        except Exception as e:
            # Handle all other errors
            result["status"] = "error"
            result["message"] = f"Error fetching fan status: {str(e)}"
            result["error_type"] = "unknown_error"
            
        return result
    
    def normalize_message(self, message: str) -> str:
        """
        Normalize S19j Pro error messages for consistent grouping
        
        Args:
            message: Original error message
            
        Returns:
            Normalized message for grouping
        """
        # For now, we'll use the exact message as provided
        return message
        
    def parse_logs(self, log_content: str) -> List[str]:
        """
        Parse logs from S19j Pro device
        
        Args:
            log_content: Raw log content
            
        Returns:
            List of parsed log entries
        """
        # For socket-based miner communication, we don't actually parse logs from text
        # Instead, we just return an empty list since we get structured data from the socket API
        return []
    
    @classmethod
    def detect(cls, ip: str, username: str, password: str, timeout: int) -> bool:
        """Detect if an IP is a S19j Pro device using socket API"""
        try:
            # Create a handler instance to use the socket command method
            handler = cls(None)  # None for scanner as it's not needed for this call
            
            # Send stats command to get device information
            stats = handler.send_socket_command(ip, "stats", timeout=timeout)
            
            # Check if we got a valid response
            if "error" in stats:
                return False
                
            # Check if this is an S19j Pro by looking at the Type field
            if "STATS" in stats and len(stats["STATS"]) >= 1:
                miner_type = stats["STATS"][0].get("Type", "")
                if miner_type and ("S19j Pro" in miner_type or "Antminer S19j Pro" in miner_type):
                    return True
            
            # If we get here, it's not an S19j Pro
            return False
            
        except Exception:
            # Any exception means we couldn't detect the device
            return False


# Register the handler and detector with the registry
DeviceRegistry.register_handler("S19j Pro", S19jProHandler)
DeviceRegistry.register_detector("S19j Pro", S19jProHandler.detect)
