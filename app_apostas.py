import streamlit as st
import pandas as pd
from datetime import datetime
from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.endpoints import leaguestandings

# --- CONFIGURACAO VISUAL PREMIUM (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; font-family: 'Segoe UI', sans-serif; }
    .game-card {
        background: linear-gradient(145deg, #1e2229, #16191f);
        padding: 20px; border-radius: 12px;
        border: 1px solid #303642; margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .score-big { font-size: 2.2em; font-weight: 800; color: white; text-align: center; line-height: 1.1; }
    .team-name { font-size: 1.0em; font-weight: 600; color: #a0a0a0; text-transform: uppercase; letter-spacing: 1px; text-align: center; }
    .game-meta { font-size: 0.8em; color: #00ff00; text-align: center; margin-bottom: 10px; font-weight: bold; }
    .bet-box { background-color: #1a2e1a; border-left: 4px solid #00cc00; padding: 15px; margin-top: 15px; border-radius: 4px; }
    .rating-badge { background-color: #333; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; color: #888; }
    </style>
""", unsafe_allow_html=True)

# --- 1. BASE DE DADOS HIBRIDA (AUTOMATICA + BACKUP) ---

# Backup manual (caso a API de Stats falhe/bloqueie)
BACKUP_RATINGS = {
    "Celtics": 10.0, "Thunder": 8.5, "Timberwolves": 7.0, "Nuggets": 7.0,
    "Clippers": 6.0, "Knicks": 5.5, "76ers": 5.0, "Bucks": 4.5, "Pelicans": 4.0,
    "Suns": 4.0, "Cavaliers": 4.0, "Mavericks": 3.5, "Heat": 3.0, "Pacers": 2.5,
    "Kings": 2.0, "Magic": 2.0, "Warriors": 2.0, "Lakers": 1.5, "Rockets": 1.0,
    "Hawks": -1.0, "Bulls": -1.5, "Nets": -2.0, "Jazz": -3.0, "Raptors": -3.5,
    "Grizzlies": -4.0, "Spurs": -5.0, "Hornets": -6.0, "Trail Blazers": -7.0,
    "Pistons": -8.0, "Wizards": -9.0
}

# Database de Jogadores (Impacto no Spread)
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

# --- 2. FUNCOES DE AUTOMACAO ---

@st.cache_data(ttl=86400)  # Cache de 24 horas para nao ser bloqueado
def atualizar_power_ratings_auto():
    """Baixa a classificacao e calcula: (Pontos Feitos - Pontos Sofridos)"""
    try:
        # Tenta conectar na API de Stats
        standings = leaguestandings.LeagueStandings(season='2024-25')
        df = standings.get_data_frames()[0]

        # Cria dicionario novo: {'Lakers': 1.5, ...}
        novos_ratings = {}

        # O 'TeamName' da API geralmente vem como 'Lakers', 'Celtics', etc.
        for index, row in df.iterrows():
            team_name = row['TeamName']
            # Net Rating Simples = Media Pontos Feitos - Media Pontos Sofridos
            # As colunas da API sao 'PointsPG' e 'OppPointsPG'
            net_rating = row['PointsPG'] - row['OppPointsPG']
            novos_ratings[team_name] = round(net_rating, 1)

        return novos_ratings, "🟢 Online (Stats API)"

    except Exception as e:
        # Se falhar, usa o backup
        return BACKUP_RATINGS, "🟡 Offline (Backup Mode)"

@st.cache_data(ttl=60)
def carregar_jogos_nba():
    try:
        board = scoreboard.ScoreBoard()
        games = board.get_dict()['scoreboard']['games']
        return games
    except:
        return []

def calcular_kelly(edge):
    if edge < 1.5:
        return "Sem Acao"
    if edge < 2.5:
        return "0.5 Unidade"
    if edge < 4.0:
        return "1.0 Unidade"
    return "1.5 Unidades 🔥"

# --- 3. INICIALIZACAO E UI ---
st.title("🏀 NBA Auto-Quant")

# Carregar Ratings Automaticamente
POWER_RATINGS, status_ratings = atualizar_power_ratings_auto()

# Cabecalho de Status
c1, c2 = st.columns([3, 1])
with c1:
    st.caption(f"Power Ratings: {status_ratings}")
with c2:
    if st.button("🔄 Refresh", width="stretch"):
        st.cache_data.clear()
        st.rerun()

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

        # Busca Ratings (se nao achar o time na lista, assume 0.0)
        r_home = POWER_RATINGS.get(home_team, BACKUP_RATINGS.get(home_team, 0.0))
        r_away = POWER_RATINGS.get(away_team, BACKUP_RATINGS.get(away_team, 0.0))

        # Calculo Automatico
        linha_justa = (r_home + 2.5) - r_away

        # --- UI DO CARD ---
        with st.container():
            st.markdown(f"""
            <div class="game-card">
                <div class="game-meta">{status}</div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1; text-align: center;">
                        <div class="team-name">{away_team} <span class="rating-badge">{r_away:+.1f}</span></div>
                        <div class="score-big">{away_score}</div>
                    </div>
                    <div style="width: 50px; text-align: center; color: #555; font-weight: bold;">@</div>
                    <div style="flex: 1; text-align: center;">
                        <div class="team-name">{home_team} <span class="rating-badge">{r_home:+.1f}</span></div>
                        <div class="score-big">{home_score}</div>
                    </div>
                </div>
                <div style="margin-top: 15px; text-align: center; border-top: 1px solid #333; padding-top: 10px;">
                    <span style="color: #666; font-size: 0.8em;">MODELO AUTOMATICO:</span><br>
                    <span style="color: #4da6ff; font-weight: bold; font-size: 1.1em;">
                        {home_team} {-linha_justa:+.1f}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Calculadora
            with st.expander(f"⚡ Calcular Valor ({away_team} vs {home_team})"):
                c1, c2 = st.columns(2)
                with c1:
                    linha_mercado = st.number_input(
                        "Spread Atual (Casa)",
                        value=float(round(-linha_justa * 2) / 2),
                        step=0.5,
                        key=f"s_{home_team}"
                    )
                with c2:
                    # Filtro de Estrelas
                    jogadores_time = [j for j, d in DB_JOGADORES.items() if d['team'] in [home_team, away_team]]
                    opcoes = ["Ninguem"] + sorted(jogadores_time) if jogadores_time else ["Sem estrelas mapeadas"]
                    jogador_out = st.selectbox("Quem esta OUT?", opcoes, key=f"p_{home_team}")

                # Ajuste de Lesao
                impacto = 0
                if jogador_out not in ["Ninguem", "Sem estrelas mapeadas"]:
                    impacto = DB_JOGADORES[jogador_out]['impact']
                    if DB_JOGADORES[jogador_out]['team'] == home_team:
                        linha_final = -linha_justa + impacto
                    else:
                        linha_final = -linha_justa - impacto
                else:
                    linha_final = -linha_justa

                # Resultado
                diff = linha_final - linha_mercado
                edge = abs(diff)

                st.divider()
                st.write(f"Linha Final: **{home_team} {linha_final:+.1f}**")

                if edge >= 1.5:
                    stake = calcular_kelly(edge)
                    lado = f"{home_team} {linha_mercado:+.1f}" if diff < 0 else f"{away_team} {linha_mercado*-1:+.1f}"

                    st.markdown(f"""
                    <div class="bet-box">
                        <h3 style="margin:0; color: #00ff00;">💰 APOSTA: {lado}</h3>
                        <p style="margin:5px 0 0 0; color: #ccc;">Edge: {edge:.1f} | Stake: <b>{stake}</b></p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Sem valor claro nesta linha.")
