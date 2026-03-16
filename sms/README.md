# Wildlife Conservation SMS API

SMS-based wildlife incident reporting system with NLP parsing for free-form messages.

## Features

- Free-form SMS parsing using hybrid NLP (rule-based + LLM fallback)
- Automatic report creation from natural language messages
- Clarification flow for low-confidence extractions
- Ranger alerts for high-priority incidents
- Delivery report tracking

## Setup

1. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
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
HUGGINGFACE_API_KEY=your_hf_key  # Optional, for LLM fallback
DEBUG=true
PORT=8001
```

4. Run the application:
```bash
python main.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sms/incoming` | POST | Incoming SMS webhook |
| `/sms/delivery` | POST | Delivery report webhook |
| `/sms/send` | POST | Send SMS manually |
| `/sms/reports` | GET | View all SMS reports |
| `/sms/messages` | GET | View message history |
| `/sms/delivery/stats` | GET | Delivery statistics |
| `/health` | GET | Health check |

## How It Works

1. User sends free-form SMS: `"Saw 3 elephants near Mara River today"`
2. NLP extracts: species=elephant, count=3, location=Mara River
3. If confidence >= 80%: Report created automatically
4. If confidence 50-80%: Confirmation SMS sent to user
5. If confidence < 50%: Clarification questions sent
6. High-priority incidents trigger ranger alerts

## Integration

Configure Africa's Talking SMS callback URL to:
```
https://your-domain.com/sms/incoming
```

Configure delivery reports callback to:
```
https://your-domain.com/sms/delivery
```
