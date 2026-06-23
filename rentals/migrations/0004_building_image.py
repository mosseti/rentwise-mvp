# Generated for RentWise prototype: add uploaded building image support.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0003_unitimage_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='building',
            name='image',
            field=models.ImageField(blank=True, upload_to='building_images/'),
        ),
    ]
