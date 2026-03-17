# Unified Wildlife Reporting API

Combined USSD and SMS wildlife incident reporting system in a single server.

## Features

**USSD Channel:**
- Menu-driven reporting for basic phones
- Emergency, sighting, and past incident flows
- Session management

**SMS Channel:**
- Free-form SMS parsing with hybrid NLP
- Rule-based extraction with HuggingFace LLM fallback
- Redirects to USSD for unclear messages
- Ranger alerts for high-priority incidents

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
AT_SHORTCODE=your_shortcode
USSD_CODE="*384*55#"
HUGGINGFACE_API_KEY=your_hf_key
DEBUG=true
PORT=8000
```

4. Run the application:
```bash
python main.py
```

## API Endpoints

### Health
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info and stats |
| `/health` | GET | Health check |

### USSD
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ussd` | POST | Main USSD callback |
| `/ussd/sessions` | GET | View active sessions |
| `/ussd/reports` | GET | View USSD reports |
| `/ussd/stats` | GET | USSD statistics |

### SMS
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sms/incoming` | POST | Incoming SMS webhook |
| `/sms/delivery` | POST | Delivery report webhook |
| `/sms/send` | POST | Send SMS manually |
| `/sms/reports` | GET | View SMS reports |
| `/sms/messages` | GET | Message history |
| `/sms/stats` | GET | SMS statistics |

## Integration

Configure Africa's Talking callbacks:
- USSD: `https://your-domain.com/ussd`
- SMS: `https://your-domain.com/sms/incoming`
- Delivery Reports: `https://your-domain.com/sms/delivery`
