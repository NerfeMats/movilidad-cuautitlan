"""Pruebas de enrutamiento, CSRF, vistas HTTP y plantillas del paso 15B."""
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http import FileResponse
from django.template.loader import get_template
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve, reverse

from . import documentos_web


class DocumentoWebTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_rutas_nombres(self):
        for nombre, args in (("documento_cargar", [1]), ("documento_descargar", [2]), ("documento_revisar", [3])):
            self.assertTrue(reverse("expedientes:" + nombre, args=args))
            self.assertTrue(resolve(reverse("expedientes:" + nombre, args=args)))

    def test_vistas_requieren_autenticacion(self):
        casos = (
            ("get", "documento_descargar", [4]),
            ("post", "documento_cargar", [5]),
            ("post", "documento_revisar", [6]),
        )
        for metodo, nombre, args in casos:
            url = reverse("expedientes:" + nombre, args=args)
            peticion = getattr(self.factory, metodo)(url)
            peticion.user = AnonymousUser()
            respuesta = resolve(url).func(peticion, *args)
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn("login", respuesta["Location"])

    def test_carga_requiere_post(self):
        req = self.factory.get("/expedientes/documentos/actividad/1/cargar/")
        req.user = SimpleNamespace(is_authenticated=True)
        res = documentos_web.cargar_documento_web(req, 1)
        self.assertEqual(res.status_code, 405)

    def test_revision_requiere_post(self):
        req = self.factory.get("/expedientes/documentos/1/revisar/")
        req.user = SimpleNamespace(is_authenticated=True)
        res = documentos_web.revisar_documento_web(req, 1)
        self.assertEqual(res.status_code, 405)

    def test_descarga_no_usa_urls_publicas_y_evitar_cache(self):
        req = self.factory.get("/expedientes/documentos/1/descargar/")
        req.user = SimpleNamespace(is_authenticated=True)
        doc = SimpleNamespace(nombre="Carta de aceptación", archivo=SimpleNamespace(name="privado/1/2/abc.pdf"))
        with patch.object(documentos_web, "get_object_or_404", return_value=doc), patch.object(
            documentos_web, "abrir_documento", return_value=BytesIO(b"%PDF-1.4")
        ):
            res = documentos_web.descargar_documento_web(req, 1)
        self.assertIsInstance(res, FileResponse)
        self.assertEqual(res["Cache-Control"], "private, no-store")
        self.assertEqual(res["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment", res["Content-Disposition"])
        res.close()

    def test_plantillas_compilan(self):
        get_template("expedientes/detalle_expediente.html")
        get_template("expedientes/ruta_responsable.html")

    def test_plantillas_tienen_csrf_y_formularios(self):
        for archivo in ("detalle_expediente.html", "ruta_responsable.html"):
            template = get_template("expedientes/" + archivo)
            self.assertIsNotNone(template)
        self.assertEqual(documentos_web.cargar_documento_web.__name__, "cargar_documento_web")
