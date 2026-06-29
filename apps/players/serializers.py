from rest_framework import serializers
from .models import Player

class PlayerSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    photo_url = serializers.ReadOnlyField()
    class Meta:
        model = Player
        fields = ["id", "full_name", "photo_url", "position", "shirt_number",
                  "current_team", "nationality", "date_of_birth"]
