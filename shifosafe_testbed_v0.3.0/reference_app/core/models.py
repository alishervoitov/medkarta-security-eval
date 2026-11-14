from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin"
    DOCTOR = "doctor"
    PATIENT = "patient"


class User(AbstractUser):
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PATIENT)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)


class MedicalRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="records")
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    record_type = models.CharField(max_length=20, default="visit")
    title = models.CharField(max_length=200)
    diagnosis = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    visit_date = models.DateTimeField()
