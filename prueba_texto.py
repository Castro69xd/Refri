# Prueba texto_resultado
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
        nombre = r.get("nombre","")
        emoji = r.get("emoji","🍽")
        tm = r.get("tiempo_min",0)
        diff = r.get("dificultad","")
        total_min += int(tm)
        lineas.append(f"{i}) {emoji} {nombre} — {tm} min · {diff}")
        ing_t = r.get("ingredientes_que_tienes",[]) or []
        if ing_t:
            lineas.append(f"Ya tienes: {', '.join(ing_t)}")
        else:
            lineas.append("Ya tienes: ")
        ing_f = r.get("ingredientes_que_faltan",[]) or []
        if not ing_f:
            lineas.append("Te falta: nada")
        else:
            lineas.append(f"Te falta: {', '.join(ing_f)}")
        lineas.append("Pasos:")
        pasos = r.get("pasos",[]) or []
        for j,p in enumerate(pasos,1):
            lineas.append(f"{j}. {p}")
        conse = r.get("consejo","")
        if conse:
            lineas.append(f"Consejo: {conse}")
        lineas.append("")
    lineas.append(f"⏱ Tiempo total sumado: {total_min} min")
    lineas.append("Hecho con AppLab IA")
    return "\n".join(lineas)

rec1 = {"nombre":"Pupusa rápida","emoji":"🫓","tiempo_min":10,"dificultad":"fácil","ingredientes_que_tienes":["masa","queso"],"ingredientes_que_faltan":[],"pasos":["Calentar","Rellenar","Cocer"],"consejo":"Servir caliente"}
rec2 = {"nombre":"Revuelto","emoji":"🍳","tiempo_min":5,"dificultad":"fácil","ingredientes_que_tienes":[],"ingredientes_que_faltan":["huevo","tomate"],"pasos":["Batir"],"consejo":""}
print(texto_resultado([rec1,rec2], pedido="arroz, huevo", tono="normal"))
print("\n---\n")
print(texto_resultado([{"nombre":"X","emoji":"🍽","tiempo_min":0,"dificultad":"media","ingredientes_que_tienes":[],"ingredientes_que_faltan":[],"pasos":[],"consejo":""}], pedido="", tono=""))
