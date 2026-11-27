#!/usr/bin/env python3
"""Lee la Tabla de Cotizaciones del Banco Central de Bolivia y guarda tipos-de-cambio.json.
Cotizaciones tomadas de https://www.bcb.gob.bo/librerias/indicadores/otras/ultimo.php
- usd_bob: Tipo de Cambio Oficial del dólar (Bs por 1 USD)
- clp_bob: Bs por 1 peso chileno (cotización indicativa del BCB)
"""
import json, os, re, sys, time, urllib.request, html
from datetime import datetime, timezone

URL = "https://www.bcb.gob.bo/librerias/indicadores/otras/ultimo.php"
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tipos-de-cambio.json")
MESES = {"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,"noviembre":11,"diciembre":12}

def bajar():
    ultimo = None
    for intento in range(4):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (compatible; MiCuaderno/1.0)"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            ultimo = e
            time.sleep(5 * (intento + 1))
    raise SystemExit("No se pudo leer el BCB: %s" % ultimo)

def num(t):
    return float(t.replace(",", ""))

def main():
    crudo = bajar()
    limpio = re.sub(r"<script.*?</script>|<style.*?</style>", "", crudo, flags=re.S)
    texto = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "|", limpio)))
    texto = re.sub(r"(\| ?)+", "| ", texto)
    f = re.search(r"(\d{1,2}) de ([A-Za-zñÑáéíóúÁÉÍÓÚ]+) (\d{4})", texto)
    usd = re.search(r"USD\| ?([0-9][0-9.,]*)", texto)
    clp = re.search(r"CLP\| ?([0-9][0-9.,]*)\| ?([0-9][0-9.,]*)", texto)
    if not (f and usd and clp):
        raise SystemExit("No encontré los datos esperados en la página del BCB")
    mes = MESES.get(f.group(2).lower())
    fecha = "%04d-%02d-%02d" % (int(f.group(3)), mes, int(f.group(1)))
    usd_bob, clp_bob, clp_usd = num(usd.group(1)), num(clp.group(1)), num(clp.group(2))
    if not (1 < usd_bob < 100 and 0 < clp_bob < 1):
        raise SystemExit("Valores fuera de lo normal: %s %s" % (usd_bob, clp_bob))
    previo = {}
    if os.path.exists(SALIDA):
        try:
            previo = json.load(open(SALIDA, encoding="utf-8"))
        except Exception:
            previo = {}
    hist = [h for h in previo.get("historial", []) if h.get("fecha") != fecha]
    hist.append({"fecha": fecha, "usd_bob": usd_bob, "clp_bob": clp_bob})
    hist = sorted(hist, key=lambda h: h["fecha"])[-400:]
    nuevo = {
        "fuente": "Banco Central de Bolivia - Tabla de Cotizaciones",
        "url": URL,
        "fecha": fecha,
        "usd_bob": usd_bob,
        "clp_bob": clp_bob,
        "clp_por_usd": clp_usd,
        "historial": hist,
    }
    igual = all(previo.get(k) == nuevo[k] for k in ("fecha", "usd_bob", "clp_bob", "clp_por_usd"))
    if igual:
        print("Sin cambios (%s)" % fecha)
        return
    nuevo["actualizado"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(SALIDA, "w", encoding="utf-8") as fh:
        json.dump(nuevo, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("Actualizado %s: 1 USD = Bs %s | 1 CLP = Bs %s" % (fecha, usd_bob, clp_bob))

if __name__ == "__main__":
    main()
