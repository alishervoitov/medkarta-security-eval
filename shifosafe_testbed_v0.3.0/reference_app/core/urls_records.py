from django.urls import path

from . import views

urlpatterns = [
    path("medical-records/", views.MedicalRecordList.as_view()),
    path("medical-records/<int:pk>/", views.MedicalRecordDetail.as_view()),
]
