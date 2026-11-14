from django.http import HttpResponse
from django.urls import include, path


def index(request):
    return HttpResponse("<!doctype html><title>Reference app</title><p>Reference app (test bed). API under /api/.</p>")


urlpatterns = [
    path("", index),
    path("api/auth/", include("core.urls_auth")),
    path("api/records/", include("core.urls_records")),
]
