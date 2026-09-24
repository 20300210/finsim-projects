"""
Módulo: Financiación de Posgrado (Colombia)
===============================================
Este módulo cubre específicamente lo que pide el alcance del proyecto
("Opción A"): desembolso único, tasa constante durante la simulación,
sistema de cuota fija — y agrega las piezas que el simulador general de
préstamos (prestamos.py) no cubría:

  1. Costo total explícito del crédito.
  2. Capacidad de pago (cuota vs. ingreso mensual del estudiante).
  3. Nivel de endeudamiento (cuota + otras deudas vs. ingreso).
  4. Escenario de disminución de ingresos (estrés de capacidad de pago).
  5. Sensibilidad de tasa ("¿y si la tasa fuera distinta?" — análisis
     comparativo entre escenarios de tasa constante, NO un crédito de tasa
     variable real, que queda fuera del alcance de la Opción A).
  6. Comparación de N alternativas de financiación completas (ICETEX,
     banco, fondo/cooperativa, etc.), cada una con su propio monto, tasa
     y plazo, todas usando el mismo sistema de cuota fija.

Todas las funciones son puras (no dependen de Streamlit ni de ningún
framework), siguiendo el mismo patrón ya auditado en el resto del proyecto.
"""

from typing import List, Optional
import pandas as pd

from modulos.prestamos import amortizacion_francesa


# ----------------------------------------------------------------------
# Alternativas de financiación con TASAS REALES vigentes en Colombia,
# verificadas mediante búsqueda web y citadas con su fuente. Estos NO son
# valores inventados: son datos públicos consultables por cualquiera.
#
#   1. ICETEX — Posgrado País (sin convenio "Aporte en tasa IES"):
#      Tasa: IPC + 8% = 13,51% efectivo anual para 2026
#      (IPC 2025 certificado por el DANE: 5,10%)
#      Fuente: https://web.icetex.gov.co/es/-/posgrado-pais-tu-pagas-el-40
#
#   2. Davivienda — Crédito educativo: 15,20% efectivo anual
#      Fuente: Superintendencia Financiera de Colombia, reportado por
#      La República (corte: 17 de julio de 2026)
#      https://www.larepublica.co/finanzas/las-tasas-de-interes-para-adquirir-creditos-educativos-van-desde-15-2-hasta-28-3-a-julio-4444914
#
#   3. Bancoomeva — Crédito educativo: 22,58% efectivo anual
#      Fuente: misma nota de Superintendencia Financiera / La República
#      (corte: 17 de julio de 2026)
#
#   4. Bancolombia (Sufi) — Crédito educativo: 28,32% efectivo anual
#      Fuente: misma nota de Superintendencia Financiera / La República
#      (corte: 17 de julio de 2026)
#
#   5. BBVA Colombia — Crédito Educativo: 29,22% efectivo anual
#      Fuente: tabla oficial de tasas de créditos de consumo de BBVA Colombia
#      (vigente desde el 5 de septiembre de 2026). Plazo oficial: 6-12 meses.
#      https://www.bbva.com.co/content/dam/public-web/colombia/documents/personas/prestamos/consumo/DO-01-Tasas-creditos-consumo.pdf
#
# IMPORTANTE — estas tasas cambian con el tiempo y NO deben tomarse como
# vigentes indefinidamente:
#   - La tasa de ICETEX está indexada al IPC y se recalcula cada enero
#     (sube o baja según la inflación del año anterior).
#   - Las tasas de los bancos son fijadas por cada entidad según su propio
#     criterio comercial y de riesgo, y pueden cambiar en cualquier momento.
# Antes de usar estos números para una decisión financiera real, verifica
# la tasa vigente directamente en la entidad. El monto y el plazo siguen
# siendo valores de ejemplo: reemplázalos por el costo real de tu programa.
# ----------------------------------------------------------------------
ALTERNATIVAS_EJEMPLO_COLOMBIA = [
    {"nombre": "ICETEX - Posgrado País", "monto": 20_000_000, "tasa_anual": 0.1351, "plazo_meses": 60},
    {"nombre": "Davivienda - Crédito educativo", "monto": 20_000_000, "tasa_anual": 0.1520, "plazo_meses": 48},
    {"nombre": "Bancoomeva - Crédito educativo", "monto": 20_000_000, "tasa_anual": 0.2258, "plazo_meses": 36},
    {"nombre": "Bancolombia - Sufi", "monto": 20_000_000, "tasa_anual": 0.2832, "plazo_meses": 48},
    {"nombre": "BBVA Colombia - Crédito educativo", "monto": 20_000_000, "tasa_anual": 0.2922, "plazo_meses": 12},
]

# Metadatos de trazabilidad: de dónde salió cada tasa y cuándo se verificó.
# Se expone por separado (en vez de solo como comentario) para que la
# interfaz pueda mostrarlo directamente al usuario si se desea.
FUENTES_TASAS_COLOMBIA = {
    "ICETEX - Posgrado País": {
        "tasa_ea": 0.1351,
        "descripcion": "IPC + 8% (IPC 2025 = 5,10%, certificado por el DANE)",
        "fuente": "web.icetex.gov.co — Plan Posgrado País",
        "url": "https://web.icetex.gov.co/es/-/posgrado-pais-tu-pagas-el-40",
        "vigente_para": 2026,
        "nota": "Tasa variable, indexada al IPC; se recalcula cada enero.",
    },
    "Davivienda - Crédito educativo": {
        "tasa_ea": 0.1520,
        "descripcion": "Tasa reportada a la Superintendencia Financiera de Colombia",
        "fuente": "Superintendencia Financiera de Colombia, vía La República",
        "url": "https://www.larepublica.co/finanzas/las-tasas-de-interes-para-adquirir-creditos-educativos-van-desde-15-2-hasta-28-3-a-julio-4444914",
        "vigente_para": "corte 17 de julio de 2026",
        "nota": "Tasa propia del banco, no indexada al IPC; puede cambiar sin aviso previo.",
    },
    "Bancoomeva - Crédito educativo": {
        "tasa_ea": 0.2258,
        "descripcion": "Tasa reportada a la Superintendencia Financiera de Colombia",
        "fuente": "Superintendencia Financiera de Colombia, vía La República",
        "url": "https://www.larepublica.co/finanzas/las-tasas-de-interes-para-adquirir-creditos-educativos-van-desde-15-2-hasta-28-3-a-julio-4444914",
        "vigente_para": "corte 17 de julio de 2026",
        "nota": "Tasa propia de la entidad, no indexada al IPC; puede cambiar sin aviso previo.",
    },
    "Bancolombia - Sufi": {
        "tasa_ea": 0.2832,
        "descripcion": "Tasa reportada a la Superintendencia Financiera de Colombia para crédito educativo",
        "fuente": "Superintendencia Financiera de Colombia, vía La República",
        "url": "https://www.larepublica.co/finanzas/las-tasas-de-interes-para-adquirir-creditos-educativos-van-desde-15-2-hasta-28-3-a-julio-4444914",
        "vigente_para": "corte 17 de julio de 2026",
        "nota": "Operado por Sufi (marca de crédito de consumo del Grupo Bancolombia); ofrece líneas de corto plazo (6-12 meses) y largo plazo (varios años, según el programa).",
    },
    "BBVA Colombia - Crédito educativo": {
        "tasa_ea": 0.2922,
        "descripcion": "Tasa política (fija) para la línea 'Crédito Educativo', dentro de créditos de consumo",
        "fuente": "BBVA Colombia — tabla oficial de tasas de créditos de consumo",
        "url": "https://www.bbva.com.co/content/dam/public-web/colombia/documents/personas/prestamos/consumo/DO-01-Tasas-creditos-consumo.pdf",
        "vigente_para": "vigente desde el 5 de septiembre de 2026",
        "nota": "Plazo oficial de este producto: 6 a 12 meses únicamente (el más corto de las alternativas comparadas); tasa fija durante toda la vigencia.",
    },
}


def _validar_ingreso(ingreso_mensual: float) -> None:
    if ingreso_mensual <= 0:
        raise ValueError("El ingreso mensual debe ser mayor que cero.")


def costo_total_credito(monto: float, interes_total: float) -> float:
    """
    Costo total del crédito = capital prestado + todos los intereses pagados
    durante el plazo. Es el número más honesto para comparar alternativas,
    porque una cuota mensual baja con un plazo muy largo puede terminar
    costando más en total que una cuota más alta a corto plazo.
    """
    return monto + interes_total


def capacidad_pago(cuota_mensual: float, ingreso_mensual: float, umbral: float = 0.35) -> dict:
    """
    Evalúa si una cuota mensual es "pagable" frente al ingreso del
    estudiante (o de quien vaya a respaldar el crédito).

    Parámetros:
        cuota_mensual: valor de la cuota del crédito
        ingreso_mensual: ingreso mensual neto disponible
        umbral: proporción máxima recomendada del ingreso que debería
                destinarse a ESTA cuota (por defecto 35%, un punto de
                referencia común; el usuario puede ajustarlo en la app)

    Retorna:
        dict con: ratio (decimal), ratio_pct, cumple (bool), umbral
    """
    _validar_ingreso(ingreso_mensual)
    if cuota_mensual < 0:
        raise ValueError("La cuota mensual no puede ser negativa.")
    if not (0 < umbral <= 1):
        raise ValueError("El umbral debe ser un valor entre 0 y 1 (ej. 0.35 = 35%).")

    ratio = cuota_mensual / ingreso_mensual
    return {
        "ratio": ratio,
        "ratio_pct": ratio * 100,
        "cumple": ratio <= umbral,
        "umbral": umbral,
    }


def nivel_endeudamiento(
    cuota_mensual: float,
    ingreso_mensual: float,
    otras_deudas_mensuales: float = 0.0,
    umbral: float = 0.40,
) -> dict:
    """
    A diferencia de "capacidad de pago" (que mira solo la cuota nueva),
    esto mide la carga financiera TOTAL: la cuota nueva más cualquier otra
    deuda mensual que ya tenga el estudiante (tarjeta de crédito, otro
    préstamo, etc.), frente al ingreso.

    Retorna:
        dict con: carga_total, ratio, ratio_pct, cumple, umbral
    """
    _validar_ingreso(ingreso_mensual)
    if cuota_mensual < 0 or otras_deudas_mensuales < 0:
        raise ValueError("La cuota y las otras deudas no pueden ser negativas.")
    if not (0 < umbral <= 1):
        raise ValueError("El umbral debe ser un valor entre 0 y 1 (ej. 0.40 = 40%).")

    carga_total = cuota_mensual + otras_deudas_mensuales
    ratio = carga_total / ingreso_mensual
    return {
        "carga_total": carga_total,
        "ratio": ratio,
        "ratio_pct": ratio * 100,
        "cumple": ratio <= umbral,
        "umbral": umbral,
    }


def escenario_disminucion_ingreso(
    ingreso_mensual: float,
    porcentaje_disminucion: float,
    cuota_mensual: float,
    otras_deudas_mensuales: float = 0.0,
    umbral: float = 0.40,
) -> dict:
    """
    Simula qué pasaría con el nivel de endeudamiento del estudiante si su
    ingreso (o el de quien respalda el crédito) cae un porcentaje dado —
    por ejemplo, por quedarse sin trabajo temporalmente durante el
    posgrado, o por un recorte salarial.

    Parámetros:
        porcentaje_disminucion: decimal entre 0 y 1 (ej. 0.30 = ingreso cae 30%)

    Retorna:
        El mismo dict de nivel_endeudamiento(), más 'ingreso_original' e
        'ingreso_reducido' para poder mostrar el contraste en la interfaz.
    """
    _validar_ingreso(ingreso_mensual)
    if not (0 <= porcentaje_disminucion < 1):
        raise ValueError("porcentaje_disminucion debe estar entre 0 (0%) y 1 (100%, sin incluir).")

    ingreso_reducido = ingreso_mensual * (1 - porcentaje_disminucion)
    resultado = nivel_endeudamiento(cuota_mensual, ingreso_reducido, otras_deudas_mensuales, umbral)
    resultado["ingreso_original"] = ingreso_mensual
    resultado["ingreso_reducido"] = ingreso_reducido
    resultado["porcentaje_disminucion"] = porcentaje_disminucion
    return resultado


def sensibilidad_tasa(
    monto: float,
    tasa_anual_base: float,
    plazo_meses: int,
    deltas_puntos_porcentuales: tuple = (-2, -1, 0, 1, 2),
) -> pd.DataFrame:
    """
    Análisis de sensibilidad: "si hubiera tomado (o si en el futuro tomo)
    este mismo crédito con una tasa distinta, ¿cómo cambiaría mi cuota?".

    IMPORTANTE (alcance): esto NO simula un crédito de tasa variable — la
    Opción A del proyecto usa tasa constante durante toda la simulación.
    Esta función compara varios escenarios de tasa CONSTANTE distintos
    entre sí, uno al lado del otro; cada fila es un préstamo hipotético
    independiente con su propia tasa fija.

    Retorna:
        DataFrame con columnas: delta_pp, tasa_anual_pct, cuota_mensual
    """
    if plazo_meses <= 0:
        raise ValueError("plazo_meses debe ser positivo.")

    filas = []
    for delta in deltas_puntos_porcentuales:
        tasa_anual = max(tasa_anual_base + delta / 100, 0.0)
        tasa_mensual = tasa_anual / 12
        tabla = amortizacion_francesa(monto, tasa_mensual, plazo_meses)
        filas.append({
            "delta_pp": delta,
            "tasa_anual_pct": round(tasa_anual * 100, 2),
            "cuota_mensual": tabla["cuota"].iloc[0],
        })
    return pd.DataFrame(filas)


def comparar_alternativas(
    alternativas: List[dict],
    ingreso_mensual: Optional[float] = None,
    otras_deudas_mensuales: float = 0.0,
    umbral_capacidad_pago: float = 0.35,
    umbral_endeudamiento: float = 0.40,
) -> pd.DataFrame:
    """
    Compara N alternativas de financiación completas, cada una con su
    propio monto/tasa/plazo, todas bajo el mismo sistema de cuota fija
    (Opción A). Si se provee ingreso_mensual, agrega DOS métricas
    separadas, cada una con su propio umbral:

      - "capacidad_pago": mira SOLO esta cuota nueva frente al ingreso.
      - "endeudamiento": mira esta cuota MÁS otras deudas ya existentes.

    Parámetros:
        alternativas: lista de dicts, cada uno con las llaves
            "nombre" (str), "monto" (float), "tasa_anual" (decimal),
            "plazo_meses" (int)
        ingreso_mensual: si se provee, se agregan las columnas anteriores
        otras_deudas_mensuales: otras deudas del estudiante (afecta solo
            el cálculo de endeudamiento, no el de capacidad de pago)
        umbral_capacidad_pago: proporción máxima recomendada de ingreso
            para ESTA cuota sola (por defecto 35%)
        umbral_endeudamiento: proporción máxima recomendada de ingreso
            para TODAS las deudas juntas (por defecto 40%)

    Retorna:
        DataFrame ordenado por costo total (de menor a mayor), con una
        fila por alternativa.
    """
    if not alternativas:
        raise ValueError("Debes proporcionar al menos una alternativa de financiación.")
    if len(alternativas) > 10:
        raise ValueError("Máximo 10 alternativas a la vez (límite razonable de la interfaz).")

    nombres_vistos = set()
    filas = []
    for alt in alternativas:
        for campo in ("nombre", "monto", "tasa_anual", "plazo_meses"):
            if campo not in alt:
                raise ValueError(f"Cada alternativa debe tener el campo '{campo}'.")

        nombre = str(alt["nombre"]).strip() or "Sin nombre"
        if nombre in nombres_vistos:
            raise ValueError(f"El nombre de alternativa '{nombre}' está repetido; usa nombres distintos.")
        nombres_vistos.add(nombre)

        tasa_mensual = alt["tasa_anual"] / 12
        tabla = amortizacion_francesa(alt["monto"], tasa_mensual, int(alt["plazo_meses"]))
        interes_total = tabla["interes"].sum()
        cuota = tabla["cuota"].iloc[0]
        costo_total = costo_total_credito(alt["monto"], interes_total)

        fila = {
            "nombre": nombre,
            "monto": alt["monto"],
            "tasa_anual_pct": round(alt["tasa_anual"] * 100, 2),
            "plazo_meses": int(alt["plazo_meses"]),
            "cuota_mensual": round(cuota, 2),
            "interes_total": round(interes_total, 2),
            "costo_total": round(costo_total, 2),
        }

        if ingreso_mensual is not None:
            cap = capacidad_pago(cuota, ingreso_mensual, umbral_capacidad_pago)
            end = nivel_endeudamiento(cuota, ingreso_mensual, otras_deudas_mensuales, umbral_endeudamiento)
            fila["capacidad_pago_pct"] = round(cap["ratio_pct"], 1)
            fila["cumple_capacidad_pago"] = cap["cumple"]
            fila["endeudamiento_pct"] = round(end["ratio_pct"], 1)
            fila["cumple_endeudamiento"] = end["cumple"]

        filas.append(fila)

    return pd.DataFrame(filas).sort_values("costo_total").reset_index(drop=True)
