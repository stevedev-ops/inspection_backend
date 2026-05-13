from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from inspections.models import (
    Business, Inspection, ReportVerificationLog, SystemActivityLog, 
    ClientErrorLog, BusinessApplication, SystemSetting
)
from inspections.serializers import (
    BusinessSerializer, InspectionSerializer, ReportVerificationLogSerializer, 
    SystemActivityLogSerializer, ClientErrorLogSerializer, BusinessApplicationSerializer,
    SystemSettingSerializer
)

class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['business_name', 'permit_no', 'subcounty_name', 'ward_name']

    def get_queryset(self):
        user = self.request.user
        # Admins and Super Admins see everything (Registry is universal)
        if user.role in ('super_admin', 'admin', 'finance_manager'):
            return Business.objects.all()
            
        applied_by_me = self.request.query_params.get('applied_by_me') == 'true'

        if user.role in ('pho', 'nccg_inspector'):
            subcounty = (user.subcounty or '').strip()
            if not subcounty:
                return Business.objects.none()
            
            qs = Business.objects.filter(subcounty_name__iexact=subcounty)
            
            if applied_by_me and user.role == 'pho':
                # Filter by businesses that have an active application by this PHO
                applied_ids = BusinessApplication.objects.filter(
                    inspector=user, status='active'
                ).values_list('business_id', flat=True)
                return qs.filter(id__in=applied_ids)

            return qs

        return Business.objects.none()

    @action(detail=False, methods=['GET'], permission_classes=[permissions.IsAuthenticated], url_path='debug-subcounties')
    def debug_subcounties(self, request):
        """Returns distinct subcounty_name values stored in Business table. Admin only."""
        if request.user.role not in ('super_admin', 'admin'):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        values = list(
            Business.objects.exclude(subcounty_name__isnull=True)
            .exclude(subcounty_name='')
            .values_list('subcounty_name', flat=True)
            .distinct()
            .order_by('subcounty_name')
        )
        return Response({'stored_subcounties': values, 'count': len(values)})

import django_filters
from django.db.models import Q

class InspectionFilter(django_filters.FilterSet):
    is_alert = django_filters.BooleanFilter(method='filter_is_alert')
    is_action_required = django_filters.BooleanFilter(method='filter_is_action_required')
    inspection_date = django_filters.DateFromToRangeFilter()
    inspection_date__date = django_filters.DateFilter(field_name='inspection_date', lookup_expr='date')

    class Meta:
        model = Inspection
        fields = {
            'is_paid': ['exact'],
            'payment_status': ['exact', 'in'],
            'payment_method': ['exact', 'in'],
            'approval_status': ['exact', 'in'],
            'status': ['exact', 'in'],
            'inspector': ['exact', 'in'],
            'is_draft': ['exact'],
            'inspection_date': ['exact', 'date', 'gte', 'lte'],
            'updated_at': ['exact', 'date', 'gte', 'lte'],
            'business__subcounty_name': ['exact', 'in', 'icontains'],
            'business__business_name': ['icontains'],
        }

    def filter_is_alert(self, queryset, name, value):
        if value:
            return queryset.filter(Q(payment_status='flagged') | Q(approval_status='pending'))
        return queryset

    def filter_is_action_required(self, queryset, name, value):
        if value:
            return queryset.filter(Q(payment_status='flagged') | Q(approval_status='declined'))
        return queryset

class InspectionViewSet(viewsets.ModelViewSet):
    queryset = Inspection.objects.all()
    serializer_class = InspectionSerializer
    filterset_class = InspectionFilter
    search_fields = ['payment_ref', 'business__business_name']
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Inspection.objects.all()
        if user.role == 'admin':
            from django.db.models import Q
            return Inspection.objects.filter(Q(inspector__created_by=user) | Q(inspector=user))
        if user.role == 'nccg_inspector':
            # Lock to own subcounty
            if user.subcounty:
                return Inspection.objects.filter(business__subcounty_name=user.subcounty)
            return Inspection.objects.none()
        if user.role == 'pho':
            # PHOs see their own inspections only (subcounty enforced at business lookup level)
            return Inspection.objects.filter(inspector=user)
        if user.role == 'finance_manager':
            # Finance managers see their company's inspections (linked via Admin they work for)
            from django.db.models import Q
            # If they have a creator, they see that creator's team's data
            if user.created_by:
                return Inspection.objects.filter(Q(inspector__created_by=user.created_by) | Q(inspector=user.created_by))
            return Inspection.objects.all() # Fallback for system-wide finance
        return Inspection.objects.filter(inspector=user)

    def perform_create(self, serializer):
        serializer.save(inspector=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        from .utils import log_activity
        instance = self.get_object()
        old_status = instance.approval_status
        old_pay_status = instance.payment_status
        
        response = super().partial_update(request, *args, **kwargs)
        
        new_status = response.data.get('approval_status', old_status)
        new_pay_status = response.data.get('payment_status', old_pay_status)
        
        if old_status != new_status or old_pay_status != new_pay_status:
            log_activity(request.user, 'INSPECTION_STATUS_CHANGE', {
                'inspection_id': str(instance.id),
                'business_name': instance.business.business_name if instance.business else "Unknown Business",
                'old_approval': old_status,
                'new_approval': new_status,
                'old_payment': old_pay_status,
                'new_payment': new_pay_status
            })
            
        return response

    @action(detail=False, methods=['GET'], permission_classes=[permissions.AllowAny], url_path='subcounties')
    def list_subcounties(self, request):
        subcounties = list(
            Business.objects.exclude(subcounty_name__isnull=True)
            .exclude(subcounty_name='')
            .values_list('subcounty_name', flat=True)
            .distinct()
            .order_by('subcounty_name')
        )
        return Response(subcounties)

    @action(detail=False, methods=['POST'], permission_classes=[permissions.IsAuthenticated], url_path='dispatch-email')
    def dispatch_email(self, request):
        """
        Server-side email dispatcher using Resend.
        Uses the creator's Company Official Email for branding.
        """
        user = request.user
        to_email = request.data.get('to')
        subject = request.data.get('subject')
        html_content = request.data.get('html')
        template_id = request.data.get('template_id')
        variables = request.data.get('variables', {})

        if not to_email:
            return Response({'error': 'Recipient email (to) is required'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Determine Company Identity
        sender_name = "NCCG Inspections"
        reply_to_email = "inspections@nccg.go.ke"
        
        # Look up the creator's company details
        creator = user.created_by
        if creator and creator.role == 'admin':
            if creator.company_name:
                sender_name = creator.company_name
            if creator.company_email:
                reply_to_email = creator.company_email

        # 2. Prepare HTML (if not provided, we could use templates, but for now we expect HTML from frontend or generate it)
        # Note: In a production app, we should use Django templates here.
        if not html_content:
            # Basic fallback template
            html_content = f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: auto;">
                <h1 style="color: #1e293b;">{sender_name}</h1>
                <p>Hello,</p>
                <p>Please find the requested document regarding <b>{variables.get('business_name', 'your inspection')}</b>.</p>
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
                <p style="font-size: 12px; color: #64748b;">
                    Sent by {user.full_name or user.username} ({user.role.upper()}) on behalf of {sender_name}.
                    Replies will be sent to {reply_to_email}.
                </p>
            </div>
            """

        # 3. Dispatch via Resend (Simulation if no key)
        import os
        import json
        import urllib.request
        from rest_framework.exceptions import APIException

        api_key = os.getenv('RESEND_API_KEY')
        
        if not api_key:
            # Log the simulation
            print(f"[Email Simulation] To: {to_email} | From: {sender_name} | Reply-To: {reply_to_email}")
            return Response({
                'message': 'Simulation: Email dispatched successfully',
                'simulated': True,
                'sender': sender_name,
                'reply_to': reply_to_email
            })

        try:
            req = urllib.request.Request(
                'https://api.resend.com/emails',
                method='POST',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                },
                data=json.dumps({
                    'from': f"{sender_name} <inspections@nccg.go.ke>", # Domain must be verified in Resend
                    'to': [to_email],
                    'reply_to': reply_to_email,
                    'subject': subject or "Inspection Update",
                    'html': html_content
                }).encode('utf-8')
            )
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return Response(res_data)

        except Exception as e:
            raise APIException(f"Failed to dispatch email via Resend: {str(e)}")

    @action(detail=False, methods=['GET'], permission_classes=[permissions.AllowAny], url_path='verify/(?P<report_id>[^/.]+)')
    def verify_report_public(self, request, report_id=None):
        from django.db.models import Q
        try:
            # Flexible lookup: UUID or Public Code
            import uuid
            inspection = None
            
            # Try parsing as UUID first
            try:
                val = uuid.UUID(report_id)
                inspection = Inspection.objects.filter(id=val).first()
            except ValueError:
                pass
            
            if not inspection:
                # Try verification_code case-insensitively
                inspection = Inspection.objects.filter(verification_code__iexact=report_id).first()
            
            if not inspection:
                raise Inspection.DoesNotExist()

            # Log the request
            ReportVerificationLog.objects.create(
                report_id=inspection.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            data = InspectionSerializer(inspection).data
            
            # Flatten some fields for the verification UI
            if inspection.business:
                data['businesses'] = BusinessSerializer(inspection.business).data
                data['permit_no'] = inspection.business.permit_no
            
            data['fingerprint'] = inspection.verification_fingerprint
            data['issued_at'] = inspection.issued_at or inspection.created_at
            
            return Response(data)
        except Inspection.DoesNotExist:
            return Response({'error': 'Inspection not found'}, status=status.HTTP_404_NOT_FOUND)

class ReportVerificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReportVerificationLog.objects.all()
    serializer_class = ReportVerificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]

class SystemActivityLogViewSet(viewsets.ModelViewSet):
    queryset = SystemActivityLog.objects.all().order_by('-created_at')
    serializer_class = SystemActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Optimization: Batch fetch related user names for the current page
        # This prevents 100+ separate queries per page load
        logs = self.get_queryset()
        # Use pagination bounds if available
        try:
            page = self.paginate_queryset(logs)
            target_logs = page if page is not None else logs
        except:
            target_logs = logs

        uids = {log.user_id for log in target_logs if log.user_id}
        if uids:
            from users.models import User
            users_map = {
                str(u.id): u.full_name or u.username 
                for u in User.objects.filter(id__in=uids)
            }
            context['user_names'] = users_map
        return context

class ClientErrorLogViewSet(viewsets.ModelViewSet):
    queryset = ClientErrorLog.objects.all()
    serializer_class = ClientErrorLogSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

class BusinessApplicationViewSet(viewsets.ModelViewSet):
    queryset = BusinessApplication.objects.all()
    serializer_class = BusinessApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return BusinessApplication.objects.all()
        if user.role == 'admin':
            return BusinessApplication.objects.filter(inspector__created_by=user)
        return BusinessApplication.objects.filter(inspector=user)

    def perform_create(self, serializer):
        serializer.save(inspector=self.request.user)

class SystemSettingViewSet(viewsets.ModelViewSet):
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'key'
