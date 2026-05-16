from django.db import models
from django.conf import settings
import uuid

class Business(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_name = models.CharField(max_length=255, db_index=True)
    permit_no = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True)
    county_name = models.CharField(max_length=100, null=True, blank=True)
    subcounty_name = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    ward_name = models.CharField(max_length=100, null=True, blank=True)
    building_name = models.CharField(max_length=255, null=True, blank=True)
    street_name = models.CharField(max_length=255, null=True, blank=True)
    plot_no = models.CharField(max_length=100, null=True, blank=True)
    facility_type = models.CharField(max_length=100, null=True, blank=True)
    contact_phone = models.CharField(max_length=50, null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    
    # Priority Contact Details
    owner_name = models.CharField(max_length=255, null=True, blank=True)
    owner_email = models.EmailField(null=True, blank=True)
    owner_phone = models.CharField(max_length=50, null=True, blank=True)
    
    contact_person_name = models.CharField(max_length=255, null=True, blank=True)
    contact_person_email = models.EmailField(null=True, blank=True)
    contact_person_phone = models.CharField(max_length=50, null=True, blank=True)
    
    location_lat = models.FloatField(null=True, blank=True)
    location_lng = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['business_name', 'subcounty_name']),
        ]

    def __str__(self):
        return self.business_name

class Inspection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='inspections', null=True, blank=True)
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='inspections_performed')
    inspector_name = models.CharField(max_length=255, null=True, blank=True)
    inspection_date = models.DateTimeField()
    next_inspection_date = models.DateTimeField(null=True, blank=True)
    service_type = models.CharField(max_length=100, null=True, blank=True)
    
    # SQLite friendly JSON fields instead of postgres ArrayField
    personnel = models.JSONField(default=list, blank=True)
    areas_affected = models.JSONField(default=list, blank=True)
    pest_types = models.JSONField(default=list, blank=True)
    chemicals_used = models.JSONField(default=list, blank=True)
    chemical_dosages = models.JSONField(default=list, blank=True)
    treatment_methods = models.JSONField(default=list, blank=True)
    issues_found = models.JSONField(default=list, blank=True)
    pest_sightings = models.JSONField(default=dict, blank=True)
    recommendations = models.JSONField(default=list, blank=True)
    
    housekeeping_rating = models.CharField(max_length=50, null=True, blank=True)
    waste_management_rating = models.CharField(max_length=50, null=True, blank=True)
    stacking_rating = models.CharField(max_length=50, null=True, blank=True)
    overall_sanitation_rating = models.CharField(max_length=50, null=True, blank=True)
    
    photo_urls = models.JSONField(default=list, blank=True)
    photo_meta = models.JSONField(default=list, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Form Customization
    form_type = models.CharField(max_length=50, default='standard', db_index=True) # standard, ipm_audit
    ipm_data = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=50, default='completed')
    is_draft = models.BooleanField(default=False)
    approval_status = models.CharField(max_length=50, default='pending')
    
    fee_category = models.CharField(max_length=100, null=True, blank=True)
    fee_premise = models.CharField(max_length=1000, null=True, blank=True)
    calculated_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_paid = models.BooleanField(default=False)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    payment_ref = models.CharField(max_length=100, null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    payment_status = models.CharField(max_length=50, default='pending')
    finance_verification_notes = models.TextField(null=True, blank=True)
    
    # Feedback from NCCG Reviewers
    nccg_notes = models.TextField(null=True, blank=True)
    decline_reason = models.CharField(max_length=100, null=True, blank=True)

    # Audit Fee Breakdowns (KES)
    ipm_audit = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    ipm_nccg = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    ipm_vendor = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    
    # Verification & Authenticity
    verification_code = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True)
    verification_fingerprint = models.CharField(max_length=100, null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-generate verification code if missing
        if not self.verification_code:
            self.verification_code = str(uuid.uuid4()).split('-')[0].upper()
        
        # Set issued_at when approved
        if self.approval_status == 'approved' and not self.issued_at:
            from django.utils import timezone
            self.issued_at = timezone.now()
            
        # Generate fingerprint if missing
        if not self.verification_fingerprint:
            import hashlib
            payload = f"{self.id}-{self.verification_code}-{self.inspection_date}"
            self.verification_fingerprint = hashlib.sha256(payload.encode()).hexdigest()[:32].upper()
            
        # Ensure 75/25 split is mathematically correct for IPM fees
        if self.ipm_audit > 0:
            from decimal import Decimal
            # We use Decimal to avoid floating point issues in financial data
            self.ipm_nccg = (self.ipm_audit * Decimal('0.25')).quantize(Decimal('0.01'))
            self.ipm_vendor = (self.ipm_audit * Decimal('0.75')).quantize(Decimal('0.01'))
            
        super().save(*args, **kwargs)

class BusinessApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='applications')
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications_made')
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='active') # active, completed

    class Meta:
        ordering = ['-applied_at']
        unique_together = ('business', 'inspector', 'status') # Prevent multiple active apps for same biz by same PHO

    def __str__(self):
        return f"App for {self.business.business_name} by {self.inspector.username}"

class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    label = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.label or self.key}: {self.value}"

class ReportVerificationLog(models.Model):
    report_id = models.UUIDField()
    verified_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

class SystemActivityLog(models.Model):
    user_id = models.UUIDField(null=True, blank=True)
    action = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ClientErrorLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    level = models.CharField(max_length=50, default='error')
    source = models.CharField(max_length=100, default='client')
    environment = models.CharField(max_length=50, default='production')
    message = models.TextField()
    error_name = models.CharField(max_length=255, null=True, blank=True)
    stack = models.TextField(null=True, blank=True)
    route = models.CharField(max_length=255, null=True, blank=True)
    url = models.TextField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    user_id = models.UUIDField(null=True, blank=True)
    user_role = models.CharField(max_length=50, null=True, blank=True)
    context = models.JSONField(default=dict, blank=True)
    client_created_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
