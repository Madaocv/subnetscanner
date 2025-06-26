#!/usr/bin/env python3
import ipaddress
import concurrent.futures
import requests
from requests.auth import HTTPDigestAuth
import json
import re
from typing import List, Dict, Any, Optional, Union
import ssl
import datetime

# Try importing websocket packages
# First, try the asyncio-based websockets package (preferred)
try:
    import asyncio
    import websockets
    WEBSOCKETS_ASYNCIO_AVAILABLE = True
except ImportError:
    WEBSOCKETS_ASYNCIO_AVAILABLE = False
    print("⚠️ WebSockets asyncio package not available. Install with 'pip install websockets' to enable improved T21 log fetching.")

# As a fallback, try the older websocket-client package
try:
    import websocket
    WEBSOCKET_CLIENT_AVAILABLE = True
except ImportError:
    WEBSOCKET_CLIENT_AVAILABLE = False
    print("⚠️ WebSocket-client package not available. Install with 'pip install websocket-client' for fallback T21 log fetching.")

# Define if any websocket capability is available
WEBSOCKET_AVAILABLE = WEBSOCKETS_ASYNCIO_AVAILABLE or WEBSOCKET_CLIENT_AVAILABLE

class SubnetControllerScan:
    """
    Subnet Controller Scan tool for scanning IP ranges and fetching device logs
    """
    def __init__(self, username: str = "root", password: str = "root", timeout: int = 5):
        self.username = username
        self.password = password
        self.timeout = timeout
        self.results = {}
        self.active_ips = []
        
    def scan_subnet(self, subnet: str, verbose: bool = True) -> List[str]:
        """
        Scan a subnet and return a list of responsive IP addresses
        
        Args:
            subnet: Subnet in CIDR notation (e.g., '192.168.1.0/24')
            verbose: Whether to print detailed output for each found host
            
        Returns:
            List of responsive IP addresses
        """
        try:
            network = ipaddress.ip_network(subnet)
            print(f"Starting scan of subnet {subnet} ({network.num_addresses} addresses)")
            
            responsive_ips = []
            
            # Use thread pool for faster scanning
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                future_to_ip = {
                    executor.submit(self.check_ip_responsive, str(ip)): str(ip) 
                    for ip in network.hosts()
                }
                
                for future in concurrent.futures.as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    try:
                        is_responsive = future.result()
                        if is_responsive:
                            responsive_ips.append(ip)
                            if verbose:
                                print(f"✅ Found responsive host: {ip}")
                    except Exception as e:
                        if verbose:
                            print(f"❌ Error checking {ip}: {e}")
            
            self.active_ips = responsive_ips
            return responsive_ips
            
        except ValueError as e:
            print(f"❌ Invalid subnet format: {e}")
            return []
    
    def check_ip_responsive(self, ip: str) -> bool:
        """Check if an IP address responds to HTTP requests"""
        url = f"http://{ip}/"
        try:
            response = requests.get(url, timeout=self.timeout, auth=HTTPDigestAuth(self.username, self.password))
            return response.status_code < 500  # Consider any non-server error response as responsive
        except requests.RequestException:
            return False
    
    def fetch_logs_from_ip(self, ip: str, endpoint: str = "/cgi-bin/get_kernel_log.cgi", verbose: bool = True) -> Dict[str, Any]:
        """
        Fetch logs from a specific IP address
        
        Args:
            ip: IP address to fetch logs from
            endpoint: API endpoint for logs
            verbose: Whether to print detailed output for each response
            
        Returns:
            Dictionary with log information
        """
        url = f"http://{ip}{endpoint}"
        auth = HTTPDigestAuth(self.username, self.password)
        
        try:
            response = requests.get(url, auth=auth, timeout=self.timeout)
            
            if response.status_code == 200:
                log_lines = response.text.strip().splitlines()
                
                # Pattern to parse syslog-style line - improved to handle more formats
                log_pattern = re.compile(r'^(?P<date>\w{3}\s+\d{1,2}) (?P<time>\d{2}:\d{2}:\d{2}) (?:[^\[]+\s+)?(?P<source>[^\s:]+(?:\[\d+\])?): (?P<message>.+)$')
                
                last_line = log_lines[-1] if log_lines else "Log is empty."
                match = log_pattern.match(last_line)
                
                result = {
                    "ip": ip,
                    "status": "success",
                    "raw_log": last_line
                }
                
                if match:
                    result.update({
                        "date": match.group('date'),
                        "time": match.group('time'),
                        "source": match.group('source'),
                        "message": match.group('message')
                    })
                
                return result
            else:
                return {
                    "ip": ip,
                    "status": "error",
                    "error_code": response.status_code,
                    "message": f"Failed to fetch logs. Status code: {response.status_code}"
                }
                
        except requests.RequestException as e:
            return {
                "ip": ip,
                "status": "error",
                "error_code": None,
                "message": f"Request exception: {str(e)}"
            }
    
    def fetch_logs_via_websocket(self, ip: str, endpoint: str = "/api/v1/logs-ws/status", timeout: int = 10) -> Dict[str, Any]:
        """
        Fetch logs from a T21 device via WebSocket connection
        
        Args:
            ip: IP address of the device
            endpoint: WebSocket endpoint for logs (default: /api/v1/logs-ws/status)
            timeout: Connection timeout in seconds
            
        Returns:
            Dictionary with log information
        """
        # Check if any websocket module is properly imported
        if not WEBSOCKET_AVAILABLE:
            return self.fallback_get_logs(ip)
        
        # Base result including device type info
        result = {
            "ip": ip,
            "status": "success",
            "device_type": "T21",  # Ensure device type is recorded
            "device_type_source": "detection",
            "message": "T21 device detected",
            "source": "T21",
            "logs": []
        }
        
        # Pattern to parse log lines: [YYYY/MM/DD HH:MM:SS] LEVEL: Message
        log_pattern = r'\[(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+(\w+):\s+(.+)'
        
        # Get today's date for filtering logs
        today = datetime.datetime.now().strftime("%Y/%m/%d")
        
        # If asyncio-based websockets is available (preferred method)
        if WEBSOCKETS_ASYNCIO_AVAILABLE:
            # Create and run the asyncio event
            try:
                # Define the async function
                async def fetch_logs_async():
                    ws_url = f"ws://{ip}{endpoint}"
                    log_messages = []
                    all_logs = []
                    today_logs = []
                    
                    try:
                        # print(f"🔌 Connecting to T21 device WebSocket...")
                        async with websockets.connect(ws_url) as ws:
                            # Receive and process messages for a limited time
                            start_time = datetime.datetime.now()
                            max_duration = datetime.timedelta(seconds=timeout)
                            message_count = 0
                            
                            while (datetime.datetime.now() - start_time) < max_duration:
                                try:
                                    # Set a timeout for receiving messages
                                    message = await asyncio.wait_for(ws.recv(), timeout=2.0)
                                    message_count += 1
                                    
                                    # Try to parse as text
                                    try:
                                        # Parse the log line using regex
                                        match = re.match(log_pattern, message)
                                        if match:
                                            timestamp, level, log_message = match.groups()
                                            log_entry = {
                                                'timestamp': timestamp,
                                                'level': level,
                                                'message': log_message
                                            }
                                            all_logs.append(log_entry)
                                            
                                            # Filter logs for today
                                            if timestamp.startswith(today):
                                                today_logs.append(log_entry)
                                                
                                    except Exception:
                                        # Silently continue on parse errors
                                        pass
                                        
                                except asyncio.TimeoutError:
                                    if message_count > 0:
                                        break  # Exit if we have some messages but timed out
                                except Exception:
                                    break
                        
                        return all_logs, today_logs
                    
                    except Exception:
                        # Silently return empty lists on errors
                        return [], []
                
                # Run the async function
                all_logs, today_logs = asyncio.run(fetch_logs_async())
                
                # Process the logs
                if today_logs:
                    # Use today's logs if available
                    logs_to_use = today_logs
                elif all_logs:
                    # Otherwise use all logs
                    logs_to_use = all_logs
                else:
                    # No logs were found
                    return self.fallback_get_logs(ip)
                
                # Use the last log for the main result
                last_log = logs_to_use[-1]
                result["message"] = last_log['message']
                result["time"] = last_log['timestamp'].split()[1]  # Extract time part
                result["date"] = last_log['timestamp'].split()[0]  # Extract date part
                result["level"] = last_log['level']
                result["logs"] = logs_to_use[:10] if len(logs_to_use) > 10 else logs_to_use  # Store up to 10 logs
                
                return result
                
            except Exception as e:
                # On error, use the fallback method
                return self.fallback_get_logs(ip)
                
        # Fallback to websocket-client if asyncio version is not available
        elif WEBSOCKET_CLIENT_AVAILABLE:
            ws_url = f"ws://{ip}{endpoint}"
            log_messages = []
            
            try:
                # Connect to WebSocket with a timeout (legacy client)
                print(f"🔌 Connecting to T21 device WebSocket (legacy)...")
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
                    result["message"] = last_log['message']
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

    def fallback_get_logs(self, ip: str) -> Dict[str, Any]:
        """
        Fallback method for getting logs when preferred method fails
        
        Args:
            ip: IP address of the device
            
        Returns:
            Dictionary with basic log information
        """
        # First try HTTP logs
        try:
            result = self.fetch_logs_from_ip(ip, "/cgi-bin/get_kernel_log.cgi", verbose=False)
            if result.get("status") == "success":
                # Add device type information
                device_info = self.detect_device_type(ip, verbose=False)
                result["device_type"] = device_info.get("device_type")
                result["device_type_source"] = device_info.get("source")
                return result
        except Exception:
            # Silently handle failed HTTP log fetch
            pass
        
        # If HTTP fails, at least return a result with device type
        device_info = self.detect_device_type(ip, verbose=False)
        return {
            "ip": ip,
            "status": "error",
            "device_type": device_info.get("device_type", "unknown"),
            "device_type_source": device_info.get("source"),
            "message": "Failed to fetch logs but device type detected"
        }
    
    def fetch_logs_from_s21(self, ip: str, endpoint: str = "/cgi-bin/hlog.cgi", verbose: bool = True) -> Dict[str, Any]:
        """
        Fetch logs from an S21 device using hlog.cgi endpoint
        
        Args:
            ip: IP address to fetch logs from
            endpoint: API endpoint for logs (default: /cgi-bin/hlog.cgi)
            verbose: Whether to print detailed output for each response
            
        Returns:
            Dictionary with log information
        """
        url = f"http://{ip}{endpoint}"
        auth = HTTPDigestAuth(self.username, self.password)
        
        try:
            # Add specific headers for S21 request
            headers = {
                'Accept': 'text/plain, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # Fetch logs without verbose output
            response = requests.get(url, auth=auth, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                log_content = response.text
                
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
                    "ip": ip,
                    "status": "success",
                    "date": date_part,
                    "time": time_part,
                    "source": "S21",
                    "message": message,
                    "raw_log": last_log_line
                }
            else:
                if verbose:
                    print(f"❌ Failed to fetch S21 logs from {ip}. Status code: {response.status_code}")
                
                return {
                    "ip": ip,
                    "status": "error",
                    "error_code": response.status_code,
                    "message": f"Failed to fetch S21 logs. Status code: {response.status_code}"
                }
        except requests.RequestException as e:
            if verbose:
                print(f"❌ Request exception when fetching S21 logs from {ip}: {str(e)}")
            
            return {
                "ip": ip,
                "status": "error",
                "message": f"Request exception for S21 logs: {str(e)}"
            }
            
    def detect_device_type(self, ip: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Detect device type by checking various API endpoints
        
        Args:
            ip: IP address to check
            verbose: Whether to print detailed output for debugging
            
        Returns:
            Dictionary with device type information
        """
        # Try system info endpoint first (Z15 devices)
        url_system_info = f"http://{ip}/cgi-bin/get_system_info.cgi"
        auth = HTTPDigestAuth(self.username, self.password)
        
        try:
            response = requests.get(url_system_info, auth=auth, timeout=self.timeout, verify=False)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "minertype" in data:
                        device_type = data["minertype"]
                        return {"device_type": device_type, "source": "system_info"}
                except Exception:
                    pass
        except Exception:
            pass
        
        # Try API v1 summary endpoint (T21 devices)
        url_api_summary = f"http://{ip}/api/v1/summary"
        try:
            response = requests.get(url_api_summary, auth=auth, timeout=self.timeout, verify=False)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check if it's a T21 device
                    if "miner" in data and "miner_type" in data["miner"]:
                        device_type = data["miner"]["miner_type"]
                        return {"device_type": device_type, "source": "api_summary"}
                except Exception:
                    pass
        except Exception:
            pass
        
        # Special case - if IP matches known patterns
        if ip.startswith("10.31.217."):  # Z15 subnet
            return {"device_type": "Z15", "source": "ip_pattern"}
        elif ip.startswith("10.31.206."):  # T21 subnet
            return {"device_type": "T21", "source": "ip_pattern"}
        elif ip.startswith("10.31.212."):  # S21 subnet
            return {"device_type": "S21", "source": "ip_pattern"}
        
        # If we reach here, we couldn't determine the device type
        return {"device_type": "unknown", "source": None}
    
    def fetch_logs_from_all_active(self, endpoint: str = "/cgi-bin/get_kernel_log.cgi") -> Dict[str, Any]:
        """
        Fetch logs from all active IPs
        
        Returns:
            Dictionary with results for each IP
        """
        results = {}
        
        # First, detect device types for all active IPs
        device_types = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ip = {
                executor.submit(self.detect_device_type, ip): ip 
                for ip in self.active_ips
            }
            
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    device_info = future.result()
                    device_types[ip] = device_info
                except Exception as e:
                    device_types[ip] = {"device_type": "unknown", "source": None}
        
        # Then fetch logs using the appropriate method for each device type
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ip = {}
            
            for ip in self.active_ips:
                device_type = device_types[ip]["device_type"]
                
                # Use the appropriate method for each device type
                if "T21" in device_type:
                    future = executor.submit(self.fetch_logs_via_websocket, ip, "/api/v1/logs-ws/system")
                elif "S21" in device_type:
                    future = executor.submit(self.fetch_logs_from_s21, ip, "/cgi-bin/hlog.cgi")
                else:
                    future = executor.submit(self.fetch_logs_from_ip, ip, endpoint)
                
                future_to_ip[future] = ip
            
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    result = future.result()
                    
                    # Add device type information
                    result["device_type"] = device_types[ip]["device_type"]
                    result["device_type_source"] = device_types[ip]["source"]
                    
                    results[ip] = result
                except Exception as e:
                    results[ip] = {
                        "ip": ip,
                        "status": "error",
                        "device_type": device_types[ip]["device_type"],
                        "device_type_source": device_types[ip]["source"],
                        "message": f"Exception occurred: {str(e)}"
                    }
        
        self.results = results
        return results
    
    def save_results_to_file(self, filename: str = "scan_results.json") -> None:
        """
        Save scan results to a JSON file
        
        Args:
            filename: Output JSON filename
        """
        with open(filename, "w") as f:
            json.dump({
                "scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "active_ips": self.active_ips,
                "results": self.results
            }, f, indent=4)
        
        print(f"✅ Results saved to {filename}")
    
    def print_results_summary(self) -> None:
        """Print a summary of scan results"""
        # General header
        print(f"\n{'-'*105}")
        print(f"📊 SCAN SUMMARY")
        print(f"{'-'*105}")
        print(f"🔍 Total IPs scanned: {len(self.results)}")
        print(f"✅ Successful log fetches: {sum(1 for r in self.results.values() if r.get('status') == 'success')}")
        print(f"❌ Failed log fetches: {sum(1 for r in self.results.values() if r.get('status') == 'error')}")
        
        # Detailed information for each IP address
        for ip, result in self.results.items():
            print(f"{'-'*105}\n📡 Device IP Address: {ip}")
            
            # Last log entry
            print("\n🕘 Last Log Entry:")
            if result.get("status") == "success":
                if "date" in result:
                    print(f"• 📅 Date     : {result.get('date')}")
                    print(f"• ⏰ Time     : {result.get('time')}")
                    print(f"• 💻 Source   : {result.get('source')}")
                    print(f"• 📝 Message  : {result.get('message')}")
                else:
                    print(f"• Raw: {result.get('raw_log', 'Log is empty.')}")
            else:
                print(f"• ❌ Error: {result.get('message')}")
        
        print(f"{'-'*105}")

# Example usage
if __name__ == "__main__":
    scanner = SubnetControllerScan(username="root", password="root")
    
    # Scan a subnet (example)
    subnet = "10.31.212.0/24"  # This will scan 10.31.212.0 through 10.31.212.255
    active_ips = scanner.scan_subnet(subnet)
    
    if active_ips:
        print(f"\nFound {len(active_ips)} active devices. Fetching logs...")
        scanner.fetch_logs_from_all_active()
        scanner.print_results_summary()
        scanner.save_results_to_file()
    else:
        print("No active devices found in the specified subnet.")
