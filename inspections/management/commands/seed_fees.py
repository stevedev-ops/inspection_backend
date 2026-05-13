import json
import os
from django.core.management.base import BaseCommand
from inspections.models import SystemSetting

class Command(BaseCommand):
    help = 'Seeds the SystemSetting table with Finance Act 2023 fees from data/fees.json'

    def handle(self, *args, **kwargs):
        file_path = os.path.join('data', 'fees.json')
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        with open(file_path, 'r') as f:
            try:
                fee_data = json.load(f)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to parse JSON: {e}"))
                return

        setting, created = SystemSetting.objects.update_or_create(
            key='finance_act_2023',
            defaults={
                'value': fee_data,
                'description': 'Nairobi County Pest Control Fee Schedule (Finance Act 2023)'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Successfully created Finance Act setting."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully updated Finance Act setting."))
