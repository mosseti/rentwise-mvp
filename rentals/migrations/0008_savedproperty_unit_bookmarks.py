# Generated for RentWise unit-level bookmarks.
from django.db import migrations, models
import django.db.models.deletion


def copy_building_saves_to_units(apps, schema_editor):
    SavedProperty = apps.get_model('rentals', 'SavedProperty')
    Unit = apps.get_model('rentals', 'Unit')
    for saved in SavedProperty.objects.filter(unit__isnull=True, building__isnull=False):
        unit = Unit.objects.filter(building_id=saved.building_id, status='available').order_by('rent', 'id').first()
        if unit:
            saved.unit_id = unit.id
            saved.save(update_fields=['unit'])


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0007_savedproperty'),
    ]

    operations = [
        migrations.AddField(
            model_name='savedproperty',
            name='unit',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='saved_by', to='rentals.unit'),
        ),
        migrations.AlterField(
            model_name='savedproperty',
            name='building',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='legacy_saved_by', to='rentals.building'),
        ),
        migrations.RunPython(copy_building_saves_to_units, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='savedproperty',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='savedproperty',
            constraint=models.UniqueConstraint(fields=('user', 'unit'), name='unique_saved_unit_per_user'),
        ),
    ]
