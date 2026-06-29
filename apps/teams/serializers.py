from rest_framework import serializers
from .models import Team, Country

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "code"]

class TeamSerializer(serializers.ModelSerializer):
    country = CountrySerializer()
    logo_url = serializers.ReadOnlyField()
    class Meta:
        model = Team
        fields = ["id", "name", "short_name", "slug", "logo_url", "country",
                  "founded", "stadium", "city", "primary_color", "secondary_color"]
