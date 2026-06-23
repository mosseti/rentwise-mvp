# Generated for RentWise prototype: add uploaded image support while keeping URL support.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0002_unitimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='unitimage',
            name='image',
            field=models.ImageField(blank=True, upload_to='unit_images/'),
        ),
        migrations.AlterField(
            model_name='unitimage',
            name='image_url',
            field=models.URLField(blank=True),
        ),
    ]
