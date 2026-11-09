from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0003_alter_category_options_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='event',
            old_name='organizer',
            new_name='user',
        ),
    ]
