import os

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import MedicalRecord, Patient, Role, User

PW = os.environ.get("REF_TEST_PASSWORD", "Fi-Test-Pass-2026!")  # throw-away value for the local copy


class Command(BaseCommand):
    help = "Create the synthetic test accounts used by the detectors."

    def handle(self, *args, **opts):
        doctor = None
        for name in ("doctor1", "doctor2"):
            u, _ = User.objects.get_or_create(username=name, defaults=dict(email=name + "@example.com", role=Role.DOCTOR))
            u.set_password(PW); u.save()
            doctor = doctor or u
        a, _ = User.objects.get_or_create(username="admin1", defaults=dict(email="admin1@example.com", role=Role.ADMIN))
        a.set_password(PW); a.save()
        for name in ("patient01", "patient02", "patient20"):
            u, _ = User.objects.get_or_create(username=name, defaults=dict(email=name + "@example.com", role=Role.PATIENT))
            u.set_password(PW); u.failed_login_attempts = 0; u.locked_until = None; u.save()
            p, _ = Patient.objects.get_or_create(user=u)
            if name != "patient20" and not p.records.exists():
                for i in range(2):
                    MedicalRecord.objects.create(patient=p, created_by=doctor, title="Synthetic record %d" % i,
                                                 diagnosis="Healthy", treatment="Advice", visit_date=timezone.now())
        self.stdout.write("SEED_OK")
