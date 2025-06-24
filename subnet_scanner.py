#!/usr/bin/env python3
import ipaddress
import concurrent.futures
import requests
from requests.auth import HTTPDigestAuth
import re
from urllib.parse import urlparse
import json
import time
from typing import List, Dict, Any, Optional, Union

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
    
    def fetch_logs_from_all_active(self, endpoint: str = "/cgi-bin/get_kernel_log.cgi") -> Dict[str, Any]:
        """
        Fetch logs from all active IPs
        
        Returns:
            Dictionary with results for each IP
        """
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ip = {
                executor.submit(self.fetch_logs_from_ip, ip, endpoint): ip 
                for ip in self.active_ips
            }
            
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    result = future.result()
                    results[ip] = result
                except Exception as e:
                    results[ip] = {
                        "ip": ip,
                        "status": "error",
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
