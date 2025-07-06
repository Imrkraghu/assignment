import os
import json
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

# Constants
VALID_USERNAME = "admin"
VALID_PASSWORD = "1234"

# File path setup
DATA_DIR = os.path.join(settings.BASE_DIR, "location_data")
os.makedirs(DATA_DIR, exist_ok=True)

# Load or initialize JSON store
JSON_FILE_PATH = os.path.join(DATA_DIR, "locations.json")
if os.path.exists(JSON_FILE_PATH):
    with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
        try:
            json_store = json.load(f)
        except Exception:
            json_store = []
else:
    json_store = []

# Views
def adminpage(request):
    return render(request, "locations/admin.html")

def adddata_page(request):
    return render(request, "locations/adddata.html")

def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            return redirect("adddata_page")
        return render(request, "locations/admin.html", {"error": "Invalid credentials"})
    return redirect("adminpage")

@csrf_exempt
def save_location(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        data = json.loads(request.body)

        loc_id = len(json_store) + 1
        location = {
            "id": loc_id,
            "name": data["name"],
            "category": data["category"],
            "latitude": data["latitude"],
            "longitude": data["longitude"],
        }

        json_store.append(location)

        with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(json_store, f, indent=2)

        return JsonResponse({"success": True, "location": location}, status=201)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

def download_geojson_file(request):
    if not os.path.exists(JSON_FILE_PATH):
        raise Http404("GeoJSON file not found")

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"locations_{timestamp}.json"
    file_path = os.path.join(DATA_DIR, filename)

    # Copy current data to new file
    with open(JSON_FILE_PATH, "r", encoding="utf-8") as src, open(file_path, "w", encoding="utf-8") as dst:
        dst.write(src.read())

    response = FileResponse(open(file_path, "rb"), content_type="application/json")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response