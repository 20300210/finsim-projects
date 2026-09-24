"""
Módulo: Valor del Dinero en el Tiempo
--------------------------------------
Contiene las fórmulas base de matemática financiera:
- Valor Futuro (VF) de un capital único
- Valor Presente (VP) de un monto futuro
- Valor Futuro de una anualidad (aportes periódicos constantes)
- Número de aportes necesarios para alcanzar una meta de ahorro (operación
  inversa de la anualidad: en vez de dar n y calcular VF, se da la meta y
  se calcula n)
- Conversión de tasa anual a su equivalente por frecuencia de aporte
  (quincenal, mensual, trimestral, anual)
- Ajuste de un monto por inflación (poder adquisitivo real)

Convención usada en todo el módulo:
    tasa   -> tasa de interés periódica, en decimal (ej. 0.08 = 8%)
    n      -> número de periodos (años, meses, etc., debe ser consistente con 'tasa')
"""

import math


def valor_futuro(capital: float, tasa: float, n: int) -> float:
    """
    Calcula el Valor Futuro de un capital inicial con interés compuesto.

    VF = VP * (1 + i)^n

    Parámetros:
        capital: monto inicial invertido (VP)
        tasa: tasa de interés por periodo (decimal)
        n: número de periodos

    Retorna:
        Valor futuro del capital.
    """
    if capital < 0 or n < 0:
        raise ValueError("El capital y el número de periodos deben ser no negativos.")
    return capital * (1 + tasa) ** n


def valor_presente(monto_futuro: float, tasa: float, n: int) -> float:
    """
    Calcula el Valor Presente de un monto que se recibirá en el futuro.

    VP = VF / (1 + i)^n

    Parámetros:
        monto_futuro: monto que se espera recibir en 'n' periodos
        tasa: tasa de descuento por periodo (decimal)
        n: número de periodos

    Retorna:
        Valor presente del monto futuro.
    """
    if n < 0:
        raise ValueError("El número de periodos debe ser no negativo.")
    return monto_futuro / (1 + tasa) ** n


def valor_futuro_anualidad(aporte: float, tasa: float, n: int, anticipada: bool = False) -> float:
    """
    Calcula el Valor Futuro de una serie de aportes periódicos iguales (anualidad).

    Anualidad vencida (aporte al final de cada periodo):
        VF = A * [ ((1 + i)^n - 1) / i ]

    Anualidad anticipada (aporte al inicio de cada periodo):
        VF = A * [ ((1 + i)^n - 1) / i ] * (1 + i)

    Parámetros:
        aporte: monto constante aportado cada periodo (A)
        tasa: tasa de interés por periodo (decimal)
        n: número de aportes
        anticipada: True si el aporte se hace al inicio del periodo

    Retorna:
        Valor futuro acumulado de la anualidad.
    """
    if tasa == 0:
        vf = aporte * n
    else:
        vf = aporte * (((1 + tasa) ** n - 1) / tasa)
        if anticipada:
            vf *= (1 + tasa)
    return vf


def periodos_necesarios_para_meta(meta: float, capital: float, aporte: float, tasa: float) -> float:
    """
    Operación INVERSA de valor_futuro_anualidad(): en vez de dar el número de
    periodos (n) y calcular cuánto se acumula, se da una meta de ahorro y se
    calcula cuántos periodos (n) se necesitan para alcanzarla.

    Combina el crecimiento del capital inicial (interés compuesto) y el
    crecimiento de los aportes periódicos (anualidad vencida) simultáneamente:

        meta = capital*(1+i)^n + aporte * [ ((1+i)^n - 1) / i ]

    Despejando x = (1+i)^n:

        x = (meta + aporte/i) / (capital + aporte/i)
        n = ln(x) / ln(1+i)

    Parámetros:
        meta: monto que se quiere alcanzar
        capital: capital inicial ya disponible
        aporte: aporte periódico constante (al final de cada periodo)
        tasa: tasa de interés por periodo (decimal)

    Retorna:
        Número de periodos necesarios (puede ser fraccionario, ej. 13.27
        significa "13 años y una fracción del siguiente"). Retorna 0.0 si
        la meta ya se alcanza solo con el capital inicial, sin necesidad de
        ningún aporte adicional.

    Lanza:
        ValueError si la meta, el capital o el aporte son negativos, o si
        con los valores dados (ej. aporte=0, tasa=0, capital insuficiente)
        es matemáticamente imposible alcanzar la meta.
    """
    if meta < 0:
        raise ValueError("La meta de ahorro no puede ser negativa.")
    if capital < 0 or aporte < 0:
        raise ValueError("El capital y el aporte no pueden ser negativos.")
    if tasa <= -1:
        raise ValueError("La tasa no puede ser <= -100% (indefinición matemática).")

    if meta <= capital:
        return 0.0  # el capital inicial, solo, ya alcanza o supera la meta

    if tasa == 0:
        if aporte <= 0:
            raise ValueError(
                "Con aporte periódico de $0 y tasa de 0%, nunca se alcanza una meta "
                "mayor al capital inicial: no hay ningún crecimiento posible."
            )
        return (meta - capital) / aporte

    ajuste = aporte / tasa
    denominador = capital + ajuste
    if denominador <= 0:
        raise ValueError(
            "Con estos valores (capital, aporte y tasa), no es matemáticamente "
            "posible alcanzar la meta. Prueba con un aporte mayor o una tasa distinta."
        )

    x = (meta + ajuste) / denominador
    if x <= 1:
        return 0.0  # ya se alcanza la meta de inmediato con estos parámetros

    return math.log(x) / math.log(1 + tasa)


def valor_presente_anualidad(aporte: float, tasa: float, n: int, anticipada: bool = False) -> float:
    """
    Calcula el Valor Presente de una serie de aportes/retiros periódicos iguales.
    Útil para pensar cuánto capital se necesita HOY para financiar 'n' retiros futuros
    (por ejemplo, en un plan de retiro).

    VP = A * [ (1 - (1 + i)^-n) / i ]
    """
    if tasa == 0:
        vp = aporte * n
    else:
        vp = aporte * ((1 - (1 + tasa) ** (-n)) / tasa)
        if anticipada:
            vp *= (1 + tasa)
    return vp


def ajustar_por_inflacion(monto_nominal: float, inflacion_anual: float, anios: int) -> float:
    """
    Convierte un monto nominal futuro a su valor real (poder adquisitivo de hoy),
    descontando la inflación acumulada.

    Monto real = Monto nominal / (1 + inflación)^años
    """
    return monto_nominal / (1 + inflacion_anual) ** anios


# ----------------------------------------------------------------------
# Frecuencia de aportes (quincenal, mensual, trimestral, anual)
# ----------------------------------------------------------------------
# Número de periodos por año para cada frecuencia. "Quincenal" usa la
# convención financiera colombiana estándar de 24 quincenas por año
# (2 por mes × 12 meses), no 26 (que sería contar semanas exactas).
FRECUENCIAS_APORTE = {
    "Anual": 1,
    "Trimestral": 4,
    "Mensual": 12,
    "Quincenal": 24,
}


def tasa_periodica_equivalente(tasa_anual: float, periodos_por_anio: int) -> float:
    """
    Convierte una tasa efectiva anual a su tasa equivalente para un periodo
    más corto (mensual, trimestral, quincenal...), preservando exactamente
    el mismo rendimiento efectivo anual real.

    IMPORTANTE: esto NO es una simple división (tasa_anual / periodos). Una
    simple división da una tasa NOMINAL, que compuesta más veces al año
    termina rindiendo MÁS que la tasa anual original — no es matemáticamente
    equivalente. La conversión correcta (la misma que usan los CDTs y
    cuentas de ahorro en Colombia) es la conversión por equivalencia de
    interés compuesto:

        tasa_periodica = (1 + tasa_anual)^(1/periodos_por_anio) - 1

    Parámetros:
        tasa_anual: tasa efectiva anual, en decimal (ej. 0.08 = 8% E.A.)
        periodos_por_anio: cuántos periodos de esa frecuencia hay en un año
                           (1=anual, 4=trimestral, 12=mensual, 24=quincenal)

    Retorna:
        La tasa periódica equivalente, en decimal.
    """
    if periodos_por_anio <= 0:
        raise ValueError("periodos_por_anio debe ser un entero positivo.")
    if tasa_anual <= -1:
        raise ValueError("La tasa anual no puede ser <= -100% (indefinición matemática).")
    return (1 + tasa_anual) ** (1 / periodos_por_anio) - 1
