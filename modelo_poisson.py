"""
Modelo de Poisson para previsão de resultados de futebol (Premier League)
Calcula probabilidades de vitória casa, empate e vitória visitante
usando a distribuição de Poisson.
"""

import numpy as np
from scipy.stats import poisson


def calcular_probabilidades_poisson(media_gols_casa: float, media_gols_visitante: float, max_gols: int = 5) -> dict:
    """
    Calcula as probabilidades de cada resultado usando a distribuição de Poisson.

    Args:
        media_gols_casa: Média de gols esperados do time da casa
        media_gols_visitante: Média de gols esperados do time visitante
        max_gols: Número máximo de gols a considerar (default: 5)

    Returns:
        Dicionário com probabilidades de vitória casa, empate e vitória visitante
    """
    prob_vitoria_casa = 0.0
    prob_empate = 0.0
    prob_vitoria_visitante = 0.0

    # Matriz de probabilidades para cada placar
    matriz_placares = np.zeros((max_gols + 1, max_gols + 1))

    for gols_casa in range(max_gols + 1):
        for gols_visitante in range(max_gols + 1):
            # Probabilidade de cada placar exato
            prob_gols_casa = poisson.pmf(gols_casa, media_gols_casa)
            prob_gols_visitante = poisson.pmf(gols_visitante, media_gols_visitante)
            prob_placar = prob_gols_casa * prob_gols_visitante

            matriz_placares[gols_casa, gols_visitante] = prob_placar

            if gols_casa > gols_visitante:
                prob_vitoria_casa += prob_placar
            elif gols_casa == gols_visitante:
                prob_empate += prob_placar
            else:
                prob_vitoria_visitante += prob_placar

    return {
        'prob_vitoria_casa': prob_vitoria_casa,
        'prob_empate': prob_empate,
        'prob_vitoria_visitante': prob_vitoria_visitante,
        'matriz_placares': matriz_placares
    }


def calcular_odds_justas(probabilidades: dict) -> dict:
    """
    Converte probabilidades em odds justas (1 / probabilidade).

    Args:
        probabilidades: Dicionário com as probabilidades

    Returns:
        Dicionário com as odds justas
    """
    return {
        'odd_vitoria_casa': 1 / probabilidades['prob_vitoria_casa'] if probabilidades['prob_vitoria_casa'] > 0 else float('inf'),
        'odd_empate': 1 / probabilidades['prob_empate'] if probabilidades['prob_empate'] > 0 else float('inf'),
        'odd_vitoria_visitante': 1 / probabilidades['prob_vitoria_visitante'] if probabilidades['prob_vitoria_visitante'] > 0 else float('inf')
    }


def calcular_valor_esperado(prob_modelo: float, odd_mercado: float) -> dict:
    """
    Calcula o Valor Esperado (+EV ou -EV) comparando a probabilidade do modelo
    com a odd de mercado.

    EV = (Probabilidade * Odd) - 1
    Se EV > 0, temos +EV (aposta com valor)

    Args:
        prob_modelo: Probabilidade calculada pelo modelo
        odd_mercado: Odd oferecida pelo mercado

    Returns:
        Dicionário com EV e indicação se tem valor
    """
    ev = (prob_modelo * odd_mercado) - 1
    ev_percentual = ev * 100

    return {
        'ev': ev,
        'ev_percentual': ev_percentual,
        'tem_valor': ev > 0
    }


def analisar_partida(media_gols_casa: float, media_gols_visitante: float,
                     odd_mercado_casa: float, odd_mercado_empate: float,
                     odd_mercado_visitante: float) -> None:
    """
    Analisa uma partida completa e exibe os resultados.

    Args:
        media_gols_casa: Média de gols do time da casa
        media_gols_visitante: Média de gols do time visitante
        odd_mercado_casa: Odd de mercado para vitória casa
        odd_mercado_empate: Odd de mercado para empate
        odd_mercado_visitante: Odd de mercado para vitória visitante
    """
    print("=" * 60)
    print("MODELO DE POISSON - ANÁLISE DE PARTIDA")
    print("=" * 60)
    print(f"\nMédia de gols esperados - Casa: {media_gols_casa:.2f}")
    print(f"Média de gols esperados - Visitante: {media_gols_visitante:.2f}")

    # Calcular probabilidades
    probs = calcular_probabilidades_poisson(media_gols_casa, media_gols_visitante)

    print("\n" + "-" * 40)
    print("PROBABILIDADES CALCULADAS")
    print("-" * 40)
    print(f"Vitória Casa:     {probs['prob_vitoria_casa'] * 100:.2f}%")
    print(f"Empate:           {probs['prob_empate'] * 100:.2f}%")
    print(f"Vitória Visitante: {probs['prob_vitoria_visitante'] * 100:.2f}%")

    # Calcular odds justas
    odds_justas = calcular_odds_justas(probs)

    print("\n" + "-" * 40)
    print("ODDS JUSTAS (1/Probabilidade)")
    print("-" * 40)
    print(f"Vitória Casa:     {odds_justas['odd_vitoria_casa']:.2f}")
    print(f"Empate:           {odds_justas['odd_empate']:.2f}")
    print(f"Vitória Visitante: {odds_justas['odd_vitoria_visitante']:.2f}")

    print("\n" + "-" * 40)
    print("ODDS DE MERCADO")
    print("-" * 40)
    print(f"Vitória Casa:     {odd_mercado_casa:.2f}")
    print(f"Empate:           {odd_mercado_empate:.2f}")
    print(f"Vitória Visitante: {odd_mercado_visitante:.2f}")

    # Calcular EV para cada resultado
    ev_casa = calcular_valor_esperado(probs['prob_vitoria_casa'], odd_mercado_casa)
    ev_empate = calcular_valor_esperado(probs['prob_empate'], odd_mercado_empate)
    ev_visitante = calcular_valor_esperado(probs['prob_vitoria_visitante'], odd_mercado_visitante)

    print("\n" + "-" * 40)
    print("ANÁLISE DE VALOR ESPERADO (EV)")
    print("-" * 40)

    def formatar_ev(nome: str, ev_data: dict, odd_justa: float, odd_mercado: float) -> None:
        status = "+EV (VALOR!)" if ev_data['tem_valor'] else "-EV (Sem valor)"
        cor = ">>>" if ev_data['tem_valor'] else "   "
        print(f"{cor} {nome}:")
        print(f"      Odd Justa: {odd_justa:.2f} | Odd Mercado: {odd_mercado:.2f}")
        print(f"      EV: {ev_data['ev_percentual']:+.2f}% | {status}")
        print()

    formatar_ev("Vitória Casa", ev_casa, odds_justas['odd_vitoria_casa'], odd_mercado_casa)
    formatar_ev("Empate", ev_empate, odds_justas['odd_empate'], odd_mercado_empate)
    formatar_ev("Vitória Visitante", ev_visitante, odds_justas['odd_vitoria_visitante'], odd_mercado_visitante)

    # Mostrar placares mais prováveis
    print("-" * 40)
    print("TOP 5 PLACARES MAIS PROVÁVEIS")
    print("-" * 40)

    matriz = probs['matriz_placares']
    placares = []
    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            placares.append((i, j, matriz[i, j]))

    placares_ordenados = sorted(placares, key=lambda x: x[2], reverse=True)[:5]

    for idx, (gols_casa, gols_fora, prob) in enumerate(placares_ordenados, 1):
        print(f"{idx}. {gols_casa} x {gols_fora} -> {prob * 100:.2f}%")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Exemplo: Arsenal (casa) vs Chelsea (visitante)
    # Médias baseadas em dados fictícios da Premier League

    print("\n*** EXEMPLO: Arsenal vs Chelsea ***\n")

    # Médias de gols (fictícias)
    media_gols_arsenal = 1.8  # Arsenal em casa marca em média 1.8 gols
    media_gols_chelsea = 1.2  # Chelsea fora marca em média 1.2 gols

    # Odds de mercado (fictícias)
    odd_mercado_casa = 2.10      # Mercado paga 2.10 na vitória do Arsenal
    odd_mercado_empate = 3.40    # Mercado paga 3.40 no empate
    odd_mercado_visitante = 3.50  # Mercado paga 3.50 na vitória do Chelsea

    analisar_partida(
        media_gols_casa=media_gols_arsenal,
        media_gols_visitante=media_gols_chelsea,
        odd_mercado_casa=odd_mercado_casa,
        odd_mercado_empate=odd_mercado_empate,
        odd_mercado_visitante=odd_mercado_visitante
    )
