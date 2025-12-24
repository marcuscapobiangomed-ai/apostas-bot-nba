import streamlit as st
import pandas as pd
from datetime import datetime
from nba_api.live.nba.endpoints import scoreboard

# --- CONFIGURACAO VISUAL (CSS) ---
st.set_page_config(page_title="NBA Pro Quant", page_icon="🏀", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .game-card {
        background-color: #1c1f26;
        padding: 15px; border-radius: 10px;
        border: 1px solid #2d313a; margin-bottom: 15px;
    }
    .team-stats { font-size: 0.8em; color: #aaa; text-align: center; }
    .status-live { color: #00ff00; font-weight: bold; font-size: 0.8em; }
    .status-final { color: #888; font-size: 0.8em; }
    .score-box { font-size: 1.4em; font-weight: bold; text-align: center; color: white; }
    .team-name { font-size: 1.2em; font-weight: 600; color: #e0e0e0; }
    </style>
""", unsafe_allow_html=True)

# --- 1. CEREBRO QUANTITATIVO (POWER RATINGS) ---
# Net Rating Estimado (Diferencial de pontos por 100 posses) - Ajuste semanalmente!
POWER_RATINGS = {
    "Celtics": 10.5, "Thunder": 9.0, "Timberwolves": 7.5, "Nuggets": 7.0,
    "Clippers": 6.5, "Knicks": 5.5, "76ers": 5.0, "Bucks": 4.5,
    "Pelicans": 4.5, "Suns": 4.0, "Cavaliers": 4.0, "Mavericks": 3.5,
    "Heat": 3.0, "Pacers": 2.5, "Kings": 2.0, "Magic": 2.0,
    "Warriors": 2.0, "Lakers": 1.5, "Rockets": 1.0, "Hawks": -1.0,
    "Bulls": -1.5, "Nets": -2.0, "Jazz": -3.0, "Raptors": -3.5,
    "Grizzlies": -4.0, "Spurs": -5.0, "Hornets": -6.0, "Trail Blazers": -7.0,
    "Pistons": -8.0, "Wizards": -9.0
}

# Impacto de Jogadores (Tier List)
DB_JOGADORES = {
    "Nikola Jokic": {"impact": 8.5, "team": "Nuggets"},
    "Luka Doncic": {"impact": 7.0, "team": "Mavericks"},
    "Giannis Antetokounmpo": {"impact": 6.5, "team": "Bucks"},
    "Shai Gilgeous-Alexander": {"impact": 6.5, "team": "Thunder"},
    "Joel Embiid": {"impact": 6.0, "team": "76ers"},
    "Jayson Tatum": {"impact": 5.0, "team": "Celtics"},
    "Stephen Curry": {"impact": 5.0, "team": "Warriors"},
    "LeBron James": {"impact": 4.5, "team": "Lakers"},
    "Anthony Davis": {"impact": 4.5, "team": "Lakers"},
    "Kevin Durant": {"impact": 4.5, "team": "Suns"},
    "Devin Booker": {"impact": 3.5, "team": "Suns"},
    "Anthony Edwards": {"impact": 4.5, "team": "Timberwolves"},
    "Jalen Brunson": {"impact": 3.5, "team": "Knicks"},
    "Ja Morant": {"impact": 3.5, "team": "Grizzlies"},
    "Tyrese Haliburton": {"impact": 3.0, "team": "Pacers"},
    "Donovan Mitchell": {"impact": 3.5, "team": "Cavaliers"},
    "Victor Wembanyama": {"impact": 4.5, "team": "Spurs"},
    "Trae Young": {"impact": 3.0, "team": "Hawks"},
    "Damian Lillard": {"impact": 3.0, "team": "Bucks"},
    "Jimmy Butler": {"impact": 3.0, "team": "Heat"},
    "Kawhi Leonard": {"impact": 3.0, "team": "Clippers"},
    "Zion Williamson": {"impact": 2.5, "team": "Pelicans"},
    "De'Aaron Fox": {"impact": 2.0, "team": "Kings"},
    "LaMelo Ball": {"impact": 2.0, "team": "Hornets"},
    "Kyrie Irving": {"impact": 2.5, "team": "Mavericks"},
    "Bam Adebayo": {"impact": 2.5, "team": "Heat"},
    "Domantas Sabonis": {"impact": 2.5, "team": "Kings"},
    "Paolo Banchero": {"impact": 1.5, "team": "Magic"},
    "Alperen Sengun": {"impact": 1.5, "team": "Rockets"},
    "Derrick White": {"impact": 1.5, "team": "Celtics"},
    "Jrue Holiday": {"impact": 1.5, "team": "Celtics"},
    "Jaylen Brown": {"impact": 1.5, "team": "Celtics"},
    "Karl-Anthony Towns": {"impact": 1.5, "team": "Knicks"},
    "Tyrese Maxey": {"impact": 1.5, "team": "76ers"},
    "Paul George": {"impact": 2.5, "team": "76ers"},
    "Cade Cunningham": {"impact": 1.5, "team": "Pistons"},
    "Jamal Murray": {"impact": 1.5, "team": "Nuggets"},
    "Chet Holmgren": {"impact": 1.5, "team": "Thunder"},
    "Pascal Siakam": {"impact": 1.5, "team": "Pacers"},
    "Lauri Markkanen": {"impact": 1.5, "team": "Jazz"}
}

# --- 2. FUNCOES ---
@st.cache_data(ttl=60)
def carregar_jogos_nba():
    try:
        board = scoreboard.ScoreBoard()
        games = board.get_dict()['scoreboard']['games']
        return games
    except:
        return []

def calcular_linha_justa_base(time_casa, time_visitante):
    # Formula: (Rating Casa + Vantagem Casa) - Rating Visitante
    # Vantagem de Casa Padrao = 2.5 pontos
    rating_casa = POWER_RATINGS.get(time_casa, 0)
    rating_visitante = POWER_RATINGS.get(time_visitante, 0)

    linha_raw = (rating_casa + 2.5) - rating_visitante
    # O resultado e quantos pontos o Casa vence. Invertemos para Spread (ex: Vence por 5 = Spread -5)
    return -linha_raw

# --- 3. INTERFACE ---
st.title("🏀 NBA Pro Quant")
st.caption("Power Ratings + Steam Chasing + Contexto")

if st.button("🔄 Atualizar Dados", width="stretch"):
    st.cache_data.clear()
    st.rerun()

jogos = carregar_jogos_nba()

if not jogos:
    st.warning("Nenhum jogo encontrado.")
else:
    for jogo in jogos:
        home_team = jogo['homeTeam']['teamName']
        away_team = jogo['awayTeam']['teamName']
        home_score = jogo['homeTeam']['score']
        away_score = jogo['awayTeam']['score']
        home_rec = f"{jogo['homeTeam']['wins']}-{jogo['homeTeam']['losses']}"
        away_rec = f"{jogo['awayTeam']['wins']}-{jogo['awayTeam']['losses']}"
        status = jogo['gameStatusText'].strip()

        # Calculo da Linha Justa Inicial (Modelo)
        linha_modelo = calcular_linha_justa_base(home_team, away_team)

        # Filtro de Jogadores
        jogadores_no_jogo = []
        for jogador, dados in DB_JOGADORES.items():
            if dados['team'] == home_team or dados['team'] == away_team:
                jogadores_no_jogo.append(jogador)
        jogadores_no_jogo.sort()

        # UI do Cartao
        with st.container():
            st.markdown(f"""
            <div class="game-card">
                <div style="display: flex; justify-content: space-between; color: #888; font-size: 0.8em; margin-bottom: 5px;">
                    <span>{away_rec}</span>
                    <span>{status}</span>
                    <span>{home_rec}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: center; width: 40%;">
                        <div class="team-name">{away_team}</div>
                        <div class="score-box">{away_score}</div>
                    </div>
                    <div style="font-weight: bold; color: #555;">@</div>
                    <div style="text-align: center; width: 40%;">
                        <div class="team-name">{home_team}</div>
                        <div class="score-box">{home_score}</div>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 10px; padding: 5px; background-color: #262a33; border-radius: 5px;">
                    <span style="color: #aaa; font-size: 0.9em;">Linha Justa (Modelo): </span>
                    <span style="color: #4da6ff; font-weight: bold;">{home_team} {linha_modelo:+.1f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Calculadora Avancada
            with st.expander(f"📊 Analisar Valor ({away_team} vs {home_team})"):
                c1, c2 = st.columns([1, 1])

                with c1:
                    linha_mercado = st.number_input("Linha da Casa (Spread)", value=float(round(linha_modelo * 2) / 2), step=0.5, key=f"s_{home_team}", help="Odd da Bet365/Pinnacle")
                with c2:
                    opcoes = ["Ninguem"] + jogadores_no_jogo if jogadores_no_jogo else ["Sem estrelas"]
                    jogador_out = st.selectbox("Quem esta OUT?", opcoes, key=f"p_{home_team}")

                # Logica de Calculo
                impacto = 0
                if jogador_out != "Ninguem" and jogador_out != "Sem estrelas":
                    impacto = DB_JOGADORES[jogador_out]['impact']
                    # Se o jogador for do time da CASA, o time da casa PIORA (Spread sobe, ex: -5 vira -1)
                    # Se for VISITANTE, o time da casa MELHORA (Spread desce, ex: -5 vira -9)
                    if DB_JOGADORES[jogador_out]['team'] == home_team:
                        linha_modelo_ajustada = linha_modelo + impacto
                    else:
                        linha_modelo_ajustada = linha_modelo - impacto
                else:
                    linha_modelo_ajustada = linha_modelo

                # Comparacao
                diff = linha_modelo_ajustada - linha_mercado

                st.divider()
                st.caption(f"Modelo Ajustado: {home_team} {linha_modelo_ajustada:+.1f}")

                # Matriz de Decisao
                # Se Modelo diz -7 e Mercado diz -4 -> Valor no Favorito (Home)
                # Se Modelo diz -2 e Mercado diz -5 -> Valor no Azarao (Away)

                # Diferenca significativa (> 1.5 pontos)
                if abs(diff) >= 1.5:
                    st.success("🔥 OPORTUNIDADE DETECTADA")
                    if diff < 0:  # Modelo (-7) e menor que Mercado (-4) -> Home e muito mais forte
                        st.write(f"Aposte em: **{home_team} {linha_mercado:+.1f}**")
                        st.write(f"Edge (Vantagem): {abs(diff):.1f} pontos")
                    else:  # Modelo (-2) e maior que Mercado (-5) -> Away deveria perder por menos
                        st.write(f"Aposte em: **{away_team} {linha_mercado*-1:+.1f}**")
                        st.write(f"Edge (Vantagem): {abs(diff):.1f} pontos")
                else:
                    st.info("⚖️ Linhas Justas. Sem valor claro no pre-live.")
