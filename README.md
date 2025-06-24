# Subnet Scanner

This project provides tools for scanning subnet IP ranges, detecting responsive devices, and retrieving system logs from them. It includes specialized support for Z15 Fan devices.

## Features

- Scan IP subnets to find responsive devices
- Retrieve logs from responsive devices using HTTP requests
- Concurrent scanning for improved performance
- Generate reports in JSON and HTML formats
- Custom configuration options

## Components

1. **subnet_scanner.py** - Core scanning tool that can scan IP ranges and fetch logs
2. **z15_fan_broker.py** - Extended tool with specialized functionality for Z15 Fan devices
3. **custom_config.json** - Configuration file for subnet settings and credentials

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Madaocv/subnetscanner.git
   cd subnetscanner
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   # Create a virtual environment with Python 3.9
   python3.9 -m venv .venv
   
   # Activate the virtual environment
   source .venv/bin/activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Z15 Fan Broker

For scanning with the Z15 Fan Broker tool, which provides additional features:

```bash
# Scan using default or specified config file
python z15_fan_broker.py --scan --config custom_config.json

# Generate reports based on scan results
python z15_fan_broker.py --scan --report --config custom_config.json

```

### Basic Subnet Scanning

To run a basic subnet scan using default settings:

```bash
python subnet_scanner.py
```

This will scan the default subnet (10.31.212.0/24) and report any responsive devices.

### Configuration

You can customize the behavior by modifying `custom_config.json`:

```json
{
    "username": "root",
    "password": "root",
    "timeout": 15,
    "subnets": [
        "10.31.212.0/24",
        "10.31.217.0/24"
    ],
    "log_endpoint": "/cgi-bin/get_kernel_log.cgi"
}
```

- **username/password**: Credentials for HTTP Digest Authentication
- **timeout**: HTTP request timeout in seconds
- **subnets**: List of subnets to scan in CIDR notation
- **log_endpoint**: API endpoint for fetching logs from devices

## Output Examples

The tools will generate:

1. Terminal output showing responsive IPs and their log entries
2. JSON file with detailed scan results
3. HTML report for easier visualization (with Z15 Fan Broker)

### Script Execution

The following screenshot shows the script execution and terminal output:

![Script Execution](img/script.png)

### Report Outputs

#### JSON Report
![JSON Report](img/reportjson.png)

#### HTML Report
![HTML Report](img/reporthtml.png)

## Requirements

- Python 3.9+
- Required packages (see requirements.txt):
  - requests
  - ipaddress
