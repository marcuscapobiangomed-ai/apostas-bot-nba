import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
import time
from datetime import datetime

# --- CONFIGURACAO VISUAL ---
st.markdown("""
<style>
.stApp { background-color: #0e1117; font-family: 'Segoe UI', sans-serif; }
.game-card {
    background: linear-gradient(145deg, #1e2229, #16191f);
    padding: 20px; border-radius: 12px;
    border: 1px solid #303642; margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}
.metric-box { text-align: center; }
.metric-value { font-size: 1.5em; font-weight: bold; color: #4da6ff; }
.metric-label { font-size: 0.8em; color: #888; }
.status-badge {
    padding: 5px 10px; border-radius: 5px; font-size: 0.8em; font-weight: bold;
    display: inline-block; margin-bottom: 10px;
}
.status-ok { background-color: #1a2e1a; color: #00ff00; border: 1px solid #00ff00; }
.status-backup { background-color: #332b00; color: #ffcc00; border: 1px solid #ffcc00; }
</style>
""", unsafe_allow_html=True)

# --- 1. DADOS DE BACKUP (Para caso o site bloqueie) ---
BACKUP_STATS = {
    "Liverpool": [19, 45, 19], "Arsenal": [19, 42, 18], "Man City": [19, 48, 20],
    "Aston Villa": [19, 30, 25], "Chelsea": [19, 35, 22], "Newcastle": [19, 32, 21],
    "Man Utd": [19, 26, 25], "Tottenham": [19, 38, 28], "Brighton": [19, 28, 28],
    "Nott'm Forest": [19, 22, 25], "Brentford": [19, 30, 30], "West Ham": [19, 26, 32],
    "Bournemouth": [19, 24, 28], "Fulham": [19, 22, 26], "Crystal Palace": [19, 20, 28],
    "Everton": [19, 18, 30], "Wolves": [19, 20, 35], "Leicester City": [19, 20, 38],
    "Ipswich Town": [19, 18, 40], "Southampton": [19, 15, 42]
}

# --- 2. MOTOR DE DADOS AO VIVO ---
@st.cache_data(ttl=600)
def obter_dados_live():
    """Baixa a tabela atualizada com tecnica anti-cache."""
    timestamp_request = int(time.time())
    url = f"https://fbref.com/en/comps/9/Premier-League-Stats?nocache={timestamp_request}"

    stats = {}
    hora_atual = datetime.now().strftime("%H:%M:%S")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=6)

        if response.status_code == 200:
            dfs = pd.read_html(response.text)
            tabela = dfs[0]
            for index, row in tabela.iterrows():
                time_nome = row['Squad']
                jogos = row['MP']
                gf = row['GF']
                ga = row['GA']
                stats[time_nome] = [jogos, gf, ga]
            return stats, "online", hora_atual
    except Exception:
        pass

    return BACKUP_STATS, "backup", hora_atual

# --- 3. CALCULO DE POISSON ---
def calcular_probs(time_casa, time_fora, stats):
    # Tratamento de erro para times nao encontrados
    def get_stat(t):
        if t in stats:
            return stats[t]
        for k in stats.keys():
            if t in k or k in t:
                return stats[k]
        return [1, 1, 1]

    stat_c = get_stat(time_casa)
    stat_f = get_stat(time_fora)

    # Medias da Liga
    dados = list(stats.values())
    total_jogos = sum([d[0] for d in dados]) / 2
    total_gols = sum([d[1] for d in dados])
    media_liga = total_gols / (total_jogos * 2) if total_jogos > 0 else 1.5

    j_c, gf_c, ga_c = stat_c
    j_f, gf_f, ga_f = stat_f

    atk_casa = (gf_c / j_c) / media_liga
    def_casa = (ga_c / j_c) / media_liga
    atk_fora = (gf_f / j_f) / media_liga
    def_fora = (ga_f / j_f) / media_liga

    xg_casa = atk_casa * def_fora * media_liga * 1.15
    xg_fora = atk_fora * def_casa * media_liga * 0.85

    prob_c, prob_e, prob_f = 0, 0, 0
    for i in range(10):
        for j in range(10):
            p = poisson.pmf(i, xg_casa) * poisson.pmf(j, xg_fora)
            if i > j:
                prob_c += p
            elif i == j:
                prob_e += p
            else:
                prob_f += p

    return xg_casa, xg_fora, prob_c, prob_e, prob_f

# --- 4. INTERFACE ---
st.title("Premier League Live-Quant")

with st.sidebar:
    st.header("Central de Controle")
    if st.button("FORCAR ATUALIZACAO AGORA", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Isso ignora o cache e tenta baixar dados frescos.")

stats, status, hora = obter_dados_live()

if status == "online":
    st.markdown(f'<div class="status-badge status-ok">ONLINE: DADOS DE {hora}</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="status-badge status-backup">MODO BACKUP (Erro na conexao)</div>', unsafe_allow_html=True)

times = sorted(list(stats.keys()))
idx_casa = next((i for i, t in enumerate(times) if "City" in t), 0)
idx_fora = next((i for i, t in enumerate(times) if "Arsenal" in t), 1)

c1, c2 = st.columns(2)
t_casa = c1.selectbox("Mandante", times, index=idx_casa)
t_fora = c2.selectbox("Visitante", times, index=idx_fora)

if t_casa != t_fora:
    xg_c, xg_f, pc, pe, pf = calcular_probs(t_casa, t_fora, stats)

    odd_c = 1/pc if pc > 0 else 0
    odd_e = 1/pe if pe > 0 else 0
    odd_f = 1/pf if pf > 0 else 0

    # CARD VISUAL - HTML sem indentacao extra
    html_card = f"""<div class="game-card">
<div style="display:flex; justify-content:space-between; align-items:center;">
<div style="text-align:center; flex:1;">
<h3 style="color:white; margin:0;">{t_casa}</h3>
<div style="color:#aaa; font-size:0.8em;">Gols Feitos: {stats.get(t_casa,[0,0,0])[1]}</div>
</div>
<div style="font-weight:bold; font-size:1.2em; color:#555;">VS</div>
<div style="text-align:center; flex:1;">
<h3 style="color:white; margin:0;">{t_fora}</h3>
<div style="color:#aaa; font-size:0.8em;">Gols Feitos: {stats.get(t_fora,[0,0,0])[1]}</div>
</div>
</div>
<hr style="border-color:#333; margin: 15px 0;">
<div style="display:flex; justify-content:space-around; margin-bottom: 20px;">
<div class="metric-box">
<div class="metric-label">xG Esperado</div>
<div class="metric-value">{xg_c:.2f}</div>
</div>
<div class="metric-box">
<div class="metric-label">xG Esperado</div>
<div class="metric-value">{xg_f:.2f}</div>
</div>
</div>
<div style="background-color:#000; padding:15px; border-radius:8px; text-align:center;">
<div style="color:#888; font-size:0.8em; margin-bottom:10px; letter-spacing: 1px;">ODDS JUSTAS (FAIR LINES)</div>
<div style="display:flex; justify-content:space-between;">
<div style="flex:1; border-right:1px solid #333;"><span style="color:#0f0; font-size:1.4em;">{odd_c:.2f}</span><br><small style="color:#888;">Casa</small></div>
<div style="flex:1; border-right:1px solid #333;"><span style="color:#ccc; font-size:1.4em;">{odd_e:.2f}</span><br><small style="color:#888;">Empate</small></div>
<div style="flex:1;"><span style="color:#0f0; font-size:1.4em;">{odd_f:.2f}</span><br><small style="color:#888;">Fora</small></div>
</div>
</div>
</div>"""

    st.markdown(html_card, unsafe_allow_html=True)

    # Calculadora de EV
    st.markdown("### Calculadora de Valor (+EV)")
    st.caption("Insira as odds do mercado para encontrar valor")

    ev_col1, ev_col2, ev_col3 = st.columns(3)

    with ev_col1:
        odd_mercado_casa = st.number_input(f"Odd {t_casa}", value=round(odd_c, 2), step=0.05, key="odd_casa")
        ev_casa = (pc * odd_mercado_casa) - 1
        if ev_casa > 0:
            st.success(f"+EV: {ev_casa*100:.1f}% - VALOR!")
        else:
            st.error(f"EV: {ev_casa*100:.1f}%")

    with ev_col2:
        odd_mercado_empate = st.number_input("Odd Empate", value=round(odd_e, 2), step=0.05, key="odd_empate")
        ev_empate = (pe * odd_mercado_empate) - 1
        if ev_empate > 0:
            st.success(f"+EV: {ev_empate*100:.1f}% - VALOR!")
        else:
            st.error(f"EV: {ev_empate*100:.1f}%")

    with ev_col3:
        odd_mercado_fora = st.number_input(f"Odd {t_fora}", value=round(odd_f, 2), step=0.05, key="odd_fora")
        ev_fora = (pf * odd_mercado_fora) - 1
        if ev_fora > 0:
            st.success(f"+EV: {ev_fora*100:.1f}% - VALOR!")
        else:
            st.error(f"EV: {ev_fora*100:.1f}%")

    # Resumo de apostas com valor
    apostas_valor = []
    if ev_casa > 0:
        apostas_valor.append(f"**{t_casa}** @ {odd_mercado_casa:.2f} (+EV: {ev_casa*100:.1f}%)")
    if ev_empate > 0:
        apostas_valor.append(f"**Empate** @ {odd_mercado_empate:.2f} (+EV: {ev_empate*100:.1f}%)")
    if ev_fora > 0:
        apostas_valor.append(f"**{t_fora}** @ {odd_mercado_fora:.2f} (+EV: {ev_fora*100:.1f}%)")

    if apostas_valor:
        st.markdown("---")
        st.success("**Apostas com Valor Encontradas:**")
        for aposta in apostas_valor:
            st.markdown(f"- {aposta}")

    # PLACARES PROVAVEIS
    with st.expander("Ver Placares Mais Provaveis"):
        lista_placares = []
        for i in range(6):
            for j in range(6):
                prob = poisson.pmf(i, xg_c) * poisson.pmf(j, xg_f)
                lista_placares.append((f"{i} - {j}", prob))

        lista_placares.sort(key=lambda x: x[1], reverse=True)

        st.write("Top 5 Resultados Matematicos:")
        for placar, prob in lista_placares[:5]:
            st.write(f"**{placar}** - {prob*100:.1f}%")

else:
    st.error("Selecione times diferentes.")

st.markdown("---")
st.caption("Modelo de Poisson | Premier League 24/25 | Dados: FBref")
