# Wildlife Incident Reporting System

A dual-channel wildlife incident reporting system using USSD and SMS, designed for areas with limited internet connectivity.

## Overview

This project provides wildlife conservation reporting via USSD and SMS channels:

| App | Port | Description |
|-----|------|-------------|
| [Unified](./unified/) | 8000 | Both USSD + SMS in single server |
| [USSD](./ussd/) | 8000 | Standalone USSD only |
| [SMS](./sms/) | 8001 | Standalone SMS only |

All apps integrate with Africa's Talking API and store reports in PostgreSQL.

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL
- Africa's Talking account

### Unified App (Recommended)
```bash
cd unified
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```

### Standalone USSD
```bash
cd ussd
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```

### Standalone SMS
```bash
cd sms
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```

## Architecture

```
ussd-sms-wildlife-incident-reporting/
├── unified/              # Combined USSD + SMS
│   ├── api/              # All routes
│   ├── database/         # Shared models
│   ├── sms_services/     # SMS business logic
│   ├── ussd_services/    # USSD business logic
│   ├── nlp/              # Text extraction
│   └── data/             # Keywords and menu options
├── ussd/                 # Standalone USSD
├── sms/                  # Standalone SMS
└── README.md
```

## Configuration

Each app uses environment variables via `.env` file. See individual app READMEs for details.

## License

AGPL-3.0