from rest_framework import serializers
from .models import Competition, Season, Standing

class CompetitionSerializer(serializers.ModelSerializer):
    logo_url = serializers.ReadOnlyField()
    class Meta:
        model = Competition
        fields = ["id", "name", "short_name", "slug", "logo_url", "comp_type", "tier"]

class SeasonSerializer(serializers.ModelSerializer):
    competition = CompetitionSerializer()
    class Meta:
        model = Season
        fields = ["id", "name", "start_date", "end_date", "is_current", "competition"]
