import streamlit as st
import pandas as pd
from datetime import datetime
from nba_api.live.nba.endpoints import scoreboard

# --- CONFIGURACAO VISUAL (CSS) ---
st.set_page_config(page_title="NBA Steam Chaser", page_icon="🏀", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .game-card {
        background-color: #1c1f26;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #2d313a;
        margin-bottom: 15px;
    }
    .status-live { color: #00ff00; font-weight: bold; font-size: 0.8em; }
    .status-final { color: #888; font-size: 0.8em; }
    .score-box { font-size: 1.2em; font-weight: bold; text-align: center; }
    .team-name { font-size: 1.1em; font-weight: 600; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- 1. BANCO DE DADOS INTELIGENTE (COM TIMES) ---
# Estrutura: "Nome": {"impact": Pontos, "team": "NomeDoTimeNaAPI"}

DB_JOGADORES = {
    # --- Tier 1: MVP Level ---
    "Nikola Jokic": {"impact": 8.5, "team": "Nuggets"},
    "Luka Doncic": {"impact": 7.0, "team": "Mavericks"},
    "Giannis Antetokounmpo": {"impact": 6.5, "team": "Bucks"},
    "Shai Gilgeous-Alexander": {"impact": 6.5, "team": "Thunder"},
    "Joel Embiid": {"impact": 6.0, "team": "76ers"},

    # --- Tier 2: Superstars ---
    "Jayson Tatum": {"impact": 5.0, "team": "Celtics"},
    "Stephen Curry": {"impact": 5.0, "team": "Warriors"},
    "LeBron James": {"impact": 4.5, "team": "Lakers"},
    "Kevin Durant": {"impact": 4.5, "team": "Suns"},
    "Anthony Davis": {"impact": 4.5, "team": "Lakers"},
    "Victor Wembanyama": {"impact": 4.5, "team": "Spurs"},
    "Anthony Edwards": {"impact": 4.5, "team": "Timberwolves"},

    # --- Tier 3 & 4: All-Stars/High Impact ---
    "Devin Booker": {"impact": 3.5, "team": "Suns"},
    "Donovan Mitchell": {"impact": 3.5, "team": "Cavaliers"},
    "Jalen Brunson": {"impact": 3.5, "team": "Knicks"},
    "Ja Morant": {"impact": 3.5, "team": "Grizzlies"},
    "Trae Young": {"impact": 3.0, "team": "Hawks"},
    "Damian Lillard": {"impact": 3.0, "team": "Bucks"},
    "Tyrese Haliburton": {"impact": 3.0, "team": "Pacers"},
    "Jimmy Butler": {"impact": 3.0, "team": "Heat"},
    "Kawhi Leonard": {"impact": 3.0, "team": "Clippers"},
    "Zion Williamson": {"impact": 2.5, "team": "Pelicans"},
    "Bam Adebayo": {"impact": 2.5, "team": "Heat"},
    "Domantas Sabonis": {"impact": 2.5, "team": "Kings"},
    "Kyrie Irving": {"impact": 2.5, "team": "Mavericks"},
    "Paul George": {"impact": 2.5, "team": "76ers"},
    "LaMelo Ball": {"impact": 2.0, "team": "Hornets"},
    "De'Aaron Fox": {"impact": 2.0, "team": "Kings"},
    "Pascal Siakam": {"impact": 1.5, "team": "Pacers"},
    "Chet Holmgren": {"impact": 1.5, "team": "Thunder"},
    "Derrick White": {"impact": 1.5, "team": "Celtics"},
    "Jrue Holiday": {"impact": 1.5, "team": "Celtics"},
    "Jamal Murray": {"impact": 1.5, "team": "Nuggets"},
    "Jaylen Brown": {"impact": 1.5, "team": "Celtics"},
    "Karl-Anthony Towns": {"impact": 1.5, "team": "Knicks"},
    "Tyrese Maxey": {"impact": 1.5, "team": "76ers"},
    "Paolo Banchero": {"impact": 1.5, "team": "Magic"},
    "Cade Cunningham": {"impact": 1.5, "team": "Pistons"},
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

# --- 3. INTERFACE PRINCIPAL ---
st.title("🏀 NBA Steam Chaser")
st.caption("Monitor de Oportunidades e Lesoes")

if st.button("🔄 Atualizar Placares", width="stretch"):
    st.cache_data.clear()
    st.rerun()

jogos = carregar_jogos_nba()

if not jogos:
    st.warning("Nenhum jogo encontrado agora.")
else:
    for jogo in jogos:
        # Dados do Jogo
        home_team = jogo['homeTeam']['teamName']
        away_team = jogo['awayTeam']['teamName']
        home_score = jogo['homeTeam']['score']
        away_score = jogo['awayTeam']['score']
        status = jogo['gameStatusText'].strip()

        # Filtro Inteligente: Achar jogadores SOMENTE destes dois times
        jogadores_no_jogo = []
        for jogador, dados in DB_JOGADORES.items():
            if dados['team'] == home_team or dados['team'] == away_team:
                jogadores_no_jogo.append(jogador)

        jogadores_no_jogo.sort()

        # Formatacao Visual
        cor_status = "status-final"
        if "ET" in status or "PM" in status.upper() or "AM" in status.upper():
            icone = "📅"
        elif "Final" in status:
            icone = "🏁"
        else:
            icone = "🔴 AO VIVO"
            cor_status = "status-live"

        # --- CARTAO DO JOGO ---
        with st.container():
            st.markdown(f"""
            <div class="game-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span class="{cor_status}">{icone} {status}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: center; width: 40%;">
                        <div class="team-name">{away_team}</div>
                        <div class="score-box">{away_score}</div>
                    </div>
                    <div style="color: #666; font-weight: bold;">@</div>
                    <div style="text-align: center; width: 40%;">
                        <div class="team-name">{home_team}</div>
                        <div class="score-box">{home_score}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- CALCULADORA INTELIGENTE ---
            with st.expander(f"💰 Simular Lesao ({away_team} vs {home_team})"):

                c1, c2 = st.columns([1, 1.5])
                with c1:
                    linha_mercado = st.number_input("Linha (Spread)", value=-4.5, step=0.5, key=f"s_{home_team}")
                with c2:
                    # Filtro inteligente: so mostra jogadores dos times em campo
                    if not jogadores_no_jogo:
                        opcoes = ["Sem estrelas mapeadas"]
                        desabilitado = True
                    else:
                        opcoes = ["Selecione..."] + jogadores_no_jogo
                        desabilitado = False

                    jogador_out = st.selectbox("Quem esta OUT?", opcoes, disabled=desabilitado, key=f"p_{home_team}")

                # Resultado
                if jogador_out != "Selecione..." and jogador_out != "Sem estrelas mapeadas":
                    impacto = DB_JOGADORES[jogador_out]['impact']
                    nova_linha = linha_mercado + impacto
                    diff = abs(nova_linha - linha_mercado)

                    st.divider()

                    if diff >= 1.5:
                        st.success(f"🔥 **ALERTA DE VALOR!**")
                        st.markdown(f"""
                        O mercado mudou **{diff} pontos** (Impacto do {jogador_out}).
                        <br>Nova Linha Justa: **{nova_linha:+.1f}**
                        <br>👉 **APOSTE CONTRA A LINHA ANTIGA**
                        """, unsafe_allow_html=True)
                    else:
                        st.warning(f"⚠️ Impacto Baixo ({diff} pts)")
                        st.markdown(f"Linha justa ajustada: **{nova_linha:+.1f}**")
