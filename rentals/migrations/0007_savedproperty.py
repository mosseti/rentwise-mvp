# Generated for RentWise saved-property feature.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('rentals', '0006_searchevent'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedProperty',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note', models.CharField(blank=True, max_length=180)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('building', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_by', to='rentals.building')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_properties', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('user', 'building')},
            },
        ),
    ]
