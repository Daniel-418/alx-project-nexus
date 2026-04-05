from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0003_alter_cartitem_quantity"),
    ]

    operations = [
        migrations.AddField(
            model_name="cart",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
