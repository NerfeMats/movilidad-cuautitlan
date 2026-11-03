"""Crea un escenario local de referencia para recorrer el módulo de movilidad.

No es un catálogo normativo definitivo. Basado en la matriz de 27 pasos
facilitada por el usuario. Sólo para una base de desarrollo sin expedientes
ajenos al escenario. Repetible, no borra ni sobrescribe avances existentes.
"""
import secrets
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from convocatorias.models import Convocatoria, TipoMovilidad
from expedientes.models import (
    ActividadExpediente, ActividadProceso, ExpedienteMovilidad, HistorialExpediente,
)
from .cargar_triptico_internacional import ACTIVIDADES

USERNAME = "alumno_demo_movilidad"
TITULO = "DEMO LOCAL - Movilidad internacional 2027A"


class Command(BaseCommand):
    help = "Prepara una convocatoria, alumno y expediente de referencia a partir de la matriz original."

    def handle(self, *args, **options):
        tipo = TipoMovilidad.objects.filter(nombre="Internacional saliente").first()
        if tipo is None:
            raise CommandError("Falta el tipo Internacional saliente. Ejecuta las migraciones primero.")

        User = get_user_model()
        if not any(f.name == "username" for f in User._meta.fields):
            raise CommandError("Este escenario requiere el modelo de usuario con username.")

        # Guardas: este comando está pensado para la base vacía de CASA, nunca
        # para una BD institucional o con expedientes que no sean la demo.
        if ExpedienteMovilidad.objects.exclude(alumno__username=USERNAME).exists():
            raise CommandError("Hay expedientes ajenos a la demo. No se modificó nada.")
        if Convocatoria.objects.exclude(titulo=TITULO).exists():
            raise CommandError("Hay convocatorias distintas de la demo. No se modificó nada.")
        if ActividadProceso.objects.exclude(tipo_movilidad=tipo).exists():
            raise CommandError("Hay actividades de otros tipos. No se modificó nada.")

        nombres_originales = {fila[1] for fila in ACTIVIDADES}
        if ActividadProceso.objects.filter(tipo_movilidad=tipo).exclude(nombre__in=nombres_originales).exists():
            raise CommandError("Ya hay actividades internacionales distintas de la matriz. No se modificó nada.")
        if User.objects.filter(username=USERNAME).exists() and not ExpedienteMovilidad.objects.filter(alumno__username=USERNAME, convocatoria__titulo=TITULO).exists():
            raise CommandError("Ya existe el usuario reservado para la demo sin su expediente. Revisar antes de continuar.")

        nueva_clave = None
        with transaction.atomic():
            # El comando original nunca cambia actividades existentes. Las nuevas
            # quedan opcionales hasta validación institucional.
            if ActividadProceso.objects.filter(tipo_movilidad=tipo).count() < len(ACTIVIDADES):
                call_command("cargar_triptico_internacional", aplicar=True, stdout=self.stdout)
            numero_catalogo = ActividadProceso.objects.filter(tipo_movilidad=tipo, nombre__in=nombres_originales).count()
            if numero_catalogo != 27:
                raise CommandError(f"Catálogo incompleto: {numero_catalogo}/27. Operación revertida.")

            convocatoria, _ = Convocatoria.objects.get_or_create(
                titulo=TITULO,
                defaults={"tipo_movilidad": tipo, "ciclo": "PRIMAVERA", "anio": 2027,
                          "estado": "BORRADOR", "destacada": False,
                          "resumen": "Ejemplo local, no oficial ni publicado.",
                          "descripcion": "Convocatoria ficticia para validar el recorrido completo del expediente."},
            )
            if convocatoria.tipo_movilidad_id != tipo.pk or convocatoria.estado != "BORRADOR":
                raise CommandError("La convocatoria demo existente tiene valores incompatibles.")

            alumno = User.objects.filter(username=USERNAME).first()
            if alumno is None:
                nueva_clave = secrets.token_urlsafe(20)
                alumno = User.objects.create_user(
                    username=USERNAME, password=nueva_clave,
                    first_name="Alumno", last_name="Demostracion",
                    email="alumno-demo@example.invalid",
                )

            expediente, creado = ExpedienteMovilidad.objects.get_or_create(
                alumno=alumno, convocatoria=convocatoria,
                defaults={"estado": "INICIADO", "estado_inicial": "INICIADO",
                          "tipo_alta": "NORMAL", "origen": "NUEVO",
                          "observaciones": "Escenario ficticio de prueba local."},
            )
            expediente.crear_actividades_iniciales()
            if creado:
                HistorialExpediente.objects.create(
                    expediente=expediente, usuario=None,
                    accion="Creación de expediente",
                    descripcion="Escenario de referencia creado por comando local.",
                    estado_anterior="", estado_nuevo=expediente.estado,
                )

            # Sólo en la primera ejecución, crear un recorrido contrastable:
            # estación 1 completada; estación 2 con una actividad obligatoria
            # PENDIENTE. Ésta es una REGLA DEMO del catálogo, no institucional.
            if creado:
                for actividad in expediente.actividades.select_related("actividad_proceso"):
                    if actividad.actividad_proceso.estado_expediente == "INICIADO":
                        actividad.estado = "COMPLETADA"
                        actividad.fecha_completada = timezone.now()
                        actividad.save(update_fields=["estado", "fecha_completada"])
                # Un solo bloqueo demostrativo para comprobar el flujo.
                pendiente = ActividadProceso.objects.get(
                    tipo_movilidad=tipo,
                    nombre="Reunir el resto de documentos exigidos por la convocatoria",
                )
                pendiente.obligatorio = True
                pendiente.save(update_fields=["obligatorio"])
                trabajo = ActividadExpediente.objects.get(expediente=expediente, actividad_proceso=pendiente)
                trabajo.estado = "PENDIENTE"
                trabajo.save(update_fields=["estado"])
                if not expediente.avanzar_estado(usuario=None):
                    raise CommandError("No fue posible avanzar desde INICIADO. Operación revertida.")

            actividades = ActividadExpediente.objects.filter(expediente=expediente)
            self.stdout.write(self.style.SUCCESS("\nESCENARIO LISTO"))
            self.stdout.write(f"Convocatoria: {convocatoria.titulo} [BORRADOR]")
            self.stdout.write(f"Alumno: {USERNAME}")
            if nueva_clave:
                self.stdout.write(self.style.WARNING(f"CLAVE TEMPORAL DEL ALUMNO (se muestra una sola vez): {nueva_clave}"))
                self.stdout.write("Guarda la clave en un gestor seguro. No la agregues a Git ni al chat.")
            else:
                self.stdout.write("Clave del alumno sin cambios; no se muestra de nuevo.")
            self.stdout.write(f"Expediente: {expediente.pk} | Estado: {expediente.estado}")
            self.stdout.write(f"Actividades asociadas: {actividades.count()}")
            self.stdout.write(f"Puede avanzar: {expediente.puede_avanzar()}")
            self.stdout.write(f"Alumno: http://127.0.0.1:8001/expedientes/{expediente.pk}/")
            self.stdout.write(f"Responsable: http://127.0.0.1:8001/expedientes/responsable/{expediente.pk}/")
            self.stdout.write("Para probar una variacion, modifica actividades desde Django Admin y revisa ambas vistas.")
            self.stdout.write("AVISO: una actividad del catalogo se marco obligatoria SOLO para demostrar el bloqueo en esta BD local.")
