import asyncio
import flet as ft
from ia import ia
from multimedia import pcm_a_wav, ia_media

CIAN = ft.Colors.CYAN_ACCENT_400

# Instrucción base para la IA: pide JSON con 3 recetas salvadoreñas rápidas
INSTRUCCION_BASE = ('Responde SOLO JSON con esta forma: '
                    '{"recetas":[{"nombre":"","tiempo_min":0,"ingredientes":[""],"pasos":[""]}]}. '
                    'Con los ingredientes que tiene el usuario, propone 3 recetas salvadoreñas rápidas. '
                    'Cada receta con máximo 4 pasos cortos. tiempo_min es un número entero. '
                    'Puedes asumir sal, aceite y agua.')

INSTRUCCION_TRANSCRIBE = "Transcribe este audio en español. Responde SOLO con el texto dicho, sin comillas ni comentarios."

# Intentamos importar la API de flet-audio-recorder según la versión 0.86.5
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


def tarjeta(receta):
    """Arma una tarjeta con una receta."""
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
                           border_color=CIAN)
    sin_horno = ft.Checkbox(label="Sin horno", value=False)
    resultado = ft.Column(spacing=10)
    boton = ft.Button("Cocinar ideas")
    boton_hablar = ft.Button("🎤 Hablar")

    # Audio recorder setup (una sola vez por page)
    recorder = None
    if AudioRecorder is not None and getattr(page, "services", None) is not None:
        try:
            recorder = AudioRecorder()
            if recorder not in page.services:
                page.services.append(recorder)
        except Exception:
            recorder = None

    audio_chunks = []
    grabando = False

    async def _detener_y_transcribir():
        nonlocal grabando
        grabando = False
        boton_hablar.disabled = True
        boton_hablar.text = "🎤 Hablar"
        boton_hablar.update()
        boton.disabled = True
        boton.update()
        sin_horno.disabled = True
        sin_horno.update()
        resultado.controls = [ft.ProgressRing(), ft.Text("⏳ Transcribiendo…")]
        resultado.update()
        try:
            if not audio_chunks:
                resultado.controls = [ft.Text("No te entendí, intenta de nuevo.")]
            else:
                pcm = b"".join(audio_chunks)
                wav = pcm_a_wav(pcm, tasa=16000, canales=1)
                # Transcribir con ia_media
                texto_transcrito = await asyncio.to_thread(ia_media, INSTRUCCION_TRANSCRIBE, wav, "audio/wav", "", False)
                texto_transcrito = (texto_transcrito or "").strip()
                if not texto_transcrito:
                    resultado.controls = [ft.Text("No te entendí, intenta de nuevo.")]
                elif len(texto_transcrito) > 300:
                    texto_transcrito = texto_transcrito[:300]
                    entrada.value = texto_transcrito
                    entrada.update()
                    resultado.controls = [ft.Text("Texto recortado a 300 caracteres.")]
                else:
                    entrada.value = texto_transcrito
                    entrada.update()
                    resultado.controls = []
                    # Generar recetas con lo transcrito
                    await generar_recetas(texto_transcrito)
        except Exception as ex:
            resultado.controls = [ft.Text("No se pudo transcribir el audio. Intenta de nuevo o escribe directamente.")]
        finally:
            audio_chunks.clear()
            boton_hablar.disabled = False
            boton_hablar.update()
            boton.disabled = False
            boton.update()
            sin_horno.disabled = False
            sin_horno.update()
            page.update()

    async def _auto_stop():
        # Detener a los 30 segundos
        await asyncio.sleep(30)
        if grabando and recorder is not None:
            try:
                await recorder.stop_recording()
            except Exception:
                pass
            await _detener_y_transcribir()

    def _on_stream(e):
        # Guardar trozos
        try:
            chunk = getattr(e, "chunk", None)
            if chunk is None and hasattr(e, "data"):
                chunk = e.data
            if chunk is not None:
                audio_chunks.append(bytes(chunk))
        except Exception:
            pass

    async def hablar_click(e):
        nonlocal grabando
        if recorder is None:
            resultado.controls = [ft.Text("No se pudo acceder al micrófono. Usa el campo de texto para escribir.")]
            resultado.update()
            return
        if not grabando:
            # Intentar pedir permiso y empezar
            try:
                # Algunos SDKs piden permiso; intentamos iniciar
                audio_chunks.clear()
                # Configurar stream si existe
                try:
                    if hasattr(recorder, "on_stream"):
                        recorder.on_stream = _on_stream
                except Exception:
                    pass
                cfg = None
                if AudioRecorderConfiguration is not None and AudioEncoder is not None:
                    try:
                        cfg = AudioRecorderConfiguration(encoder=AudioEncoder.PCM16BITS, sample_rate=16000, channels=1)
                    except Exception:
                        cfg = None
                try:
                    if cfg is not None:
                        await recorder.start_recording(configuration=cfg)
                    else:
                        await recorder.start_recording()
                except Exception:
                    resultado.controls = [ft.Text("No se pudo iniciar la grabación. Revisa los permisos del micrófono.")]
                    resultado.update()
                    return
                grabando = True
                boton_hablar.text = "⏹ Detener"
                boton_hablar.update()
                boton.disabled = True
                boton.update()
                sin_horno.disabled = True
                sin_horno.update()
                resultado.controls = [ft.Text("🔴 Grabando…")]
                resultado.update()
                page.run_task(_auto_stop)
            except Exception:
                resultado.controls = [ft.Text("No se pudo acceder al micrófono. Permítelo en el navegador o usa el campo de texto.")]
                resultado.update()
        else:
            # Detener manualmente
            try:
                await recorder.stop_recording()
            except Exception:
                pass
            await _detener_y_transcribir()

    boton_hablar.on_click = hablar_click

    async def generar_recetas(texto):
        boton.disabled = True
        boton.update()
        boton_hablar.disabled = True
        boton_hablar.update()
        sin_horno.disabled = True
        sin_horno.update()
        resultado.controls = [ft.ProgressRing(), ft.Text("El cocinero está pensando…")]
        resultado.update()
        try:
            instruccion = INSTRUCCION_BASE
            if sin_horno.value:
                instruccion += ' SOLO propone recetas que NO requieran horno. Usa únicamente sartén, olla, microondas o preparaciones frías.'
            datos = await asyncio.to_thread(ia, instruccion, texto, True)
            recetas = datos["recetas"][:3]
            total = sum(int(r.get("tiempo_min", 0)) for r in recetas)
            resultado.controls = [tarjeta(r) for r in recetas] + [
                ft.Text(f"Tiempo sumado de las {len(recetas)} recetas: {total} min", color=CIAN)]
        except Exception:
            resultado.controls = [ft.Text("Algo falló al generar las recetas. Intenta de nuevo.")]
        finally:
            boton.disabled = False
            boton.update()
            boton_hablar.disabled = False
            boton_hablar.update()
            sin_horno.disabled = False
            sin_horno.update()
            resultado.update()

    async def generar_click(e):
        texto = (entrada.value or "").strip()
        if not texto:
            resultado.controls = [ft.Text("Escribe qué tienes en casa primero.")]
            resultado.update()
            return
        if len(texto) > 300:
            resultado.controls = [ft.Text("Muy largo: máximo 300 caracteres.")]
            resultado.update()
            return
        await generar_recetas(texto)

    boton.on_click = generar_click

    return ft.Column([entrada, sin_horno, ft.Row([boton, boton_hablar]), resultado])
