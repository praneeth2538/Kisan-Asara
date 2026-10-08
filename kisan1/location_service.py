import logging
import re

from django.core.cache import cache
from django.db import transaction

from kisan1.models import PincodeMapping
from kisan1.pincode_data import PINCODE_DATA, is_hidden_pincode

logger = logging.getLogger(__name__)
PINCODE_PATTERN = re.compile(r'^[1-9][0-9]{5}$')


def normalize_pincode(pincode):
    """Return a normalized six-digit Indian pincode, or None for invalid input."""
    normalized = str(pincode or '').strip()
    return normalized if PINCODE_PATTERN.fullmatch(normalized) else None


def _pincode_locations(data):
    return data.get('locations') or [data]


def load_telangana_pincodes(force=False):
    """Load bundled Telangana pincode/mandal/village data into DB."""
    created_count = 0
    skipped_pincodes = []
    with transaction.atomic():
        if force:
            PincodeMapping.objects.all().delete()

        for pincode, data in PINCODE_DATA.items():
            if is_hidden_pincode(pincode):
                skipped_pincodes.append(pincode)
                continue
            normalized = normalize_pincode(pincode)
            if normalized is None:
                raise ValueError(f'Invalid pincode in bundled data: {pincode!r}')
            for location in _pincode_locations(data):
                district = location['district'].strip()
                mandal = location['mandal'].strip()
                for village in location.get('villages', []):
                    village = village.strip()
                    if not village:
                        continue
                    _, created = PincodeMapping.objects.get_or_create(
                        pincode=normalized,
                        district=district,
                        mandal=mandal,
                        village=village,
                    )
                    if created:
                        created_count += 1

    if skipped_pincodes:
        logger.info('Skipped explicitly restricted pincodes: %s', ', '.join(skipped_pincodes))
    return created_count


def get_cached_location_details(pincode):
    normalized = normalize_pincode(pincode)
    if normalized is None or is_hidden_pincode(normalized):
        return None

    bundled_location = PINCODE_DATA.get(normalized)
    if bundled_location:
        village_locations = {}
        for location in _pincode_locations(bundled_location):
            district = location['district'].strip()
            mandal = location['mandal'].strip()
            for village in location.get('villages', []):
                village = village.strip()
                if village:
                    village_locations.setdefault(village, {
                        'district': district,
                        'mandal': mandal,
                    })
        first_location = _pincode_locations(bundled_location)[0]
        return {
            'state': 'Telangana',
            'district': first_location['district'].strip(),
            'mandal': first_location['mandal'].strip(),
            'villages': list(village_locations),
            'village_locations': village_locations,
        }

    cache_key = f'location:pincode:{normalized}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    locations = PincodeMapping.objects.filter(pincode=normalized).order_by('id')
    if not locations.exists():
        logger.info('No location mapping found for pincode=%s', normalized)
        return None

    first_record = locations.first()
    village_locations = {}
    for location in locations:
        village = location.village.strip()
        if village:
            village_locations.setdefault(village, {
                'district': location.district,
                'mandal': location.mandal,
            })
    data = {
        'state': first_record.state,
        'district': first_record.district,
        'mandal': first_record.mandal,
        'villages': list(village_locations),
        'village_locations': village_locations,
    }
    cache.set(cache_key, data, 600)
    return data
