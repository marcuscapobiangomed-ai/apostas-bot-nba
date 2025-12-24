import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from nba_api.live.nba.endpoints import scoreboard

# --- CONFIGURACAO VISUAL PREMIUM (CSS) ---
st.set_page_config(page_title="NBA Pro Quant v2", page_icon="🏀", layout="centered")

st.markdown("""
    <style>
    /* Fundo e Fonte */
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

    /* Placar Gigante */
    .score-big {
        font-size: 2.2em;
        font-weight: 800;
        color: white;
        text-align: center;
        line-height: 1.1;
    }

    /* Nomes dos Times */
    .team-name {
        font-size: 1.0em;
        font-weight: 600;
        color: #a0a0a0;
        text-transform: uppercase;
        letter-spacing: 1px;
        text-align: center;
    }

    /* Status do Jogo */
    .game-meta {
        font-size: 0.8em;
        color: #00ff00;
        text-align: center;
        margin-bottom: 10px;
        font-weight: bold;
    }

    /* Badges (B2B, Lesao) */
    .badge-b2b {
        background-color: #ff4b4b;
        color: white;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.7em;
        font-weight: bold;
        margin-left: 5px;
    }

    /* Caixa de Sugestao (Kelly) */
    .bet-box {
        background-color: #1a2e1a;
        border-left: 4px solid #00cc00;
        padding: 15px;
        margin-top: 15px;
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. DADOS E LOGICA ---

# Power Ratings (Atualize semanalmente!)
POWER_RATINGS = {
    "Celtics": 10.0, "Thunder": 8.5, "Timberwolves": 7.0, "Nuggets": 7.0,
    "Clippers": 6.0, "Knicks": 5.5, "76ers": 5.0, "Bucks": 4.5,
    "Pelicans": 4.0, "Suns": 4.0, "Cavaliers": 4.0, "Mavericks": 3.5,
    "Heat": 3.0, "Pacers": 2.5, "Kings": 2.0, "Magic": 2.0,
    "Warriors": 2.0, "Lakers": 1.5, "Rockets": 1.0, "Hawks": -1.0,
    "Bulls": -1.5, "Nets": -2.0, "Jazz": -3.0, "Raptors": -3.5,
    "Grizzlies": -4.0, "Spurs": -5.0, "Hornets": -6.0, "Trail Blazers": -7.0,
    "Pistons": -8.0, "Wizards": -9.0
}

# Database de Jogadores e Impacto
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

# --- 2. FUNCOES AVANCADAS ---
@st.cache_data(ttl=60)
def carregar_jogos_nba():
    try:
        board = scoreboard.ScoreBoard()
        games = board.get_dict()['scoreboard']['games']
        return games
    except:
        return []

def calcular_kelly(edge):
    """
    Calcula o tamanho da aposta baseado na vantagem (Kelly Criterion Simplificado).
    Edge = Diferenca entre nossa linha e a do mercado.
    """
    if edge < 1.5:
        return "Sem Acao (Margem pequena)"
    if edge < 2.5:
        return "0.5 Unidade (Aposta Pequena)"
    if edge < 4.0:
        return "1.0 Unidade (Aposta Padrao)"
    return "1.5 Unidades (Aposta Forte 🔥)"

def detectar_b2b(team_name):
    # Simulacao: Em um app real, verificaria a data do ultimo jogo.
    # Aqui usamos uma lista manual ou retorna False.
    times_b2b = []
    return team_name in times_b2b

# --- 3. INTERFACE ---
st.title("🏀 NBA Pro Quant v2.0")
st.caption("Power Ratings • Steam Chasing • Kelly Criterion")

if st.button("🔄 Atualizar Odds & Placares", width="stretch"):
    st.cache_data.clear()
    st.rerun()

jogos = carregar_jogos_nba()

if not jogos:
    st.info("Nenhum jogo ao vivo ou agendado para agora.")
else:
    for jogo in jogos:
        home_team = jogo['homeTeam']['teamName']
        away_team = jogo['awayTeam']['teamName']
        home_score = jogo['homeTeam']['score']
        away_score = jogo['awayTeam']['score']
        status = jogo['gameStatusText'].strip()

        # Logica de Fadiga (Penalidade de B2B)
        penalty_home = -1.5 if detectar_b2b(home_team) else 0
        penalty_away = -1.5 if detectar_b2b(away_team) else 0

        # Calculo Linha Base
        rating_casa = POWER_RATINGS.get(home_team, 0) + penalty_home
        rating_visitante = POWER_RATINGS.get(away_team, 0) + penalty_away
        # HFA (Home Field Advantage) = +2.5
        linha_modelo_raw = (rating_casa + 2.5) - rating_visitante

        # UI: Cartao do Jogo
        with st.container():
            st.markdown(f"""
            <div class="game-card">
                <div class="game-meta">{status}</div>

                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1; text-align: center;">
                        <div class="team-name">{away_team}</div>
                        <div class="score-big">{away_score}</div>
                    </div>

                    <div style="width: 50px; text-align: center; color: #555; font-weight: bold; font-size: 1.2em;">@</div>

                    <div style="flex: 1; text-align: center;">
                        <div class="team-name">{home_team}</div>
                        <div class="score-big">{home_score}</div>
                    </div>
                </div>

                <div style="margin-top: 15px; text-align: center; border-top: 1px solid #333; padding-top: 10px;">
                    <span style="color: #666; font-size: 0.8em;">POWER RATING DIZ:</span><br>
                    <span style="color: #4da6ff; font-weight: bold; font-size: 1.1em;">
                        {home_team} {-linha_modelo_raw:+.1f}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Expander de Analise
            with st.expander(f"⚡ Analisar Valor & Aposta ({away_team} vs {home_team})"):

                # Inputs
                c1, c2 = st.columns(2)
                with c1:
                    linha_mercado = st.number_input(
                        "Spread da Casa (Bet365)",
                        value=float(round(-linha_modelo_raw * 2) / 2),
                        step=0.5,
                        key=f"s_{home_team}"
                    )
                with c2:
                    # Filtro de Jogadores
                    jogadores_no_jogo = [j for j, d in DB_JOGADORES.items() if d['team'] in [home_team, away_team]]
                    opcoes = ["Ninguem"] + sorted(jogadores_no_jogo) if jogadores_no_jogo else ["Sem estrelas"]
                    jogador_out = st.selectbox("Quem esta OUT?", opcoes, key=f"p_{home_team}")

                # Calculo Final
                impacto = 0
                if jogador_out not in ["Ninguem", "Sem estrelas"]:
                    impacto = DB_JOGADORES[jogador_out]['impact']
                    # Se jogador e do HOME, Home piora (Linha sobe, ex: -5 -> -1)
                    if DB_JOGADORES[jogador_out]['team'] == home_team:
                        linha_modelo_final = -linha_modelo_raw + impacto
                    else:
                        linha_modelo_final = -linha_modelo_raw - impacto
                else:
                    linha_modelo_final = -linha_modelo_raw

                # Veredito
                diff = linha_modelo_final - linha_mercado
                edge = abs(diff)

                st.divider()
                st.write(f"Linha Ajustada (Modelo): **{home_team} {linha_modelo_final:+.1f}**")

                if edge >= 1.5:
                    sugestao_kelly = calcular_kelly(edge)

                    # Decidir o lado
                    if diff < 0:  # Modelo (-7) < Mercado (-4) -> Home Stronger
                        lado = f"{home_team} {linha_mercado:+.1f}"
                    else:  # Modelo (-2) > Mercado (-5) -> Away Stronger
                        lado = f"{away_team} {linha_mercado*-1:+.1f}"

                    st.markdown(f"""
                    <div class="bet-box">
                        <h3 style="margin:0; color: #00ff00;">💰 APOSTA INDICADA</h3>
                        <p style="font-size: 1.2em; margin: 10px 0;">Pick: <b>{lado}</b></p>
                        <p style="margin:0; font-size: 0.9em; color: #ccc;">
                            Edge: {edge:.1f} pts<br>
                            Stake: <b>{sugestao_kelly}</b>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("⚖️ Sem valor claro. Linha justa.")
