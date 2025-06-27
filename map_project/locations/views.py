from django.shortcuts import render

# Create your views here.
# locations/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Location
from .serializers import LocationSerializer
from django.db.models import Count

def index(request):
    return render(request, "locations/index.html")
def adminpage(request):
    return render(request, "locations/admin.html")

class LocationGeoJSONView(APIView):
    def get(self, request):
        locations = Location.objects.all()
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [loc.longitude, loc.latitude],
                    },
                    "properties": {
                        "name": loc.name,
                        "category": loc.category
                    }
                } for loc in locations
            ]
        }
        return Response(geojson)

class LocationStatsView(APIView):
    def get(self, request):
        total = Location.objects.count()
        most_common = Location.objects.values('category').annotate(count=Count('id')).order_by('-count').first()
        return Response({
            'total_locations': total,
            'most_common_category': most_common['category'] if most_common else None
        })
