# Mirage Honeypot

Mirage is a lightweight Python honeypot that exposes a simple HTTP endpoint and a TCP listener to capture basic probing activity.

## Run

```bash
python run.py
```

After this change the project will prefer running a prototype storefront web app at http://localhost:5000.

Storefront notes:
- Admin user: `admin@example.com` / `adminpass`
- Database file: `storefront/storefront.db`

- Public honeypot: http://127.0.0.1:5000
- Hidden admin console: http://127.0.0.1:5001/hidden-ops/login

## Structure

- mirage/config.py: runtime settings
- mirage/logger.py: event logging
- mirage/server.py: HTTP and TCP listeners
- tests/test_honeypot.py: smoke tests
