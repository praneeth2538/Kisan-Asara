from kisan1.location_service import load_telangana_pincodes

def run():
    created_count = load_telangana_pincodes()
    print(f"Loaded {created_count} new pincode-to-village mappings")
    return created_count