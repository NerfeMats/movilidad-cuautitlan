"""Presentación de documentos agrupados, sin modificar estados ni datos."""
from django import template

register = template.Library()


@register.filter
def documentos_aprobados(documentos):
    return [d for d in documentos if d.estado == "APROBADO"]


@register.filter
def documentos_pendientes(documentos):
    return [d for d in documentos if d.estado in ("CARGADO", "EN_REVISION")]


@register.filter
def documentos_correccion(documentos):
    return [d for d in documentos if d.estado in ("REQUIERE_CORRECCION", "RECHAZADO")]
