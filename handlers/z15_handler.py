"""
Z15 Device Handler for Subnet Scanner

This module provides implementation for Z15 devices,
including detection logic and log handling.
"""
import re
import json
import requests
from typing import Dict, Any, List
from requests.auth import HTTPDigestAuth

from device_handler import DeviceHandler
from device_registry import DeviceRegistry


class Z15Handler(DeviceHandler):
    """Handler for Z15 devices"""
    device_type = "Z15"
    
    def get_log_endpoint(self) -> str:
        """Return the standard log endpoint for Z15 devices"""
        return "/cgi-bin/get_kernel_log.cgi"
    
    def fetch_logs(self, ip: str) -> Dict[str, Any]:
        """
        Fetch logs from Z15 device using standard CGI endpoint
        
        Args:
            ip: IP address of the device
            
        Returns:
            Dictionary with log information
        """
        # Use standard log fetching for Z15
        url = f"http://{ip}{self.get_log_endpoint()}"
        auth = HTTPDigestAuth(self.scanner.username, self.scanner.password)
        
        try:
            response = requests.get(url, auth=auth, timeout=self.scanner.timeout, verify=False)
            
            if response.status_code == 200:
                return self.parse_logs(response.text)
            else:
                return {
                    "ip": ip,
                    "status": "error", 
                    "error_code": response.status_code,
                    "message": f"Failed to fetch Z15 logs. Status code: {response.status_code}"
                }
        except requests.RequestException as e:
            return {
                "ip": ip,
                "status": "error",
                "message": f"Request exception for Z15 logs: {str(e)}"
            }
    
    def parse_logs(self, log_content: str) -> Dict[str, Any]:
        """
        Parse Z15 log format (JSON)
        
        Args:
            log_content: Raw log content
            
        Returns:
            Dictionary with parsed log information
        """
        try:
            # Z15 logs are usually in JSON format
            log_data = json.loads(log_content)
            
            # Extract log message from the JSON structure
            if "log" in log_data:
                message = log_data["log"].strip() if log_data["log"] else "No log message"
                
                return {
                    "ip": "",  # Will be filled in by the caller
                    "status": "success",
                    "source": "Z15",
                    "message": message,
                    "raw_log": log_data["log"]
                }
        except json.JSONDecodeError:
            # If not valid JSON, try to extract useful info from text
            lines = log_content.strip().split("\n")
            last_line = lines[-1] if lines else ""
            
            return {
                "ip": "",
                "status": "success",
                "source": "Z15-text",
                "message": last_line,
                "raw_log": last_line
            }
    
    def normalize_message(self, message: str) -> str:
        """
        Normalize Z15 error messages for consistent grouping
        
        Args:
            message: Original error message
            
        Returns:
            Normalized message for grouping
        """
        # For Z15 fan errors, normalize to ignore timestamps
        if "Fan find, check again" in message:
            import re
            match = re.search(r'No \d+ Fan find, check again', message)
            if match:
                return match.group(0)
        
        # Return original message if no normalization rules match
        return message
    
    @classmethod
    def detect(cls, ip: str, username: str, password: str, timeout: int) -> bool:
        """
        Detect if an IP is a Z15 device
        
        Args:
            ip: IP address to check
            username: Username for authentication
            password: Password for authentication
            timeout: Request timeout
            
        Returns:
            True if the IP is a Z15 device, False otherwise
        """
        # -------------------------------------------------------
        # This exactly matches the logic in detect_device_type for Z15 devices
        # -------------------------------------------------------
        
        # Try system info endpoint first (Z15 devices)
        url = f"http://{ip}/cgi-bin/get_system_info.cgi"
        auth = HTTPDigestAuth(username, password)
        
        try:
            response = requests.get(url, auth=auth, timeout=timeout, verify=False)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "minertype" in data:
                        device_type = data["minertype"]
                        # Z15 detection
                        if "Antminer Z15" == device_type:
                            return True
                except Exception:
                    pass
        except Exception:
            pass
            
        # If we get here, none of the Z15-specific APIs responded
        return False


# Register the handler and detector with the registry
DeviceRegistry.register_handler("Z15", Z15Handler)
DeviceRegistry.register_detector("Z15", Z15Handler.detect)
