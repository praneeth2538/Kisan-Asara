# Farmer Support Platform 🌾

A Django-based platform for farmers and rural service providers (labor, tractor, tools, lease, and pesticide/fertilizer shops) with OTP login, role dashboards, bookings, and location-aware workflows.

## Features
- OTP-based registration and login flow
- Multi-role service marketplace (farmer + providers)
- Booking lifecycle (request, accept/reject, track)
- Cart/checkout flow for pesticide shop orders
- Pincode-based district/mandal/village lookup APIs
- Admin analytics dashboard
- AI crop disease detection page with upload validation and graceful fallback states
- AI farming chatbot with backend provider configuration and safe error handling
- AI crop price prediction with historical data and a simple baseline forecast

## Tech Stack
- Python 3.12+
- Django 6
- SQLite (default) / PostgreSQL (production)
- Bootstrap + vanilla JavaScript

## Quick Start (Local)
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables (copy `.env.example` if available).
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Start development server:
   ```bash
   python manage.py runserver
   ```

## Required Environment Variables
- `DJANGO_SECRET_KEY` (required unless using local insecure override)
- `DJANGO_DEBUG` (`true`/`false`)
- `DJANGO_ALLOWED_HOSTS` (required when debug is false)

### Optional AI Configuration
- `AI_PROVIDER` / `AI_CHATBOT_PROVIDER` (`gemini`, `openai`, `unconfigured`)
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` for Google's free-tier Gemini API
- `AI_CHATBOT_API_URL` for a custom OpenAI-compatible endpoint
- `AI_CHATBOT_API_KEY` for alternative chatbot providers
- `AI_CHATBOT_MODEL` (default: `gemini-1.5-flash`)
- `AI_DISEASE_API_URL` for a vision-capable inference endpoint
- `AI_DISEASE_API_KEY` for the disease model provider
- `AI_DISEASE_MODEL` (default: `gemini-1.5-flash`)
- `AI_DISEASE_MODEL_PATH` for an optional local open-source model path
- `AI_MARKET_PRICE_DATA_PATH` for a CSV file with `date,crop,market,price`

If these values are not set, the AI pages stay available and show a clear configuration message rather than failing the entire app.

### Local convenience for checks/tests
For local checks without a production secret key:
```bash
DJANGO_ALLOW_INSECURE_DEV_KEY=true DJANGO_DEBUG=true DJANGO_ALLOWED_HOSTS=localhost python manage.py check
```

## OTP and Security Notes
- OTP requests and login attempts are rate limited.
- OTP expiration/attempt windows are configurable via settings environment variables.
- Production should run behind HTTPS with secure cookie settings enabled.

## Common Commands
```bash
# run tests
DJANGO_ALLOW_INSECURE_DEV_KEY=true DJANGO_DEBUG=true DJANGO_ALLOWED_HOSTS=localhost python manage.py test

# Django system checks
DJANGO_ALLOW_INSECURE_DEV_KEY=true DJANGO_DEBUG=true DJANGO_ALLOWED_HOSTS=localhost python manage.py check

# AI pages and routes
python manage.py runserver
```

## AI Setup Notes
- The free-first architecture prefers Google Gemini free-tier credentials (`GEMINI_API_KEY` / `GOOGLE_API_KEY`) for the chatbot and image-vision workflow when configured.
- Alternative providers are supported through `AI_CHATBOT_API_URL`, `AI_CHATBOT_API_KEY`, `AI_DISEASE_API_URL`, `AI_DISEASE_API_KEY`, or a local `AI_DISEASE_MODEL_PATH` if you operate a local open-source model.
- Disease detection and chatbot pages are ready to use without an API key, but they will show a configuration notice when credentials are missing.
- Crop price forecasting requires a CSV dataset with columns: `date,crop,market,price`. Set `AI_MARKET_PRICE_DATA_PATH` to the file. A simple trend-based forecast is used as the baseline model.
- The project does not auto-install image or ML-heavy dependencies beyond the existing Pillow stack; optional AI providers should be configured as needed.

## Production Checklist
- Set `DJANGO_ENV=production`
- Set `DJANGO_DEBUG=false`
- Set strong `DJANGO_SECRET_KEY`
- Configure non-SQLite DB settings (`DJANGO_DB_*`)
- Configure `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`
- Run `python manage.py collectstatic`
