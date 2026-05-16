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

        file_path = 'data/SIMPLIFIED DATA.xlsx'
        try:
            xl = pd.ExcelFile(file_path)
            sheet_names = xl.sheet_names
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Could not load excel file: {e}"))
            return

        existing_permits = set()
        businesses_to_create = []
        total_created = 0
        skipped_duplicates = 0

        subcounties_list = [
            'Dagoretti North', 'Dagoretti South', 'Embakasi Central', 'Embakasi East', 
            'Embakasi North', 'Embakasi South', 'Embakasi West', 'Kamkunji', 
            'Kasarani', 'Kibra', 'Langata', 'Makadara', 'Mathare', 
            'Roysambu', 'Ruaraka', 'Starehe', 'Westlands'
        ]

        for sheet_name in sheet_names:
            if sheet_name == 'Sheet2':
                continue
                
            self.stdout.write(f"Processing sheet: {sheet_name}...")
            df = xl.parse(sheet_name)
            
            # Determine subcounty from sheet name if not in column
            default_subcounty = sheet_name if sheet_name in subcounties_list else None
            
            for index, row in df.iterrows():
                business_name = str(row.get('Business Name', '')).strip()
                if not business_name or business_name.lower() in ['nan', 'none', '']:
                    continue
                    
                permit_no = str(row.get('Permit No.', '')).strip()
                if not permit_no or permit_no.lower() in ['nan', 'none', '', 'null']:
                    permit_no = None
                
                # Check for duplicates across all sheets
                if permit_no:
                    if permit_no in existing_permits:
                        skipped_duplicates += 1
                        continue
                    existing_permits.add(permit_no)

                subcounty_name = str(row.get('Subcounty Name', '')).strip()
                if subcounty_name.lower() in ['nan', ''] or not subcounty_name:
                    subcounty_name = default_subcounty
                
                ward_name = str(row.get('Ward Name', '')).strip()
                if ward_name.lower() in ['nan', '']: ward_name = None

                building_name = str(row.get('Building Name', '')).strip()
                if building_name.lower() in ['nan', '']: building_name = None
                
                street_name = str(row.get('Street Name', '')).strip()
                if street_name.lower() in ['nan', '']: street_name = None
                
                plot_no = str(row.get('Plot No.', '')).strip()
                if plot_no.lower() in ['nan', '']: plot_no = None

                contact_phone = str(row.get('Contact Person Mobile No', '')).strip()
                if contact_phone.lower() in ['nan', '']: contact_phone = None

                contact_email = str(row.get('Contact Person Email', '')).strip()
                if contact_email.lower() in ['nan', '']: contact_email = None

                businesses_to_create.append(Business(
                    business_name=business_name,
                    permit_no=permit_no,
                    subcounty_name=subcounty_name,
                    ward_name=ward_name,
                    building_name=building_name,
                    street_name=street_name,
                    plot_no=plot_no,
                    contact_phone=contact_phone,
                    contact_email=contact_email
                ))

                if len(businesses_to_create) >= 1000:
                    Business.objects.bulk_create(businesses_to_create)
                    total_created += len(businesses_to_create)
                    self.stdout.write(f"Inserted {total_created} businesses... (Skipped {skipped_duplicates} duplicates)")
                    businesses_to_create = []

        if businesses_to_create:
            Business.objects.bulk_create(businesses_to_create)
            total_created += len(businesses_to_create)

        self.stdout.write(self.style.SUCCESS(f"Finished. Created {total_created} businesses. Skipped {skipped_duplicates} duplicates."))

