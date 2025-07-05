"""
Socket-Based Device Handler for Subnet Scanner

This module provides a base implementation for device handlers that use socket communication,
reducing duplication across socket-based handlers like S19j Pro, S21, S21 Pro, and T21.
"""
import json
import socket
from typing import Dict, Any, List, Optional, Tuple

from device_handler import DeviceHandler


class SocketBasedHandler(DeviceHandler):
    """Base handler for devices that support socket API communication"""
    
    def send_socket_command(self, ip: str, command: str, port: int = 4028, timeout: int = 5) -> Dict[Any, Any]:
        """
        Send a command to the miner's socket API and return the parsed JSON response
        
        Args:
            ip: IP address of the miner
            command: Command to send (e.g., "stats", "summary", "pools")
            port: Port for socket API (default: 4028)
            timeout: Timeout in seconds
            
        Returns:
            Parsed JSON response or error message
        """
        try:
            # Create socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            
            # Connect to the miner
            s.connect((ip, port))
            
            # Prepare the command in JSON format
            payload = json.dumps({"command": command}).encode()
            
            # Send the command
            s.sendall(payload)
            
            # Receive response
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
            
            # Close the connection
            s.close()
            
            # Try to parse as JSON
            try:
                # Remove any trailing null bytes or % character
                response_str = response.decode('utf-8').rstrip('\0').rstrip('%')
                
                # Try standard JSON parsing first
                try:
                    return json.loads(response_str)
                except json.JSONDecodeError:
                    # Some miners (like Z15j) produce malformed JSON where objects are not separated by commas
                    # Try to fix common JSON errors
                    fixed_json = self.fix_malformed_json(response_str)
                    if fixed_json:
                        return fixed_json
                    
                return {"error": "Invalid JSON response", "raw": response.decode('utf-8', errors='replace')}
            except Exception as e:
                return {"error": f"JSON parsing error: {str(e)}", "raw": response.decode('utf-8', errors='replace')}
                
        except socket.timeout:
            return {"error": "Connection timed out"}
        except ConnectionRefusedError:
            return {"error": "Connection refused"}
        except Exception as e:
            return {"error": f"Error: {str(e)}"}
    
    def extract_fan_status(self, stats: Dict[Any, Any]) -> Tuple[int, Dict[str, int], Optional[str]]:
        """
        Extract fan status information from a stats response
        
        Args:
            stats: The parsed JSON stats response
            
        Returns:
            Tuple containing:
              - Number of failed fans
              - Dictionary mapping fan keys to RPM values
              - Error message if any, None if successful
        """
        failed_fans = 0
        fan_data = {}
        
        try:
            if "error" in stats:
                return 0, {}, stats["error"]
                
            # Extract fan data from the second STATS object (index 1)
            if "STATS" in stats and len(stats["STATS"]) >= 2:
                stats_data = stats["STATS"][1]
                
                # Check if fan data exists
                if "fan_num" in stats_data:
                    fan_num = stats_data.get("fan_num", 0)
                    
                    # Count fans with 0 rpm (failed fans)
                    for i in range(1, fan_num + 1):
                        fan_key = f"fan{i}"
                        if fan_key in stats_data:
                            fan_rpm = stats_data[fan_key]
                            fan_data[fan_key] = fan_rpm
                            if fan_rpm == 0:
                                failed_fans += 1
                    
                    return failed_fans, fan_data, None
            
            return 0, {}, "No fan data found in stats response"
            
        except Exception as e:
            return 0, {}, f"Error parsing fan status: {str(e)}"
    
    def get_default_fan_message(self, failed_fans: int) -> str:
        """
        Generate a standardized message about fan status
        
        Args:
            failed_fans: Number of failed fans detected
            
        Returns:
            Message string to report fan status
        """
        if failed_fans > 0:
            return f"No {failed_fans} Fan find"
        return ""

    def get_device_type_from_stats(self, stats: Dict[Any, Any]) -> Optional[str]:
        """
        Extract device type information from stats response
        
        Args:
            stats: The parsed JSON stats response
            
        Returns:
            Device type string if found, None otherwise
        """
        try:
            if "STATS" in stats and len(stats["STATS"]) >= 1:
                return stats["STATS"][0].get("Type", None)
            return None
        except Exception:
            return None

    def parse_logs(self, log_content: str) -> List[str]:
        """
        Parse logs from a socket-based device
        
        Args:
            log_content: Raw log content
            
        Returns:
            List of parsed log entries
        """
        # For socket-based communication, we typically don't parse text logs
        # Instead, we get structured data directly from the socket API
        return []
