import json

def texto_para_voz(recetas):
    partes = []
    for i, r in enumerate(recetas, 1):
        nombre = r.get("nombre","")
        try:
            tm = int(r.get("tiempo_min",0))
        except:
            tm = 0
        diff = r.get("dificultad","")
        partes.append(f"Receta {i}: {nombre}. Tarda {tm} minutos y es {diff}.")
        ing_t = r.get("ingredientes_que_tienes",[]) or []
        if ing_t:
            partes.append(f"Ya tienes: {', '.join(ing_t)}.")
        else:
            partes.append("Ya tienes: nada.")
        ing_f = r.get("ingredientes_que_faltan",[]) or []
        if ing_f:
            partes.append(f"Te falta: {', '.join(ing_f)}.")
        else:
            partes.append("No te falta nada.")
        pasos = r.get("pasos",[]) or []
        for j,p in enumerate(pasos,1):
            partes.append(f"Paso {j}: {p}.")
        conse = r.get("consejo","")
        if conse:
            partes.append(f"Consejo: {conse}.")
    total = sum(int(r.get("tiempo_min",0)) for r in recetas)
    partes.append(f"Tiempo total: {total} minutos.")
    texto = " ".join(partes)
    # remover emojis basico
    import re
    texto = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+', '', texto)
    return texto

rec1 = {"nombre":"Arroz con huevo","emoji":"🍳","tiempo_min":15,"dificultad":"fácil","ingredientes_que_tienes":["arroz","huevo"],"ingredientes_que_faltan":["cebolla"],"pasos":["Freír","Mezclar"],"consejo":"Servir caliente"}
txt = texto_para_voz([rec1])
print('has_emoji:', any(ord(c)>127000 for c in txt))
print(json.dumps(txt[:50]))
print(json.dumps("texto con \"comillas\" y\nsalto"))
