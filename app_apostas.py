import streamlit as st
import pandas as pd
from datetime import datetime
from nba_api.live.nba.endpoints import scoreboard

# --- CONFIGURACAO VISUAL (CSS INJETADO) ---
st.set_page_config(page_title="NBA Steam Chaser", page_icon="🏀", layout="centered")

# CSS para deixar com cara de App Mobile
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
    }
    .game-card {
        background-color: #1c1f26;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #2d313a;
        margin-bottom: 15px;
    }
    .status-live {
        color: #00ff00;
        font-weight: bold;
        font-size: 0.8em;
    }
    .status-final {
        color: #888;
        font-size: 0.8em;
    }
    .score-box {
        font-size: 1.2em;
        font-weight: bold;
        text-align: center;
    }
    .team-name {
        font-size: 1.1em;
        font-weight: 600;
    }
    /* Remover padding excessivo do topo */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. BANCO DE DADOS DE IMPACTO (Tier List 2025) ---
IMPACTO_ESTRELAS = {
    # Tier 1: MVP Level
    "Nikola Jokic": 8.5, "Luka Doncic": 7.0, "Giannis Antetokounmpo": 6.5,
    "Shai Gilgeous-Alexander": 6.5, "Joel Embiid": 6.0,
    # Tier 2: Superstars
    "Jayson Tatum": 5.0, "Stephen Curry": 5.0, "LeBron James": 4.5,
    "Kevin Durant": 4.5, "Anthony Davis": 4.5, "Victor Wembanyama": 4.5,
    "Anthony Edwards": 4.5,
    # Tier 3 & 4 (Resumido para UI Limpa)
    "Devin Booker": 3.5, "Donovan Mitchell": 3.5, "Jalen Brunson": 3.5,
    "Ja Morant": 3.5, "Trae Young": 3.0, "Damian Lillard": 3.0,
    "Tyrese Haliburton": 3.0, "Jimmy Butler": 3.0, "Kawhi Leonard": 3.0,
    "Zion Williamson": 2.5, "Bam Adebayo": 2.5, "Domantas Sabonis": 2.5,
    "Kyrie Irving": 2.5, "Paul George": 2.5, "LaMelo Ball": 2.0,
    "De'Aaron Fox": 2.0, "Pascal Siakam": 1.5, "Chet Holmgren": 1.5,
    "Derrick White": 1.5, "Jrue Holiday": 1.5, "Jamal Murray": 1.5
}

# --- 2. FUNCOES ---
@st.cache_data(ttl=60)  # Cache de 1 minuto para nao travar a API
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
        # Dados
        home_team = jogo['homeTeam']['teamName']
        away_team = jogo['awayTeam']['teamName']
        home_score = jogo['homeTeam']['score']
        away_score = jogo['awayTeam']['score']
        status = jogo['gameStatusText'].strip()

        # Formatacao Visual do Status
        cor_status = "status-final"
        if "ET" in status or "PM" in status.upper() or "AM" in status.upper():  # Jogo agendado
            icone = "📅"
        elif "Final" in status:
            icone = "🏁"
        else:  # Jogo rolando
            icone = "🔴 AO VIVO"
            cor_status = "status-live"

        # --- CARTAO DO JOGO (Visual Limpo) ---
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

            # --- CALCULADORA (Dentro do Card) ---
            # Expander minimalista
            with st.expander(f"💰 Simular Lesao ({away_team} vs {home_team})"):

                c1, c2 = st.columns([1, 1.5])
                with c1:
                    # Input de Spread mais intuitivo
                    linha_mercado = st.number_input("Linha (Spread)", value=-4.5, step=0.5, key=f"s_{home_team}", help="Ex: Se Lakers e favorito por 4.5, digite -4.5")
                with c2:
                    estrelas = ["Selecione..."] + sorted(list(IMPACTO_ESTRELAS.keys()))
                    jogador_out = st.selectbox("Quem esta OUT?", estrelas, key=f"p_{home_team}")

                # Resultado Visual
                if jogador_out != "Selecione...":
                    impacto = IMPACTO_ESTRELAS[jogador_out]
                    nova_linha = linha_mercado + impacto
                    diff = abs(nova_linha - linha_mercado)

                    st.divider()

                    # Logica de Decisao Colorida
                    if diff >= 1.5:
                        st.success(f"🔥 **ALERTA DE VALOR!**")
                        st.markdown(f"""
                        O mercado mudou **{diff} pontos**.
                        <br>Nova Linha Justa: **{nova_linha:+.1f}**
                        <br>👉 **APOSTE CONTRA A LINHA ANTIGA**
                        """, unsafe_allow_html=True)
                    else:
                        st.warning(f"⚠️ Impacto Baixo ({diff} pts)")
                        st.markdown(f"Ajuste pequeno. Linha justa: **{nova_linha:+.1f}**")
