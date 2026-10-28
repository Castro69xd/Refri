TONOS = ["normal", "divertido", "chef elegante", "para niños"]
IDIOMAS = ["español", "inglés", "español salvadoreño"]

def get_style(tono, idioma, minutos):
    t = tono if tono in TONOS else "normal"
    i = idioma if idioma in IDIOMAS else "español"
    try:
        m = int(minutos)
    except:
        m = 30
    if m < 10: m = 10
    if m > 60: m = 60
    bloque = f"Estilo pedido: tono = {t}; idioma = {i}; tiempo máximo por receta = {m} minutos.\nEscribe los valores de texto (nombre, pasos, consejo, etc.) en el idioma elegido y con el tono elegido. Si el idioma es 'español salvadoreño', usa expresiones naturales de El Salvador sin exagerar ni ofender. Tono 'para niños': simple y con cuidado de seguridad en cocina. Cada receta debe durar tiempo_min <= {m}. IMPORTANTE: los NOMBRES de los campos del JSON (nombre, emoji, tiempo_min, dificultad, ingredientes_que_tienes, ingredientes_que_faltan, pasos, consejo) NO se traducen nunca; solo cambian los valores. El campo dificultad sigue siendo 'fácil' o 'media'."
    return t,i,m,bloque

# pruebas
print(get_style(None,None,None))
print(get_style("raro","otro",5))
print(get_style("divertido","inglés",45))
print(get_style("para niños","español salvadoreño",20))
