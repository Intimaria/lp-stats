from app.busqueda import formatear_tipo_badge

def test_badge_contrato():
    assert "Contrato" in formatear_tipo_badge("Contrato")

def test_badge_inmueble():
    assert "Inmueble" in formatear_tipo_badge("Inmueble")

def test_badge_decreto():
    assert "Decreto" in formatear_tipo_badge("Decreto")

def test_badge_desconocido():
    result = formatear_tipo_badge("Otro")
    assert isinstance(result, str)
