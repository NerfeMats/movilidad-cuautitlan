"""Servicio documental fase 15A. Sin URLs públicas ni cambios de esquema.

Los nuevos archivos se guardan fuera de MEDIA_ROOT. La interfaz HTTP y las
políticas de retención/versionado se implementarán después de auditar permisos.
"""
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.utils.text import get_valid_filename

from .models import ActividadExpediente, DocumentoExpediente, ExpedienteMovilidad, HistorialExpediente

MAX_BYTES = 10 * 1024 * 1024
MAGIAS = {
    ".pdf": lambda b: b.startswith(b"%PDF-"),
    ".png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    ".jpg": lambda b: b.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
}
PREFIJO = "privado/"


def almacenamiento_privado():
    destino = (Path(settings.BASE_DIR) / "documentos_privados").resolve()
    media = Path(settings.MEDIA_ROOT).resolve()
    if destino == media or media in destino.parents or destino in media.parents:
        raise ValidationError("El repositorio privado debe estar separado de MEDIA_ROOT")
    return FileSystemStorage(location=str(destino), base_url=None)


def _autenticado(usuario):
    if not getattr(usuario, "is_authenticated", False) or not getattr(usuario, "is_active", False):
        raise PermissionDenied("Debe iniciar sesión")


def _puede_ver(usuario, expediente):
    _autenticado(usuario)
    if expediente.alumno_id == usuario.pk:
        return True
    return bool(usuario.is_staff and usuario.has_perm("expedientes.view_documentoexpediente"))


def _puede_modificar(usuario, expediente, permiso):
    _autenticado(usuario)
    return bool(usuario.is_staff and usuario.has_perm(f"expedientes.{permiso}_documentoexpediente"))


def _validar_archivo(archivo):
    nombre = getattr(archivo, "name", "") or ""
    sufijo = Path(nombre).suffix.lower()
    if sufijo not in MAGIAS:
        raise ValidationError("Solo se admiten PDF, PNG y JPEG")
    tamano = getattr(archivo, "size", None)
    if tamano is None or tamano <= 0 or tamano > MAX_BYTES:
        raise ValidationError("El archivo debe tener entre 1 byte y 10 MB")
    posicion = archivo.tell() if hasattr(archivo, "tell") else None
    cabecera = archivo.read(16)
    if posicion is not None:
        archivo.seek(posicion)
    if not MAGIAS[sufijo](cabecera):
        raise ValidationError("La firma del archivo no corresponde a su extensión")
    return sufijo


def cargar_documento(*, usuario, actividad, archivo, nombre):
    """Carga en almacenamiento privado y registra auditoría de la operación.

    Alumno: solo su expediente, estación actual y actividad a cargo del alumno.
    Responsable: permiso explícito de alta y estación actual.
    No marca actividades como completadas ni aprueba documentos.
    """
    if not isinstance(actividad, ActividadExpediente) or not actividad.pk:
        raise ValidationError("Actividad de expediente no válida")
    actividad = ActividadExpediente.objects.select_related("expediente", "actividad_proceso").get(pk=actividad.pk)
    expediente = actividad.expediente
    _autenticado(usuario)
    es_alumno = usuario.pk == expediente.alumno_id
    if not es_alumno and not _puede_modificar(usuario, expediente, "add"):
        raise PermissionDenied("Sin permiso para aportar documentos")
    if actividad.estado == ActividadExpediente.Estado.COMPLETADA:
        raise ValidationError("La actividad completada está en modo de consulta")
    if actividad.actividad_proceso.estado_expediente != expediente.estado:
        raise ValidationError("Solo se pueden aportar documentos a la estación actual")
    if es_alumno and actividad.actividad_proceso.responsable != "ALUMNO":
        raise PermissionDenied("La actividad corresponde a otra área")
    nombre = (nombre or "").strip()
    if not nombre or len(nombre) > 200:
        raise ValidationError("Indique un nombre de documento de hasta 200 caracteres")
    sufijo = _validar_archivo(archivo)
    # Almacenar SOLO el nombre base original, nunca rutas del cliente ni el UUID privado.
    nombre_original = Path(str(archivo.name).replace("\\", "/")).name.strip()[:255]
    archivo.seek(0)
    storage = almacenamiento_privado()
    ruta = f"{expediente.pk}/{actividad.pk}/{uuid4().hex}{sufijo}"
    guardado = None
    try:
        guardado = storage.save(ruta, archivo)
        with transaction.atomic():
            documento = DocumentoExpediente.objects.create(
                expediente=expediente, actividad=actividad, nombre=nombre,
                archivo=PREFIJO + guardado, estado=DocumentoExpediente.Estado.CARGADO,
                version=1, nombre_archivo_original=nombre_original,
            )
            HistorialExpediente.objects.create(
                expediente=expediente, usuario=usuario,
                accion="DOCUMENTO_CARGADO",
                descripcion=f"Documento {documento.pk} adjuntado a actividad {actividad.pk}",
                estado_anterior=expediente.estado, estado_nuevo=expediente.estado,
            )
        return documento
    except Exception:
        if guardado and storage.exists(guardado):
            storage.delete(guardado)
        raise


def documentos_de_actividad(*, usuario, actividad):
    actividad = ActividadExpediente.objects.select_related("expediente").get(pk=actividad.pk)
    if not _puede_ver(usuario, actividad.expediente):
        raise PermissionDenied("Sin permiso de consulta")
    return DocumentoExpediente.objects.filter(expediente=actividad.expediente, actividad=actividad)


def abrir_documento(*, usuario, documento):
    """Devuelve archivo abierto; el llamador debe cerrarlo. Nunca publica URL."""
    doc = DocumentoExpediente.objects.select_related("expediente").get(pk=documento.pk)
    if not _puede_ver(usuario, doc.expediente):
        raise PermissionDenied("Sin permiso de descarga")
    nombre = doc.archivo.name
    if not nombre.startswith(PREFIJO):
        raise ValidationError("Documento anterior: requiere migración a almacenamiento privado")
    relativa = nombre[len(PREFIJO):]
    partes = Path(relativa).parts
    if not relativa or Path(relativa).is_absolute() or ".." in partes or len(partes) != 3:
        raise ValidationError("Ruta de documento inválida")
    if partes[0] != str(doc.expediente_id) or (doc.actividad_id and partes[1] != str(doc.actividad_id)):
        raise ValidationError("La ruta no corresponde al expediente")
    return almacenamiento_privado().open(relativa, "rb")


def revisar_documento(*, usuario, documento, aprobar, observaciones):
    """Solo responsable autorizado. Registra cambio, pero no completa actividad."""
    _autenticado(usuario)
    if not isinstance(aprobar, bool):
        raise ValidationError("Debe indicar aprobación o rechazo")
    observaciones = (observaciones or "").strip()
    if not aprobar and not observaciones:
        raise ValidationError("El rechazo requiere observaciones")
    with transaction.atomic():
        doc = DocumentoExpediente.objects.select_for_update().select_related("expediente").get(pk=documento.pk)
        if not _puede_modificar(usuario, doc.expediente, "change"):
            raise PermissionDenied("Sin permiso de revisión")
        if not doc.archivo.name.startswith(PREFIJO):
            raise ValidationError("El documento anterior requiere migración segura")
        if doc.estado not in (DocumentoExpediente.Estado.CARGADO, DocumentoExpediente.Estado.EN_REVISION):
            raise ValidationError("El documento ya fue dictaminado")
        anterior = doc.estado
        doc.estado = DocumentoExpediente.Estado.APROBADO if aprobar else DocumentoExpediente.Estado.REQUIERE_CORRECCION
        doc.observaciones = observaciones
        doc.save(update_fields=["estado", "observaciones"])
        HistorialExpediente.objects.create(
            expediente=doc.expediente, usuario=usuario,
            accion="DOCUMENTO_APROBADO" if aprobar else "DOCUMENTO_REQUIERE_CORRECCION",
            descripcion=f"Documento {doc.pk}; estado {anterior} a {doc.estado}; observaciones: {observaciones}",
            estado_anterior=doc.expediente.estado, estado_nuevo=doc.expediente.estado,
        )
        return doc
