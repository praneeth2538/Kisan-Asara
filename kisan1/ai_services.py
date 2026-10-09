import time
import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {'.jpg', '.jpeg', '.png', '.webp'}


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_ai_provider_settings() -> Dict[str, Any]:
    configured_provider = (os.getenv('AI_PROVIDER') or os.getenv('AI_CHATBOT_PROVIDER') or 'unconfigured').strip().lower()
    gemini_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or os.getenv('AI_CHATBOT_API_KEY') or os.getenv('AI_DISEASE_API_KEY') or ''
    chatbot_key = os.getenv('AI_CHATBOT_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or os.getenv('OPENAI_API_KEY') or ''
    disease_key = os.getenv('AI_DISEASE_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or os.getenv('OPENAI_API_KEY') or ''
    provider = configured_provider if configured_provider not in {'', 'unconfigured'} else ('gemini' if gemini_key else 'unconfigured')
    return {
        'provider': provider,
        'chatbot_api_key': chatbot_key,
        'chatbot_api_url': os.getenv('AI_CHATBOT_API_URL') or '',
        'disease_api_key': disease_key,
        'disease_api_url': os.getenv('AI_DISEASE_API_URL') or '',
        'market_data_path': os.getenv('AI_MARKET_PRICE_DATA_PATH') or '',
        'chatbot_model': os.getenv('AI_CHATBOT_MODEL', 'gemini-1.5-flash'),
        'disease_model': os.getenv('AI_DISEASE_MODEL', 'gemini-1.5-flash'),
        'local_model_path': os.getenv('AI_DISEASE_MODEL_PATH') or '',
    }


def validate_image_upload(uploaded_file) -> Optional[Dict[str, str]]:
    if uploaded_file is None:
        return {'status': 'error', 'message': 'Please select an image before submitting.'}

    filename = getattr(uploaded_file, 'name', '') or ''
    if not filename:
        return {'status': 'error', 'message': 'Uploaded file is missing a valid filename.'}

    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_IMAGE_TYPES:
        return {
            'status': 'error',
            'message': 'Unsupported file type. Please upload a JPG, JPEG, PNG, or WEBP image.',
        }

    if getattr(uploaded_file, 'size', 0) and uploaded_file.size > MAX_UPLOAD_SIZE:
        return {
            'status': 'error',
            'message': 'Uploaded image is too large. Please upload an image smaller than 10 MB.',
        }

    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        return {'status': 'error', 'message': 'The uploaded file is not a valid image. Please upload a real crop photo.'}
    finally:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass

    return None


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_market_text(value: Any) -> str:
    return str(value or '').strip()


def _parse_market_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _extract_result_payload(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        label = data.get('label') or data.get('crop') or data.get('disease') or data.get('name') or 'Unknown'
        confidence = _safe_float(data.get('confidence'))
        explanation = data.get('explanation') or data.get('summary') or data.get('message') or ''
        return {'label': str(label), 'confidence': confidence, 'explanation': str(explanation)}

    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            return _extract_result_payload(data[0])
    return {'label': 'Unknown', 'confidence': None, 'explanation': ''}


def predict_crop_disease(uploaded_file) -> Dict[str, Any]:
    validation_error = validate_image_upload(uploaded_file)
    if validation_error:
        return {
            'status': 'error',
            'provider': 'validation',
            'message': validation_error['message'],
        }

    settings_data = get_ai_provider_settings()
    if not settings_data['disease_api_key'] and not settings_data['disease_api_url'] and not settings_data['local_model_path']:
        return {
            'status': 'unavailable',
            'provider': 'unconfigured',
            'label': 'Model not configured',
            'confidence': None,
            'message': 'Disease detection is not configured yet. Add GEMINI_API_KEY, GOOGLE_API_KEY, or AI_DISEASE_API_KEY to enable inference, or set AI_DISEASE_MODEL_PATH for a local open-source model.',
            'explanation': 'This model is disabled until a valid provider or local model is configured. Until then, we cannot safely provide a crop or disease diagnosis from the uploaded photo.',
            'next_steps': [
                'Upload a clear, well-lit image of a cotton, rice, wheat, or vegetable leaf.',
                'Use a healthy leaf and a close-up photo for better analysis.',
                'Consult a local agricultural officer or agronomist if you suspect a serious disease outbreak.',
            ],
        }

    endpoint = settings_data['disease_api_url']
    if settings_data['provider'] in {'gemini', 'google'} and not endpoint:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{settings_data['disease_model']}:generateContent?key={settings_data['disease_api_key']}"
    elif not endpoint:
        endpoint = 'https://api.openai.com/v1/chat/completions'

    headers = {'Content-Type': 'application/json'}
    payload = {}

    try:
        uploaded_file.seek(0)
        encoded = uploaded_file.read()
        file_b64 = __import__('base64').b64encode(encoded).decode('utf-8')
        if settings_data['provider'] in {'gemini', 'google'}:
            payload = {
                'contents': [{
                    'parts': [
                        {'text': 'Return JSON only with keys: label, confidence, explanation, next_steps. Do not claim a definitive diagnosis. Describe likely disease or stress based on this crop image. Use Indian agricultural context and keep guidance suitable for farmers.'},
                        {'inlineData': {'mimeType': uploaded_file.content_type or 'image/jpeg', 'data': file_b64}},
                    ]
                }],
                'generationConfig': {'temperature': 0.2, 'responseMimeType': 'application/json'}
            }
            response = requests.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            candidates = data.get('candidates') or []
            if not candidates:
                raise ValueError('No candidates returned by Gemini disease model.')
            text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            parsed = json.loads(text)
            result = _extract_result_payload(parsed)
            return {
                'status': 'success',
                'provider': settings_data['provider'],
                'label': result.get('label') or 'Unable to classify',
                'confidence': result.get('confidence'),
                'explanation': result.get('explanation') or 'The model could not confidently identify the disease. Please seek local agronomy support.',
                'message': 'The image was analyzed by the configured free-tier Gemini model.',
                'next_steps': parsed.get('next_steps', []) if isinstance(parsed, dict) else [],
            }

        payload = {
            'model': settings_data['disease_model'],
            'messages': [
                {
                    'role': 'system',
                    'content': 'Reply only with a JSON object containing keys: label, confidence, explanation, next_steps. Do not claim a definitive diagnosis. Use Indian agriculture context and keep advice grounded in crop health management.',
                },
                {
                    'role': 'user',
                    'content': 'Analyze this crop leaf image.',
                },
            ],
            'temperature': 0.2,
        }
        if settings_data['disease_api_key']:
            headers['Authorization'] = f"Bearer {settings_data['disease_api_key']}"
        image_data_url = f'data:{uploaded_file.content_type or "image/jpeg"};base64,{file_b64}'
        payload['messages'][1]['content'] = [
            {'type': 'text', 'text': 'Analyze this crop leaf image for likely disease or stress. Return JSON only with keys: label, confidence, explanation, next_steps.'},
            {'type': 'image_url', 'image_url': {'url': image_data_url}},
        ]

        response = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=25)
        response.raise_for_status()
        data = response.json()
        choices = data.get('choices') or []
        if not choices:
            raise ValueError('No response choices returned by disease model.')
        content = choices[0].get('message', {}).get('content', '')
        parsed = json.loads(content) if isinstance(content, str) else content
        result = _extract_result_payload(parsed)
        return {
            'status': 'success',
            'provider': settings_data['provider'],
            'label': result.get('label') or 'Unable to classify',
            'confidence': result.get('confidence'),
            'explanation': result.get('explanation') or 'The model could not confidently identify the disease. Please seek local agronomy support.',
            'message': 'The image was analyzed by the configured model.',
            'next_steps': parsed.get('next_steps', []) if isinstance(parsed, dict) else [],
        }
    except Exception as exc:
        logger.exception('Crop disease inference failed: %s', exc)
        return {
            'status': 'error',
            'provider': settings_data['provider'],
            'label': 'Unable to classify',
            'confidence': None,
            'message': 'The AI model could not process the image right now. Please try again with a clearer photo or contact an agricultural expert.',
            'explanation': 'The prediction was not completed because the provider was unavailable, timed out, or rejected the image.',
            'next_steps': [
                'Increase the image resolution and crop close-up.',
                'Use even daylight and avoid blurry photos.',
                'Check the crop for leaf spots, yellowing, or wilting and consult a local agronomist if symptoms are severe.',
            ],
        }


def generate_chatbot_reply(question: str, conversation: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    if not question or not question.strip():
        return {'status': 'error', 'message': 'Please enter a question before sending it.'}

    settings_data = get_ai_provider_settings()
    if not settings_data['chatbot_api_key'] and not settings_data['chatbot_api_url']:
        return {
            'status': 'unconfigured',
            'provider': 'unconfigured',
            'message': 'The AI chatbot is not configured yet. Add GEMINI_API_KEY, GOOGLE_API_KEY, or AI_CHATBOT_API_KEY in your environment to enable live answers.',
            'answer': 'The AI chatbot is not configured yet because no provider credentials are available. Please add a valid API key or local model endpoint and try again.',
        }

    endpoint = settings_data['chatbot_api_url']
    if settings_data['provider'] in {'gemini', 'google'} and not endpoint:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{settings_data['chatbot_model']}:generateContent?key={settings_data['chatbot_api_key']}"
    elif not endpoint:
        endpoint = 'https://api.openai.com/v1/chat/completions'

    history = conversation or []
    messages = [
        {
            'role': 'system',
            'content': 'You are a calm, practical agricultural assistant for Indian farmers. Answer in plain English or simple Hindi-style wording. Focus on crop care, irrigation, soil health, fertilizer safety, pest prevention, and Kisan Asara platform usage. Encourage consultation with agricultural experts for urgent disease outbreaks or high-risk decisions. Never claim guaranteed yields or prices. Do not invent crop facts. If uncertain, say so clearly.',
        }
    ]
    for entry in history:
        if isinstance(entry, dict):
            role = 'user' if entry.get('role') == 'user' else 'assistant'
            content = entry.get('content') or ''
            if content:
                messages.append({'role': role, 'content': content})
    messages.append({'role': 'user', 'content': question.strip()})

    headers = {'Content-Type': 'application/json'}
    if settings_data['provider'] in {'gemini', 'google'}:
        payload = {
            'contents': [{
                'parts': [{
                    'text': 'Answer as a practical agricultural advisor for Indian farmers. If uncertain, explicitly say so. Do not invent yields, prices, or disease diagnoses. Provide safe guidance for fertilizer and pesticide use.'
                }]
            }],
            'generationConfig': {'temperature': 0.4, 'responseMimeType': 'text/plain'}
        }
        payload['contents'].append({'parts': [{'text': question.strip()}]})
        try:
            response = None
            for attempt in range(2):
                response = requests.post(
                    endpoint,
                    json=payload,
                    timeout=(5, 15),
                )
                if response.status_code not in (429, 500, 502, 503, 504):
                    break
                if attempt < 1:
                    time.sleep(1)

            response.raise_for_status()
            payload_data = response.json()
            candidates = payload_data.get('candidates') or []
            if not candidates:
                raise ValueError('No candidates returned by Gemini chatbot.')
            answer = ''
            for part in candidates[0].get('content', {}).get('parts', []):
                answer += (part.get('text') or '')
            return {'status': 'success', 'provider': settings_data['provider'], 'answer': answer.strip() or 'The AI provider responded without text; please try again.'}
        except Exception as exc:
            logger.error('AI chatbot request failed: %s', type(exc).__name__)
            return {
                'status': 'error',
                'provider': settings_data['provider'],
                'message': 'The AI chatbot could not answer that question right now. Please rephrase the question or retry in a moment.',
                'answer': 'The AI provider is temporarily unavailable. Please retry after a short pause or consult a local agronomist for urgent farming questions.',
            }

    if settings_data['chatbot_api_key']:
        headers['Authorization'] = f"Bearer {settings_data['chatbot_api_key']}"

    payload = {'model': settings_data['chatbot_model'], 'messages': messages, 'temperature': 0.4}

    try:
        response = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=25)
        response.raise_for_status()
        payload_data = response.json()
        if not isinstance(payload_data, dict):
            raise ValueError('Unexpected response format from AI chatbot.')
        choices = payload_data.get('choices') or []
        if choices:
            answer = str((choices[0].get('message', {}) or {}).get('content') or 'The AI provider responded without text. Please try again.').strip()
        else:
            answer = str(payload_data.get('reply') or 'The AI provider responded without text. Please try again.').strip()
        return {'status': 'success', 'provider': settings_data['provider'], 'answer': answer}
    except Exception as exc:
        logger.error('AI chatbot request failed: %s', type(exc).__name__)
        return {
            'status': 'error',
            'provider': settings_data['provider'],
            'message': 'The AI chatbot could not answer that question right now. Please rephrase the question or retry in a moment.',
            'answer': 'The AI provider is temporarily unavailable. Please retry after a short pause or consult a local agronomist for urgent farming questions.',
        }


def _read_market_csv(path: str) -> List[Dict[str, Any]]:
    if not path:
        return []
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows = []
    with file_path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row:
                continue
            rows.append({
                'date': row.get('date') or row.get('Date') or row.get('market_date') or '',
                'crop': (row.get('crop') or row.get('Crop') or '').strip(),
                'market': (row.get('market') or row.get('Market') or '').strip(),
                'price': _safe_float(row.get('price') or row.get('Price')) or 0.0,
            })
    return rows


def forecast_crop_prices(crop: str, market: str, forecast_days: int = 30) -> Dict[str, Any]:
    crop_name = (crop or '').strip()
    market_name = (market or '').strip()
    if not crop_name or not market_name:
        return {'status': 'error', 'message': 'Please select a crop and market before forecasting.'}

    csv_path = os.getenv('AI_MARKET_PRICE_DATA_PATH') or str(_project_root() / 'market_prices.csv')
    rows = _read_market_csv(csv_path)
    if not rows:
        return {
            'status': 'unavailable',
            'message': 'No historical market-price dataset is configured. Set AI_MARKET_PRICE_DATA_PATH to a CSV file with columns date,crop,market,price to enable forecasts.',
            'crop': crop_name,
            'market': market_name,
            'historical_prices': [],
            'forecast': [],
        }

    filtered = [
        row for row in rows
        if row.get('crop', '').lower() == crop_name.lower() and row.get('market', '').lower() == market_name.lower() and row.get('price', 0)
    ]
    if not filtered:
        return {
            'status': 'unavailable',
            'message': f'No valid historical price data was found for {crop_name} in {market_name}. Use a different market or add market data to the configured CSV file.',
            'crop': crop_name,
            'market': market_name,
            'historical_prices': [],
            'forecast': [],
        }

    filtered.sort(key=lambda item: item.get('date') or '1970-01-01')
    history = []
    for row in filtered:
        value = _safe_float(row.get('price'))
        if value is not None:
            history.append({'date': row.get('date'), 'price': value})

    if len(history) < 3:
        return {
            'status': 'insufficient_data',
            'message': 'The available history is too short for a reliable forecast. At least 3 valid market price points are required.',
            'crop': crop_name,
            'market': market_name,
            'historical_prices': history,
            'forecast': [],
        }

    days = max(1, int(forecast_days))
    prices = [entry['price'] for entry in history]
    mean_x = (len(prices) - 1) / 2.0
    mean_y = sum(prices) / max(1, len(prices))
    numerator = sum((idx - mean_x) * (value - mean_y) for idx, value in enumerate(prices))
    denominator = sum((idx - mean_x) ** 2 for idx in range(len(prices)))
    slope = numerator / denominator if denominator else 0.0
    last_price = prices[-1]
    trend = max(-last_price * 0.25, min(last_price * 0.25, slope * 7.0))
    forecast = []
    for step in range(1, days + 1):
        forecast.append({'date': f'Forecast {step}', 'price': round(max(0.0, last_price + trend * step), 2)})

    last_updated = history[-1].get('date') or datetime.utcnow().date().isoformat()
    return {
        'status': 'success',
        'crop': crop_name,
        'market': market_name,
        'last_updated': last_updated,
        'historical_prices': history,
        'forecast': forecast,
        'forecast_horizon_days': days,
        'uncertainty': 'This is a simple trend-based baseline using the last available market data and should be treated as a rough estimate, not a guaranteed price outcome.',
        'unit': 'INR per unit',
    }
