# Ping_result

Continuous network and transport-security telemetry script that measures host reachability, HSTS presence, forward secrecy support, and MTBF-like service behavior, storing results in SQLite.

## Problem
When teams rely on ad-hoc checks, service degradation and security-control drift are detected late. Continuous probes with stored historical data provide stronger operational awareness.

## Security Context
- Tracks host/network availability through recurring ping checks.
- Validates HTTPS security properties (HSTS, forward secrecy signals).
- Stores structured telemetry for incident and trend analysis.

## Architecture/Flow
Flow summary:
1. Initialize local SQLite datastore.
2. Start concurrent threads for ping, HSTS, forward secrecy, and MTBF checks.
3. Persist results to dedicated DB tables.
4. Use `report.py` and DB outputs for review and follow-up action.

## Setup
```bash
git clone git@github.com:jaskaranhundal/Ping_result.git
cd Ping_result
python3 -m venv .venv
source .venv/bin/activate
pip install requests
python3 main.py
```

## Example Output
```text
Pinging github.com...
Result: Status=1, Time=22 ms
HSTS is enabled for https://github.com
Forward Secrecy is supported by google.com
Mean Time Between Failures (MTBF) for https://github.com: 0.00 seconds
```

## Limitations
- Uses static host/URL configuration in source by default.
- Local SQLite storage is single-node and not centralized.
- Long-running thread model requires manual lifecycle control.

## Roadmap
- Move all runtime config into environment variables or config file.
- Add graceful shutdown controls and signal handling.
- Add export path for SIEM-friendly JSON output.
- Add tests for parsing and DB write paths.
