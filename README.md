# Wildlife Incident Reporting System

A dual-channel wildlife incident reporting system using USSD and SMS, designed for areas with limited internet connectivity.

## Overview

This project provides two standalone applications for wildlife conservation reporting:

| App | Port | Description |
|-----|------|-------------|
| [USSD](./ussd/) | 8000 | Menu-driven reporting via USSD codes |
| [SMS](./sms/) | 8001 | Free-form SMS with NLP parsing |

Both apps integrate with Africa's Talking API and store reports in PostgreSQL.

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL
- Africa's Talking account

### USSD App
```bash
cd ussd
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```

### SMS App
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
├── ussd/                 # USSD application
│   ├── api/              # Routes and endpoints
│   ├── database/         # Models and repository
│   ├── services/         # Business logic
│   └── data/             # Menu options
├── sms/                  # SMS application
│   ├── api/              # Routes and schemas
│   ├── database/         # Models and repository
│   ├── services/         # SMS, notifications, LLM
│   ├── nlp/              # Text extraction
│   └── data/keywords/    # Species, locations, etc.
└── README.md
```

## Configuration

Each app uses environment variables via `.env` file. See individual app READMEs for details.

## License

AGPL-3.0