# Generated for RentWise prototype
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField(blank=True)),
                ('latitude', models.DecimalField(decimal_places=6, default=-1.286389, max_digits=9)),
                ('longitude', models.DecimalField(decimal_places=6, default=36.817223, max_digits=9)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='AssistantMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(blank=True, max_length=80)),
                ('role', models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant')], max_length=20)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.CreateModel(
            name='Building',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('slug', models.SlugField(blank=True, unique=True)),
                ('landmark', models.CharField(blank=True, max_length=160)),
                ('description', models.TextField(blank=True)),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('image_url', models.URLField(blank=True)),
                ('amenities', models.CharField(blank=True, help_text='Comma separated amenities', max_length=255)),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('area', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='buildings', to='rentals.area')),
                ('caretaker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buildings', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['area__name', 'name']},
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unit_type', models.CharField(choices=[('bedsitter', 'Bedsitter'), ('studio', 'Studio'), ('one_bedroom', 'One bedroom'), ('two_bedroom', 'Two bedroom'), ('three_bedroom', 'Three bedroom'), ('shop', 'Shop unit')], max_length=30)),
                ('label', models.CharField(blank=True, help_text='Example: A12, Ground floor, Unit 4', max_length=50)),
                ('rent', models.PositiveIntegerField()),
                ('deposit', models.PositiveIntegerField(default=0)),
                ('service_charge', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(choices=[('available', 'Available'), ('occupied', 'Occupied'), ('reserved', 'Reserved'), ('maintenance', 'Maintenance')], default='available', max_length=20)),
                ('image_url', models.URLField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('building', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='units', to='rentals.building')),
            ],
            options={'ordering': ['rent', 'unit_type']},
        ),
        migrations.CreateModel(
            name='ViewingRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('phone', models.CharField(max_length=30)),
                ('message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('requester', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='viewing_requests', to='rentals.unit')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
