from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inspections.views import (
    BusinessViewSet, InspectionViewSet, 
    ReportVerificationLogViewSet, SystemActivityLogViewSet, ClientErrorLogViewSet,
    BusinessApplicationViewSet, SystemSettingViewSet
)
from .upload_view import upload_photo

router = DefaultRouter()
router.register(r'businesses', BusinessViewSet)
router.register(r'inspections', InspectionViewSet)
router.register(r'business-applications', BusinessApplicationViewSet)
router.register(r'settings', SystemSettingViewSet, basename='settings')
router.register(r'activity-logs', SystemActivityLogViewSet)
router.register(r'client-error-logs', ClientErrorLogViewSet)
router.register(r'report-verification-logs', ReportVerificationLogViewSet)

urlpatterns = [
    path('upload/', upload_photo, name='upload_photo'),
    path('', include(router.urls)),
]
