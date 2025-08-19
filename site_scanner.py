#!/usr/bin/env python3
"""
Site Scanner Tool
For scanning mining sites using a hierarchical configuration structure:
- Locations
- Subsections (racks/pods)
- Miner types and quantities
"""

import ipaddress
import concurrent.futures
import requests
from requests.auth import HTTPDigestAuth
import json
import re
import os
import argparse
import datetime
import time
from typing import List, Dict, Any, Optional, Union, Tuple

# Try importing websocket packages
try:
    import asyncio
    import websockets
    WEBSOCKETS_ASYNCIO_AVAILABLE = True
except ImportError:
    WEBSOCKETS_ASYNCIO_AVAILABLE = False
    print("⚠️ WebSockets asyncio package not available. Install with 'pip install websockets' to enable improved T21 log fetching.")
    
# Try importing netaddr package
try:
    import netaddr
    NETADDR_AVAILABLE = True
except ImportError:
    NETADDR_AVAILABLE = False
    print("⚠️ Netaddr package not available. Install with 'pip install netaddr' to enable improved IP scanning.")

# Try importing pytricia package
try:
    import pytricia
    PYTRICIA_AVAILABLE = True
except ImportError:
    PYTRICIA_AVAILABLE = False
    print("⚠️ Pytricia package not available. Install with 'pip install pytricia' to enable faster IP prefix matching.")


# As a fallback, try the older websocket-client package
try:
    import websocket
    WEBSOCKET_CLIENT_AVAILABLE = True
except ImportError:
    WEBSOCKET_CLIENT_AVAILABLE = False
    print("⚠️ WebSocket-client package not available. Install with 'pip install websocket-client' for fallback T21 log fetching.")

# Define if any websocket capability is available
WEBSOCKET_AVAILABLE = WEBSOCKETS_ASYNCIO_AVAILABLE or WEBSOCKET_CLIENT_AVAILABLE

# Import device components
from device_manager import DeviceManager
from handlers import t21_handler
from handlers import s21_handler
from handlers import z15j_handler  # Import Z15j before Z15 for detection order
from handlers import z15_handler
from handlers import s21_pro_handler
from handlers import s19j_pro_handler
from handlers import dg1_handler
from device_registry import DeviceRegistry

# Ensure Z15j is checked before Z15 in device detection
# This is critical because both devices respond to similar APIs
DeviceRegistry.reorder_detectors(preferred_order=["Z15j", "Z15", "T21", "S21", "S21Pro", "S19jPro", "DG1"])

class SiteScanner:
    """
    Site Scanner tool for scanning mining sites using hierarchical configuration.
    The scanner supports:
    - Multiple locations 
    - Custom subsections (racks/pods) per location
    - Expected miner quantities per subsection
    - Comparison of expected vs. actual miners
    - Issues detection for miners
    """
    def __init__(self, config_file: str = None):
        # Basic scanner settings
        self.username = "root"
        self.password = "root"
        self.timeout = 5
        self.results = {}
        self.active_ips = []
        
        # Initialize the device manager
        self.device_manager = DeviceManager(self)
        
        # Load site configuration
        self.site_config = self.load_site_config(config_file)
        
        # Get authentication parameters directly from site config
        if self.site_config:
            self.username = self.site_config.get("username", self.username)
            self.password = self.site_config.get("password", self.password)
            self.timeout = self.site_config.get("timeout", self.timeout)
        
        # Raw scan data storage - will hold complete device data
        self.raw_scan_data = {}
        
    # ==========================================
    # Configuration and Setup Methods
    # ==========================================
    
    def load_site_config(self, config_file: str = None) -> Dict[str, Any]:
        """
        Load site configuration from file
        
        Args:
            config_file: Path to JSON configuration file
            
        Returns:
            Configuration as dictionary
        """
        if not config_file:
            print("❌ No site config file specified.")
            return {}
            
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config
        except FileNotFoundError as e:
            # Використовуємо атрибут self._reported_error, щоб уникнути дублювання повідомлень
            if not hasattr(self, '_reported_error') or self._reported_error != str(e):
                print(f"❌ Error loading site config file: {e}")
                self._reported_error = str(e)
            return {}
        except Exception as e:
            print(f"❌ Error loading site config file: {e}")
            return {}

    def load_auth_config(self, config_file: str = None) -> Dict[str, Any]:
        """
        Load authentication configuration from file
        
        Args:
            config_file: Path to JSON configuration file
            
        Returns:
            Configuration as dictionary
        """
        if not config_file:
            return {}
            
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"⚠️ Error loading auth config file: {e}")
            return {}
            
    # ==========================================
    # Subnet Scanning Methods  
    # ==========================================
    
    def parse_ip_range(self, ip_range: str) -> List[str]:
        """
        Parse IP range in various formats:
        - CIDR notation (e.g., 10.32.101.0/24)
        - Range notation (e.g., 10.32.101.1-255)
        
        Args:
            ip_range: String representing IP range
            
        Returns:
            List of IPs in the range
        """
        # Check if it's CIDR notation (e.g., 10.32.101.0/24)
        if "/" in ip_range:
            try:
                network = ipaddress.ip_network(ip_range)
                return [str(ip) for ip in network.hosts()]
            except ValueError as e:
                print(f"❌ Error parsing CIDR range '{ip_range}': {e}")
                return []
        
        # Check if it's a range notation (e.g., 10.32.101.1-255)
        elif "-" in ip_range:
            try:
                # Split the range
                ip_parts = ip_range.split("-")
                base_ip = ip_parts[0].strip()
                
                # Get the base IP components
                ip_components = base_ip.split(".")
                if len(ip_components) != 4:
                    raise ValueError("Invalid IP format")
                
                # Get the range end
                range_end = ip_parts[1].strip()
                
                # Create list of IPs
                ip_list = []
                
                # Check if range is for last octet
                if range_end.isdigit():
                    start_octet = int(ip_components[3])
                    end_octet = int(range_end)
                    
                    for i in range(start_octet, end_octet + 1):
                        ip = f"{ip_components[0]}.{ip_components[1]}.{ip_components[2]}.{i}"
                        ip_list.append(ip)
                    
                    return ip_list
                else:
                    # More complex range (not implemented)
                    print(f"❌ Complex IP range not supported: {ip_range}")
                    return []
            except Exception as e:
                print(f"❌ Error parsing range '{ip_range}': {e}")
                return []
        
        # Single IP
        else:
            try:
                # Validate it's a valid IP
                ipaddress.ip_address(ip_range)
                return [ip_range]
            except ValueError:
                print(f"❌ Invalid IP: {ip_range}")
                return []
            
    def scan_ip_range(self, ip_range: str, verbose: bool = True) -> List[str]:
        """
        Scan an IP range and return responsive IPs
        
        Args:
            ip_range: IP range in CIDR or range notation
            verbose: Whether to print detailed output
            
        Returns:
            List of responsive IP addresses
        """
        # Parse the IP range to get individual IPs
        ips = self.parse_ip_range(ip_range)
        
        if not ips:
            return []
            
        if verbose:
            print(f"Starting scan of {ip_range} ({len(ips)} addresses)")
        
        responsive_ips = []
        max_workers = 50  # Number of threads
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {
                executor.submit(self.check_ip_responsive, ip): ip 
                for ip in ips
            }
            
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    is_responsive = future.result()
                    if is_responsive:
                        responsive_ips.append(ip)
                except Exception as exc:
                    print(f"IP {ip} generated an exception: {exc}")
        
        return responsive_ips
        
    def scan_ip_range_more_threads(self, ip_range: str, verbose: bool = True) -> List[str]:
        """
        Scan an IP range with increased thread count
        
        Args:
            ip_range: IP range in CIDR or range notation
            verbose: Whether to print detailed output
            
        Returns:
            List of responsive IP addresses
        """
        # Parse the IP range to get individual IPs
        ips = self.parse_ip_range(ip_range)
        
        if not ips:
            return []
            
        if verbose:
            print(f"Starting scan of {ip_range} ({len(ips)} addresses) with increased threads")
        
        responsive_ips = []
        max_workers = 200  # Increased number of threads
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {
                executor.submit(self.check_ip_responsive, ip): ip 
                for ip in ips
            }
            
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    is_responsive = future.result()
                    if is_responsive:
                        responsive_ips.append(ip)
                except Exception as exc:
                    print(f"IP {ip} generated an exception: {exc}")
        
        return responsive_ips
        
    async def _check_ip_responsive_async(self, ip: str) -> Tuple[str, bool]:
        """
        Async version of checking if an IP is responsive
        
        Args:
            ip: IP address to check
            
        Returns:
            Tuple containing (ip, is_responsive)
        """
        import socket
        import asyncio
        
        try:
            # Create a future for the socket connection with timeout
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            
            def _socket_check():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(self.timeout)
                    s.connect((ip, 80))
                    s.close()
                    future.set_result(True)
                except (socket.timeout, socket.error, ConnectionRefusedError):
                    future.set_result(False)
                    
            # Run the socket check in a thread
            await loop.run_in_executor(None, _socket_check)
            is_responsive = await asyncio.wait_for(future, timeout=self.timeout)
            return ip, is_responsive
        except asyncio.TimeoutError:
            return ip, False
        except Exception:
            return ip, False
    
    def scan_ip_range_async(self, ip_range: str, verbose: bool = True) -> List[str]:
        """
        Scan an IP range using asyncio for potentially better performance
        
        Args:
            ip_range: IP range in CIDR or range notation
            verbose: Whether to print detailed output
            
        Returns:
            List of responsive IP addresses
        """
        import asyncio
        
        # Parse the IP range to get individual IPs
        ips = self.parse_ip_range(ip_range)
        
        if not ips:
            return []
            
        if verbose:
            print(f"Starting async scan of {ip_range} ({len(ips)} addresses)")
        
        # Define the async function to run all checks
        async def run_all_checks():
            tasks = [self._check_ip_responsive_async(ip) for ip in ips]
            results = await asyncio.gather(*tasks)
            return [ip for ip, is_responsive in results if is_responsive]
        
        # Run the async tasks and get results
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            responsive_ips = loop.run_until_complete(run_all_checks())
            loop.close()
        except Exception as e:
            print(f"Error in async scanning: {e}")
            return []
            
        return responsive_ips
        
    def scan_ip_range_chunked(self, ip_range: str, verbose: bool = True) -> List[str]:
        """
        Scan an IP range by dividing it into smaller chunks for better resource management
        
        Args:
            ip_range: IP range in CIDR or range notation
            verbose: Whether to print detailed output
            
        Returns:
            List of responsive IP addresses
        """
        # Parse the IP range to get individual IPs
        ips = self.parse_ip_range(ip_range)
        
        if not ips:
            return []
            
        if verbose:
            print(f"Starting chunked scan of {ip_range} ({len(ips)} addresses)")
        
        # Divide IPs into chunks of appropriate size
        chunk_size = 100  # Adjust as needed for performance
        ip_chunks = [ips[i:i + chunk_size] for i in range(0, len(ips), chunk_size)]
        
        responsive_ips = []
        total_chunks = len(ip_chunks)
        
        for i, chunk in enumerate(ip_chunks):
            if verbose:
                print(f"Scanning chunk {i+1}/{total_chunks} ({len(chunk)} IPs)")
                
            # Use thread pool for each chunk
            chunk_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                future_to_ip = {
                    executor.submit(self.check_ip_responsive, ip): ip 
                    for ip in chunk
                }
                
                for future in concurrent.futures.as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    try:
                        is_responsive = future.result()
                        if is_responsive:
                            chunk_results.append(ip)
                    except Exception as exc:
                        print(f"IP {ip} generated an exception: {exc}")
            
            responsive_ips.extend(chunk_results)
            if verbose and chunk_results:
                print(f"Found {len(chunk_results)} active IPs in chunk {i+1}")
        
        return responsive_ips
        
    def scan_ip_range_netaddr(self, ip_range: str, verbose: bool = True) -> List[str]:
        """
        Scan an IP range using the netaddr library for efficient IP handling
        
        Args:
            ip_range: IP range in CIDR or range notation
            verbose: Whether to print detailed output
            
        Returns:
            List of responsive IP addresses
        """
        if not NETADDR_AVAILABLE:
            print("❌ Netaddr library not available. Install with 'pip install netaddr'")
            return []
            
        if verbose:
            print(f"Starting netaddr scan of {ip_range}")
            
        # Parse IP range using netaddr
        try:
            # Handle CIDR notation (e.g., 192.168.1.0/24)
            if '/' in ip_range:
                ip_network = netaddr.IPNetwork(ip_range)
                # Exclude network and broadcast addresses
                ips = [str(ip) for ip in ip_network if ip != ip_network.network and ip != ip_network.broadcast]
            # Handle range notation (e.g., 192.168.1.1-192.168.1.100)
            elif '-' in ip_range:
                start_ip, end_ip = ip_range.split('-')
                start_ip = start_ip.strip()
                end_ip = end_ip.strip()
                ip_range = netaddr.IPRange(start_ip, end_ip)
                ips = [str(ip) for ip in ip_range]
            else:
                # Single IP address
                ips = [ip_range]
                
            if verbose:
                print(f"Found {len(ips)} IPs to scan")
        except Exception as e:
            print(f"❌ Error parsing IP range with netaddr: {e}")
            return []
            
        # Use optimized concurrent scanning with thread pooling
        responsive_ips = []
        max_workers = 100  # Optimized thread count for netaddr
        
        if verbose:
            print(f"Scanning with {max_workers} concurrent threads")
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {
                executor.submit(self.check_ip_responsive, str(ip)): str(ip) 
                for ip in ips
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_ip)):
                if verbose and i > 0 and i % 50 == 0:
                    print(f"Progress: {i}/{len(ips)} IPs checked")
                    
                ip = future_to_ip[future]
                try:
                    is_responsive = future.result()
                    if is_responsive:
                        responsive_ips.append(ip)
                        if verbose:
                            print(f"Found responsive IP: {ip}")
                except Exception as exc:
                    if verbose:
                        print(f"IP {ip} generated an exception: {exc}")
        
        if verbose:
            print(f"Completed scan of {len(ips)} IPs, found {len(responsive_ips)} responsive IPs")
            
        return responsive_ips
        
    def scan_ip_range_pytricia(self, ip_range: str, verbose: bool = True) -> List[str]:
        """
        Scan an IP range using the pytricia library for efficient prefix tree-based IP matching
        
        Args:
            ip_range: IP range in CIDR notation
            verbose: Whether to print detailed output
            
        Returns:
            List of responsive IP addresses
        """
        if not PYTRICIA_AVAILABLE:
            print("❌ Pytricia library not available. Install with 'pip install pytricia'")
            return []
            
        if verbose:
            print(f"Starting pytricia scan of {ip_range}")
        
        # Create a new pytricia prefix tree
        pyt = pytricia.PyTricia()
        
        # Parse IP range - pytricia requires CIDR notation
        try:
            # Convert range to CIDR if needed
            if '/' in ip_range:
                # Already in CIDR format
                prefix = ip_range
                # Add to prefix tree
                pyt[prefix] = True
                
                # Generate list of IPs to scan
                if NETADDR_AVAILABLE:
                    # Use netaddr for IP generation if available (faster)
                    ip_network = netaddr.IPNetwork(ip_range)
                    # Exclude network and broadcast addresses
                    ips = [str(ip) for ip in ip_network if ip != ip_network.network and ip != ip_network.broadcast]
                else:
                    # Fallback to ipaddress module
                    ip_network = ipaddress.IPv4Network(ip_range, strict=False)
                    ips = [str(ip) for ip in ip_network.hosts()]
                    
            elif '-' in ip_range:
                # Convert range notation to list of IPs
                start_ip, end_ip = ip_range.split('-')
                start_ip = start_ip.strip()
                end_ip = end_ip.strip()
                
                # Generate all IPs in the range
                start_int = int(ipaddress.IPv4Address(start_ip))
                end_int = int(ipaddress.IPv4Address(end_ip))
                ips = [str(ipaddress.IPv4Address(ip)) for ip in range(start_int, end_int + 1)]
                
                # For pytricia, we need to add each IP as /32
                for ip in ips:
                    pyt[f"{ip}/32"] = True
            else:
                # Single IP - add as /32
                pyt[f"{ip_range}/32"] = True
                ips = [ip_range]
            
            if verbose:
                print(f"Found {len(ips)} IPs to scan")
        except Exception as e:
            print(f"❌ Error setting up pytricia tree: {e}")
            return []
        
        # Optimized parallel scanning with efficient lookup
        responsive_ips = []
        max_workers = 120  # Higher thread count optimized for pytricia's fast lookups
        
        if verbose:
            print(f"Scanning with {max_workers} concurrent threads using pytricia for lookups")
        
        # Function to check if IP is responsive and in our prefix tree
        def check_ip_in_tree(ip):
            try:
                # Check if the IP is in our prefix tree first (very fast operation)
                if pyt.get(ip) is not None:
                    # Only then check if it's responsive
                    return self.check_ip_responsive(ip)
                return False
            except Exception:
                return False
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {executor.submit(check_ip_in_tree, ip): ip for ip in ips}
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                completed += 1
                
                if verbose and completed % 50 == 0:
                    print(f"Progress: {completed}/{len(ips)} IPs checked")
                
                try:
                    if future.result():
                        responsive_ips.append(ip)
                        if verbose:
                            print(f"Found responsive IP: {ip}")
                except Exception as exc:
                    if verbose:
                        print(f"IP {ip} generated an exception: {exc}")
        
        if verbose:
            print(f"Completed pytricia scan of {len(ips)} IPs, found {len(responsive_ips)} responsive IPs")
        
        return responsive_ips

    #     try:
    #         response = requests.get(f"http://{ip}/", 
    #                                auth=HTTPDigestAuth(self.username, self.password),
    #                                timeout=self.timeout)
    #         return True
    #     except requests.RequestException:
    #         return False
    def check_ip_responsive(self, ip: str) -> bool:
        """Check if an IP responds using socket connection"""
        import socket
        
        # Порт для перевірки (за замовчуванням 80 для HTTP)
        port = 80
        # Таймаут у секундах
        timeout = self.timeout
        
        try:
            # Створюємо сокет
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            # Пробуємо підключитися
            result = sock.connect_ex((ip, port))
            
            # Закриваємо сокет
            sock.close()
            
            # Якщо результат 0, підключення успішне
            is_responsive = result == 0
            if is_responsive:
                print(f"Found active IP: {ip}")
            return is_responsive
        except socket.error as e:
            print(f"Socket error for {ip}: {str(e)}")
            return False
    def scan_subsection(self, subsection: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
        """
        Scan a subsection and collect device information
        
        Args:
            subsection: Subsection configuration with IP ranges and expected miners
            verbose: Whether to print detailed output
            
        Returns:
            Dictionary with scan results for the subsection
        """
        subsection_name = subsection.get("name", "Unnamed Subsection")
        ip_ranges = subsection.get("ip_ranges", [])
        expected_miners = subsection.get("miners", [])
        
        print(f"\n🔍 Scanning subsection: {subsection_name}")
        
        # Store all results for this subsection
        subsection_results = {
            "name": subsection_name,
            "ip_ranges": ip_ranges,
            "expected_miners": expected_miners,
            "active_ips": [],
            "devices": {},
            "summary": {}
        }
        
        # Scan each IP range in this subsection
        all_active_ips = []
        for ip_range in ip_ranges:
            active_ips = self.scan_ip_range(ip_range, verbose=verbose)
            all_active_ips.extend(active_ips)
        
        # Store active IPs
        subsection_results["active_ips"] = all_active_ips
        
        # Detect device types and get logs for each active IP
        print(f"Detecting device types for {len(all_active_ips)} active IPs...")
        
        for ip in all_active_ips:
            # Detect device type
            device_info = self.device_manager.detect_device_type(ip, verbose=False)
            
            # Get the device type
            device_type = device_info.get("device_type", "unknown")
            
            # Fetch logs using device_manager
            result = self.device_manager.fetch_logs_from_device(ip, device_type, verbose=False)
            
            if result:
                # Add device type information to the result
                result["device_type"] = device_type
                result["device_type_source"] = device_info.get("source")
                result["ip"] = ip
                
                # Store in subsection results
                subsection_results["devices"][ip] = result
                
                # Store in raw scan data
                self.raw_scan_data[ip] = result
                
        # Generate summary for this subsection
        subsection_results["summary"] = self.generate_subsection_summary(subsection_results)
        
        return subsection_results
    
    def scan_site(self) -> Dict[str, Any]:
        """
        Scan entire site based on the already loaded configuration
        
        Returns:
            Dictionary with complete scan results
        """
        site_id = self.site_config.get("site_id", "Unknown Site")
        subsections = self.site_config.get("subsections", [])
        
        print(f"Starting scan for site: {site_id}")
        start_time = time.time()
        
        # Store results for the entire site
        site_results = {
            "site_id": site_id,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "subsections": [],
            "raw_data": {}
        }
        
        # Scan each subsection
        for subsection in subsections:
            subsection_result = self.scan_subsection(subsection)
            site_results["subsections"].append(subsection_result)
        
        # Store raw data
        site_results["raw_data"] = self.raw_scan_data
        
        # Calculate scan duration
        scan_duration = time.time() - start_time
        site_results["duration_seconds"] = round(scan_duration, 2)
        
        return site_results
        
    # ==========================================
    # Analysis and Reporting Methods
    # ==========================================
    
    def analyze_device_issues(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze device data to detect issues
        
        Args:
            device_data: Raw device data from scan
            
        Returns:
            Dictionary with detected issues
        """
        issues = {}
        device_type = device_data.get("device_type", "unknown")
        
        # Extract model configuration for this device type
        model_config = self.site_config.get("models", {}).get(device_type, {})
        
        # Check for common issues based on device type
        
        # Check hashboards
        if "hashboards" in device_data:
            expected_hashboards = model_config.get("HB", 3)
            active_hashboards = sum(1 for hb in device_data.get("hashboards", []) if hb.get("status") == "active")
            
            if active_hashboards < expected_hashboards:
                issues["hashboards"] = f"Missing {expected_hashboards - active_hashboards} Hashboard(s)"
        
        # Check fans
        if "fans" in device_data:
            expected_fans = model_config.get("fans", 2)
            active_fans = sum(1 for fan in device_data.get("fans", []) if fan.get("speed", 0) > 0)
            
            if active_fans < expected_fans:
                issues["fans"] = f"No fans" if active_fans == 0 else f"Missing {expected_fans - active_fans} Fan(s)"
        
        # Check hashrate if available
        if "hashrate" in device_data:
            expected_hashrate = model_config.get("hashrate", 0)
            actual_hashrate = device_data.get("hashrate", 0)
            
            # If hashrate is below 60% of expected
            if actual_hashrate > 0 and actual_hashrate < (expected_hashrate * 0.6):
                issues["hashrate"] = f"Low hashrate: {actual_hashrate} (Expected: {expected_hashrate})"
        
        # Any other message from device logs
        if "message" in device_data and device_data.get("message"):
            issues["message"] = device_data.get("message")
            
        return issues
    
    def generate_subsection_summary(self, subsection_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary for a subsection
        
        Args:
            subsection_results: Raw scan results for a subsection
            
        Returns:
            Summary dictionary for the subsection
        """
        # Expected miners from config
        expected_miners = {miner["model"]: miner["quantity"] for miner in subsection_results.get("expected_miners", [])}
        
        # Actual miners found
        devices = subsection_results.get("devices", {})
        
        # Group devices by type
        devices_by_type = {}
        devices_with_issues = {}
        
        for ip, device_data in devices.items():
            device_type = device_data.get("device_type", "unknown")
            
            # Normalize device type
            device_type = DeviceRegistry.normalize_device_type(device_type)
            
            # Add to device type group
            if device_type not in devices_by_type:
                devices_by_type[device_type] = []
            devices_by_type[device_type].append(ip)
            
            # Check for issues
            issues = self.analyze_device_issues(device_data)
            if issues:
                if device_type not in devices_with_issues:
                    devices_with_issues[device_type] = []
                
                devices_with_issues[device_type].append({
                    "ip": ip,
                    "issues": issues
                })
                
        # Generate summary
        summary = {
            "working": {},
            "issues": devices_with_issues,
            "comparison": {}
        }
        
        # Summarize working devices by type
        for device_type, ips in devices_by_type.items():
            # Count devices with issues
            issues_count = sum(1 for issues in devices_with_issues.get(device_type, []))
            working_count = len(ips) - issues_count
            
            summary["working"][device_type] = working_count
        
        # Comparison between expected and actual
        for device_type, expected_count in expected_miners.items():
            actual_count = len(devices_by_type.get(device_type, []))
            issues_count = len(devices_with_issues.get(device_type, []))
            
            summary["comparison"][device_type] = {
                "expected": expected_count,
                "actual": actual_count,
                "working": actual_count - issues_count,
                "with_issues": issues_count,
                "offline": expected_count - actual_count
            }
            
        return summary
    
    # ==========================================
    # Output and Reporting Methods
    # ==========================================
    
    def save_scan_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """
        Save scan results to a JSON file
        
        Args:
            results: Scan results dictionary
            filename: Optional filename, if None a timestamped name will be used
            
        Returns:
            Path to saved file
        """
        # Create output directory if it doesn't exist
        output_dir = "reports"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            site_id = results.get("site_id", "unknown").replace(" ", "_")
            filename = f"{output_dir}/site_scan_{site_id}_{timestamp}.json"
        
        # Save JSON results
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"✅ Results saved to {filename}")
        return filename
    
    def print_subsection_report(self, subsection_result: Dict[str, Any]) -> None:
        """
        Print a human-readable report for a subsection
        
        Args:
            subsection_result: Scan results for a subsection
        """
        subsection_name = subsection_result.get("name", "Unnamed Subsection")
        ip_ranges = subsection_result.get("ip_ranges", [])
        summary = subsection_result.get("summary", {})
        
        # Print header
        print(f"\n{'—'*40}")
        print(f"{subsection_name} = {', '.join(ip_ranges)}")
        
        # Print working devices
        print("\nWorking:")
        working = summary.get("working", {})
        if working:
            for device_type, count in working.items():
                if count > 0:
                    print(f"{count}x {device_type}")
        else:
            print("None")
        
        # Print issues
        print("\nIssues:")
        issues = summary.get("issues", {})
        if issues:
            for device_type, devices_with_issues in issues.items():
                for device in devices_with_issues:
                    issue_texts = []
                    for issue_type, issue_desc in device["issues"].items():
                        if issue_type != "message":  # Skip general messages
                            issue_texts.append(issue_desc)
                    
                    if issue_texts:
                        print(f"1x {device_type} -> {' & '.join(issue_texts)}")
        else:
            print("None")
        
        # Print theoretical vs real comparison
        print("\nTheoretical Online vs Real")
        comparison = summary.get("comparison", {})
        for device_type, stats in comparison.items():
            expected = stats.get("expected", 0)
            actual = stats.get("actual", 0)
            issues_count = stats.get("with_issues", 0)
            offline = stats.get("offline", 0)
            
            # Format offline warning if needed
            offline_warning = f"  {offline} Miners are offline !!!" if offline > 0 else ""
            
            print(f"{actual} out of {expected} {device_type} online with {issues_count} issues.{offline_warning}")
    
    def print_site_report(self, site_results: Dict[str, Any]) -> None:
        """
        Print a complete site report
        
        Args:
            site_results: Complete scan results for a site
        """
        site_id = site_results.get("site_id", "Unknown Site")
        timestamp = site_results.get("timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        duration = site_results.get("duration_seconds", 0)
        subsections = site_results.get("subsections", [])
        
        # Print header
        # Розрахунок хвилин та секунд для зручнішого відображення
        minutes = int(duration // 60)
        remaining_seconds = int(duration % 60)
        
        # Відображення часу у зручному форматі
        if minutes > 0:
            time_display = f"{minutes} min {remaining_seconds} sec ({duration} seconds)"
        else:
            time_display = f"{duration} seconds"
            
        print(f"\nScan completed for {site_id} (Time taken: {time_display})")
        
        print(f"Timestamp: {timestamp}")
        
        # Print each subsection
        for subsection in subsections:
            self.print_subsection_report(subsection)
        
        print(f"\n{'—'*40}")


def compare_ip_libraries(ip_range="192.168.1.0/24"):
    """
    Direct comparison between ipaddress and netaddr libraries
    
    Args:
        ip_range: IP range to parse and compare
    """
    print(f"\n{'='*50}")
    print(f"Comparing IP libraries on range: {ip_range}")
    print(f"{'='*50}\n")
    
    # Timing for ipaddress
    print("\n1. Using standard ipaddress library:")
    start_time = time.time()
    try:
        # Parse with ipaddress
        if '/' in ip_range:  # CIDR notation
            ip_network = ipaddress.IPv4Network(ip_range, strict=False)
            ips_ipaddress = [str(ip) for ip in ip_network.hosts()]
        elif '-' in ip_range:  # Range notation
            start_ip, end_ip = ip_range.split('-')
            start_ip = start_ip.strip()
            end_ip = end_ip.strip()
            
            # Convert to integers
            start_int = int(ipaddress.IPv4Address(start_ip))
            end_int = int(ipaddress.IPv4Address(end_ip))
            
            # Generate all IPs in range
            ips_ipaddress = [str(ipaddress.IPv4Address(ip)) for ip in range(start_int, end_int + 1)]
        else:
            # Single IP
            ips_ipaddress = [ip_range]
            
        ipaddress_time = time.time() - start_time
        print(f"Parsed {len(ips_ipaddress)} IPs in {ipaddress_time:.6f} seconds")
        print(f"First 5 IPs: {', '.join(ips_ipaddress[:5])}{'...' if len(ips_ipaddress) > 5 else ''}")
    except Exception as e:
        print(f"Error with ipaddress: {e}")
        ipaddress_time = float('inf')
    
    # Only proceed with netaddr comparison if it's available
    if not NETADDR_AVAILABLE:
        print("\n⚠️ Netaddr library not available - cannot compare")
        return
    
    # Timing for netaddr
    print("\n2. Using netaddr library:")
    start_time = time.time()
    try:
        # Parse with netaddr
        if '/' in ip_range:  # CIDR notation
            ip_network = netaddr.IPNetwork(ip_range)
            ips_netaddr = [str(ip) for ip in ip_network]
        elif '-' in ip_range:  # Range notation
            start_ip, end_ip = ip_range.split('-')
            start_ip = start_ip.strip()
            end_ip = end_ip.strip()
            ip_range_obj = netaddr.IPRange(start_ip, end_ip)
            ips_netaddr = [str(ip) for ip in ip_range_obj]
        else:
            # Single IP
            ips_netaddr = [ip_range]
        
        netaddr_time = time.time() - start_time
        print(f"Parsed {len(ips_netaddr)} IPs in {netaddr_time:.6f} seconds")
        print(f"First 5 IPs: {', '.join(ips_netaddr[:5])}{'...' if len(ips_netaddr) > 5 else ''}")
    except Exception as e:
        print(f"Error with netaddr: {e}")
        netaddr_time = float('inf')
    
    # Compare results
    print("\n--- Comparison Results ---")
    
    # Compare parsing time
    if ipaddress_time < netaddr_time:
        print(f"🕒 ipaddress was faster by {netaddr_time - ipaddress_time:.6f} seconds")
    elif netaddr_time < ipaddress_time:
        print(f"🕒 netaddr was faster by {ipaddress_time - netaddr_time:.6f} seconds")
    else:
        print("🕒 Both libraries performed at similar speed")
    
    # Compare features
    print("\n--- Feature Comparison ---")
    print("ipaddress:")
    print("  ✓ Built into Python standard library")
    print("  ✓ Simple API for common use cases")
    print("  ✓ IPv4 and IPv6 support")
    print("  ✗ Limited support for non-standard notation")
    
    print("\nnetaddr:")
    print("  ✓ More comprehensive parsing capabilities")
    print("  ✓ Better support for various notations and formats")
    print("  ✓ Additional network utilities")
    print("  ✓ Enhanced CIDR operations")
    print("  ✗ External dependency (not in standard library)")
    
    # Recommendation
    print("\n--- Recommendation ---")
    print("Use ipaddress for:")
    print("  - Simple network operations")
    print("  - When avoiding external dependencies is important")
    print("  - Standard IPv4/IPv6 CIDR notation")
    
    print("\nUse netaddr for:")
    print("  - Complex network operations")
    print("  - When parsing various IP formats")
    print("  - Working with MAC addresses")
    print("  - More advanced network calculations")


def compare_scan_methods(ip_range=None):
    """
    Compare different scanning methods for performance
    
    Args:
        ip_range: IP range to scan for testing, or "combined" for testing multiple networks
    """
    # Create scanner instance
    scanner = SiteScanner()
    
    # Check if we're doing the combined networks test
    if ip_range == "combined":
        print(f"\n{'='*50}")
        print(f"Testing combined networks: 10.32.101.0/24 + 10.31.105.0/24")
        print(f"{'='*50}\n")
        
        networks = ["10.32.101.0/24", "10.31.105.0/24"]
        
        # Test different methods on each network separately
        for network in networks:
            print(f"\nTesting network: {network}")
            print("-" * 30)
            
            # Test async method for this network
            print("\nAsync method:")
            ips = scanner.scan_ip_range_async(network)
            print(f"Found {len(ips)} active IPs")
            
            # Test standard method for this network
            print("\nStandard method:")
            ips_standard = scanner.scan_ip_range(network)
            print(f"Found {len(ips_standard)} active IPs")
            
        print("\nCombined networks testing complete")
        return
        
    # If IP range is not specified, use 10.32.101.0/24 by default
    if not ip_range:
        ip_range = "10.32.101.0/24"
        
    print(f"\n{'='*50}")
    print(f"Comparing scanning methods on range {ip_range}")
    print(f"{'='*50}\n")
    
    # Original method with 50 threads
    print("\n1. Original method (50 threads):")
    start = time.time()  # Start timing
    responsive_ips_original = scanner.scan_ip_range(ip_range)
    duration = time.time() - start  # Calculate duration
    print(f"Found {len(responsive_ips_original)} active IP addresses")
    print(f"Time: {duration:.2f} seconds")
    
    # Method with increased thread count (200)
    print("\n2. Method with increased thread count (200):")
    start = time.time()  # Start timing
    responsive_ips_more_threads = scanner.scan_ip_range_more_threads(ip_range)
    duration = time.time() - start  # Calculate duration
    print(f"Found {len(responsive_ips_more_threads)} active IP addresses")
    print(f"Time: {duration:.2f} seconds")
    
    # Async method with asyncio
    print("\n3. Async method with asyncio:")
    start = time.time()  # Start timing
    responsive_ips_async = scanner.scan_ip_range_async(ip_range)
    duration = time.time() - start  # Calculate duration
    print(f"Found {len(responsive_ips_async)} active IP addresses")
    print(f"Time: {duration:.2f} seconds")
    
    # Chunked method
    print("\n4. Chunked method:")
    start = time.time()  # Start timing
    responsive_ips_chunked = scanner.scan_ip_range_chunked(ip_range)
    duration = time.time() - start  # Calculate duration
    print(f"Found {len(responsive_ips_chunked)} active IP addresses")
    print(f"Time: {duration:.2f} seconds")
    
    # Netaddr method (if available)
    if NETADDR_AVAILABLE:
        print("\n5. Netaddr method:")
        start = time.time()  # Start timing
        responsive_ips_netaddr = scanner.scan_ip_range_netaddr(ip_range)
        duration = time.time() - start  # Calculate duration
        print(f"Found {len(responsive_ips_netaddr)} active IP addresses")
        print(f"Time: {duration:.2f} seconds")
        
    # Pytricia method (if available)
    if PYTRICIA_AVAILABLE:
        print("\n6. Pytricia method:")
        start = time.time()  # Start timing
        responsive_ips_pytricia = scanner.scan_ip_range_pytricia(ip_range)
        duration = time.time() - start  # Calculate duration
        print(f"Found {len(responsive_ips_pytricia)} active IP addresses")
        print(f"Time: {duration:.2f} seconds")
    
    # Output comparison results
    print(f"\n{'='*50}")
    print("Comparison Results:")
    print(f"{'='*50}")
    
    # Check if all methods found the same IPs
    all_same = True
    if set(responsive_ips_original) != set(responsive_ips_more_threads):
        all_same = False
        print("❌ Results from method with increased thread count differ")
    if set(responsive_ips_original) != set(responsive_ips_async):
        all_same = False
        print("❌ Results from async method differ")
    if set(responsive_ips_original) != set(responsive_ips_chunked):
        all_same = False
        print("❌ Results from chunked method differ")
    
    # Compare with netaddr method if available
    if NETADDR_AVAILABLE:
        if 'responsive_ips_netaddr' in locals() and set(responsive_ips_original) != set(responsive_ips_netaddr):
            all_same = False
            print("❌ Results from netaddr method differ")
            
    # Compare with pytricia method if available
    if PYTRICIA_AVAILABLE:
        if 'responsive_ips_pytricia' in locals() and set(responsive_ips_original) != set(responsive_ips_pytricia):
            all_same = False
            print("❌ Results from pytricia method differ")
    
    if all_same:
        print("✅ All methods found the same IP addresses")
    
    # Recommendation for fastest method
    print("\nRecommendation: ")
    print("Based on testing results, we recommend using:")
    
    # NOTE: Logic could be added here to select the best method
    # based on execution time. For now, we're just providing general
    # recommendations based on network size.
    print("- For small networks (<100 IPs): Original method")
    print("- For medium networks (<1000 IPs): Method with increased thread count")
    print("- For large networks (<5000 IPs): Async method")
    print("- For very large networks (>5000 IPs): Chunked method")
    
    if NETADDR_AVAILABLE:
        print("- For complex network ranges: Netaddr method (accurate IP parsing)")
    else:
        print("- Install 'netaddr' package for improved handling of complex network ranges")
        
    if PYTRICIA_AVAILABLE:
        print("- For network prefix matching: Pytricia method (fastest prefix lookups)")
    else:
        print("- Install 'pytricia' package for faster prefix-tree based IP matching")


def main():
    """
    Main function to run the site scanner from command line
    """
    parser = argparse.ArgumentParser(description="Site Scanner Tool for mining operations")
    parser.add_argument("config", nargs="?", help="Path to site configuration file")
    parser.add_argument("--output", "-o", help="Output file for scan results")
    parser.add_argument("--benchmark", "-b", help="Run benchmark on specified IP range")
    parser.add_argument("--compare-libs", "-c", help="Compare ipaddress and netaddr libraries for the specified IP range")
    
    args = parser.parse_args()
    
    # If benchmark flag is provided, run performance comparison
    if args.benchmark:
        compare_scan_methods(args.benchmark)
        return
        
    # If compare-libs flag is provided, run library comparison
    if args.compare_libs:
        compare_ip_libraries(args.compare_libs)
        return
    
    # If no config file provided, show help
    if not args.config:
        parser.print_help()
        return
    
    # Create scanner instance with the config file
    scanner = SiteScanner(args.config)
    
    if not scanner.site_config:
        print("❌ No valid site configuration provided.")
        return
        
    # Scan site
    results = scanner.scan_site()
    
    # Save results if scan successful
    if results:
        filename = scanner.save_scan_results(results, args.output)
        
        # Print report
        scanner.print_site_report(results)
        
        print(f"\nComplete scan results saved to: {filename}")
    

if __name__ == "__main__":
    main()
