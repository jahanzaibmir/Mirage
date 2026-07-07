# Mirage Honeypot

Mirage is a  Python based honeypot exposing HTTP and TCP listeners to lure attackers, capturing their connection attempts, payloads, and behavior for security analysis.


## Setup

```bash
git clone https://github.com/jahanzaibmir/Mirage.git

cd Mirage
```
## Install the Requirments

```bash
pip install requirements.txt
```


## Run

```bash
python run.py
```

After this change the project will prefer running a prototype storefront web app at http://localhost:5000.

Storefront notes:
- Admin user/Activity console creds: `admin@gmail.com` / `adminpass`

- Public honeypot: http://127.0.0.1:5000
- Hidden admin console: http://127.0.0.1:5001/hidden-ops/login

## Structure

- mirage/config.py: runtime settings
- mirage/logger.py: event logging
- mirage/server.py: HTTP and TCP listeners
- tests/test_honeypot.py: smoke tests


## Author

Mirage is under active development and continues to improve day by day.

Developed by **Jahanzaib Ashraf Mir** - Cybersecurity Researcher
