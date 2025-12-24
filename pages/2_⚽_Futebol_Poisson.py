"""
Dashboard de Apostas - Modelo de Poisson
Aplicativo visual para analise de valor em apostas de futebol
"""

import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import poisson

# Funcoes do modelo
def calcular_probabilidades(xg_casa: float, xg_visitante: float, max_gols: int = 6) -> dict:
    """Calcula probabilidades usando Poisson"""
    probs_casa = poisson.pmf(np.arange(max_gols), xg_casa)
    probs_visitante = poisson.pmf(np.arange(max_gols), xg_visitante)

    prob_placar = np.outer(probs_casa, probs_visitante)

    prob_vitoria_casa = np.sum(np.tril(prob_placar, -1))
    prob_empate = np.sum(np.diag(prob_placar))
    prob_vitoria_visitante = np.sum(np.triu(prob_placar, 1))

    return {
        'casa': prob_vitoria_casa,
        'empate': prob_empate,
        'visitante': prob_vitoria_visitante,
        'matriz': prob_placar
    }

def calcular_ev(prob: float, odd_mercado: float) -> float:
    """Calcula o Valor Esperado"""
    return (prob * odd_mercado) - 1

# Titulo
st.title("⚽ Modelo de Poisson - Analise de Apostas")
st.markdown("**Premier League - Calculadora de Valor Esperado (+EV)**")
st.markdown("---")

# Layout em colunas
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Dados da Partida")

    time_casa = st.text_input("Time da Casa", value="Manchester City")
    time_visitante = st.text_input("Time Visitante", value="Arsenal")

    st.markdown("**Expected Goals (xG)**")
    xg_casa = st.slider("xG Time Casa", 0.5, 4.0, 1.8, 0.1)
    xg_visitante = st.slider("xG Time Visitante", 0.5, 4.0, 1.2, 0.1)

with col2:
    st.subheader("💰 Odds de Mercado")

    odd_casa = st.number_input("Odd Vitoria Casa", min_value=1.01, max_value=20.0, value=2.10, step=0.05)
    odd_empate = st.number_input("Odd Empate", min_value=1.01, max_value=20.0, value=3.40, step=0.05)
    odd_visitante = st.number_input("Odd Vitoria Visitante", min_value=1.01, max_value=20.0, value=3.50, step=0.05)

st.markdown("---")

# Calcular probabilidades
probs = calcular_probabilidades(xg_casa, xg_visitante)

# Calcular odds justas
odd_justa_casa = 1 / probs['casa'] if probs['casa'] > 0 else float('inf')
odd_justa_empate = 1 / probs['empate'] if probs['empate'] > 0 else float('inf')
odd_justa_visitante = 1 / probs['visitante'] if probs['visitante'] > 0 else float('inf')

# Calcular EVs
ev_casa = calcular_ev(probs['casa'], odd_casa)
ev_empate = calcular_ev(probs['empate'], odd_empate)
ev_visitante = calcular_ev(probs['visitante'], odd_visitante)

# Resultados
st.subheader(f"📈 Resultados: {time_casa} vs {time_visitante}")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"### {time_casa}")
    st.metric("Probabilidade", f"{probs['casa']*100:.1f}%")
    st.metric("Odd Justa", f"{odd_justa_casa:.2f}")
    st.metric("Odd Mercado", f"{odd_casa:.2f}")

    if ev_casa > 0:
        st.success(f"✅ +EV: {ev_casa*100:.1f}%")
        st.markdown("**APOSTAR!**")
    else:
        st.error(f"❌ EV: {ev_casa*100:.1f}%")

with col2:
    st.markdown("### Empate")
    st.metric("Probabilidade", f"{probs['empate']*100:.1f}%")
    st.metric("Odd Justa", f"{odd_justa_empate:.2f}")
    st.metric("Odd Mercado", f"{odd_empate:.2f}")

    if ev_empate > 0:
        st.success(f"✅ +EV: {ev_empate*100:.1f}%")
        st.markdown("**APOSTAR!**")
    else:
        st.error(f"❌ EV: {ev_empate*100:.1f}%")

with col3:
    st.markdown(f"### {time_visitante}")
    st.metric("Probabilidade", f"{probs['visitante']*100:.1f}%")
    st.metric("Odd Justa", f"{odd_justa_visitante:.2f}")
    st.metric("Odd Mercado", f"{odd_visitante:.2f}")

    if ev_visitante > 0:
        st.success(f"✅ +EV: {ev_visitante*100:.1f}%")
        st.markdown("**APOSTAR!**")
    else:
        st.error(f"❌ EV: {ev_visitante*100:.1f}%")

st.markdown("---")

# Matriz de placares
st.subheader("🎯 Matriz de Probabilidades de Placares")

matriz = probs['matriz']
df_matriz = pd.DataFrame(
    matriz * 100,
    index=[f"{time_casa} {i}" for i in range(6)],
    columns=[f"{time_visitante} {i}" for i in range(6)]
)

st.dataframe(df_matriz.style.format("{:.2f}%").background_gradient(cmap='YlOrRd'), use_container_width=True)

# Top placares
st.subheader("🏆 Top 5 Placares Mais Provaveis")

placares = []
for i in range(6):
    for j in range(6):
        placares.append({
            'Placar': f"{i} x {j}",
            'Probabilidade': matriz[i, j] * 100
        })

df_placares = pd.DataFrame(placares).sort_values('Probabilidade', ascending=False).head(5)
df_placares['Probabilidade'] = df_placares['Probabilidade'].apply(lambda x: f"{x:.2f}%")
df_placares = df_placares.reset_index(drop=True)
df_placares.index = df_placares.index + 1

st.table(df_placares)

# Resumo
st.markdown("---")
st.subheader("📋 Resumo de Apostas com Valor")

apostas_valor = []
if ev_casa > 0:
    apostas_valor.append(f"✅ **{time_casa}** (EV: +{ev_casa*100:.1f}%)")
if ev_empate > 0:
    apostas_valor.append(f"✅ **Empate** (EV: +{ev_empate*100:.1f}%)")
if ev_visitante > 0:
    apostas_valor.append(f"✅ **{time_visitante}** (EV: +{ev_visitante*100:.1f}%)")

if apostas_valor:
    st.success("Apostas recomendadas:")
    for aposta in apostas_valor:
        st.markdown(aposta)
else:
    st.warning("⚠️ Nenhuma aposta com valor encontrada neste jogo.")

# Rodape
st.markdown("---")
st.caption("Modelo baseado na Distribuicao de Poisson | Use com responsabilidade")
