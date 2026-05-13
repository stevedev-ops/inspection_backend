from django.urls import path
from metrics.views import get_admin_dashboard_metrics, get_finance_summary, get_superadmin_metrics, get_pho_dashboard_stats

urlpatterns = [
    path('admin/', get_admin_dashboard_metrics, name='admin_metrics'),
    path('finance/', get_finance_summary, name='finance_metrics'),
    path('superadmin/', get_superadmin_metrics, name='superadmin_metrics'),
    path('pho/', get_pho_dashboard_stats, name='pho_metrics'),
]
