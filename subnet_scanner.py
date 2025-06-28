#!/usr/bin/env python3
"""
Subnet Scanner Tool
For scanning IP subnets, detecting device types, and fetching logs
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
from typing import List, Dict, Any, Optional, Union

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

# Import device components
from device_manager import DeviceManager
from handlers import t21_handler
from handlers import s21_handler
from handlers import z15_handler
from handlers import s21_pro_handler
from handlers import dg1_handler
from device_registry import DeviceRegistry

class SubnetScanner:
    """
    Subnet Scanner tool for scanning IP ranges, detecting device types, 
    fetching logs, and generating reports.
    
    This class combines the functionality of the previous SubnetControllerScan
    and Z15FanBroker classes into a single unified scanner.
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
        
        # Load configuration
        self.config = self.load_config(config_file)
        
        # Update credentials from config if available
        if self.config:
            self.username = self.config.get("username", self.username)
            self.password = self.config.get("password", self.password)
            self.timeout = self.config.get("timeout", self.timeout)
    
    # ==========================================
    # Configuration and Setup Methods
    # ==========================================
    
    def load_config(self, config_file: str = None) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults
        
        Args:
            config_file: Path to JSON configuration file
            
        Returns:
            Configuration as dictionary
        """
        default_config = {
            "username": "root",
            "password": "root",
            "timeout": 5,
            "subnets": ["10.31.212.0/24"],
            "log_endpoint": "/cgi-bin/api.cgi"
        }
        
        if not config_file:
            print("⚠️ No config file specified, using defaults.")
            return default_config
            
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"❌ Error loading config file: {e}")
            return default_config
            
    # ==========================================
    # Subnet Scanning Methods  
    # ==========================================
            
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
            # Always display this information, regardless of verbose setting
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
                            # Disable output about found hosts
                            # if verbose:
                            #    print(f"✅ Found responsive host: {ip}")
                    except Exception as e:
                        if verbose:
                            print(f"❌ Error checking {ip}: {e}")
            
            self.active_ips = responsive_ips
            return responsive_ips
            
        except ValueError as e:
            print(f"❌ Error: {e}")
            return []

    def check_ip_responsive(self, ip: str) -> bool:
        """Check if an IP responds to HTTP requests"""
        try:
            response = requests.get(f"http://{ip}/", 
                                   auth=HTTPDigestAuth(self.username, self.password),
                                   timeout=self.timeout)
            return True
        except requests.RequestException:
            return False
    
    def scan_subnets(self) -> List[str]:
        """
        Scan all configured subnets and return active IPs
        
        Returns:
            List of all responsive IP addresses across all configured subnets
        """
        all_active_ips = []
        all_results = {}
        
        # Scan each subnet without printing details for each IP
        for subnet in self.config.get("subnets"):
            # Scan the subnet
            print(f"🔍 Scanning subnet: {subnet}")
            subnet_ips = self.scan_subnet(subnet, verbose=False)
            
            # If active IPs found in this subnet
            if subnet_ips:
                # First detect device types
                for ip in subnet_ips:
                    # Detect device type using the device_manager (quietly)
                    device_info = self.device_manager.detect_device_type(ip, verbose=False)
                    
                    # Get logs for each IP
                    self.active_ips = [ip]  # Temporarily set one IP for getting logs
                    
                    # Get the device type
                    device_type = device_info.get("device_type", "unknown")
                    
                    # Fetch logs using device_manager (which will use the appropriate handler)
                    result = self.device_manager.fetch_logs_from_device(ip, device_type, verbose=False)
                    
                    if result:
                        # Add device type information to the result
                        result["device_type"] = device_type
                        result["device_type_source"] = device_info.get("source")
                        all_results[ip] = result
            
            # Add to overall list
            all_active_ips.extend(subnet_ips)
                
        # Store all results
        self.results = all_results
        self.active_ips = all_active_ips
        
        return all_active_ips
        
    # ==========================================
    # Report Generation Methods
    # ==========================================
    
    def save_results_to_file(self, filename: str = "scan_results.json") -> None:
        """
        Save scan results to a JSON file with improved formatting
        
        Args:
            filename: Name of the output file
        """
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        # Group results by device type for better readability
        structured_results = {
            "scan_summary": {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_devices": len(self.results),
                "subnets_scanned": self.config.get('subnets', []),
            },
            "devices_by_type": {}
        }
        
        # Process and group devices by type
        for ip, result in self.results.items():
            device_type = result.get("device_type", "unknown")
            
            # Normalize device type (handle common variations)
            main_type = DeviceRegistry.normalize_device_type(device_type)
            
            # Initialize device type group if not exists
            if main_type not in structured_results["devices_by_type"]:
                structured_results["devices_by_type"][main_type] = {}
            
            # Add device to its type group
            structured_results["devices_by_type"][main_type][ip] = result
        
        # Add device type counts to summary
        device_counts = {}
        for device_type, devices in structured_results["devices_by_type"].items():
            device_counts[device_type] = len(devices)
        structured_results["scan_summary"]["device_counts"] = device_counts
        
        # Save structured JSON results
        with open(filename, 'w') as f:
            json.dump(structured_results, f, indent=2)
        
        # print(f"✅ Results saved to {filename}")
    
    def generate_report(self):
        """
        Generate a report with scan results
        
        Returns:
            Dictionary with paths to generated report files
        """
        # Ensure output directory exists
        output_dir = "reports"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate JSON report
        output_file = f"{output_dir}/scan_report_{timestamp}.json"
        self.save_results_to_file(output_file)
        
        return {
            "json_report": output_file,
        }
        
    def print_aggregate_report(self):
        """
        Print an aggregate report of scan results, grouping devices by type
        and normalizing error messages for better readability
        """
        # Get total IPs scanned across all subnets
        total_ips_scanned = sum(ipaddress.ip_network(subnet).num_addresses 
                                for subnet in self.config.get('subnets'))
        
        responsive_ips = len(self.active_ips)
        unresponsive_ips = total_ips_scanned - responsive_ips
        
        # Group devices by detected type
        device_types = {}
        
        for ip, result in self.results.items():
            # Process all devices regardless of log fetch status
            # (device type detection happens before log fetching)
            device_type = result.get("device_type", "unknown")
            
            # Use the device registry to normalize device type
            main_type = DeviceRegistry.normalize_device_type(device_type)
            
            if main_type not in device_types:
                device_types[main_type] = []
            device_types[main_type].append(ip)
            
        # Print summary report header
        print(f"\n{'='*40}")
        print(f"============ Scanner Report ============")
        print(f"{'='*40}")
        
        # Print subnet information
        print(f"Subnets scanned: {', '.join(self.config.get('subnets'))}")
        print(f"IPs scanned: {total_ips_scanned}")
        print(f"Responsive IPs: {responsive_ips}")
        
        # Print device type counts
        print(f"\nDevice Types Found:")
        for device_type, ips in device_types.items():
            print(f"• {device_type}: {len(ips)} devices")
        
        print(f"IPs unresponsive: {unresponsive_ips}")
        
        # Aggregate errors by device type and message
        device_error_groups = {}
        
        for ip, result in self.results.items():
            # Get device type with normalized format using the registry
            device_type = result.get("device_type", "unknown")
            main_type = DeviceRegistry.normalize_device_type(device_type)
            
            # Get message, all devices may have messages (error or success)
            message = result.get('message', '')
            
            if message:
                # Use device type from the result to ensure proper classification
                
                if main_type not in device_error_groups:
                    device_error_groups[main_type] = {}
                
                # Normalize the message to group similar errors using device handlers
                normalized_message = message
                
                # Use device handlers to normalize messages
                handler_class = DeviceRegistry.get_handler(main_type)
                if handler_class:
                    try:
                        handler = handler_class(self)
                        normalized_message = handler.normalize_message(message)
                    except Exception as e:
                        # If normalization fails, fall back to the original message
                        print(f"Error during message normalization for {main_type}: {str(e)}")
                
                # Store the normalized message in the error groups
                if normalized_message not in device_error_groups[main_type]:
                    device_error_groups[main_type][normalized_message] = []
                
                # Add this IP to the list for this message group
                device_error_groups[main_type][normalized_message].append(ip)
        
        # Print error groups by device type if any exist
        if device_error_groups:
            print(f"\n{'='*40}")
            print(f"Grouped Messages by Device Type:")
            print(f"{'='*40}")
            
            # Sort device types to put 'unknown' at the end
            sorted_device_types = sorted(device_error_groups.keys(), key=lambda x: (x == "unknown", x))
            
            for device_type in sorted_device_types:
                message_groups = device_error_groups[device_type]
                print(f"\nErrors found on {device_type} devices:")
                
                for message, ips in message_groups.items():
                    # Display all IPs in the list
                    ip_display = ", ".join(ips)
                    
                    # Display the normalized message (without timestamps)
                    print(f"• 📝 Message  : {message} | {len(ips)} devices | {ip_display}")

# Main function for command-line usage
def main():
    parser = argparse.ArgumentParser(description='Subnet Scanner - Device discovery and log analysis')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--scan', action='store_true', help='Scan subnets for active devices')
    parser.add_argument('--report', action='store_true', help='Generate a report of scan results')
    args = parser.parse_args()
    
    scanner = SubnetScanner(config_file=args.config)
    
    if args.scan:
        print("🔍 Starting subnet scan...")
        active_ips = scanner.scan_subnets()
        
        # Always display the aggregate report after scanning
        scanner.print_aggregate_report()
        
        # Generate JSON report if requested
        if args.report:
            print("\n📊 Generating JSON report...")
            reports = scanner.generate_report()
            print(f"✅ JSON report saved to {reports['json_report']}")
    
    elif args.report and not args.scan:
        print("\n📊 Generating report...")
        reports = scanner.generate_report()
        print(f"✅ JSON report saved to {reports['json_report']}") 

if __name__ == "__main__":
    main()
