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
                # Get logs for each IP
                for ip in subnet_ips:
                    self.scanner.active_ips = [ip]  # Temporarily set one IP for getting logs
                    result = self.scanner.fetch_logs_from_ip(ip, endpoint, verbose=False)
                    if result:
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
        
        # Treat all responsive devices as Z15 devices
        z15_devices = list(self.scanner.results.keys())
        non_z15_devices = []
        
        # Print summary report header
        print(f"\n{'='*40}")
        print(f"============ Scanner Report ============")
        print(f"{'='*40}")
        
        # Print subnet information
        print(f"Subnets scanned: {', '.join(self.config.get('subnets'))}")
        print(f"IPs scanned: {total_ips_scanned}")
        print(f"IPs with device Found: {responsive_ips}")
        print(f"Z15 Found: {len(z15_devices)}")
        print(f"Non Z-15 Found: {len(non_z15_devices)}")
        print(f"IPs unresponsive: {unresponsive_ips}")
        
        # Aggregate errors by message
        error_groups = {}
        
        for ip, result in self.scanner.results.items():
            if ip in z15_devices:
                message = result.get('message', '')
                if message:
                    if message not in error_groups:
                        error_groups[message] = []
                    error_groups[message].append(ip)
        
        # Print error summary
        if error_groups:
            print(f"\nErrors found on Z15 devices:")
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
