# Mirage Honeypot

Mirage is a lightweight Python honeypot that exposes a simple HTTP endpoint and a TCP listener to capture basic probing activity.

## Run

```bash
python run.py
```

## Structure

- mirage/config.py: runtime settings
- mirage/logger.py: event logging
- mirage/server.py: HTTP and TCP listeners
- tests/test_honeypot.py: smoke tests
