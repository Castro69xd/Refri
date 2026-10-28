import asyncio
import base64
import re
import traceback
import json
import urllib.parse
import flet as ft
from ia import ia
from multimedia import pcm_a_wav, ia_media

CIAN = ft.Colors.CYAN_ACCENT_400
MAX_CARACTERES = 500
TONOS_OPCIONES = ["normal", "divertido", "chef elegante", "para niños"]
IDIOMAS_OPCIONES = ["español", "inglés", "español salvadoreño"]

# Instrucciones
INSTRUCCION_BASE = ('Responde SOLO JSON con esta forma: '
                    '{"recetas":[{"nombre":"","emoji":"","tiempo_min":0,"dificultad":"fácil","ingredientes_que_tienes":[""],"ingredientes_que_faltan":[""],"pasos":[""],"consejo":""}]}. '
                    'Con los ingredientes que tiene el usuario, propone 3 recetas salvadoreñas rápidas. '
                    'Usa el historial para dar continuidad: si el pedido nuevo hace referencia a algo anterior (ahora, también, otra, distinta, sin eso), respétalo. '
                    'No repitas recetas que ya diste, a menos que lo pidan. Mantén el mismo formato JSON de siempre. '
                    'emoji = un solo emoji de la receta; tiempo_min = número entero; dificultad = "fácil" o "media"; '
                    'ingredientes_que_faltan = máximo 3 ingredientes comunes que no mencionó (puede ser lista vacía); '
                    'pasos = máximo 4 pasos cortos; consejo = una frase corta. '
                    'Puede asumir sal, aceite y agua. Si el usuario marcó "Sin horno", no usar horno. '
                    'Estilo pedido: tono = {tono}; idioma = {idioma}; tiempo máximo por receta = {minutos} minutos. '
                    "Escribe los valores de texto (nombre, pasos, consejo, etc.) en el idioma elegido y con el tono elegido. Si el idioma es 'español salvadoreño', usa expresiones naturales de El Salvador sin exagerar ni ofender. Tono 'para niños': simple y con cuidado de seguridad en cocina. Cada receta debe durar tiempo_min <= {minutos}. IMPORTANTE: los NOMBRES de los campos del JSON (nombre, emoji, tiempo_min, dificultad, ingredientes_que_tienes, ingredientes_que_faltan, pasos, consejo) NO se traducen nunca; solo cambian los valores. El campo dificultad sigue siendo 'fácil' o 'media'.")

INSTRUCCION_TRANSCRIBE = "Transcribe este audio en español. Responde SOLO con el texto dicho, sin comillas ni comentarios."
INSTRUCCION_FOTO = "Mira la foto e identifica los alimentos e ingredientes que se ven. Responde SOLO con una lista separada por comas, en español, sin comentarios. Si no hay alimentos visibles, responde exactamente: NINGUNO."
INSTRUCCION_TEXTO = "Del siguiente texto, extrae los alimentos e ingredientes que menciona. Responde SOLO con una lista separada por comas, en español, sin comentarios. Si no hay alimentos, responde exactamente: NINGUNO."
INSTRUCCION_LEER_FOTO_TEXTO = "Lee TODO el texto que aparece en esta imagen y transcríbelo tal cual, en el idioma original, respetando los saltos de línea. No agregues comentarios ni explicaciones. Si no hay texto legible, responde exactamente: SIN_TEXTO."
INSTRUCCION_EXTRAER_ING = "Del siguiente texto, extrae solo los alimentos e ingredientes. Responde SOLO con una lista separada por comas, en español, sin cantidades ni precios. Si no hay alimentos, responde exactamente: NINGUNO."

# Audio recorder
try:
    from flet_audio_recorder import AudioRecorder, AudioRecorderConfiguration, AudioEncoder
except Exception:
    try:
        import flet_audio_recorder as far
        AudioRecorder = getattr(far, "AudioRecorder")
        AudioRecorderConfiguration = getattr(far, "AudioRecorderConfiguration")
        AudioEncoder = getattr(far, "AudioEncoder")
    except Exception:
        AudioRecorder = None
        AudioRecorderConfiguration = None
        AudioEncoder = None


def validar_entrada(texto):
    if texto is None:
        return False, "Escribe qué tienes en casa primero"
    t = str(texto).strip()
    if not t:
        return False, "Escribe qué tienes en casa primero"
    if len(t) > MAX_CARACTERES:
        return False, f"Muy largo: máximo {MAX_CARACTERES} caracteres (llevas {len(t)})"
    if not re.search(r'[A-Za-zÁÉÍÓÚáéíóúÑñ]', t):
        return False, "Escribe ingredientes con palabras"
    return True, ""


def normalizar_receta(r):
    try:
        if not isinstance(r, dict):
            return []
        recetas_raw = r.get("recetas")
        if not isinstance(recetas_raw, list) or len(recetas_raw) == 0:
            return []
        resultado = []
        for item in recetas_raw:
            if not isinstance(item, dict):
                continue
            nombre = item.get("nombre") or "Receta sin nombre"
            emoji = item.get("emoji") or "🍽"
            if not isinstance(emoji, str) or len(emoji.strip()) == 0:
                emoji = "🍽"
            else:
                emoji = emoji.strip()
            tm = item.get("tiempo_min", 0)
            try:
                if isinstance(tm, str):
                    m = re.findall(r'-?\d+', tm)
                    tm = int(m[0]) if m else 0
                else:
                    tm = int(tm)
            except Exception:
                tm = 0
            dificultad = item.get("dificultad") or "media"
            if dificultad not in ["fácil", "media"]:
                dificultad = "media"
            def _to_list(x):
                if x is None:
                    return []
                if isinstance(x, list):
                    out = []
                    for it in x:
                        if isinstance(it, str) and it.strip():
                            out.append(it.strip())
                    return out
                if isinstance(x, str):
                    s = x.strip()
                    if not s:
                        return []
                    parts = re.split(r'[\n,;]+', s)
                    out = []
                    for it in parts:
                        it2 = it.strip()
                        if it2:
                            out.append(it2)
                    return out
                return []
            ing_t = _to_list(item.get("ingredientes_que_tienes"))
            ing_f = _to_list(item.get("ingredientes_que_faltan"))
            if len(ing_f) > 3:
                ing_f = ing_f[:3]
            pasos = _to_list(item.get("pasos"))
            if len(pasos) > 4:
                pasos = pasos[:4]
            consejo = item.get("consejo") or ""
            if not isinstance(consejo, str):
                consejo = str(consejo)
            resultado.append({
                "nombre": str(nombre),
                "emoji": emoji,
                "tiempo_min": tm,
                "dificultad": dificultad,
                "ingredientes_que_tienes": ing_t,
                "ingredientes_que_faltan": ing_f,
                "pasos": pasos,
                "consejo": consejo.strip()
            })
            if len(resultado) >= 3:
                break
        return resultado
    except Exception:
        traceback.print_exc()
        return []


def texto_resultado(recetas, pedido="", tono=""):
    lineas = []
    lineas.append("🍳 Cocinero de refri")
    if pedido:
        lineas.append(f"Pedido: {pedido}")
    if tono:
        lineas.append(f"Tono: {tono}")
    lineas.append("")
    total_min = 0
    for i, r in enumerate(recetas, 1):
        nombre = r.get("nombre", "")
        emoji = r.get("emoji", "🍽")
        try:
            tm = int(r.get("tiempo_min", 0))
        except Exception:
            tm = 0
        total_min += tm
        diff = r.get("dificultad", "")
        lineas.append(f"{i}) {emoji} {nombre} — {tm} min · {diff}")
        ing_t = r.get("ingredientes_que_tienes", []) or []
        if ing_t:
            lineas.append(f"Ya tienes: {', '.join([str(x) for x in ing_t])}")
        else:
            lineas.append("Ya tienes: ")
        ing_f = r.get("ingredientes_que_faltan", []) or []
        if not ing_f:
            lineas.append("Te falta: nada")
        else:
            lineas.append(f"Te falta: {', '.join([str(x) for x in ing_f])}")
        lineas.append("Pasos:")
        pasos = r.get("pasos", []) or []
        for j, p in enumerate(pasos, 1):
            lineas.append(f"{j}. {p}")
        conse = r.get("consejo", "")
        if conse:
            lineas.append(f"Consejo: {conse}")
        lineas.append("")
    lineas.append(f"⏱ Tiempo total sumado: {total_min} min")
    lineas.append("Hecho con AppLab IA")
    return "\n".join(lineas)


def texto_para_voz(recetas):
    partes = []
    try:
        for i, r in enumerate(recetas, 1):
            nombre = r.get("nombre", "")
            try:
                tm = int(r.get("tiempo_min", 0))
            except Exception:
                tm = 0
            diff = r.get("dificultad", "")
            partes.append(f"Receta {i}: {nombre}. Tarda {tm} minutos y es {diff}.")
            ing_t = r.get("ingredientes_que_tienes", []) or []
            if ing_t:
                partes.append(f"Ya tienes: {', '.join([str(x) for x in ing_t])}.")
            else:
                partes.append("Ya tienes: nada.")
            ing_f = r.get("ingredientes_que_faltan", []) or []
            if ing_f:
                partes.append(f"Te falta: {', '.join([str(x) for x in ing_f])}.")
            else:
                partes.append("No te falta nada.")
            pasos = r.get("pasos", []) or []
            for j, p in enumerate(pasos, 1):
                partes.append(f"Paso {j}: {p}.")
            conse = r.get("consejo", "")
            if conse:
                partes.append(f"Consejo: {conse}.")
        total = 0
        for r in recetas:
            try:
                total += int(r.get("tiempo_min", 0))
            except Exception:
                pass
        partes.append(f"Tiempo total: {total} minutos.")
        texto = " ".join(partes)
        # quitar emojis
        texto = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\u2600-\u26FF\u2700-\u27BF]+', '', texto)
        # quitar símbolos raros comunes
        texto = texto.replace("—", "-").replace("·", ",").replace("⏱", "").replace("🍳", "").replace("🧡", "").replace("✅", "").replace("🛒", "").replace("👩‍🍳", "").replace("💡", "").replace("🧠", "").replace("🔊", "").replace("⏹", "").replace("📋", "").replace("📤", "")
        return texto
    except Exception:
        traceback.print_exc()
        return ""


def tarjeta(receta):
    pasos = [ft.Text(f"{i}. {p}") for i, p in enumerate(receta.get("pasos", []), start=1)]
    ingredientes = ", ".join(str(x) for x in receta.get("ingredientes", []))
    return ft.Container(
        padding=14, border_radius=12, bgcolor=ft.Colors.with_opacity(0.08, CIAN),
        content=ft.Column([
            ft.Text(f"🍳 {receta.get('nombre', 'Receta')}", size=18,
                    weight=ft.FontWeight.BOLD, color=CIAN),
            ft.Text(f"⏱ {receta.get('tiempo_min', '?')} min"),
            ft.Text(f"Ingredientes: {ingredientes}"),
            *pasos,
        ], spacing=4))


def vista(page=None):
    entrada = ft.TextField(label="¿Qué tienes en el refri?", hint_text="arroz, huevo, tomate",
                           border_color=CIAN, max_length=MAX_CARACTERES)
    sin_horno = ft.Checkbox(label="Sin horno", value=False)
    resultado = ft.Column(spacing=10)
    boton = ft.Button("Cocinar ideas")
    boton_hablar = ft.Button("🎤 Hablar")
    boton_foto = ft.Button("📷 Foto")
    boton_txt = ft.Button("📄 Archivo .txt")
    boton_leer_foto = ft.Button("🧾 Leer texto de foto")
    aviso_priv = ft.Text("No subas fotos de personas ni datos personales (teléfono, DUI, tarjetas, contraseñas)", size=12, color=ft.Colors.GREY_400)
    preview = ft.Container(visible=False)
    preview_ocr = ft.Container(visible=False)

    progress_ring = ft.ProgressRing(visible=False)
    progreso_texto = ft.Text("", visible=False)
    progreso_row = ft.Row([progress_ring, progreso_texto], visible=False)

    texto_largo = ft.TextField(label="O pega aquí un texto largo", multiline=True, min_lines=4, max_lines=8)
    boton_leer = ft.Button("Leer texto")

    # Selectores de estilo
    try:
        tono_dropdown = ft.Dropdown(label="🎭 Tono", options=[ft.dropdown.Option(t) for t in TONOS_OPCIONES], value="normal")
    except Exception:
        try:
            tono_dropdown = ft.Dropdown(label="🎭 Tono", options=[ft.DropdownOption(t) for t in TONOS_OPCIONES], value="normal")
        except Exception:
            tono_dropdown = ft.Dropdown(label="🎭 Tono", options=TONOS_OPCIONES, value="normal")
    try:
        idioma_dropdown = ft.Dropdown(label="🌎 Idioma", options=[ft.dropdown.Option(t) for t in IDIOMAS_OPCIONES], value="español")
    except Exception:
        try:
            idioma_dropdown = ft.Dropdown(label="🌎 Idioma", options=[ft.DropdownOption(t) for t in IDIOMAS_OPCIONES], value="español")
        except Exception:
            idioma_dropdown = ft.Dropdown(label="🌎 Idioma", options=IDIOMAS_OPCIONES, value="español")
    try:
        tiempo_slider = ft.Slider(min=10, max=60, divisions=5, value=30, label="{value} min")
    except Exception:
        tiempo_slider = ft.Slider(min=10, max=60, divisions=5, value=30)

    # Acciones copiar/compartir
    clipboard_service = None
    share_service = None
    try:
        if page is not None:
            if getattr(page, "services", None) is None:
                page.services = []
            # clipboard
            try:
                clipboard_service = ft.Clipboard()
                if clipboard_service not in page.services:
                    page.services.append(clipboard_service)
            except Exception:
                traceback.print_exc()
                clipboard_service = None
            # share
            try:
                share_service = getattr(ft, "Share", None)
                if share_service is not None:
                    share_service = share_service()
                    if share_service not in page.services:
                        page.services.append(share_service)
            except Exception:
                traceback.print_exc()
                share_service = None
    except Exception:
        traceback.print_exc()

    ultimo_texto_copiar = ""
    ultimo_recetas_norm = []
    ultimo_pedido = ""
    ultimo_tono = ""
    ultimo_idioma = ""
    ultimo_minutos = 30

    fila_acciones = ft.Row(visible=False)
    expansion_copiar = ft.ExpansionTile(title=ft.Text("Ver texto para copiar"), controls=[ft.Text(selectable=True)], initially_expanded=False, visible=False)
    snack_text = ft.Text("")

    def poner_ocupado(ocupado_flag, mensaje=""):
        nonlocal ocupado
        ocupado = ocupado_flag
        boton.disabled = ocupado_flag
        boton_hablar.disabled = ocupado_flag
        boton_foto.disabled = ocupado_flag
        boton_txt.disabled = ocupado_flag
        boton_leer_foto.disabled = ocupado_flag
        boton_leer.disabled = ocupado_flag
        tono_dropdown.disabled = ocupado_flag
        idioma_dropdown.disabled = ocupado_flag
        tiempo_slider.disabled = ocupado_flag
        sin_horno.disabled = ocupado_flag
        if ocupado_flag and mensaje:
            progress_ring.visible = True
            progreso_texto.value = mensaje
            progreso_texto.visible = True
            progreso_row.visible = True
        else:
            progress_ring.visible = False
            progreso_texto.value = ""
            progreso_texto.visible = False
            progreso_row.visible = False
        try:
            for c in [boton, boton_hablar, boton_foto, boton_txt, boton_leer_foto, boton_leer, tono_dropdown, idioma_dropdown, tiempo_slider, sin_horno, progress_ring, progreso_texto, progreso_row]:
                try:
                    c.update()
                except Exception:
                    pass
        except Exception:
            pass
        if page is not None:
            try:
                page.update()
            except Exception:
                pass

    ocupado = False
    return ft.Column([
        entrada,
        sin_horno,
        ft.Row([boton, boton_hablar, boton_foto, boton_txt, boton_leer_foto], wrap=True),
        ft.Row([tono_dropdown, idioma_dropdown, tiempo_slider], wrap=True),
        aviso_priv,
        progress_ring,
        progreso_texto,
        resultado,
    ])
