from django.core.management.base import BaseCommand
import pandas as pd
import math
from inspections.models import Business
from users.models import User

class Command(BaseCommand):
    help = 'Seeds local SQLite / PostgreSQL backend with data from excel files'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding superadmin / sample PHO users...")
        
        # 1. Super Admin (Global Access)
        if not User.objects.filter(email='superadmin@ipcms.go.ke').exists():
            User.objects.create_superuser(
                username='superadmin@ipcms.go.ke',
                email='superadmin@ipcms.go.ke',
                password='superadmin@2026',
                role='super_admin',
                full_name='Global Super Admin',
                status='active'
            )
            self.stdout.write(self.style.SUCCESS('Created Super Admin (superadmin@ipcms.go.ke / superadmin@2026)'))

        # 2. Company Admin (Universal Regional Access)
        admin_user = User.objects.filter(email='admin@ipcms.go.ke').first()
        if not admin_user:
            admin_user = User.objects.create_user(
                username='admin@ipcms.go.ke',
                email='admin@ipcms.go.ke',
                password='admin@2026',
                role='admin',
                full_name='Operations Manager',
                status='active',
                subcounty='All Regions',
                company_name='Nairobi Pest Solvers Ltd',
                company_email='ops@nairobiltd.com'
            )
            self.stdout.write(self.style.SUCCESS('Created Company Admin: Nairobi Pest Solvers Ltd'))

        # 3. Standard PHO (Locked to Westlands by Admin)
        if not User.objects.filter(email='pho@example.com').exists():
            User.objects.create_user(
                username='pho@example.com',
                email='pho@example.com',
                password='pho',
                role='pho',
                full_name='Westlands Inspector',
                status='active',
                subcounty='Westlands',
                created_by=admin_user
            )
            self.stdout.write(self.style.SUCCESS('Created PHO user (pho@example.com / pho) - Westlands'))

        # 4. Finance Manager (Company-bound)
        if not User.objects.filter(email='finance@ipcms.go.ke').exists():
            User.objects.create_user(
                username='finance@ipcms.go.ke',
                email='finance@ipcms.go.ke',
                password='finance@2026',
                role='finance_manager',
                full_name='Finance Audit Manager',
                status='active',
                subcounty='All Regions',
                created_by=admin_user
            )
            self.stdout.write(self.style.SUCCESS('Created Finance Manager (finance@ipcms.go.ke / finance@2026)'))


        self.stdout.write("Wiping existing businesses for a fresh seed...")
        Business.objects.all().delete()

        self.stdout.write("Loading SIMPLIFIED DATA.xlsx for businesses...")
        
        file_path = 'data/SIMPLIFIED DATA.xlsx'
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Could not load excel file: {e}"))
            return

        businesses_created = 0
        
        for index, row in df.iterrows():
            business_name = str(row.get('Business Name', '')).strip()
            if not business_name or business_name.lower() == 'nan':
                continue
                
            permit_no = str(row.get('Permit No.', '')).strip()
            if permit_no.lower() == 'nan':
                permit_no = None

            subcounty_name = str(row.get('Subcounty Name', '')).strip()
            if subcounty_name.lower() == 'nan': subcounty_name = None
            
            ward_name = str(row.get('Ward Name', '')).strip()
            if ward_name.lower() == 'nan': ward_name = None

            building_name = str(row.get('Building Name', '')).strip()
            if building_name.lower() == 'nan': building_name = None
            
            street_name = str(row.get('Street Name', '')).strip()
            if street_name.lower() == 'nan': street_name = None
            
            plot_no = str(row.get('Plot No.', '')).strip()
            if plot_no.lower() == 'nan': plot_no = None

            contact_phone = str(row.get('Contact Person Mobile No', '')).strip()
            if contact_phone.lower() == 'nan': contact_phone = None

            contact_email = str(row.get('Contact Person Email', '')).strip()
            if contact_email.lower() == 'nan': contact_email = None

            Business.objects.create(
                business_name=business_name,
                permit_no=permit_no,
                subcounty_name=subcounty_name,
                ward_name=ward_name,
                building_name=building_name,
                street_name=street_name,
                plot_no=plot_no,
                contact_phone=contact_phone,
                contact_email=contact_email
            )
            businesses_created += 1

            if businesses_created % 500 == 0:
                self.stdout.write(f"Created {businesses_created} businesses...")

        self.stdout.write(self.style.SUCCESS(f"Finished inserting {businesses_created} businesses."))
