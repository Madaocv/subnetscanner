"""
S21 Device Handler for Subnet Scanner

This module provides implementation for S21 devices,
including detection logic and log handling.
"""
import re
import requests
from typing import Dict, Any, List
from requests.auth import HTTPDigestAuth

from device_handler import DeviceHandler
from device_registry import DeviceRegistry


class S21Handler(DeviceHandler):
    """Handler for S21+ devices"""
    device_type = "S21+"
    
    def get_log_endpoint(self) -> str:
        """Return the log endpoint for S21+ devices"""
        return "/cgi-bin/hlog.cgi"
    
    def fetch_logs(self, ip: str) -> Dict[str, Any]:
        """
        Fetch logs from S21+ device using HTTP with special headers
        
        Args:
            ip: IP address of the device
            
        Returns:
            Dictionary with log information
        """
        url = f"http://{ip}{self.get_log_endpoint()}"
        auth = HTTPDigestAuth(self.scanner.username, self.scanner.password)
        
        try:
            # Add specific headers for S21 request
            headers = {
                'Accept': 'text/plain, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # Fetch logs
            response = requests.get(url, auth=auth, headers=headers, timeout=self.scanner.timeout, verify=False)
            
            if response.status_code == 200:
                return self.parse_logs(response.text)
            else:
                return {
                    "ip": ip,
                    "status": "error",
                    "error_code": response.status_code,
                    "message": f"Failed to fetch S21 logs. Status code: {response.status_code}"
                }
        except requests.RequestException as e:
            return {
                "ip": ip,
                "status": "error",
                "message": f"Request exception for S21 logs: {str(e)}"
            }
    
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
        """
        Detect if an IP is an S21+ device
        
        Args:
            ip: IP address to check
            username: Username for authentication
            password: Password for authentication
            timeout: Request timeout
            
        Returns:
            True if the IP is an S21 device, False otherwise
        """
        # -------------------------------------------------------
        # This exactly matches the logic in detect_device_type for S21 devices
        # -------------------------------------------------------
        
        # Try system info endpoint first
        url = f"http://{ip}/cgi-bin/get_system_info.cgi"
        auth = HTTPDigestAuth(username, password)
        
        try:
            response = requests.get(url, auth=auth, timeout=timeout, verify=False)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "minertype" in data:
                        device_type = data["minertype"]
                        # S21+ detection
                        if "S21+" in device_type or "S21\+" in device_type or "S21" in device_type:
                            return True
                except Exception:
                    pass
        except Exception:
            pass
            
        # If we get here, none of the S21-specific APIs responded
        return False


# Register the handler and detector with the registry
DeviceRegistry.register_handler("S21+", S21Handler)
DeviceRegistry.register_detector("S21+", S21Handler.detect)
