#!/usr/bin/env python3
"""
Z15 Fan Broker - Plugin for FluxSentry
Allows for scanning subnets and interacting with Z15 Fan devices
"""

from subnet_scanner import SubnetControllerScan
import argparse
import json
import os
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
        
        # Скануємо кожну підмережу та обробляємо результати відразу
        for subnet in self.config.get("subnets"):
            print(f"\n🔍 Scanning subnet: {subnet}")
            # Сканування підмережі
            subnet_ips = self.scanner.scan_subnet(subnet)
            
            # Якщо знайдено активні IP в цій підмережі
            if subnet_ips:
                # Отримуємо логи для кожного IP окремо
                for ip in subnet_ips:
                    self.scanner.active_ips = [ip]  # Тимчасово встановлюємо один IP для отримання логів
                    result = self.scanner.fetch_logs_from_ip(ip, endpoint)
                    if result:
                        all_results[ip] = result
                        
                        # Показуємо деталі для цього IP відразу
                        print(f"{'-'*105}\n📡 Device IP Address: {ip}")
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
            
            # Додаємо до загального списку
            all_active_ips.extend(subnet_ips)
        
        # Зберігаємо всі результати
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
        
        # Generate HTML report
        html_report = os.path.join(output_dir, "z15_fan_report.html")
        self._generate_html_report(html_report)
        
        return {
            "json_report": output_file,
            "html_report": html_report
        }
    
    def _generate_html_report(self, output_file: str):
        """Generate an HTML report from scan results"""
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Z15 Fan Broker - Scan Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        h1, h2 {{ color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .device {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .device-success {{ border-left: 5px solid #4CAF50; }}
        .device-error {{ border-left: 5px solid #F44336; }}
        .label {{ font-weight: bold; display: inline-block; min-width: 100px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Z15 Fan Broker - Scan Report</h1>
        
        <div class="summary">
            <h2>Scan Summary</h2>
            <p><span class="label">Scan Time:</span> {self.scanner.results.get('scan_time', 'N/A')}</p>
            <p><span class="label">Total IPs:</span> {len(self.scanner.active_ips)}</p>
            <p><span class="label">Successful:</span> {sum(1 for r in self.scanner.results.values() if r.get('status') == 'success')}</p>
            <p><span class="label">Failed:</span> {sum(1 for r in self.scanner.results.values() if r.get('status') == 'error')}</p>
        </div>
        
        <h2>Device Details</h2>
"""
        
        # Add device sections
        for ip, result in self.scanner.results.items():
            status_class = "device-success" if result.get("status") == "success" else "device-error"
            html_content += f"""
        <div class="device {status_class}">
            <h3>Device IP: {ip}</h3>
"""
            
            if result.get("status") == "success":
                if "date" in result:
                    html_content += f"""
            <p><span class="label">Date:</span> {result.get('date')}</p>
            <p><span class="label">Time:</span> {result.get('time')}</p>
            <p><span class="label">Source:</span> {result.get('source')}</p>
            <p><span class="label">Message:</span> {result.get('message')}</p>
"""
                else:
                    html_content += f"""
            <p><span class="label">Raw Log:</span> {result.get('raw_log')}</p>
"""
            else:
                html_content += f"""
            <p><span class="label">Error:</span> {result.get('message')}</p>
"""
            
            html_content += """
        </div>
"""
        
        # Close HTML
        html_content += """
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"✅ HTML report saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Z15 Fan Broker - Subnet scanning and device management')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--scan', action='store_true', help='Scan subnets for active devices')
    parser.add_argument('--report', action='store_true', help='Generate a report of scan results')
    args = parser.parse_args()
    
    broker = Z15FanBroker(config_file=args.config)
    
    if args.scan:
        print("🔍 Starting subnet scan...")
        active_ips = broker.scan_subnets()  # Скануємо та показуємо результати відразу
        
        if active_ips:
            # Показуємо лише підсумок, оскільки деталі вже показані
            print(f"\n✅ Found {len(active_ips)} active devices.")
            print(f"\n{'-'*105}")
            print(f"📊 SUMMARY")
            print(f"{'-'*105}")
            print(f"🔍 Total devices found: {len(active_ips)}")
            print(f"✅ IP addresses: {', '.join(active_ips)}")
            print(f"{'-'*105}")
            
            # Генеруємо звіт якщо потрібно
            if args.report:
                print("\n📊 Generating report...")
                reports = broker.generate_report()
                print(f"✅ Reports saved to {broker.config.get('output_dir')} directory")
        else:
            print("❌ No active devices found.")
    
    if args.report:
        print("\n📊 Generating report...")
        reports = broker.generate_report()
        print(f"✅ JSON report saved to {reports['json_report']}")
        print(f"✅ HTML report saved to {reports['html_report']}")
        
if __name__ == "__main__":
    main()
