# SNMP Proxy

This SNMP Proxy listens for SNMPv3 requests and either responds with locally handled OIDs or proxies the request to a target SNMP device.

## Requirements

- Python 3.6+ (3.11 preferred)
- `pysnmp` library
- `pyasn1` library

Does not work with python >= 3.12 due to incompatibility with `pysnmp` library.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/snmpproxy.git
    cd snmpproxy
    ```

2. Create a virtual environment and activate it:
    ```sh
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

## Running the SNMP Proxy

1. Ensure the `snmpproxy.py` script is executable:
    ```sh
    chmod +x snmpproxy.py
    ```

2. Run the SNMP proxy:
    ```sh
    python snmpproxy.py
    ```

The SNMP Proxy will start listening on UDP port 161 for SNMPv3 requests.

## Configuration

- SNMPv3 credentials and target device settings can be modified in the `snmpproxy.py` file.
- Local OID mappings are defined in the `LOCAL_OIDS` dictionary within the `snmpproxy.py` file.

## Logging

Logs are written to `snmp_proxy.log` in the same directory as the script.

## Stopping the SNMP Proxy

To stop the SNMP Proxy, press `Ctrl+C` in the terminal where the proxy is running.

## Test


```
sudo python snmpproxy.py
```

client (1)

```
sudo python snmpclient.py
```

client (2)

```
 snmpget -v3 -l authPriv -u proxyUser -a SHA -A "authPassword123" -x AES -X "privPassword123" localhost 1.3.6.1.4.1.6302.2.1.2.28.6.0
```
