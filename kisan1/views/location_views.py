from django.http import JsonResponse
from kisan1.location_service import get_cached_location_details, normalize_pincode
from kisan1.pincode_data import is_hidden_pincode

def get_villages_by_pincode(request):
    pincode = normalize_pincode(request.GET.get('pincode'))
    if pincode is None or is_hidden_pincode(pincode):
        return JsonResponse({'villages': []})

    location = get_cached_location_details(pincode)
    return JsonResponse({'villages': location['villages'] if location else []})


def get_location_api(request):
    raw_pincode = request.GET.get('pincode', '')
    pincode = normalize_pincode(raw_pincode)
    if pincode is None:
        return JsonResponse(
            {'success': False, 'error': 'Invalid pincode', 'villages': []},
            status=400,
        )

    if is_hidden_pincode(pincode):
        return JsonResponse({'success': False, 'error': 'Restricted Pincode'})

    location = get_cached_location_details(pincode)
    if location is None:
        return JsonResponse(
            {'success': False, 'error': 'Pincode not found', 'villages': []},
            status=404,
        )

    return JsonResponse({
        'success': True,
        'state': location['state'],
        'district': location['district'],
        'mandal': location['mandal'],
        'villages': location['villages'],
        'village_locations': location['village_locations'],
    })