# Generated for RentWise free map/geocoder update

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0004_building_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='CachedPlace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(max_length=180, unique=True)),
                ('label', models.CharField(max_length=255)),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('source', models.CharField(default='nominatim', max_length=40)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['query']},
        ),
    ]
