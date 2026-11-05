from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("expedientes", "0006_seguimiento_v19"),
        ("convocatorias", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UniversidadCandidataExpediente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("estado", models.CharField(max_length=24, default="PROPUESTA", choices=[
                    ("PROPUESTA", "Propuesta en documentación"),
                    ("POSTULADA", "Postulación acreditada"),
                    ("RESPUESTA_PENDIENTE", "Respuesta pendiente"),
                    ("ACEPTADA", "Aceptación acreditada"),
                    ("DESCARTADA", "Descartada"),
                ])),
                ("observaciones", models.TextField(blank=True)),
                ("fecha_registro", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                ("documento", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="candidaturas_universitarias", to="expedientes.documentoexpediente", help_text="Documento de evidencia perteneciente al mismo expediente.")),
                ("expediente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="universidades_candidatas", to="expedientes.expedientemovilidad")),
                ("ies", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="candidaturas_movilidad", to="convocatorias.ies")),
            ],
            options={"ordering": ["pk"], "verbose_name": "Universidad candidata de expediente", "verbose_name_plural": "Universidades candidatas de expedientes"},
        ),
        migrations.AddConstraint(
            model_name="universidadcandidataexpediente",
            constraint=models.UniqueConstraint(fields=("expediente", "ies"), name="universidad_unica_por_expediente"),
        ),
    ]
