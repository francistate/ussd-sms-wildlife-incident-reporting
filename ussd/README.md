# Wildlife Conservation USSD API

USSD-based wildlife incident reporting system for areas with limited internet connectivity.

## Features

- Emergency incident reporting (poaching, injured animals, human-wildlife conflict)
- Wildlife sighting logging
- Past incident reporting
- Menu-driven interface accessible via basic phones

## Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`:
```
DATABASE_URL=postgresql://user:pass@localhost/wildlife
AT_USERNAME=your_africastalking_username
AT_API_KEY=your_africastalking_api_key
DEBUG=true
PORT=8000
```

4. Run the application:
```bash
python main.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ussd` | POST | Main USSD callback handler |
| `/` | GET | Health check with stats |
| `/health` | GET | Simple health check |
| `/sessions` | GET | View active sessions |
| `/reports` | GET | View all reports |
| `/reports/pending` | GET | View pending high-priority reports |

## USSD Flow

```
Main Menu
├── 1. Report Emergency NOW
│   ├── Select incident type
│   ├── Select species
│   ├── Select location
│   └── Confirm submission
├── 2. Wildlife Sighting
│   ├── Select species
│   ├── Enter count
│   ├── Select location
│   └── Confirm submission
├── 3. Report Past Incident
│   └── Similar to emergency flow
└── 4. Help
```

## Integration

Configure your Africa's Talking USSD callback URL to point to:
```
https://your-domain.com/ussd
```
