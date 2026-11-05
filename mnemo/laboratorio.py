"""Laboratorio interactivo para jugar con ACT-R y HMAC.

Uso (desde la carpeta del proyecto): .venv/bin/python -m mnemo.laboratorio

No necesita Docker ni Ollama, y no usa tu clave real de seudónimos.
"""
import hashlib
import hmac
import re
import secrets
import time

from mnemo.cognitivo.actr import ModeloACTR
from mnemo.config import obtener_configuracion

UNIDADES = {"s": 1, "m": 60, "h": 3600, "d": 86400, "sem": 604800}
PATRON_DURACION = re.compile(r"(\d+(?:[.,]\d+)?)\s*(sem|s|m|h|d)")
FUTUROS = [("ahora", 0), ("en 1 hora", 3600), ("en 1 día", 86400),
           ("en 3 días", 3 * 86400), ("en 1 semana", 604800), ("en 1 mes", 30 * 86400)]
IDS_A_PROBAR = 1_000_000


def leer_duraciones(texto: str) -> list[float]:
    """Convierte '3d 1h 20m' en segundos. Da error si hay algo que no entiende."""
    texto = texto.strip().lower()
    if not texto or PATRON_DURACION.sub("", texto).strip(" ,"):
        raise ValueError("No lo entiendo. Ejemplo válido: 3d 2d 1h 20m")
    return [float(n.replace(",", ".")) * UNIDADES[u] for n, u in PATRON_DURACION.findall(texto)]


def barra(probabilidad: float, ancho: int = 25) -> str:
    llenos = round(probabilidad * ancho)
    return "█" * llenos + "░" * (ancho - llenos)


def curva_de_olvido(hace_segundos: list[float], modelo: ModeloACTR) -> list[tuple[str, float, float]]:
    """(momento, activación, probabilidad) ahora y en el futuro, sin más prácticas."""
    ahora = max(hace_segundos) + 1  # tiempos relativos: da igual la fecha real
    practicas = [ahora - s for s in hace_segundos]
    return [(nombre, modelo.activacion(practicas, ahora + extra), modelo.predecir(practicas, ahora + extra))
            for nombre, extra in FUTUROS]


def seudonimo_sha256(estudiante_id: int) -> str:
    return hashlib.sha256(f"estudiante:{estudiante_id}".encode()).hexdigest()


def seudonimo_hmac(clave: bytes, estudiante_id: int) -> str:
    return hmac.new(clave, f"estudiante:{estudiante_id}".encode(), hashlib.sha256).hexdigest()


def romper_por_fuerza_bruta(objetivo: str, calcular, limite: int = IDS_A_PROBAR) -> int | None:
    """Prueba todos los IDs. Devuelve el que coincide, o None si ninguno."""
    for candidato in range(1, limite + 1):
        if calcular(candidato) == objetivo:
            return candidato
    return None


def laboratorio_actr() -> None:
    modelo = ModeloACTR()
    umbral = obtener_configuracion().umbral_repaso
    print("\n¿Hace cuánto practicaste? Una duración por práctica.")
    print("Unidades: s, m, h, d, sem. Ejemplos: '1d'  o  '3d 2d 1d'  o  '2sem 1h'")
    print("Pulsa Enter sin escribir nada para volver al menú.")
    while True:
        texto = input("\nPrácticas> ").strip()
        if not texto:
            return
        try:
            hace = leer_duraciones(texto)
        except ValueError as error:
            print(error)
            continue

        print(f"\n{len(hace)} práctica(s). Si no vuelves a practicar:\n")
        print(f"{'Momento':13} {'Activación':>10}  {'P(recuerdo)':>11}")
        for nombre, activacion, probabilidad in curva_de_olvido(hace, modelo):
            print(f"{nombre:13} {activacion:10.2f}  {probabilidad:10.1%}  {barra(probabilidad)}")

        p_ahora = curva_de_olvido(hace, modelo)[0][2]
        if p_ahora < umbral:
            print(f"\n→ Toca repasar: {p_ahora:.1%} está por debajo del umbral de {umbral:.0%}.")
        else:
            print(f"\n→ Todavía no hace falta repasar: {p_ahora:.1%} supera el umbral de {umbral:.0%}.")


def laboratorio_hmac() -> None:
    print(f"\nEres un atacante con acceso a la tabla de ClickHouse y pruebas {IDS_A_PROBAR:,} IDs.")
    print("Pulsa Enter sin escribir nada para volver al menú.")
    while True:
        texto = input(f"\nID del estudiante (1 a {IDS_A_PROBAR:,})> ").strip()
        if not texto:
            return
        if not texto.isdigit() or not 1 <= int(texto) <= IDS_A_PROBAR:
            print(f"Escribe un número entero entre 1 y {IDS_A_PROBAR:,}.")
            continue
        estudiante_id = int(texto)

        # 1. Hash simple: el atacante puede repetir el cálculo
        objetivo = seudonimo_sha256(estudiante_id)
        print(f"\n1) SHA-256 simple\n   En la tabla: {objetivo[:32]}...")
        inicio = time.perf_counter()
        hallado = romper_por_fuerza_bruta(objetivo, seudonimo_sha256)
        print(f"   ¡ROTO en {time.perf_counter() - inicio:.2f} s! Es el estudiante {hallado}.")

        # 2. HMAC: el atacante no tiene la clave y solo puede inventarse otra
        clave_real, clave_inventada = secrets.token_bytes(32), secrets.token_bytes(32)
        objetivo = seudonimo_hmac(clave_real, estudiante_id)
        print(f"\n2) HMAC con clave secreta (generada solo para esta prueba)\n   En la tabla: {objetivo[:32]}...")
        inicio = time.perf_counter()
        hallado = romper_por_fuerza_bruta(objetivo, lambda i: seudonimo_hmac(clave_inventada, i))
        duracion = time.perf_counter() - inicio
        print(f"   Probados todos los IDs en {duracion:.2f} s con una clave inventada: "
              f"{'sin coincidencias' if hallado is None else hallado}.")
        print("   Sin la clave real no hay forma de saber quién es.")
        print(f"\n   Comprobación: con la clave real, el ID {estudiante_id} sí da el mismo código: "
              f"{seudonimo_hmac(clave_real, estudiante_id) == objetivo}.")


def main() -> None:
    print("=== Laboratorio de Mnemo ===")
    opciones = {"1": laboratorio_actr, "2": laboratorio_hmac}
    try:
        while True:
            print("\n1) ACT-R: ¿cuánto recuerdas?\n2) HMAC: intenta romper un seudónimo\n3) Salir")
            eleccion = input("Elige> ").strip()
            if eleccion == "3":
                break
            if eleccion in opciones:
                opciones[eleccion]()
            else:
                print("Elige 1, 2 o 3.")
    except (EOFError, KeyboardInterrupt):
        print()
    print("¡Hasta luego!")


if __name__ == "__main__":
    main()
