"""Carga reproducible de la matriz ORIGINAL de 27 pasos de movilidad internacional.

Fuente: matriz institucional aportada por el usuario, con siete columnas por paso.
La correspondencia de cada paso con uno de los nueve estados es una
interpretación funcional basada en la segunda matriz, NO un estado oficial.
Se preserva texto literal de responsable, evidencia, intervención, condición
para avanzar y estado propuesto en la descripción.

No se definen actividades obligatorias automáticamente: la matriz funcional
señala requisitos según convocatoria y casos condicionales. Debe revisarse
esa decisión antes de usar las actividades como bloqueo de transiciones.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from convocatorias.models import TipoMovilidad
from expedientes.models import ActividadProceso, ActividadExpediente, ExpedienteMovilidad

# (número, nombre original, estación funcional, fase, responsable del modelo,
#  responsable ORIGINAL, evidencia ORIGINAL, intervención ORIGINAL,
#  condición ORIGINAL, estado propuesto ORIGINAL)
ACTIVIDADES = ((1, 'Asistir a sesión informativa para resolver dudas de la convocatoria', 'INICIADO', 'ANTES', 'ALUMNO', 'Alumno', 'No necesariamente documento', 'DAAE', 'Conocer condiciones de la convocatoria', 'INFORMACION'), (2, 'Consultar la tabla orientativa para elegir la IES destino', 'INICIADO', 'ANTES', 'OTRO', 'Alumno + Responsable de Movilidad', 'Selección preliminar de IES', 'Responsable de Movilidad', 'Identificar opciones de destino', 'SELECCION_IES'), (3, 'Realizar certificación de idioma y tramitar pasaporte', 'INTEGRANDO_EXPEDIENTE', 'ANTES', 'ALUMNO', 'Alumno', 'Certificación/acreditación y pasaporte', 'Instituciones correspondientes', 'Contar con requisitos aplicables', 'REQUISITOS_PERSONALES'), (4, 'Elaborar propuesta de Carta de Homologación Preliminar y cuadros de mínimos', 'INTEGRANDO_EXPEDIENTE', 'ANTES', 'ALUMNO', 'Alumno', 'Carta de Homologación Preliminar + cuadro de mínimos', 'Coordinador de Carrera, Subdirector Académico y Tutor', 'Obtener vistos buenos requeridos', 'HOMOLOGACION_PRELIMINAR'), (5, 'Someter las Cartas de Homologación Preliminar a los órganos colegiados', 'EN_REVISION', 'ANTES', 'ESPACIO_ACADEMICO', 'Espacio Académico', 'Carta de Homologación Preliminar', 'H.H. Consejo de Gobierno y órgano académico correspondiente', 'Obtener validación institucional', 'HOMOLOGACION_EN_VALIDACION'), (6, 'Reunir el resto de documentos exigidos por la convocatoria', 'INTEGRANDO_EXPEDIENTE', 'ANTES', 'ALUMNO', 'Alumno', 'Expediente documental', '—', 'Tener documentos obligatorios completos', 'INTEGRANDO_EXPEDIENTE'), (7, 'Entregar documentos en físico y PDF al Responsable de Movilidad', 'INTEGRANDO_EXPEDIENTE', 'ANTES', 'ALUMNO', 'Alumno', 'Expediente físico y digital', 'Responsable de Movilidad', 'Recepción del expediente', 'EXPEDIENTE_ENTREGADO'), (8, 'Entregar la documentación a la DAAE', 'ENVIADO_DAAE', 'ANTES', 'RESPONSABLE_MOVILIDAD', 'Responsable de Movilidad', 'Expediente', 'DAAE', 'Remisión formal del expediente', 'ENVIADO_DAAE'), (9, 'Analizar documentación y asignar IES', 'ENVIADO_DAAE', 'ANTES', 'DAAE', 'DAAE', 'Expediente y opciones de IES', 'DAAE', 'Determinación de IES asignada', 'IES_ASIGNADA'), (10, 'Notificar por correo la IES destino asignada', 'POSTULACION_IES', 'ANTES', 'DAAE', 'DAAE', 'Correo de notificación', 'Alumno', 'Alumno informado de la asignación', 'IES_NOTIFICADA'), (11, 'Realizar la postulación ante la IES destino', 'POSTULACION_IES', 'ANTES', 'DAAE', 'DAAE', 'Expediente de postulación', 'IES destino', 'Postulación enviada', 'POSTULADO_IES'), (12, 'Analizar postulación y emitir Carta de Aceptación', 'POSTULACION_IES', 'ANTES', 'IES_DESTINO', 'IES destino', 'Carta de Aceptación', 'Alumno / DAAE', 'Recepción de aceptación', 'ACEPTADO_IES'), (13, 'Realizar trámite de visado, cuando corresponda', 'PREPARACION_MOVILIDAD', 'ANTES', 'ALUMNO', 'Alumno', 'Solicitud de visa', 'Autoridad consular', 'Trámite presentado', 'VISA_EN_TRAMITE'), (14, 'Recibir la visa correspondiente', 'PREPARACION_MOVILIDAD', 'ANTES', 'ALUMNO', 'Alumno', 'Visa', '—', 'Visa concedida cuando sea necesaria', 'VISA_OBTENIDA'), (15, 'Adquirir vuelos y seguro de gastos médicos', 'PREPARACION_MOVILIDAD', 'ANTES', 'ALUMNO', 'Alumno', 'Seguro y documentación de viaje', '—', 'Contar con condiciones para viajar', 'PREPARANDO_SALIDA'), (16, 'Asegurar registro en SICDE y trámite de exención de pago', 'PREPARACION_MOVILIDAD', 'ANTES', 'OTRO', 'Alumno / instancias universitarias', 'Registro y trámite administrativo', 'UAEMéx', 'Registro administrativo confirmado', 'LISTO_PARA_MOVILIDAD'), (17, 'Considerar el periodo de baja de materias de la IES destino y UAEMéx', 'EN_MOVILIDAD', 'DURANTE', 'ALUMNO', 'Alumno', 'En su caso, modificación de inscripción', 'IES destino / UAEMéx', 'Confirmar carga académica real', 'EN_MOVILIDAD'), (18, 'Enviar Carta de Condiciones Reales de Estudio y Formato de Inicio y Término de Movilidad', 'EN_MOVILIDAD', 'DURANTE', 'ALUMNO', 'Alumno', 'Ambos formatos en PDF', 'DAAE', 'Documentación recibida', 'CONDICIONES_REALES_REPORTADAS'), (19, 'Enviar Carta de Homologación de Condiciones Reales al Espacio Académico', 'EN_MOVILIDAD', 'DURANTE', 'DAAE', 'DAAE', 'Carta de Homologación de Condiciones Reales', 'Espacio Académico', 'Recepción institucional', 'HOMOLOGACION_REAL_RECIBIDA'), (20, 'Mantener contacto con la DAAE', 'EN_MOVILIDAD', 'DURANTE', 'ALUMNO', 'Alumno', 'Comunicaciones / seguimiento', 'DAAE', 'Seguimiento activo', 'EN_MOVILIDAD'), (21, 'Enviar o confirmar calificaciones y reporte de actividades', 'EN_MOVILIDAD', 'DURANTE', 'ALUMNO', 'Alumno', 'Calificaciones + reporte de actividades', 'DAAE', 'Documentación final de estancia entregada', 'MOVILIDAD_CONCLUIDA'), (22, 'Enviar constancia de calificaciones, reporte y formato de Homologación Definitiva', 'HOMOLOGACION', 'DESPUES', 'DAAE', 'DAAE', 'Calificaciones + reporte + formato', 'Espacio Académico', 'Documentación recibida', 'DOCUMENTACION_RETORNO'), (23, 'Elaborar Carta de Homologación Definitiva y recabar firma del estudiante', 'HOMOLOGACION', 'DESPUES', 'ESPACIO_ACADEMICO', 'Espacio Académico', 'Carta de Homologación Definitiva', 'Alumno', 'Carta elaborada y firmada', 'HOMOLOGACION_DEFINITIVA'), (24, 'Integrar expediente con calificaciones y Carta de Homologación Definitiva', 'HOMOLOGACION', 'DESPUES', 'ESPACIO_ACADEMICO', 'Espacio Académico', 'Expediente final', 'Espacio Académico', 'Expediente completo', 'EXPEDIENTE_FINAL_INTEGRADO'), (25, 'Proponer homologación ante los órganos colegiados', 'HOMOLOGACION', 'DESPUES', 'OTRO', 'Subdirección Académica', 'Propuesta y documentación académica', 'Consejos correspondientes', 'Resolución de los órganos colegiados', 'HOMOLOGACION_EN_DICTAMEN'), (26, 'Enviar resolución y documentación a Control Escolar', 'HOMOLOGACION', 'DESPUES', 'ESPACIO_ACADEMICO', 'Espacio Académico', 'Resolución + carta + calificaciones', 'Dirección de Control Escolar', 'Documentación remitida', 'EN_CONTROL_ESCOLAR'), (27, 'Entregar al estudiante el dictamen y copia de la Carta de Homologación Definitiva', 'CERRADO', 'DESPUES', 'ESPACIO_ACADEMICO', 'Espacio Académico', 'Dictamen + Carta de Homologación Definitiva', 'Alumno', 'Entrega registrada', 'CERRADO'))


class Command(BaseCommand):
    help = "Previsualiza o carga las 27 actividades de la matriz original de movilidad internacional."

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true", help="Inserta únicamente actividades ausentes en el catálogo")
        parser.add_argument("--sincronizar-expedientes", action="store_true", help="Añade asociaciones faltantes a expedientes existentes (requiere --aplicar)")

    def handle(self, *args, **options):
        if options["sincronizar_expedientes"] and not options["aplicar"]:
            raise CommandError("--sincronizar-expedientes requiere --aplicar")
        tipo = TipoMovilidad.objects.filter(nombre="Internacional saliente").first()
        if tipo is None:
            raise CommandError("No existe el tipo de movilidad Internacional saliente")
        self.stdout.write("MATRIZ ORIGINAL: 27 pasos de movilidad internacional. 9 estaciones funcionales.")
        for numero, nombre, estado, *_ in ACTIVIDADES:
            self.stdout.write(f"{numero:02d} | {estado} | {nombre}")
        if not options["aplicar"]:
            self.stdout.write(self.style.WARNING("Previsualización; no se modificó la base. Para insertar use --aplicar."))
            return
        nuevas = 0
        conservadas = 0
        asociaciones = 0
        with transaction.atomic():
            for numero, nombre, estado, etapa, responsable, responsable_original, evidencia, interviene, condicion, estado_original in ACTIVIDADES:
                descripcion = (f"Paso {numero} de 27 — Matriz institucional original.\n"
                               f"Responsable original: {responsable_original}\n"
                               f"Documento / evidencia: {evidencia}\n"
                               f"Quién recibe o interviene: {interviene}\n"
                               f"Condición para avanzar (matriz): {condicion}\n"
                               f"Estado propuesto originalmente: {estado_original}\n"
                               "Estación de Django: correspondencia funcional con matriz de nueve estados.\n"
                               "Obligatoriedad técnica: pendiente de parametrización por convocatoria.")
                actividad, creada = ActividadProceso.objects.get_or_create(
                    tipo_movilidad=tipo, nombre=nombre,
                    defaults={"descripcion": descripcion, "etapa": etapa,
                              "responsable": responsable, "obligatorio": False,
                              "orden": numero, "activo": True,
                              "estado_expediente": estado},
                )
                nuevas += int(creada)
                conservadas += int(not creada)
                if options["sincronizar_expedientes"] and actividad.activo:
                    for expediente in ExpedienteMovilidad.objects.filter(convocatoria__tipo_movilidad=tipo).iterator():
                        anterior_excepcional = (
                            expediente.tipo_alta == ExpedienteMovilidad.TipoAlta.EXCEPCIONAL
                            and ExpedienteMovilidad.ORDEN_ESTADOS.get(actividad.estado_expediente, 0)
                            < ExpedienteMovilidad.ORDEN_ESTADOS.get(expediente.estado_inicial, 0)
                        )
                        _, creada_asociacion = ActividadExpediente.objects.get_or_create(
                            expediente=expediente, actividad_proceso=actividad,
                            defaults={"estado": (ActividadExpediente.Estado.NO_REGISTRADA
                                                if anterior_excepcional else ActividadExpediente.Estado.PENDIENTE)},
                        )
                        asociaciones += int(creada_asociacion)
        self.stdout.write(self.style.SUCCESS(
            f"Resultado: {nuevas} nuevas, {conservadas} conservadas, {asociaciones} asociaciones nuevas."
        ))
