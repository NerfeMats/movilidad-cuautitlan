from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("expedientes", "0003_documento_nombre_original")]

    operations = [
        migrations.AddField(
            model_name="expedientemovilidad",
            name="fecha_inicio_real_movilidad",
            field=models.DateField(
                null=True, blank=True,
                verbose_name="Fecha real de inicio de movilidad",
                help_text=(
                    "Fecha acreditada de inicio de la movilidad, si se conoce. "
                    "No sustituye la fecha de registro digital del expediente."
                ),
            ),
        ),
        migrations.AddField(
            model_name="actividadexpediente",
            name="fecha_cumplimiento_real",
            field=models.DateField(
                null=True, blank=True,
                verbose_name="Fecha real de cumplimiento",
                help_text=(
                    "Fecha histórica acreditada, cuando se conozca. "
                    "La fecha de completado es la marca técnica del sistema."
                ),
            ),
        ),
    ]
