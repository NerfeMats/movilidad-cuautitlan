"""Importa PDF clasificados de un ZIP inventariado sin crear expedientes.

Simulación por defecto. Importa solo archivos del INVENTARIO.csv y omite el
escaneo original. No altera estados académicos. Requiere usuario staff autorizado.
"""
import csv
import hashlib
import io
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError

from expedientes.documentos_servicio import MAX_BYTES, importar_documento_historico
from expedientes.models import ExpedienteMovilidad


class Command(BaseCommand):
    help = "Audita/importa inventario CSV de documentos históricos (simulación predeterminada)."

    def add_arguments(self, parser):
        parser.add_argument("--expediente", type=int, required=True)
        parser.add_argument("--usuario", required=True)
        parser.add_argument("--zip", dest="archivo_zip", required=True)
        parser.add_argument("--aplicar", action="store_true")

    def handle(self, *args, **opciones):
        expediente = ExpedienteMovilidad.objects.filter(pk=opciones["expediente"]).first()
        if expediente is None:
            raise CommandError("Expediente inexistente")
        usuario = get_user_model().objects.filter(username=opciones["usuario"], is_active=True, is_staff=True).first()
        if usuario is None or not usuario.has_perm("expedientes.add_documentoexpediente"):
            raise CommandError("Usuario sin permiso administrativo documental")
        ruta = Path(opciones["archivo_zip"])
        if not ruta.is_file():
            raise CommandError("No se encuentra el ZIP")
        with ZipFile(ruta) as z:
            nombres = z.namelist()
            inventarios = [x for x in nombres if x.endswith("/INVENTARIO.csv")]
            if len(inventarios) != 1:
                raise CommandError("Se requiere exactamente un INVENTARIO.csv")
            origen = inventarios[0].rsplit("/", 1)[0] + "/"
            registros = list(csv.DictReader(io.StringIO(z.read(inventarios[0]).decode("utf-8-sig"))))
            if not registros or len(registros) > 200:
                raise CommandError("Inventario vacío o excesivo")
            verificados = []
            for fila in registros:
                rel = fila.get("archivo", "")
                partes = PurePosixPath(rel)
                if not rel or partes.is_absolute() or ".." in partes.parts or "\\" in rel:
                    raise CommandError("Ruta insegura en inventario")
                nombre_zip = origen + rel
                if nombre_zip not in nombres or nombre_zip.endswith("/"):
                    raise CommandError(f"Archivo no encontrado: {rel}")
                info = z.getinfo(nombre_zip)
                if info.file_size <= 0 or info.file_size > MAX_BYTES or Path(rel).suffix.lower() != ".pdf":
                    raise CommandError(f"PDF inválido o mayor a 10 MB: {rel}")
                datos = z.read(info)
                digest = hashlib.sha256(datos).hexdigest()
                if not datos.startswith(b"%PDF-") or digest != fila.get("sha256", "").lower():
                    raise CommandError(f"Firma o SHA256 incorrecto: {rel}")
                descripcion = fila.get("descripcion", "").strip() or Path(rel).stem
                observaciones = (
                    "Importación desde expediente físico digitalizado. "
                    f"Páginas en escaneo original: {fila.get('paginas_original', 'sin dato')}. "
                    f"Criterio de clasificación: {fila.get('observacion', '')}. "
                    f"SHA256: {digest}"
                )
                verificados.append((rel, datos, descripcion[:200], observaciones))
            self.stdout.write(f"Expediente: {expediente.pk} | Archivos verificados: {len(verificados)}")
            if not opciones["aplicar"]:
                for rel, _, _, _ in verificados:
                    self.stdout.write("SIMULACIÓN: " + rel)
                self.stdout.write("Sin modificaciones. Use --aplicar solo después de revisar expediente e inventario.")
                return
            creados = repetidos = 0
            for rel, datos, descripcion, observaciones in verificados:
                archivo = SimpleUploadedFile(Path(rel).name, datos, content_type="application/pdf")
                _, nuevo = importar_documento_historico(
                    usuario=usuario, expediente=expediente, archivo=archivo,
                    nombre=descripcion, observaciones=observaciones,
                )
                creados += bool(nuevo)
                repetidos += not nuevo
            self.stdout.write(self.style.SUCCESS(
                f"IMPORTACION TERMINADA | Nuevos: {creados} | Duplicados omitidos: {repetidos}"
            ))
