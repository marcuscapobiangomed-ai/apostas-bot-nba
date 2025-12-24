import streamlit as st
import pandas as pd
import requests
from nba_api.stats.endpoints import leaguestandings

# --- CONFIGURACAO INICIAL ---
# Removido st.set_page_config pois esta no Home.py

# --- CHAVE DA 'THE ODDS API' ---
API_KEY = "e6a32983f406a1fbf89fda109149ac15"

# --- CONFIGURACAO VISUAL (CSS) ---
st.markdown("""
<style>
.stApp { background-color: #0e1117; font-family: 'Segoe UI', sans-serif; }
.game-card {
    background: linear-gradient(145deg, #1e2229, #16191f);
    padding: 20px; border-radius: 12px;
    border: 1px solid #303642; margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}
.team-name { font-size: 1.1em; font-weight: 600; color: #e0e0e0; text-align: center; }
.vs { color: #555; font-weight: bold; text-align: center; font-size: 0.9em; margin: 0 10px;}
.odds-box {
    background-color: #000; padding: 10px; border-radius: 8px; text-align: center; margin-top: 10px;
    border: 1px solid #333;
}
.val-box {
    background-color: #1a2e1a; border-left: 4px solid #00ff00; padding: 15px;
    margin-top: 10px; border-radius: 5px;
}
.badge {
    background-color: #333; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; color: #aaa;
}
</style>
""", unsafe_allow_html=True)

# --- 1. CEREBRO: POWER RATINGS (NBA API) ---
@st.cache_data(ttl=86400)
def get_nba_ratings():
    """Baixa Net Rating atualizado da NBA oficial"""
    try:
        standings = leaguestandings.LeagueStandings(season='2024-25')
        df = standings.get_data_frames()[0]
        ratings = {}
        for _, row in df.iterrows():
            team = row['TeamName']
            net = row['PointsPG'] - row['OppPointsPG']
            ratings[team] = round(net, 1)
        return ratings
    except:
        return {"Celtics": 10.5, "Thunder": 9.0, "Nuggets": 7.0, "Lakers": 1.5,
                "Cavaliers": 8.0, "Knicks": 5.5, "Bucks": 4.5, "Heat": 3.0}

# --- 2. MERCADO: ODDS REAIS (THE ODDS API) ---
def get_live_odds(api_key):
    """Baixa odds da Bet365/Pinnacle via API"""
    url = f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'
    params = {
        'api_key': api_key,
        'regions': 'us,eu',
        'markets': 'spreads',
        'oddsFormat': 'decimal',
        'bookmakers': 'bet365,pinnacle'
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.error("Erro de Chave: A API Key parece invalida.")
            return []
        elif response.status_code == 429:
            st.warning("Limite mensal de requisicoes atingido!")
            return []
        else:
            st.warning(f"Erro na API de Odds: {response.status_code}")
            return []
    except:
        return []

# --- 3. IMPACTO DE LESOES ---
DB_LESAO = {
    "Nikola Jokic": 8.5, "Luka Doncic": 7.0, "Giannis Antetokounmpo": 6.5,
    "SGA": 6.5, "Joel Embiid": 6.0, "Jayson Tatum": 5.0, "Steph Curry": 5.0,
    "LeBron James": 4.5, "Anthony Davis": 4.5, "Kevin Durant": 4.5,
    "Ja Morant": 4.0, "Tyrese Haliburton": 3.5, "Donovan Mitchell": 3.5
}

# --- 4. APP PRINCIPAL ---
st.title("NBA Quant Trader")
st.caption("Conectado: NBA Stats (Forca) + The Odds API (Mercado)")

# Carregar Ratings
RATINGS = get_nba_ratings()

# Botao de Atualizacao
if st.button("Escanear Mercado (Live)", type="primary"):
    st.cache_data.clear()
    st.rerun()

# Busca Odds
odds_data = get_live_odds(API_KEY)

if not odds_data:
    st.info("Nenhum jogo encontrado agora ou erro na conexao.")
else:
    st.success(f"{len(odds_data)} jogos encontrados no mercado.")

    for game in odds_data:
        home_team = game['home_team']
        away_team = game['away_team']
        start_time = pd.to_datetime(game['commence_time']).strftime('%H:%M')

        # Match de Ratings
        r_home = 0.0
        r_away = 0.0
        for nome_curto, rating in RATINGS.items():
            if nome_curto in home_team:
                r_home = rating
            if nome_curto in away_team:
                r_away = rating

        # 1. LINHA JUSTA DO MODELO
        fair_spread = (r_home + 2.5) - r_away
        fair_line = -fair_spread

        # 2. LINHA DO MERCADO
        market_line = None
        bookie_name = "N/A"

        sites = game.get('bookmakers', [])
        for site in sites:
            if site['key'] in ['bet365', 'pinnacle']:
                try:
                    market_line = site['markets'][0]['outcomes'][0]['point']
                    name_on_bet = site['markets'][0]['outcomes'][0]['name']

                    if name_on_bet != home_team:
                        market_line = -market_line

                    bookie_name = site['title']
                    break
                except:
                    pass

        if market_line is None:
            if sites:
                try:
                    market_line = sites[0]['markets'][0]['outcomes'][0]['point']
                    if sites[0]['markets'][0]['outcomes'][0]['name'] != home_team:
                        market_line = -market_line
                    bookie_name = sites[0]['title']
                except:
                    market_line = 0.0
            else:
                market_line = 0.0

        # --- EXIBICAO VISUAL ---
        with st.container():
            html_card = f"""<div class="game-card">
<div style="text-align:center; color:#888; font-size:0.8em; margin-bottom:5px;">Inicio: {start_time}</div>
<div style="display:flex; justify-content:center; align-items:center;">
<div style="flex:1; text-align:right;">
<div class="team-name">{away_team}</div>
<span class="badge">{r_away:+.1f}</span>
</div>
<div class="vs">@</div>
<div style="flex:1; text-align:left;">
<div class="team-name">{home_team}</div>
<span class="badge">{r_home:+.1f}</span>
</div>
</div>
<div class="odds-box">
<div style="display:flex; justify-content:space-around;">
<div>
<small style="color:#888">MEU MODELO (Justo)</small><br>
<span style="color:#4da6ff; font-weight:bold; font-size:1.2em;">{fair_line:+.1f}</span>
</div>
<div>
<small style="color:#888">REAL ({bookie_name})</small><br>
<span style="color:#fff; font-weight:bold; font-size:1.2em;">{market_line:+.1f}</span>
</div>
</div>
</div>
</div>"""
            st.markdown(html_card, unsafe_allow_html=True)

            # --- AREA DE AJUSTE E DECISAO ---
            with st.expander(f"Simular Lesao em {home_team} vs {away_team}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    jogador = st.selectbox("Quem esta OUT?", ["Ninguem"] + list(DB_LESAO.keys()), key=f"p_{home_team}")

                if jogador != "Ninguem":
                    impacto = DB_LESAO[jogador]
                    st.caption(f"Aplicando penalidade de {impacto} pontos na linha justa.")
                    fair_line_adj = fair_line + impacto
                else:
                    fair_line_adj = fair_line

                # CALCULO DE VALOR (EDGE)
                diff = abs(fair_line_adj - market_line)

                st.write(f"Linha Justa Ajustada: **{fair_line_adj:+.1f}**")

                if diff >= 1.5:
                    st.markdown(f"""<div class="val-box">
<b>OPORTUNIDADE (+EV)</b><br>
Diferenca de <b>{diff:.1f} pontos</b> entre voce e a casa.<br>
Mercado: {market_line} | Voce: {fair_line_adj:.1f}
</div>""", unsafe_allow_html=True)
                else:
                    st.info("Mercado eficiente. Sem valor claro nesta linha.")
