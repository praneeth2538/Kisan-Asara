import os

from django.contrib import messages
from django.shortcuts import redirect, render

from kisan1.ai_services import forecast_crop_prices, generate_chatbot_reply, predict_crop_disease
from kisan1.views.shared import check_login


AI_CROPS = ['Rice', 'Wheat', 'Maize', 'Cotton', 'Groundnut', 'Turmeric']
AI_MARKETS = ['Hyderabad', 'Warangal', 'Nizamabad', 'Vijayawada', 'Rajahmundry']


def _require_ai_login(request):
    if not check_login(request):
        messages.warning(request, 'Please log in to access AI tools.')
        return redirect('login')
    return None


def ai_dashboard(request):
    redirect_response = _require_ai_login(request)
    if redirect_response:
        return redirect_response

    return render(request, 'kisan1/ai_dashboard.html', {'show_language_selector': False})


def crop_disease_detection(request):
    redirect_response = _require_ai_login(request)
    if redirect_response:
        return redirect_response

    result = None
    if request.method == 'POST':
        uploaded = request.FILES.get('image')
        result = predict_crop_disease(uploaded)
        if result.get('status') == 'error':
            messages.error(request, result.get('message', 'The crop image could not be processed.'))
        elif result.get('status') == 'unavailable':
            messages.warning(request, result.get('message', 'Disease detection is not configured.'))
        elif result.get('status') == 'success':
            messages.success(request, 'Image analyzed successfully.')
    return render(
        request,
        'kisan1/ai_disease_detection.html',
        {'show_language_selector': False, 'result': result, 'crops': AI_CROPS},
    )


def ai_chatbot(request):
    redirect_response = _require_ai_login(request)
    if redirect_response:
        return redirect_response

    conversation = request.session.get('ai_chat_history', [])
    answer = None
    if request.method == 'POST':
        question = (request.POST.get('question') or '').strip()
        if not question:
            messages.error(request, 'Please type a question before sending it.')
        else:
            answer = generate_chatbot_reply(question, conversation)
            conversation.append({'role': 'user', 'content': question})
            if answer.get('status') in {'success', 'unconfigured'}:
                conversation.append({'role': 'assistant', 'content': answer.get('answer', '')})
            else:
                conversation.append({'role': 'assistant', 'content': answer.get('answer', answer.get('message', ''))})
            request.session['ai_chat_history'] = conversation[:10]
            request.session.modified = True
    return render(
        request,
        'kisan1/ai_chatbot.html',
        {'show_language_selector': False, 'conversation': conversation, 'answer': answer},
    )


def crop_price_prediction(request):
    redirect_response = _require_ai_login(request)
    if redirect_response:
        return redirect_response

    result = None
    if request.method == 'POST':
        crop = (request.POST.get('crop') or '').strip()
        market = (request.POST.get('market') or '').strip()
        if not crop or not market:
            messages.error(request, 'Please select both a crop and a market.')
        else:
            result = forecast_crop_prices(crop, market)
            if result.get('status') == 'success':
                messages.success(request, 'Forecast generated using the supplied market history.')
            elif result.get('status') in {'unavailable', 'insufficient_data'}:
                messages.warning(request, result.get('message', 'Forecast data is unavailable right now.'))
            else:
                messages.error(request, result.get('message', 'The forecast could not be prepared.'))

    return render(
        request,
        'kisan1/ai_price_prediction.html',
        {
            'show_language_selector': False,
            'result': result,
            'crops': AI_CROPS,
            'markets': AI_MARKETS,
        },
    )
