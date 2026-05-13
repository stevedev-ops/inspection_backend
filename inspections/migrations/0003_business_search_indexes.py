from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='business',
            name='business_name',
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='business',
            name='permit_no',
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='business',
            name='subcounty_name',
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True),
        ),
        migrations.AddIndex(
            model_name='business',
            index=models.Index(fields=['business_name', 'subcounty_name'], name='inspections_busines_932997_idx'),
        ),
    ]
