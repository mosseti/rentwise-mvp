# Generated for RentWise prototype.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnitImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image_url', models.URLField()),
                ('caption', models.CharField(blank=True, max_length=120)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='rentals.unit')),
            ],
            options={
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]
