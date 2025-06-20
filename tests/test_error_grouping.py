#!/usr/bin/env python3
import os
import sys
import json
import ipaddress
import unittest
from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from subnet_scanner import SubnetControllerScan
from z15_fan_broker import Z15FanBroker


class TestErrorGrouping(unittest.TestCase):
    """Test case for verifying error grouping functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.broker = Z15FanBroker()
        self.broker.scanner = SubnetControllerScan()
        
        # Create mock results dict
        self.mock_results = {}
        
        # Setup test data
        self.create_test_data()
    
    def create_test_data(self):
        """Create mock test data for different error scenarios"""
        # Case 1: disable_PIC16F1704_dc_dc_new ok
        self.mock_results["10.68.28.3"] = {
            "ip": "10.68.28.3",
            "status": "success",
            "message": "disable_PIC16F1704_dc_dc_new ok",
            "raw_log": "2025-06-20 09:00:00 Z15_Fan: disable_PIC16F1704_dc_dc_new ok"
        }
        self.mock_results["10.44.25.2"] = {
            "ip": "10.44.25.2",
            "status": "success",
            "message": "disable_PIC16F1704_dc_dc_new ok",
            "raw_log": "2025-06-20 09:05:00 Z15_Fan: disable_PIC16F1704_dc_dc_new ok"
        }
        
        # Case 2: heart_beat_PIC16F1704_new
        self.mock_results["10.55.32.1"] = {
            "ip": "10.55.32.1",
            "status": "success",
            "message": "heart_beat_PIC16F1704_new: read_back_data[0]",
            "raw_log": "2025-06-20 09:10:00 Z15_Fan: heart_beat_PIC16F1704_new: read_back_data[0]"
        }
        self.mock_results["10.55.32.5"] = {
            "ip": "10.55.32.5",
            "status": "success",
            "message": "heart_beat_PIC16F1704_new: read_back_data[0]",
            "raw_log": "2025-06-20 09:12:00 Z15_Fan: heart_beat_PIC16F1704_new: read_back_data[0]"
        }
        self.mock_results["10.55.32.1_dup"] = {
            "ip": "10.55.32.1",
            "status": "success",
            "message": "heart_beat_PIC16F1704_new: read_back_data[0]",
            "raw_log": "2025-06-20 09:15:00 Z15_Fan: heart_beat_PIC16F1704_new: read_back_data[0]"
        }
        
        # Case 3: low freq with complex message
        self.mock_results["10.56.29.5"] = {
            "ip": "10.56.29.5",
            "status": "success",
            "message": "low freq[2-1]: cur freq 805, [775, 815], invalid nonce 0, ox status 1",
            "raw_log": "2025-06-20 09:20:00 Z15_Fan: low freq[2-1]: cur freq 805, [775, 815], invalid nonce 0, ox status 1"
        }
        
        # Case 4: No 2 Fan find
        self.mock_results["10.34.4.56"] = {
            "ip": "10.34.4.56",
            "status": "success",
            "message": "No 2 Fan find, check again",
            "raw_log": "2025-06-20 09:30:00 Z15_Fan: No 2 Fan find, check again"
        }
        self.mock_results["10.34.4.55"] = {
            "ip": "10.34.4.55",
            "status": "success",
            "message": "No 2 Fan find, check again",
            "raw_log": "2025-06-20 09:31:00 Z15_Fan: No 2 Fan find, check again"
        }
        self.mock_results["10.34.4.66"] = {
            "ip": "10.34.4.66",
            "status": "success",
            "message": "No 2 Fan find, check again",
            "raw_log": "2025-06-20 09:32:00 Z15_Fan: No 2 Fan find, check again"
        }
    
    def extract_error_groups(self, output_text):
        """Parse the output text to extract error groups"""
        error_groups = {}
        current_message = None
        lines = output_text.split('\n')
        
        for line in lines:
            if line.startswith('• 📝 Message  : '):
                parts = line[len('• 📝 Message  : '):].split(' | ')
                if len(parts) >= 3:
                    message = parts[0].strip()
                    count = int(parts[1].split()[0])
                    ips_text = parts[2]
                    ips = [ip.strip() for ip in ips_text.split(',')]
                    error_groups[message] = {'count': count, 'ips': ips}
        
        return error_groups
    
    def test_error_grouping(self):
        """Test that error messages are properly grouped"""
        # Set the results in the scanner
        self.broker.scanner.results = self.mock_results
        self.broker.scanner.active_ips = list(self.mock_results.keys())
        
        # Set config with mock subnets
        self.broker.config = {
            "subnets": ["10.68.28.0/24", "10.44.25.0/24", "10.55.32.0/24", "10.56.29.0/24", "10.34.4.0/24"]
        }
        
        # Capture the output of _print_aggregate_report
        output_buffer = StringIO()
        with redirect_stdout(output_buffer):
            self.broker._print_aggregate_report()
        
        output_text = output_buffer.getvalue()
        
        # Print the captured output to see it in the terminal
        print("\n\nCaptured Test Output:\n" + "="*50)
        print(output_text)
        print("="*50)
        
        error_groups = self.extract_error_groups(output_text)
        
        # Verify the expected error groups exist
        expected_groups = {
            "disable_PIC16F1704_dc_dc_new ok": {'count': 2, 'ips': ['10.68.28.3', '10.44.25.2']},
            "heart_beat_PIC16F1704_new: read_back_data[0]": {'count': 3, 'ips': ['10.55.32.1', '10.55.32.5', '10.55.32.1_dup']},
            "low freq[2-1]: cur freq 805, [775, 815], invalid nonce 0, ox status 1": {'count': 1, 'ips': ['10.56.29.5']},
            "No 2 Fan find, check again": {'count': 3, 'ips': ['10.34.4.56', '10.34.4.55', '10.34.4.66']},
        }
        
        # Assertions for each error group
        for message, expected_data in expected_groups.items():
            self.assertIn(message, error_groups, f"Error message '{message}' not found in output")
            actual_data = error_groups[message]
            self.assertEqual(expected_data['count'], actual_data['count'], 
                         f"Expected {expected_data['count']} devices for '{message}', got {actual_data['count']}")
            
            # Check that all expected IPs are present (ignoring order)
            expected_ips_set = set(expected_data['ips'])
            actual_ips_set = set(actual_data['ips'])
            self.assertEqual(expected_ips_set, actual_ips_set, 
                         f"IP sets don't match for '{message}'")


if __name__ == "__main__":
    unittest.main()
