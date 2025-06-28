"""
DG1+ Device Handler for Subnet Scanner

This module provides implementation for DG1+ devices,
including detection logic and log handling.
"""
import re
import json
import requests
from typing import Dict, Any, List
from requests.auth import HTTPDigestAuth

from device_handler import DeviceHandler
from device_registry import DeviceRegistry


class DG1Handler(DeviceHandler):
    """Handler for DG1+ devices"""
    device_type = "DG1+"
    
    def get_log_endpoint(self) -> str:
        """Return the log endpoint for DG1+ devices"""
        return "/cgi-bin/hlog.cgi"
    
    @classmethod
    def get_info_endpoint(cls) -> str:
        """Return the system info endpoint for DG1+ devices"""
        return "/cgi-bin/get_system_info.cgi"
    
    @classmethod
    def detect(cls, ip: str, username: str, password: str, timeout: int) -> bool:
        """
        Detect if the device at the given IP is a DG1+ device
        
        Args:
            ip: IP address to check
            username: Username for authentication
            password: Password for authentication
            timeout: Request timeout in seconds
            
        Returns:
            True if device is detected as DG1+
        """
        try:
            # Try to get system info
            info_url = f"http://{ip}{cls.get_info_endpoint()}"
            auth = HTTPDigestAuth(username, password)
            
            response = requests.get(info_url, auth=auth, timeout=timeout, verify=False)
            
            if response.status_code == 200:
                # Try to parse JSON response
                try:
                    info = response.json()
                    # Check for minertype attribute
                    if info.get("minertype") == "DG1+":
                        return True
                except json.JSONDecodeError:
                    pass
            
            return False
        except requests.RequestException:
            return False
    
    def fetch_logs(self, ip: str) -> Dict[str, Any]:
        """
        Fetch logs from DG1+ device using HTTP with special headers
        
        Args:
            ip: IP address of the device
            
        Returns:
            Dictionary with log information
        """
        url = f"http://{ip}{self.get_log_endpoint()}"
        auth = HTTPDigestAuth(self.scanner.username, self.scanner.password)
        
        try:
            # Add specific headers for request
            headers = {
                'Accept': 'text/plain, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # Fetch logs
            response = requests.get(url, auth=auth, headers=headers, timeout=self.scanner.timeout, verify=False)
            
            if response.status_code == 200:
                return self.parse_logs(response.text, ip)
            else:
                return {
                    "ip": ip,
                    "status": "error",
                    "error_code": response.status_code,
                    "message": f"Failed to fetch DG1+ logs. Status code: {response.status_code}"
                }
        except requests.RequestException as e:
            return {
                "ip": ip,
                "status": "error",
                "message": f"Request exception for DG1+ logs: {str(e)}"
            }
    
    def parse_logs(self, log_content: str, ip: str) -> Dict[str, Any]:
        """
        Parse DG1+ log format
        
        Args:
            log_content: Raw log content as string
            ip: IP address of the device
            
        Returns:
            Dictionary with parsed log information
        """
        # Extract log lines
        log_lines = log_content.strip().split("\n")
        if not log_lines:
            return {
                "ip": ip,
                "status": "error",
                "message": "No log content found"
            }
        
        # Get the last (most recent) log line
        last_log_line = log_lines[-1]
        
        # Try to parse log components with regex
        date_part = ""
        time_part = ""
        message = last_log_line
        
        # Try to extract timestamp if present (format may vary)
        timestamp_match = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(.*)", last_log_line)
        if timestamp_match:
            date_part = timestamp_match.group(1)
            time_part = timestamp_match.group(2)
            message = timestamp_match.group(3)
        
        return {
            "ip": ip,
            "status": "success",
            "device_type": "DG1+",
            "device_type_source": "detected",
            "date": date_part,
            "time": time_part,
            "message": message,
            "raw_log": last_log_line,
            "logs": log_lines[-10:] if len(log_lines) > 10 else log_lines  # Store up to 10 most recent logs
        }
    
    def normalize_message(self, message: str) -> str:
        """
        Normalize DG1+ error messages for consistent grouping
        
        Args:
            message: Raw message string
            
        Returns:
            Normalized message string
        """
        # Remove timestamps, IP addresses, and other variable parts
        normalized = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'IP_ADDRESS', message)
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', normalized)
        normalized = re.sub(r'\d{2}:\d{2}:\d{2}', 'TIME', normalized)
        
        return normalized


# Register the handler and detector with the registry
DeviceRegistry.register_handler("DG1+", DG1Handler)
DeviceRegistry.register_detector("DG1+", DG1Handler.detect)
