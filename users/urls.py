from django.urls import path
from .views import (
    UserViewSet, me, admin_create_user, admin_purge_user, resolve_staff_login_email, transfer_subcounty
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('me/', me, name='me'),
    path('admin-create/', admin_create_user, name='admin_create_user'),
    path('admin-purge/', admin_purge_user, name='admin_purge_user'),
    path('transfer-subcounty/', transfer_subcounty, name='transfer_subcounty'),
    path('resolve-email/', resolve_staff_login_email, name='resolve_staff_login_email'),
] + router.urls
