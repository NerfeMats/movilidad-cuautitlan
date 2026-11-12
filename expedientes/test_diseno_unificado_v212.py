"""No cambia registros: contratos de navegacion y separacion de pantallas."""
from pathlib import Path
from django.test import SimpleTestCase
from django.urls import reverse
from django.template.loader import get_template
ROOT = Path(__file__).resolve().parent
class DisenoUnificadoV212Tests(SimpleTestCase):
    def test_sin_permiso_no_puede_abrir_estudiantes(self):
        from types import SimpleNamespace
        from django.test import RequestFactory
        from django.core.exceptions import PermissionDenied
        from expedientes.panel_responsable import estudiantes_responsable
        usuario=SimpleNamespace(is_authenticated=True,is_staff=False,has_perm=lambda *_:False)
        solicitud=RequestFactory().get('/expedientes/responsable/estudiantes/')
        solicitud.user=usuario
        with self.assertRaises(PermissionDenied):
            estudiantes_responsable(solicitud)
    def test_ruta_independiente_estudiantes(self):
        self.assertEqual(reverse('expedientes:estudiantes_responsable'), '/expedientes/responsable/estudiantes/')
    def test_menu_no_se_desplaza_por_ancla(self):
        fuente=(ROOT/'templates/expedientes/base_responsable.html').read_text(encoding='utf-8')
        self.assertIn("{% url 'expedientes:estudiantes_responsable' %}",fuente)
        self.assertNotIn('#estudiantes',fuente)
    def test_plantillas_administrativas(self):
        for nombre in ('estudiantes_responsable','centro_seguimiento','inventario_documental'):
            get_template('expedientes/'+nombre+'.html')
    def test_tema_usa_tokens_institucionales(self):
        css=(ROOT/'static/expedientes/centro_gestion_v212.css').read_text(encoding='utf-8')
        self.assertIn('var(--ui-accent',css)
        self.assertIn('position:sticky',css)
    def test_no_reintroduce_documentos_historicos_en_recorrido(self):
        html=(ROOT/'templates/expedientes/ruta_responsable.html').read_text(encoding='utf-8')
        self.assertNotIn('for documento in documentos_historicos',html)
