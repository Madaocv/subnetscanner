"""
S21 Device Handler for Subnet Scanner

This module provides implementation for S21 devices,
including detection logic and log handling.
"""
import json
import requests
from typing import Dict, Any, List
from requests.auth import HTTPDigestAuth

from device_socket_based_handler import SocketBasedHandler
from device_registry import DeviceRegistry


class S21Handler(SocketBasedHandler):
    """Handler for S21+ devices"""
    device_type = "S21+"
    
    def get_log_endpoint(self) -> str:
        """Return the log endpoint for S21+ devices"""
        return "/cgi-bin/hlog.cgi"
    

    
    def fetch_logs(self, ip: str) -> Dict[str, Any]:
        """
        Fetch logs from S21+ device using socket API
        
        Args:
            ip: IP address of the device
            
        Returns:
            Dictionary with fan status information
        """
        # Base result including device type info
        result = {
            "ip": ip,
            "status": "success",
            "device_type": "S21+",
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
    
    def parse_logs(self, log_content: str) -> Dict[str, Any]:
        """
        Parse S21+ log format
        
        Args:
            log_content: Raw log content as string
            
        Returns:
            Dictionary with parsed log information
        """
        # S21 logs format might differ, extract the most useful information
        log_lines = log_content.strip().split("\n")
        last_log_line = log_lines[-1] if log_lines else ""
        
        # Try to parse log components with regex
        date_part = ""
        time_part = ""
        message = last_log_line
        
        # Try to extract timestamp if present
        timestamp_match = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(.*)", last_log_line)
        if timestamp_match:
            date_part = timestamp_match.group(1)
            time_part = timestamp_match.group(2)
            message = timestamp_match.group(3)
        
        return {
            "status": "success",
            "date": date_part,
            "time": time_part,
            "source": "S21+",
            "message": message,
            "raw_log": last_log_line
        }
    
    def normalize_message(self, message: str) -> str:
        """
        Normalize S21+ error messages for consistent grouping
        
        Args:
            message: Original error message
            
        Returns:
            Normalized message for grouping
        """
        # For S21 hashrate info messages, could optionally normalize formatting
        # but for now we'll maintain them as is since they're typically unique per device
        # and contain important specific values
        
        # Return original message if no normalization rules match
        return message
    
    @classmethod
    def detect(cls, ip: str, username: str, password: str, timeout: int) -> bool:
        """Detect if an IP is an S21+ device using socket API"""
        try:
            # Create a handler instance to use the socket command method
            handler = cls(None)  # None for scanner as it's not needed for this call
            
            # Send stats command to get device information
            stats = handler.send_socket_command(ip, "stats", timeout=timeout)
            
            # Check if we received a valid response
            if "STATS" in stats and len(stats["STATS"]) > 0:
                # Get device type from stats
                if "Type" in stats["STATS"][0]:
                    device_type = stats["STATS"][0]["Type"]
                    # S21+ detection
                    if "S21+" in device_type or "S21\+" in device_type or "S21" in device_type:
                        return True
        except Exception:
            pass
            
        return False


# Register the handler and detector with the registry
DeviceRegistry.register_handler("S21+", S21Handler)
DeviceRegistry.register_detector("S21+", S21Handler.detect)
