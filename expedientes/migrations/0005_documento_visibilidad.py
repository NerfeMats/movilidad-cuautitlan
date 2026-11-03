from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("expedientes", "0004_fechas_reales_mvp")]

    operations = [
        migrations.AddField(
            model_name="documentoexpediente",
            name="visibilidad",
            field=models.CharField(
                choices=[
                    ("ALUMNO", "Compartido con el alumno"),
                    ("RESPONSABLE", "Reservado al personal autorizado"),
                ],
                default="ALUMNO",
                max_length=20,
            ),
        ),
    ]
