import os
import json
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.drawing.image import Image as ExcelImage
from PIL import Image as PILImage
from io import BytesIO
import requests

# Constants
VALID_USERNAME = "admin"
VALID_PASSWORD = "1234"
LOCATIONIQ_TOKEN = "pk.fefa518e69c3babaf9c877ef8fb2c26b"

# File path setup
DATA_DIR = os.path.join(settings.BASE_DIR, "Media/location_data")
SCREENSHOT_DIR = os.path.join(DATA_DIR, "screenshots")
GEOJSON_FOLDER_PATH = os.path.join(DATA_DIR, "geojson")
GEOJSON_FILE_PATH = os.path.join(GEOJSON_FOLDER_PATH, "locations.geojson")
Excel_FOLDER_PATH = os.path.join(DATA_DIR, "Excel")


os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(GEOJSON_FOLDER_PATH, exist_ok=True)
os.makedirs(Excel_FOLDER_PATH, exist_ok=True)

cleanup_done = False  # Global flag to ensure cleanup runs only once

# Cleanup after every session
def clear_previous_session_files():
    for filename in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"❌ Failed to delete {file_path}: {e}")

    if os.path.exists(SCREENSHOT_DIR):
        for filename in os.listdir(SCREENSHOT_DIR):
            file_path = os.path.join(SCREENSHOT_DIR, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"❌ Failed to delete screenshot {file_path}: {e}")

# Views
def adminpage(request):
    return render(request, "locations/admin.html")

def adddata_page(request):
    global cleanup_done
    if not cleanup_done:
        clear_previous_session_files()
        cleanup_done = True
    return render(request, "locations/adddata.html")

def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            return redirect("adddata_page")
        return render(request, "locations/admin.html", {"error": "Invalid credentials"})
    return redirect("adminpage")

# Load or initialize GeoJSON store
if os.path.exists(GEOJSON_FILE_PATH):
    with open(GEOJSON_FILE_PATH, "r", encoding="utf-8") as f:
        try:
            geojson_store = json.load(f)
        except Exception:
            geojson_store = {"type": "FeatureCollection", "features": []}
else:
    geojson_store = {"type": "FeatureCollection", "features": []}

def save_location(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        name = request.POST.get("name")
        category = request.POST.get("category")
        latitude = float(request.POST.get("latitude"))
        longitude = float(request.POST.get("longitude"))

        if not all([name, category, latitude, longitude]):
            return JsonResponse({"error": "Missing required fields"}, status=400)

        # ✅ Generate static map URL from LocationIQ
        static_map_url = (
            f"https://maps.locationiq.com/v3/staticmap"
            f"?key={LOCATIONIQ_TOKEN}"
            f"&center={latitude},{longitude}"
            f"&zoom=13&size=600x400&markers=icon:large-red-cutout|{latitude},{longitude}"
        )

        # ✅ Fetch the image
        response = requests.get(static_map_url)
        if response.status_code != 200:
            return JsonResponse({"error": "Failed to fetch map image"}, status=500)

        # ✅ Save the image
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        screenshot_filename = f"{safe_name}.png"
        screenshot_path = os.path.join(SCREENSHOT_DIR, screenshot_filename)
        with open(screenshot_path, "wb") as f:
            f.write(response.content)

        # ✅ Add to GeoJSON
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [longitude, latitude],
            },
            "properties": {
                "id": len(geojson_store["features"]) + 1,
                "name": name,
                "category": category,
                "screenshot": screenshot_filename
            }
        }

        geojson_store["features"].append(feature)

        with open(GEOJSON_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(geojson_store, f, indent=2)

        return JsonResponse({"success": True, "feature": feature}, status=201)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

def download_geojson_file(request):
    if not os.path.exists(GEOJSON_FILE_PATH):
        raise Http404("GeoJSON file not found")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"locations_{timestamp}.json"
    temp_path = os.path.join(GEOJSON_FOLDER_PATH, filename)

    with open(GEOJSON_FILE_PATH, "r", encoding="utf-8") as src, open(temp_path, "w", encoding="utf-8") as dst:
        dst.write(src.read())

    response = FileResponse(open(temp_path, "rb"), content_type="application/json")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def download_excel_report(request):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"Location_Report_{timestamp}.xlsx"
        excel_path = os.path.join(Excel_FOLDER_PATH, excel_filename)

        wb = Workbook()
        ws = wb.active
        ws.title = "Location Report"

        headers = ["ID", "Name", "Category", "Latitude", "Longitude", "Screenshots"]
        ws.append(headers)

        for cell in ws[1]:
            cell.font = Font(bold=True)

        # ✅ Set column width for screenshot column
        ws.column_dimensions["F"].width = 40

        row_index = 2
        for feature in geojson_store["features"]:
            props = feature["properties"]
            coords = feature["geometry"]["coordinates"]
            screenshot_file = props.get("screenshot", "")
            screenshot_path = os.path.join(SCREENSHOT_DIR, screenshot_file)

            ws.append([
                props.get("id"),
                props.get("name"),
                props.get("category"),
                coords[1],
                coords[0],
                ""  # Placeholder for image
            ])

            if os.path.exists(screenshot_path):
                try:
                    img = ExcelImage(screenshot_path)
                    img.width = 240
                    img.height = 180
                    ws.row_dimensions[row_index].height = 140  # ✅ Set row height
                    ws.add_image(img, f"F{row_index}")
                except Exception as e:
                    print(f"⚠️ Could not embed image {screenshot_file}: {e}")

            row_index += 1

        wb.save(excel_path)

        response = FileResponse(open(excel_path, "rb"), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = f'attachment; filename="{excel_filename}"'
        return response

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def search_location(request):
    name = request.GET.get("name", "").strip().lower()
    category = request.GET.get("category", "").strip().lower()

    if not name or not category:
        return JsonResponse({"error": "Please provide both name and category."}, status=400)

    matched = []
    for feature in geojson_store.get("features", []):
        props = feature.get("properties", {})
        if props.get("name", "").strip().lower() == name and props.get("category", "").strip().lower() == category:
            matched.append(feature)

    if not matched:
        return JsonResponse({"message": "No matching locations found."}, status=404)

    return JsonResponse({"matches": matched}, status=200)