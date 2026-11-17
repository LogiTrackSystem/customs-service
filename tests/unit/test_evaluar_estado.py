"""Unitaria 1: events._evaluar_estado decide si una declaración se aprueba o se retiene."""
from app import events


def test_evaluar_estado_aprueba_ruta_normal_y_retiene_pais_restringido():
    assert events._evaluar_estado("Colombia", "Ecuador") == ("aprobado", None)
    estado, motivo = events._evaluar_estado("Colombia", " CUBA ")
    assert estado == "retenido" and "revisión aduanera" in motivo
