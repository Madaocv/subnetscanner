"""
Handler for Z15j devices using socket communication
"""
import json
import socket
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from requests.auth import HTTPDigestAuth

from device_socket_based_handler import SocketBasedHandler
from device_registry import DeviceRegistry


class Z15jHandler(SocketBasedHandler):
    """Handler for Antminer Z15j devices"""
    device_type = "Z15j"
    
    def fetch_logs(self, ip: str, ignore_success: bool = True) -> Dict[str, Any]:
        """Fetch logs from Z15j device using socket"""
        try:
            # Get stats from device
            stats = self.send_socket_command(ip, "stats")
            
            if stats and "STATS" in stats and len(stats["STATS"]) > 1:  # Перевіряємо наявність обох об'єктів у масиві STATS
                # Get fan status using socket API - для Z15j дані про вентилятори у другому об'єкті (індекс 1)
                fan_stats = stats["STATS"][1]
                
                # Get device type from stats for consistent return values
                device_type = self.get_device_type_from_stats(stats) or "Z15j"
                device_type_source = "api" if self.get_device_type_from_stats(stats) else "registry"
                
                # Extract fan status - Z15j має іншу структуру даних, ніж інші пристрої
                failed_fans, fan_data, error = self.extract_z15j_fan_status(fan_stats)
                
                # Generate message based on fan status
                if error:
                    return {
                        "status": "error",
                        "message": f"Error fetching fan status: {error}",
                        "device_type": device_type,
                        "device_type_source": device_type_source,
                        "error_type": "device_error"
                    }
                
                # Для Z15j, успішним вважається стан, коли кількість працюючих вентиляторів
                # дорівнює або перевищує очікувану кількість у fan_num
                # Z15j особливість: працюють fan3 і fan4, а fan1 і fan2 завжди показують 0
                working_fans = [f for f, rpm in fan_data.items() if rpm > 0]
                working_fans_count = len(working_fans)
                expected_fans = int(stats.get("fan_num", 0))
                
                # Якщо кількість працюючих вентиляторів >= очікуваної, все добре
                if working_fans_count >= expected_fans:
                    # Все працює як треба - не повідомляємо про помилку
                    return {
                        "status": "ok",
                        "message": "",  # Порожнє повідомлення для успіху
                        "device_type": device_type,
                        "device_type_source": device_type_source,
                        "fan_data": fan_data
                    }
                else:
                    # Помилка: недостатньо працюючих вентиляторів
                    failed_fans = expected_fans - working_fans_count
                    return {
                        "status": "error",
                        "message": f"No {failed_fans} Fan find, check again",
                        "device_type": device_type,
                        "device_type_source": device_type_source,
                        "error_type": "device_error",
                        "fan_data": fan_data
                    }
                    
                # Deprecated code path - залишено для сумісності
                # Буде видалено в майбутніх версіях
                    
                return {
                        "status": "ok",
                        "message": "",  # Empty message for successful state
                        "device_type": device_type,
                        "device_type_source": device_type_source,
                        "fan_data": fan_data
                    }
            else:
                # Invalid response from socket API, try HTTP fallback
                return self._fetch_logs_via_http(ip, ignore_success)
        
        except Exception as e:
            # Handle any errors, try HTTP fallback
            return self._fetch_logs_via_http(ip, ignore_success)
            
    def _fetch_logs_via_http(self, ip: str, ignore_success: bool = True) -> Dict[str, Any]:
        """
        Fetch logs from Z15j device using HTTP API as fallback when socket API fails
        
        Args:
            ip: IP address of the device
            ignore_success: Whether to ignore success messages
            
        Returns:
            Dictionary with log information
        """
        import requests
        from requests.auth import HTTPDigestAuth
        
        try:
            # Try to get kernel logs using the same endpoint as Z15
            # Configuration should have the log_endpoint set (typically /cgi-bin/get_kernel_log.cgi)
            config = self.config if hasattr(self, 'config') else {}
            log_endpoint = config.get('log_endpoint', '/cgi-bin/get_kernel_log.cgi')
            auth_user = config.get('username', 'root')
            auth_pass = config.get('password', 'root')
            timeout = config.get('timeout', 15)
            
            url = f"http://{ip}{log_endpoint}"
            response = requests.get(
                url, 
                auth=HTTPDigestAuth(auth_user, auth_pass),
                timeout=timeout
            )
            
            if response.status_code == 200:
                # Parse the log content
                log_content = response.text
                log_data = self._parse_z15j_http_log(log_content)
                
                # Add IP and device type info
                log_data["ip"] = ip
                log_data["device_type"] = "Z15j"
                log_data["device_type_source"] = "http_fallback"
                
                # If message is empty or needs to be ignored, set status accordingly
                if ignore_success and (not log_data.get("message") or "success" in log_data.get("status", "").lower()):
                    log_data["status"] = "ok"
                    log_data["message"] = ""
                
                return log_data
            else:
                return {
                    "status": "error",
                    "message": f"HTTP Error: {response.status_code}",
                    "device_type": "Z15j",
                    "device_type_source": "http_fallback",
                    "error_type": "http_error"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"HTTP Connection Error: {str(e)}",
                "device_type": "Z15j",
                "device_type_source": "http_fallback",
                "error_type": "connection_error"
            }
    
    def _parse_z15j_http_log(self, log_content: str) -> Dict[str, Any]:
        """
        Parse Z15j log format from HTTP response
        
        Args:
            log_content: Raw log content from HTTP response
            
        Returns:
            Dictionary with parsed log information
        """
        try:
            # Try to parse as JSON first (same as Z15)
            log_data = json.loads(log_content)
            
            # Extract log message from the JSON structure
            if "log" in log_data:
                message = log_data["log"].strip() if log_data["log"] else "No log message"
                
                return {
                    "status": "success",
                    "source": "Z15j-http",
                    "message": message,
                    "raw_log": log_data["log"]
                }
        except json.JSONDecodeError:
            # If not valid JSON, try to extract useful info from text
            # Extract the most relevant log line
            lines = log_content.strip().split("\n")
            
            # Z15j fan error messages often contain this pattern
            for line in reversed(lines):
                # Шукаємо конкретно повідомлення про помилки вентиляторів у форматі "No X Fan find"
                if "no" in line.lower() and "fan find" in line.lower():
                    # Витягуємо тільки основну частину повідомлення
                    fan_error_match = re.search(r'(?:.*cgminer\[\d+\]:\s*)?(No\s+\d+\s+Fan\s+find,\s+check\s+again)', line)
                    error_message = fan_error_match.group(1) if fan_error_match else line
                    
                    return {
                        "status": "error",
                        "source": "Z15j-http-text",
                        "message": error_message,
                        "raw_log": log_content
                    }
            
            # If no fan error found, take the last line or a kernel message
            for line in reversed(lines):
                if "kernel" in line.lower() or "error" in line.lower():
                    return {
                        "status": "error",
                        "source": "Z15j-http-text",
                        "message": line,
                        "raw_log": log_content
                    }
            
            # Fall back to last line if nothing else found
            last_line = lines[-1] if lines else ""
            
            return {
                "status": "success",
                "source": "Z15j-http-text",
                "message": last_line,
                "raw_log": log_content
            }
    
    def extract_z15j_fan_status(self, stats: Dict[str, Any]) -> Tuple[int, Dict[str, int], str]:
        """
        Extract fan status information from Z15j stats response
        
        Args:
            stats: The parsed JSON stats response for Z15j devices
            
        Returns:
            Tuple containing:
              - Number of failed fans
              - Dictionary mapping fan keys to RPM values
              - Error message if any, None if successful
        """
        fan_data = {}
        failed_fans = 0
        
        try:
            # Check if we got a valid response
            if "error" in stats:
                return 0, {}, stats["error"]
            
            # Z15j специфіка: fan_num вказує очікувану кількість працюючих вентиляторів
            # Але працюючі вентилятори мають індекси fan3, fan4, тощо
            if "fan_num" in stats:
                expected_fans = int(stats.get("fan_num", 0))  # Скільки вентиляторів повинно працювати
                working_fans = 0  # Скільки вентиляторів реально працює
                
                # Збираємо дані про всі вентилятори
                for i in range(1, 7):  # Перевіряємо до fan6 щоб бути впевненими
                    fan_key = f"fan{i}"
                    if fan_key in stats:
                        rpm = int(stats[fan_key])
                        fan_data[fan_key] = rpm
                        # Рахуємо працюючі вентилятори (тільки ті, що мають RPM > 0)
                        if rpm > 0:
                            working_fans += 1
                
                # Кількість несправних вентиляторів - це різниця між очікуваними і працюючими
                if working_fans < expected_fans:
                    failed_fans = expected_fans - working_fans
                else:
                    failed_fans = 0  # Всі очікувані вентилятори працюють
                # Ensure we don't report negative failed fans
                if failed_fans < 0:
                    failed_fans = 0
                
                return failed_fans, fan_data, None
            
            return 0, {}, "No fan data found in Z15j stats response"
            
        except Exception as e:
            return 0, {}, f"Error parsing Z15j fan status: {str(e)}"
    
    def get_z15j_fan_message(self, fan_data: Dict[str, int], failed_fans: int) -> str:
        """
        Generate a message about the fan status for Z15j
        
        Args:
            fan_data: Dictionary mapping fan keys to RPM values
            failed_fans: Number of failed fans according to Z15j's fan_num vs working fans
            
        Returns:
            A human-readable message about the fan status
        """
        # Z15j peculiarity: Only specific fans (fan3, fan4) should be working
        # fan1 and fan2 are always 0 despite fan_num=2
        working_fans = [f for f, rpm in fan_data.items() if rpm > 0]
        non_working_fans = [f for f, rpm in fan_data.items() if rpm == 0 and f in ['fan3', 'fan4']]
        
        # Special message for Z15j based on expected vs working fans
        if failed_fans > 0:
            if non_working_fans:
                return f"Z15j: {failed_fans} fan(s) not working - {', '.join(non_working_fans)}"
            return f"Z15j: {failed_fans} expected fan(s) not detected"
        
        return f"All Z15j fans working properly ({', '.join(working_fans)})"
    
    def normalize_message(self, message: str) -> str:
        """Normalize Z15j error messages for consistent grouping"""
        # Для повідомлень про працюючі вентилятори - приховуємо їх
        if "fan" in message.lower() and ("working" in message.lower() or "normal" in message.lower()):
            return ""
            
        # Шукаємо повідомлення про вентилятори у форматі "Дата... cgminer: No X Fan find, check again"
        # Цей регулярний вираз обробляє повні логи з датою і системною інформацією
        fan_error_match = re.search(r'(?:.*(\w+\s+\d+\s+\d+:\d+:\d+).*)?(No\s+\d+\s+Fan\s+find,\s+check\s+again)', message)
        if fan_error_match:
            # Повертаємо тільки основне повідомлення без дати, хоста тощо
            return fan_error_match.group(2)
            
        # Шукаємо інший формат повідомлення про помилки вентиляторів
        if "fan" in message.lower() and ("error" in message.lower() or "find" in message.lower()):
            # Спрощений формат - просто витягнемо "No X Fan find, check again"
            basic_fan_match = re.search(r'(No\s+\d+\s+Fan\s+find.*?)(?:$|\s*\|)', message)
            if basic_fan_match:
                return basic_fan_match.group(1)
                
        return message
        
    def send_socket_command(self, ip: str, command: str, port: int = 4028, timeout: int = 5) -> Dict[Any, Any]:
        """Override to handle Z15j-specific malformed JSON"""
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
                
                # Z15j produces malformed JSON - fix it before parsing
                fixed_json_str = self._fix_z15j_json(response_str)
                
                return json.loads(fixed_json_str)
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON response: {str(e)}", "raw": response.decode('utf-8', errors='replace')}
            except Exception as e:
                return {"error": f"Error parsing response: {str(e)}", "raw": response.decode('utf-8', errors='replace')}
                
        except socket.timeout:
            return {"error": "Connection timed out"}
        except ConnectionRefusedError:
            return {"error": "Connection refused"}
        except Exception as e:
            return {"error": f"Error: {str(e)}"}
    
    def _fix_z15j_json(self, json_str: str) -> str:
        """Fix malformed JSON from Z15j devices"""
        # Fix missing commas between objects in STATS array
        # Common pattern: ..."Type":"Antminer Z15j"}{"STATS":0,...
        json_str = re.sub(r'(\})(\{)', r'\1,\2', json_str)
        return json_str
    
    @classmethod
    def detect(cls, ip: str, username: str, password: str, timeout: int) -> bool:
        """
        Detect if an IP is a Z15j device using socket API or HTTP fallback
        
        Args:
            ip: IP address to check
            username: Used for HTTP-based detection fallback
            password: Used for HTTP-based detection fallback
            timeout: Connection timeout
            
        Returns:
            True if the IP is a Z15j device, False otherwise
        """
        try:
            # First try socket API detection
            # Send "stats" command to get miner info
            stats = cls().send_socket_command(ip, "stats", timeout=timeout)
            
            # Check if we got a valid response with Type field
            device_type = cls.get_device_type_from_stats(stats)
            
            # For Z15j, type should be "Antminer Z15j"
            if device_type and "Z15j" in device_type:
                return True
                
            # If socket detection didn't identify as Z15j, check HTTP detection as fallback
            # Sometimes Z15j devices have socket API disabled
            return cls._detect_via_http(ip, username, password, timeout)
            
        except Exception as e:
            # If socket connection fails, try HTTP detection as fallback
            return cls._detect_via_http(ip, username, password, timeout)
            
    @classmethod
    def _detect_via_http(cls, ip: str, username: str, password: str, timeout: int) -> bool:
        """
        Fallback detection for Z15j using HTTP requests when socket API is unavailable
        
        Args:
            ip: IP address to check
            username: Username for HTTP authentication
            password: Password for HTTP authentication
            timeout: Request timeout
            
        Returns:
            True if the IP is likely a Z15j device based on HTTP, False otherwise
        """
        import requests
        from requests.auth import HTTPDigestAuth
        import re
        
        try:
            # Try system info endpoint (similar to Z15)
            url = f"http://{ip}/cgi-bin/get_system_info.cgi"
            response = requests.get(url, auth=HTTPDigestAuth(username, password), timeout=timeout)
            
            if response.status_code == 200:
                content = response.text
                
                # Check if content contains Z15j specific identifiers
                if "Z15j" in content or ("Antminer" in content and "zcash" in content.lower()):
                    return True
                    
            # Check for web interface title containing Z15j
            url = f"http://{ip}/"
            response = requests.get(url, auth=HTTPDigestAuth(username, password), timeout=timeout)
            
            if response.status_code == 200:
                content = response.text.lower()
                if "z15j" in content:
                    return True
                    
            # Not a Z15j or couldn't determine
            return False
            
        except Exception as e:
            # HTTP detection failed
            return False
    
    @classmethod
    def get_device_type_from_stats(cls, stats: Dict[str, Any]) -> Optional[str]:
        """
        Extract device type from stats response
        
        Args:
            stats: The parsed JSON stats response
            
        Returns:
            Device type if found, None otherwise
        """
        if isinstance(stats, dict) and "STATS" in stats and len(stats["STATS"]) > 0:
            if "Type" in stats["STATS"][0]:
                return stats["STATS"][0]["Type"]
        return None


# Register the handler and detector with the registry
# NOTE: Register before Z15 to ensure Z15j is checked first
DeviceRegistry.register_handler("Z15j", Z15jHandler)
DeviceRegistry.register_detector("Z15j", Z15jHandler.detect)
