import difflib
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fi_run as fi

tmp = tempfile.mkdtemp()
fi.WORK_B = tmp + "/b"
fi.WORK_F = tmp + "/f"
for d in ("config", "users", "records"):
    os.makedirs(fi.WORK_B + "/" + d)
os.makedirs(fi.WORK_F)

FILES = {
    "config/settings.py": '''INSTALLED_APPS = [
    "rest_framework_simplejwt.token_blacklist",
    "django.contrib.admin",
    "rest_framework",
]
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "login": "5/min",
        "register": "10/hour",
        "password_reset": "5/hour",
    },
}
''',
    "users/serializers.py": '''        except Exception:
            # Muvaffaqiyatsiz urinish - hisoblagichni oshiramiz
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                    user.locked_until = timezone.now() + LOCKOUT_DURATION
''',
    "records/permissions.py": '''class PatientObjectPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == Role.PATIENT:
            return obj.user_id == user.id and request.method in SAFE_METHODS


class MedicalRecordObjectPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == Role.PATIENT:
            return obj.patient.user_id == user.id and request.method in SAFE_METHODS


class PrescriptionObjectPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == Role.PATIENT:
            return obj.patient.user_id == user.id and request.method in SAFE_METHODS
''',
    "records/views.py": '''class PatientListView(generics.ListAPIView):
    permission_classes = [IsAdminOrDoctor]

    def get_queryset(self):
        qs = Patient.objects.all()
        return qs


class MedicalRecordListCreateView(generics.ListCreateAPIView):
    permission_classes = [MedicalRecordObjectPermission]

    def get_queryset(self):
        user = self.request.user
        qs = MedicalRecord.objects.select_related("patient__user", "created_by")

        if user.role == Role.PATIENT:
            qs = qs.filter(patient__user=user)
        elif user.role == Role.DOCTOR:
            pass


class PrescriptionListView(generics.ListCreateAPIView):
    def get_queryset(self):
        qs = Prescription.objects.all()
        if user.role == Role.PATIENT:
            qs = qs.filter(patient__user=user)
''',
    "users/views.py": '''class UserListView(generics.ListAPIView):
    permission_classes = [IsAdmin]


class UserDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdmin]


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]


class PasswordResetRequestView(APIView):
    def post(self, request):
        generic_response = Response({"detail": "Agar shu email bilan hisob mavjud bo'lsa"})
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            security_logger.info("Parolni tiklash so'ralgan, lekin email topilmadi: %s", email)
            return generic_response

        uid = 1
''',
    ".env.docker": "POSTGRES_DB=x\nDEBUG=False\nSECRET=y\n",
}
NGINX = '''server {
    listen 80;
    server_tokens off;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; frame-ancestors 'none'" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_hide_header X-Frame-Options;
        add_header Cache-Control "no-store" always;
        add_header Content-Security-Policy "default-src 'none'" always;
    }
}
'''
ORIG = {}


def write_all():
    for rel, txt in FILES.items():
        with open(fi.WORK_B + "/" + rel, "w") as f:
            f.write(txt)
    with open(fi.WORK_F + "/nginx.conf", "w") as f:
        f.write(NGINX)


def read(path):
    with open(path) as f:
        return f.read()


paths = {"F1": [fi.WORK_B + "/config/settings.py"], "F2": [fi.WORK_B + "/config/settings.py"],
         "F3": [fi.WORK_B + "/users/serializers.py"],
         "F4": [fi.WORK_B + "/records/permissions.py", fi.WORK_B + "/records/views.py"],
         "F5": [fi.WORK_B + "/users/views.py"], "F6": [fi.WORK_B + "/users/views.py"],
         "F7": [fi.WORK_F + "/nginx.conf"], "F8": [fi.WORK_B + "/.env.docker"]}
for cfg in fi.ALL[1:]:
    write_all()
    before = {p: read(p) for p in paths[cfg]}
    fi.FAULTS[cfg]()
    print("=" * 20, cfg, fi.META[cfg][0])
    for p in paths[cfg]:
        after = read(p)
        d = list(difflib.unified_diff(before[p].splitlines(), after.splitlines(), lineterm="", n=0))
        print("\n".join(d[2:]))
