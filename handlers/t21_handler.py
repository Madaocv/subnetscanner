"""
T21 Device Handler for Subnet Scanner

This module provides implementation for T21 devices,
including detection logic and log handling.
"""
import re
import json
import ssl
import time
import datetime
import asyncio
import threading
import requests
from typing import Dict, Any, List
from requests.auth import HTTPDigestAuth

from device_handler import DeviceHandler
from device_registry import DeviceRegistry

# Try importing websocket packages
# First, try the asyncio-based websockets package (preferred)
try:
    import websockets
    WEBSOCKETS_ASYNCIO_AVAILABLE = True
except ImportError:
    WEBSOCKETS_ASYNCIO_AVAILABLE = False

# As a fallback, try the older websocket-client package
try:
    import websocket
    WEBSOCKET_CLIENT_AVAILABLE = True
except ImportError:
    WEBSOCKET_CLIENT_AVAILABLE = False

# Define if any websocket capability is available
WEBSOCKET_AVAILABLE = WEBSOCKETS_ASYNCIO_AVAILABLE or WEBSOCKET_CLIENT_AVAILABLE


class T21Handler(DeviceHandler):
    """Handler for T21 devices"""
    device_type = "T21"
    
    def get_log_endpoint(self) -> str:
        """Return the WebSocket endpoint for T21 logs"""
        return "/api/v1/logs-ws/status"
    
    def fallback_get_logs(self, ip: str) -> Dict[str, Any]:
        """
        Fallback method when websocket connection fails
        
        Args:
            ip: IP address of the device
            
        Returns:
            Dictionary with log information
        """
        # Return an honest connection error message
        return {
            "ip": ip,
            "status": "error",
            "device_type": "T21",
            "device_type_source": "registry",
            "message": "Could not connect to logs WebSocket endpoint",
            "error_type": "connection_error"
        }
    
    def fetch_logs(self, ip: str) -> Dict[str, Any]:
        """
        Fetch logs from T21 device using WebSocket
        
        Args:
            ip: IP address of the device
            
        Returns:
            Dictionary with log information
        """
        # Get logs via WebSocket for T21
        endpoint = self.get_log_endpoint()
        timeout = self.scanner.timeout
        result = self.fetch_logs_via_websocket(ip, endpoint, timeout)
        
        # Update device type to T21 if it was different
        result["device_type"] = "T21"
        result["device_type_source"] = "registry"
        
        return result
    
    def fetch_logs_via_websocket(self, ip: str, endpoint: str = "/api/v1/logs-ws/status", timeout: int = 10) -> Dict[str, Any]:
        """
        Fetch logs from a device via WebSocket connection using the approach from t21_logs_client.py
        
        Args:
            ip: IP address of the device
            endpoint: WebSocket endpoint for logs (default: /api/v1/logs-ws/status)
            timeout: Connection timeout in seconds
            
        Returns:
            Dictionary with log information
        """
        # Base result including device type info
        result = {
            "ip": ip,
            "status": "success",
            "device_type": "T21",
            "device_type_source": "registry"
        }
        
        # Get today's date for filtering logs (in both formats used in the devices)
        today_date = datetime.datetime.now().strftime('%Y/%m/%d')
        today_short = datetime.datetime.now().strftime('%m/%d')
        
        # Log pattern matches format like: [2025/06/28 09:23:01] INFO: Performance settings setup completed
        log_pattern = r'\[(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+(\w+):\s+(.+)'
        
        # Try websockets (asyncio) approach first if available
        if WEBSOCKETS_ASYNCIO_AVAILABLE:
            ws_url = f"ws://{ip}{endpoint}"
            
            async def fetch_logs_async():
                raw_logs = []
                valid_logs = []
                
                try:
                    # Connect to WebSocket - одне просте підключення
                    async with websockets.connect(ws_url) as ws:
                        try:
                            # Get one message with timeout
                            message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                            
                            if isinstance(message, str):
                                # Save the received message
                                raw_logs.append(message)
                                
                                # Split the message into lines
                                log_lines = message.splitlines()
                                
                                # Find all valid logs - lines that start with a date in [YYYY/MM/DD] format
                                for line in log_lines:
                                    if line.strip().startswith('[') and ']' in line:
                                        # Try to parse the log
                                        match = re.match(log_pattern, line)
                                        if match:
                                            timestamp, level, log_message = match.groups()
                                            log_entry = {
                                                'timestamp': timestamp,
                                                'level': level,
                                                'message': log_message
                                            }
                                            valid_logs.append(log_entry)
                        
                        except asyncio.TimeoutError:
                            # Timeout while waiting for a message
                            pass
                        except Exception as e:
                            # Other error when receiving a message
                            print(f"WebSocket error: {e}")
                    
                    return valid_logs
                
                except Exception as e:
                    # Connection error
                    print(f"WebSocket connection error: {e}")
                    return []
            
            # Run the async function
            valid_logs = asyncio.run(fetch_logs_async())
            
            # Process the logs
            if not valid_logs:
                # No logs were found
                return self.fallback_get_logs(ip)
            
            # Sort logs by timestamp (oldest first, newest last)
            valid_logs.sort(key=lambda log: log['timestamp'])
            
            # Select the freshest log (last in the list)
            last_log = valid_logs[-1]
            result["message"] = last_log['message']  # Only the message itself, without timestamp and level
            result["time"] = last_log['timestamp'].split()[1]  # Extract time part
            result["date"] = last_log['timestamp'].split()[0]  # Extract date part
            result["level"] = last_log['level']
            result["logs"] = valid_logs[-10:] if len(valid_logs) > 10 else valid_logs  # Save the last 10 logs
            
            return result
            
        # Fallback to websocket-client if asyncio version is not available
        elif WEBSOCKET_CLIENT_AVAILABLE:
            ws_url = f"ws://{ip}{endpoint}"
            log_messages = []
            
            try:
                # Connect to WebSocket with a timeout (legacy client)
                ws = websocket.create_connection(
                    ws_url,
                    timeout=timeout,
                    sslopt={"cert_reqs": ssl.CERT_NONE}
                )
                
                # Receive log messages
                for _ in range(10):  # Try to get more logs
                    try:
                        message = ws.recv()
                        if message:
                            # Try to parse as text with regex
                            match = re.match(log_pattern, message)
                            if match:
                                timestamp, level, log_message = match.groups()
                                log_entry = {
                                    'timestamp': timestamp,
                                    'level': level,
                                    'message': log_message
                                }
                                log_messages.append(log_entry)
                    except Exception:
                        break
                
                # Close connection
                try:
                    ws.close()
                except Exception:
                    pass
                    
                # Process logs like the asyncio version
                if log_messages:
                    # Filter today's logs
                    today_logs = [log for log in log_messages if log['timestamp'].startswith(today)]
                    
                    # Use today's logs if available, otherwise use all
                    logs_to_use = today_logs if today_logs else log_messages
                    
                    # Use the last log for the main result
                    last_log = logs_to_use[-1]
                    result["message"] = f"[{last_log['timestamp']}] {last_log['level']}: {last_log['message']}"
                    result["time"] = last_log['timestamp'].split()[1]  # Extract time part
                    result["date"] = last_log['timestamp'].split()[0]  # Extract date part
                    result["level"] = last_log['level']
                    result["logs"] = logs_to_use[:10] if len(logs_to_use) > 10 else logs_to_use
                    
                    return result
                else:
                    return self.fallback_get_logs(ip)
                    
            except Exception:
                return self.fallback_get_logs(ip)
                
        # If we get here, something went wrong with both methods
        return self.fallback_get_logs(ip)
    
    def parse_logs(self, log_content: str) -> Dict[str, Any]:
        """
        Parse T21 log format (plain text with timestamps)
        
        Args:
            log_content: Raw log content
            
        Returns:
            Parsed log data
        """
        logs = []
        today_logs = []
        last_log = ""
        
        # Parse logs line by line
        for line in log_content.splitlines():
            # Extract timestamp and message using regex
            match = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.*)', line)
            if match:
                timestamp, level, message = match.groups()
                log_entry = {
                    "timestamp": timestamp,
                    "level": level, 
                    "message": message
                }
                logs.append(log_entry)
                
                # Get today's logs
                if self._is_today(timestamp):
                    today_logs.append(log_entry)
                
                # Update last log
                last_log = message
        
        # Use today's logs if available, otherwise use all logs
        final_logs = today_logs if today_logs else logs
        
        # Limit to last 10 logs
        final_logs = final_logs[-10:] if len(final_logs) > 10 else final_logs
        
        return {
            "status": "success",
            "source": "T21-WebSocket",
            "message": last_log,
            "logs": final_logs
        }
    
    async def _fetch_logs_via_asyncio_websocket(self, ws_url: str, timeout: int) -> Dict[str, Any]:
        """
        Fetch logs using asyncio WebSocket
        
        Args:
            ws_url: WebSocket URL
            timeout: Connection timeout in seconds
            
        Returns:
            Dictionary with log information
        """
        messages = []
        
        try:
            async with websockets.connect(ws_url, ssl=None, close_timeout=timeout) as websocket:
                # Set a timeout for receiving messages
                while True:
                    try:
                        # Wait for a message with timeout
                        message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                        messages.append(message)
                    except asyncio.TimeoutError:
                        # Stop when no more messages received within timeout
                        break
                    except Exception as e:
                        break
            
            if messages:
                logs = "\n".join(messages)
                return {
                    "ip": ws_url.split("//")[1].split("/")[0].split(":")[0],  # Extract IP from URL
                    "status": "ok",
                    "raw_content": logs,
                    "content_type": "text"
                }
            else:
                return {
                    "ip": ws_url.split("//")[1].split("/")[0].split(":")[0],
                    "status": "error",
                    "message": "No messages received from WebSocket within timeout"
                }
                
        except Exception as e:
            return {
                "ip": ws_url.split("//")[1].split("/")[0].split(":")[0],
                "status": "error",
                "message": f"WebSocket asyncio error: {str(e)}"
            }
    
    def _is_today(self, timestamp: str) -> bool:
        """
        Check if timestamp is from today
        
        Args:
            timestamp: Timestamp string in format "YYYY-MM-DD HH:MM:SS"
            
        Returns:
            True if the timestamp is from today
        """
        from datetime import datetime
        
        # Extract date part from the timestamp
        date_part = timestamp.split()[0]  # "YYYY-MM-DD"
        today = datetime.now().strftime('%Y-%m-%d')
        
        return date_part == today
    
    def normalize_message(self, message: str) -> str:
        """
        Normalize T21 error messages for consistent grouping
        
        Args:
            message: Original error message
            
        Returns:
            Normalized message for grouping
        """
        # For T21 errors, normalize common patterns related to pools
        if any(pattern in message for pattern in ["Pools", "pool"]):
            if "wrong format" in message:
                return "Pools not specifed or have wrong format"
            elif "specify" in message:
                return "Need to specify at least one pool"
        
        # Return original message if no normalization rules match
        return message
    
    @classmethod
    def detect(cls, ip: str, username: str, password: str, timeout: int) -> bool:
        """
        Detect if an IP is a T21 device
        
        Args:
            ip: IP address to check
            username: Username for authentication
            password: Password for authentication
            timeout: Request timeout
        Returns:
            True if the IP is a T21 device, False otherwise
        """
        # -------------------------------------------------------
        # This exactly matches the logic in detect_device_type for T21 devices
        # -------------------------------------------------------
        # Try API v1 summary endpoint
        url = f"http://{ip}/api/v1/summary"
        auth = HTTPDigestAuth(username, password)
        
        try:
            response = requests.get(url, auth=auth, timeout=timeout, verify=False)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "miner" in data and "miner_type" in data["miner"]:
                        device_type = data["miner"]["miner_type"]
                        # T21 detection
                        if "T21" in device_type:
                            return True
                except Exception:
                    pass
        except Exception:
            pass
        # If we get here, none of the T21-specific APIs responded
        return False


# Register the handler and detector with the registry
DeviceRegistry.register_handler("T21", T21Handler)
DeviceRegistry.register_detector("T21", T21Handler.detect)
