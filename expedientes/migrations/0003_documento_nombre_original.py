from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expedientes", "0002_reglas_configuracion"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentoexpediente",
            name="nombre_archivo_original",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
