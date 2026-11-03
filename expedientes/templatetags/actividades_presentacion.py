"""Presentación del catálogo heredado. No cambia los datos almacenados."""
from django import template

register = template.Library()

@register.filter(name="evidencia_actividad")
def evidencia_actividad(descripcion):
    """Extrae únicamente la evidencia de la matriz; oculta sus notas técnicas.

    Las descripciones que no proceden de la matriz se muestran completas.
    """
    if not descripcion:
        return ""
    texto = str(descripcion).strip()
    if not texto.startswith("Paso ") or "Matriz institucional original." not in texto:
        return texto
    for linea in texto.splitlines():
        clave, sep, valor = linea.partition(":")
        if sep and clave.strip().casefold() == "documento / evidencia":
            evidencia = valor.strip()
            if evidencia.casefold() in {"—", "-", "no necesariamente documento", "ninguno", "sin evidencia"}:
                return ""
            return evidencia
    return ""
