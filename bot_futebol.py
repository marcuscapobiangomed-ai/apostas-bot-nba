import numpy as np
from scipy.stats import poisson

def calcular_odds_justas(xg_casa, xg_visitante):
    """
    Implementação da Seção 3.1: Distribuição de Poisson Bivariada (Simplificada)
    Calcula as probabilidades de vitória somando as chances de cada placar.
    """
    # Matriz de placares possíveis (de 0x0 até 5x5)
    max_gols = 6
    probs_casa = poisson.pmf(np.arange(max_gols), xg_casa)
    probs_visitante = poisson.pmf(np.arange(max_gols), xg_visitante)

    # Probabilidade de cada placar específico (Matriz)
    prob_placar = np.outer(probs_casa, probs_visitante)

    # Somar probabilidades para cada resultado (1X2)
    prob_vitoria_casa = np.sum(np.tril(prob_placar, -1))
    prob_empate = np.sum(np.diag(prob_placar))
    prob_vitoria_visitante = np.sum(np.triu(prob_placar, 1))

    return prob_vitoria_casa, prob_empate, prob_vitoria_visitante

def verificar_valor(time_casa, time_visitante, xg_casa, xg_visitante, odd_mercado_casa):
    print(f"\n--- Analisando: {time_casa} vs {time_visitante} ---")
    print(f"Inputs do Modelo: xG Casa {xg_casa} | xG Visitante {xg_visitante}")

    # 1. Roda o Modelo
    p_casa, p_empate, p_visitante = calcular_odds_justas(xg_casa, xg_visitante)

    # 2. Converte para Odds (Odd = 1 / Probabilidade)
    odd_justa_casa = 1 / p_casa

    print(f"\nProbabilidade Real (Modelo): {p_casa:.1%}")
    print(f"Odd Justa (Modelo): {odd_justa_casa:.2f}")
    print(f"Odd Oferecida (Bet365/Pinnacle): {odd_mercado_casa:.2f}")

    # 3. Calculo de EV (Secao 1.1 do texto)
    ev = (odd_mercado_casa / odd_justa_casa) - 1

    if ev > 0:
        print(f">> OPORTUNIDADE DE VALOR! EV: +{ev:.1%}")
        print("Recomendacao: APOSTAR (Respeitando Kelly)")
    else:
        print(f">> Sem valor. O mercado esta pagando menos do que devia.")

# --- SIMULACAO (Isso e o que o Bot faria automaticamente) ---

if __name__ == "__main__":
    # Exemplo 1: Manchester City vs Arsenal (Jogo Equilibrado)
    # O City tem xG esperado de 1.8 e Arsenal 1.2
    verificar_valor("Man City", "Arsenal", 1.80, 1.20, 2.10)

    # Exemplo 2: Liverpool vs Luton (Massacre provavel)
    # Liverpool xG 3.1 | Luton xG 0.5
    # Mercado pagando 1.15 no Liverpool
    verificar_valor("Liverpool", "Luton", 3.10, 0.50, 1.15)
