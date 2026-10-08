import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmer_project.settings')
django.setup()




from kisan1.location_service import load_telangana_pincodes

print("Starting to load pincodes...")
loaded_count = load_telangana_pincodes()
print(f"Loaded {loaded_count} new pincode-to-village mappings.")
from django.contrib.auth.models import User

def run():
    if not User.objects.filter(username="admin").exists():
        user = User.objects.create_user(
            username="admin",
            email="test@gmail.com",
            password="123456"
        )
        print("User created")
    else:
        user = User.objects.get(username="admin")
        print("User already exists")

    # ALWAYS update permissions
    user.is_staff = True
    user.is_superuser = True
    user.set_password("123456")  # ensure password works
    user.save()

    print("Admin access granted")