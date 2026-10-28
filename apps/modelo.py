import asyncio, flet as ft
from ia import ia

INSTRUCCION = ('Responde SOLO JSON: {"creible":"","epica":"","absurda":""}. '
               'Con la situación del usuario, escribe 3 excusas de una frase: '
               'una creíble, una épica y una absurda.')

def vista():
    entrada = ft.TextField(label="¿Qué pasó?", hint_text="Llegué tarde a clase")
    resultado = ft.Column()

    async def generar(e):
        if not entrada.value or not entrada.value.strip():
            resultado.controls = [ft.Text("Escribe qué pasó primero.")]
            resultado.update()
            return
        resultado.controls = [ft.Text("La IA está inventando…")]
        resultado.update()
        try:
            datos = await asyncio.to_thread(ia, INSTRUCCION, entrada.value, True)
            resultado.controls = [ft.Text(f"{tipo.upper()}: {frase}") for tipo, frase in datos.items()]
        except Exception as ex:
            resultado.controls = [ft.Text(f"Error: {ex}")]
        resultado.update()

    return ft.Column([entrada, ft.Button("Inventar excusas", on_click=generar), resultado])
