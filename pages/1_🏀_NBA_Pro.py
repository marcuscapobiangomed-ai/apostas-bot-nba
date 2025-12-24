import streamlit as st
import pandas as pd
from datetime import datetime
from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.endpoints import leaguestandings

# --- CONFIGURACAO VISUAL PREMIUM (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; font-family: 'Segoe UI', sans-serif; }

    /* Cartao do Jogo */
    .game-card {
        background: linear-gradient(145deg, #1e2229, #16191f);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #303642;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }

    /* Placar e Texto */
    .score-big { font-size: 2.2em; font-weight: 800; color: white; text-align: center; line-height: 1.1; }
    .team-name { font-size: 1.0em; font-weight: 600; color: #a0a0a0; text-transform: uppercase; letter-spacing: 1px; text-align: center; }
    .game-meta { font-size: 0.8em; color: #00ff00; text-align: center; margin-bottom: 10px; font-weight: bold; }

    /* Badge de Rating */
    .rating-badge {
        background-color: #333;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8em;
        color: #ddd;
        font-weight: bold;
        border: 1px solid #444;
    }

    /* Caixas de Aposta */
    .bet-box { background-color: #1a2e1a; border-left: 4px solid #00cc00; padding: 15px; margin-top: 15px; border-radius: 4px; }
    .tutorial-box { background-color: #262730; padding: 10px; border-radius: 5px; border-left: 4px solid #4da6ff; margin-top: 10px; font-size: 0.9em;}
    </style>
""", unsafe_allow_html=True)

# --- 1. DADOS DE BACKUP E JOGADORES ---
BACKUP_RATINGS = {
    "Celtics": 10.0, "Thunder": 8.5, "Timberwolves": 7.0, "Nuggets": 7.0, "Clippers": 6.0, "Knicks": 5.5,
    "76ers": 5.0, "Bucks": 4.5, "Pelicans": 4.0, "Suns": 4.0, "Cavaliers": 4.0, "Mavericks": 3.5,
    "Heat": 3.0, "Pacers": 2.5, "Kings": 2.0, "Magic": 2.0, "Warriors": 2.0, "Lakers": 1.5,
    "Rockets": 1.0, "Hawks": -1.0, "Bulls": -1.5, "Nets": -2.0, "Jazz": -3.0, "Raptors": -3.5,
    "Grizzlies": -4.0, "Spurs": -5.0, "Hornets": -6.0, "Trail Blazers": -7.0, "Pistons": -8.0, "Wizards": -9.0
}

DB_JOGADORES = {
    "Nikola Jokic": {"impact": 8.5, "team": "Nuggets"}, "Luka Doncic": {"impact": 7.0, "team": "Mavericks"},
    "Giannis Antetokounmpo": {"impact": 6.5, "team": "Bucks"}, "Shai Gilgeous-Alexander": {"impact": 6.5, "team": "Thunder"},
    "Joel Embiid": {"impact": 6.0, "team": "76ers"}, "Jayson Tatum": {"impact": 5.0, "team": "Celtics"},
    "Stephen Curry": {"impact": 5.0, "team": "Warriors"}, "LeBron James": {"impact": 4.5, "team": "Lakers"},
    "Anthony Davis": {"impact": 4.5, "team": "Lakers"}, "Kevin Durant": {"impact": 4.5, "team": "Suns"},
    "Devin Booker": {"impact": 3.5, "team": "Suns"}, "Anthony Edwards": {"impact": 4.5, "team": "Timberwolves"},
    "Jalen Brunson": {"impact": 3.5, "team": "Knicks"}, "Ja Morant": {"impact": 3.5, "team": "Grizzlies"},
    "Tyrese Haliburton": {"impact": 3.0, "team": "Pacers"}, "Donovan Mitchell": {"impact": 3.5, "team": "Cavaliers"},
    "Victor Wembanyama": {"impact": 4.5, "team": "Spurs"}, "Trae Young": {"impact": 3.0, "team": "Hawks"},
    "Damian Lillard": {"impact": 3.0, "team": "Bucks"}, "Jimmy Butler": {"impact": 3.0, "team": "Heat"},
    "Kawhi Leonard": {"impact": 3.0, "team": "Clippers"}, "Zion Williamson": {"impact": 2.5, "team": "Pelicans"},
    "De'Aaron Fox": {"impact": 2.0, "team": "Kings"}, "LaMelo Ball": {"impact": 2.0, "team": "Hornets"},
    "Kyrie Irving": {"impact": 2.5, "team": "Mavericks"}, "Bam Adebayo": {"impact": 2.5, "team": "Heat"},
    "Domantas Sabonis": {"impact": 2.5, "team": "Kings"}, "Paolo Banchero": {"impact": 1.5, "team": "Magic"},
    "Alperen Sengun": {"impact": 1.5, "team": "Rockets"}, "Derrick White": {"impact": 1.5, "team": "Celtics"},
    "Jrue Holiday": {"impact": 1.5, "team": "Celtics"}, "Jaylen Brown": {"impact": 1.5, "team": "Celtics"},
    "Karl-Anthony Towns": {"impact": 1.5, "team": "Knicks"}, "Tyrese Maxey": {"impact": 1.5, "team": "76ers"},
    "Paul George": {"impact": 2.5, "team": "76ers"}, "Cade Cunningham": {"impact": 1.5, "team": "Pistons"},
    "Jamal Murray": {"impact": 1.5, "team": "Nuggets"}, "Chet Holmgren": {"impact": 1.5, "team": "Thunder"},
    "Pascal Siakam": {"impact": 1.5, "team": "Pacers"}, "Lauri Markkanen": {"impact": 1.5, "team": "Jazz"}
}

# --- 2. FUNCOES AUTOMATICAS ---
@st.cache_data(ttl=86400)
def atualizar_power_ratings_auto():
    try:
        standings = leaguestandings.LeagueStandings(season='2024-25')
        df = standings.get_data_frames()[0]
        novos_ratings = {}
        for index, row in df.iterrows():
            team_name = row['TeamName']
            net_rating = row['PointsPG'] - row['OppPointsPG']
            novos_ratings[team_name] = round(net_rating, 1)
        return novos_ratings, "Online (Stats API)"
    except:
        return BACKUP_RATINGS, "Offline (Backup)"

@st.cache_data(ttl=60)
def carregar_jogos_nba():
    try:
        board = scoreboard.ScoreBoard()
        return board.get_dict()['scoreboard']['games']
    except:
        return []

def calcular_kelly(edge):
    if edge < 1.5: return "Sem Acao"
    if edge < 2.5: return "0.5 Unidade (Leve)"
    if edge < 4.0: return "1.0 Unidade (Padrao)"
    return "1.5 Unidades (Forte)"

# --- 3. BARRA LATERAL EDUCATIVA ---
with st.sidebar:
    st.header("Escola de Apostas")
    st.markdown("### O que e a Badge cinza?")
    st.info("E o **Net Rating**: O saldo medio de pontos do time na temporada.")
    st.markdown("### Como ler?")
    st.markdown("""
    * **+7.0+:** Elite
    * **+3.0 a +6.0:** Forte
    * **+1.0 a +2.9:** Mediano
    * **-1.0 a -5.0:** Fraco
    """)
    if st.button("Atualizar App"):
        st.cache_data.clear()
        st.rerun()

# --- 4. APP PRINCIPAL ---
st.title("NBA Auto-Quant v2.0")

POWER_RATINGS, status_ratings = atualizar_power_ratings_auto()
st.caption(f"Status do Robo: {status_ratings}")

jogos = carregar_jogos_nba()

if not jogos:
    st.info("Nenhum jogo encontrado agora.")
else:
    for jogo in jogos:
        home_team = jogo['homeTeam']['teamName']
        away_team = jogo['awayTeam']['teamName']
        home_score = jogo['homeTeam']['score']
        away_score = jogo['awayTeam']['score']
        status = jogo['gameStatusText'].strip()

        # Ratings
        r_home = POWER_RATINGS.get(home_team, BACKUP_RATINGS.get(home_team, 0.0))
        r_away = POWER_RATINGS.get(away_team, BACKUP_RATINGS.get(away_team, 0.0))

        # Modelo
        linha_justa = (r_home + 2.5) - r_away

        with st.container():
            # HTML DO CARTAO - unsafe_allow_html=True e OBRIGATORIO
            st.markdown(f"""
            <div class="game-card">
                <div class="game-meta">{status}</div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1; text-align: center;">
                        <div class="team-name">{away_team} <span class="rating-badge" title="Net Rating">{r_away:+.1f}</span></div>
                        <div class="score-big">{away_score}</div>
                    </div>
                    <div style="width: 50px; text-align: center; color: #555; font-weight: bold;">@</div>
                    <div style="flex: 1; text-align: center;">
                        <div class="team-name">{home_team} <span class="rating-badge" title="Net Rating">{r_home:+.1f}</span></div>
                        <div class="score-big">{home_score}</div>
                    </div>
                </div>
                <div style="margin-top: 15px; text-align: center; border-top: 1px solid #333; padding-top: 10px;">
                    <span style="color: #666; font-size: 0.8em;">PREVISAO DO MODELO:</span><br>
                    <span style="color: #4da6ff; font-weight: bold; font-size: 1.1em;">
                        {home_team} {-linha_justa:+.1f}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"Simular Aposta ({away_team} vs {home_team})"):
                c1, c2 = st.columns(2)
                with c1:
                    linha_mercado = st.number_input("Linha Bet365 (Casa)", value=float(round(-linha_justa * 2) / 2), step=0.5, key=f"s_{home_team}")
                with c2:
                    jogadores_time = [j for j, d in DB_JOGADORES.items() if d['team'] in [home_team, away_team]]
                    opcoes = ["Ninguem"] + sorted(jogadores_time) if jogadores_time else ["Sem estrelas mapeadas"]
                    jogador_out = st.selectbox("Quem esta OUT?", opcoes, key=f"p_{home_team}")

                impacto = 0
                if jogador_out not in ["Ninguem", "Sem estrelas mapeadas"]:
                    impacto = DB_JOGADORES[jogador_out]['impact']
                    linha_final = -linha_justa + impacto if DB_JOGADORES[jogador_out]['team'] == home_team else -linha_justa - impacto
                else:
                    linha_final = -linha_justa

                diff = linha_final - linha_mercado
                edge = abs(diff)

                st.write(f"Linha Justa Ajustada: **{home_team} {linha_final:+.1f}**")

                if edge >= 1.5:
                    stake = calcular_kelly(edge)
                    lado = home_team if diff < 0 else away_team
                    linha_aposta = linha_mercado if diff < 0 else linha_mercado * -1

                    st.markdown(f"""
                    <div class="bet-box">
                        <h3 style="margin:0; color: #00ff00;">OPORTUNIDADE: {lado} {linha_aposta:+.1f}</h3>
                        <p style="margin:5px 0 0 0; color: #ccc;">Aposte <b>{stake}</b> da sua unidade.</p>
                    </div>
                    <div class="tutorial-box">
                        <b>Motivo:</b> Vantagem matematica de <b>{edge:.1f} pontos</b> sobre a casa.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Mercado eficiente. Sem valor claro.")
