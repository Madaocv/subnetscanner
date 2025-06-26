#!/usr/bin/env python3
"""
Z15 Fan Broker - Plugin for FluxSentry
Allows for scanning subnets and interacting with Z15 Fan devices
"""

from subnet_scanner import SubnetControllerScan
import argparse
import json
import os
import ipaddress
from typing import Dict, Any, List

class Z15FanBroker:
    """
    Z15 Fan Broker - Plugin for subnet scanning and device management
    This plugin can be activated in the SCS (Subnet Controller Scan) system
    """
    def __init__(self, config_file: str = None):
        self.scanner = SubnetControllerScan()
        self.config = self.load_config(config_file)
        
    def load_config(self, config_file: str = None) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        default_config = {
            "username": "root",
            "password": "root", 
            "timeout": 5,
            "subnets": ["10.31.212.0/24"],
            "log_endpoint": "/cgi-bin/get_kernel_log.cgi",
            "output_dir": "scan_results"
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Update default config with loaded values
                    default_config.update(loaded_config)
            except Exception as e:
                print(f"❌ Error loading config file: {e}")
                
        return default_config
    
    def scan_subnets(self) -> List[str]:
        """Scan all configured subnets and return active IPs"""
        all_active_ips = []
        all_results = {}
        endpoint = self.config.get("log_endpoint")
        
        # Update scanner with config
        self.scanner.username = self.config.get("username")
        self.scanner.password = self.config.get("password")
        self.scanner.timeout = self.config.get("timeout")
        
        # Scan each subnet without printing details for each IP
        for subnet in self.config.get("subnets"):
            # Scan the subnet
            print(f"🔍 Scanning subnet: {subnet}")
            subnet_ips = self.scanner.scan_subnet(subnet, verbose=False)
            
            # If active IPs found in this subnet
            if subnet_ips:
                # First detect device types
                for ip in subnet_ips:
                    # Detect device type (quietly)
                    device_info = self.scanner.detect_device_type(ip, verbose=False)
                    
                    # Get logs for each IP
                    self.scanner.active_ips = [ip]  # Temporarily set one IP for getting logs
                    
                    # Fetch logs based on device type
                    result = None
                    device_type = device_info.get("device_type", "unknown")
                    
                    if "T21" in device_type:
                        result = self.scanner.fetch_logs_via_websocket(ip, "/api/v1/logs-ws/status")
                    elif "S21" in device_type:
                        # Try S21-specific endpoint
                        result = self.scanner.fetch_logs_from_s21(ip, "/cgi-bin/hlog.cgi")
                    else:
                        # Default log fetching
                        result = self.scanner.fetch_logs_from_ip(ip, endpoint, verbose=False)
                    
                    if result:
                        # Add device type information to the result
                        result["device_type"] = device_type
                        result["device_type_source"] = device_info.get("source")
                        all_results[ip] = result
            
            # Add to overall list
            all_active_ips.extend(subnet_ips)
        
        # Save all results
        self.scanner.active_ips = all_active_ips
        self.scanner.results = all_results
            
        return all_active_ips
        
    def fetch_logs(self) -> Dict[str, Any]:
        """Fetch logs from all active IPs"""
        endpoint = self.config.get("log_endpoint")
        return self.scanner.fetch_logs_from_all_active(endpoint)
        
    def generate_report(self):
        """Generate a report with scan results"""
        # Ensure output directory exists
        output_dir = self.config.get("output_dir")
        os.makedirs(output_dir, exist_ok=True)
        
        # Save results to file
        output_file = os.path.join(output_dir, "z15_fan_scan.json")
        self.scanner.save_results_to_file(output_file)
        
        # Display aggregated report
        self._print_aggregate_report()
        
        return {
            "json_report": output_file
        }
    
    def _print_aggregate_report(self):
        """Print an aggregated summary report of scan results"""
        # Count devices by type
        total_ips_scanned = sum(ipaddress.ip_network(subnet).num_addresses for subnet in self.config.get("subnets"))
        responsive_ips = len(self.scanner.active_ips)
        unresponsive_ips = total_ips_scanned - responsive_ips
        
        # Group devices by detected type
        device_types = {}
        
        for ip, result in self.scanner.results.items():
            # Process all devices regardless of log fetch status
            # (device type detection happens before log fetching)
            device_type = result.get("device_type", "unknown")
            
            # Extract main device model from longer strings
            # Use a more comprehensive approach to categorize devices
            if device_type != "unknown":
                # Extract the main model from full device type string
                if "Z15" in device_type:
                    main_type = "Z15"
                elif "T21" in device_type:
                    main_type = "T21"
                elif "S21" in device_type:  # Added for Antminer S21+ devices
                    main_type = "S21"
                else:
                    # For any other models, extract the model number (e.g., Antminer XXX -> XXX)
                    import re
                    model_match = re.search(r'Antminer\s+([A-Z]\d+[\+]*)', device_type)
                    if model_match:
                        main_type = model_match.group(1)
                    else:
                        # Use the full string if we can't extract a specific model
                        main_type = device_type
            else:
                main_type = "unknown"
            
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
        
        for ip, result in self.scanner.results.items():
            # Get device type with same processing as above
            device_type = result.get("device_type", "unknown")
            if device_type != "unknown":
                if "Z15" in device_type:
                    main_type = "Z15"
                elif "T21" in device_type:
                    main_type = "T21"
                elif "S21" in device_type:
                    main_type = "S21"
                else:
                    import re
                    model_match = re.search(r'Antminer\s+([A-Z]\d+[\+]*)', device_type)
                    if model_match:
                        main_type = model_match.group(1)
                    else:
                        main_type = device_type
            else:
                main_type = "unknown"
            
            # Get message, all devices may have messages (error or success)
            message = result.get('message', '')
            
            if message:
                if main_type not in device_error_groups:
                    device_error_groups[main_type] = {}
                
                if message not in device_error_groups[main_type]:
                    device_error_groups[main_type][message] = []
                
                device_error_groups[main_type][message].append(ip)
        
        # Print error summary by device type
        for device_type, error_groups in device_error_groups.items():
            if error_groups:
                print(f"\nErrors found on {device_type} devices:")
                for message, ips in error_groups.items():
                    # Display abbreviated IP list if too many
                    if len(ips) > 3:
                        ip_display = f"{ips[0]}, {ips[1]}, {ips[2]}, etc."
                    else:
                        ip_display = ", ".join(ips)
                    
                    print(f"• 📝 Message  : {message} | {len(ips)} devices | {ip_display}")

def main():
    parser = argparse.ArgumentParser(description='Z15 Fan Broker - Subnet scanning and device management')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--scan', action='store_true', help='Scan subnets for active devices')
    parser.add_argument('--report', action='store_true', help='Generate a report of scan results')
    args = parser.parse_args()
    
    broker = Z15FanBroker(config_file=args.config)
    
    if args.scan:
        print("🔍 Starting subnet scan...")
        active_ips = broker.scan_subnets()
        
        # Always display the aggregate report after scanning
        broker._print_aggregate_report()
        
        # Generate JSON report if requested
        if args.report:
            print("\n📊 Generating JSON report...")
            reports = broker.generate_report()
            print(f"✅ JSON report saved to {reports['json_report']}")
    
    elif args.report and not args.scan:
        print("\n📊 Generating report...")
        reports = broker.generate_report()
        print(f"✅ JSON report saved to {reports['json_report']}") 
if __name__ == "__main__":
    main()
