from rest_framework import serializers

from .models import MedicalRecord, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]


class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = ["id", "patient", "record_type", "title", "diagnosis", "treatment", "visit_date"]
