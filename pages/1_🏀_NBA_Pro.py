import streamlit as st
import pandas as pd
import requests
import feedparser
from datetime import datetime
from deep_translator import GoogleTranslator
from nba_api.stats.endpoints import leaguestandings

# --- CONFIGURACAO INICIAL ---
# st.set_page_config removido - esta no Home.py

# --- SUA CHAVE ---
API_KEY = "e6a32983f406a1fbf89fda109149ac15"

# --- CSS MODERNO & ANIMACOES ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; font-family: 'Roboto', sans-serif; }

    /* Animacao de Piscar para o LIVE */
    @keyframes blink {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
    }
    .live-dot {
        display: inline-block;
        width: 10px; height: 10px;
        background-color: #ff0000;
        border-radius: 50%;
        margin-right: 8px;
        animation: blink 1.5s infinite;
        box-shadow: 0 0 5px #ff0000;
    }
    .live-tag {
        color: #ff4b4b; font-weight: bold; font-size: 0.8em; letter-spacing: 1px;
    }

    /* Cards e Layout */
    .trade-strip {
        background-color: #1c1e26; border-radius: 8px; padding: 15px; margin-bottom: 12px;
        border-left: 4px solid #444; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .strip-live { border-left: 4px solid #ff4b4b; background-color: #261c1c; }
    .strip-value { border-left: 4px solid #00ff00; background-color: #1f291f; }

    .time-text { color: #888; font-size: 0.8em; font-weight: bold; display: block; margin-bottom: 4px;}
    .team-name { font-size: 1.1em; font-weight: 600; color: #eee; }
    .score-live { font-size: 1.4em; font-weight: bold; color: #fff; padding: 0 10px; }
    .game-clock { font-size: 0.8em; color: #ff4b4b; font-weight: bold; }

    /* Noticias e Badges */
    .news-card { background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 3px solid #4da6ff; font-size: 0.9em; }
    .news-alert { border-left: 3px solid #ff4b4b; background-color: #2d1b1b; }
    .news-title { color: #e0e0e0; font-weight: 500; }

    .stake-badge { background-color: #00ff00; color: #000; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; box-shadow: 0 0 10px rgba(0, 255, 0, 0.2); }
    .stake-normal { background-color: #ffff00; color: black; }
    .stake-high { background-color: #ff00ff; color: white; }

    div[data-baseweb="select"] > div { background-color: #262730; border-color: #444; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (GESTAO) ---
with st.sidebar:
    st.header("Gestao de Banca")
    banca_total = st.number_input("Banca Total (R$)", value=1000.0, step=100.0, format="%.2f")
    pct_unidade = st.slider("Valor da Unidade (%)", 0.5, 5.0, 1.0, step=0.5)
    valor_unidade = banca_total * (pct_unidade / 100)
    st.markdown(f"""<div style="text-align:center; background-color: #1a1c24; padding: 10px; border-radius: 8px;"><small style="color:#888">1 UNIDADE</small><br><span style="font-size: 1.5em; color: #4da6ff; font-weight: bold;">R$ {valor_unidade:.2f}</span></div>""", unsafe_allow_html=True)

# --- 1. MOTOR DE DADOS AO VIVO (NBA CDN) ---
@st.cache_data(ttl=30)
def get_nba_live_scores():
    try:
        url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
        data = requests.get(url).json()
        games = data['scoreboard']['games']

        live_data = {}
        for g in games:
            status_code = g['gameStatus']
            is_live = status_code == 2
            is_final = status_code == 3

            home_team = g['homeTeam']['teamName']
            away_team = g['awayTeam']['teamName']

            info = {
                "live": is_live,
                "final": is_final,
                "period": g['period'],
                "clock": g['gameClock'],
                "score_home": g['homeTeam']['score'],
                "score_away": g['awayTeam']['score']
            }
            live_data[home_team] = info
            live_data[away_team] = info
            live_data[g['homeTeam']['teamCity'] + " " + home_team] = info

        return live_data
    except:
        return {}

# --- 2. MOTOR DE NOTICIAS (TRADUZIDO) ---
@st.cache_data(ttl=600)
def get_nba_news_translated():
    try:
        feed = feedparser.parse("https://www.espn.com/espn/rss/nba/news")
        noticias = []
        keywords = ["injury", "out", "surgery", "suspended", "trade", "doubtful"]
        translator = GoogleTranslator(source='auto', target='pt')

        for entry in feed.entries[:4]:
            titulo_en = entry.title
            alerta = any(w in titulo_en.lower() for w in keywords)
            try: titulo_pt = translator.translate(titulo_en)
            except: titulo_pt = titulo_en
            titulo_pt = titulo_pt.replace("Fontes:", "").strip()
            try: hora = datetime(*entry.published_parsed[:6]).strftime("%H:%M")
            except: hora = "Hoje"
            noticias.append({"titulo": titulo_pt, "hora": hora, "alerta": alerta})
        return noticias
    except: return []

# --- 3. RATINGS & ODDS ---
@st.cache_data(ttl=86400)
def get_nba_ratings():
    try:
        standings = leaguestandings.LeagueStandings(season='2024-25')
        df = standings.get_data_frames()[0]
        ratings = {}
        for _, row in df.iterrows():
            team = row['TeamName']
            ratings[team] = round(row['PointsPG'] - row['OppPointsPG'], 1)
        return ratings
    except: return {"Celtics": 10.5, "Thunder": 9.0, "Nuggets": 7.0, "Lakers": 1.5, "Knicks": 4.0}

def get_odds(api_key):
    try:
        return requests.get(f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds', params={'api_key': api_key, 'regions': 'us,eu', 'markets': 'spreads', 'oddsFormat': 'decimal', 'bookmakers': 'pinnacle,bet365'}).json()
    except: return []

DB_LESAO_FULL = {
    "Nikola Jokic": [8.5, "Nuggets"], "Luka Doncic": [7.0, "Mavericks"], "Giannis": [6.5, "Bucks"],
    "SGA": [6.5, "Thunder"], "Embiid": [6.0, "76ers"], "Tatum": [5.0, "Celtics"], "LeBron": [4.5, "Lakers"],
    "AD": [4.5, "Lakers"], "Durant": [4.5, "Suns"], "Curry": [5.0, "Warriors"], "Morant": [4.0, "Grizzlies"],
    "Mitchell": [4.0, "Cavaliers"], "Brunson": [3.5, "Knicks"], "Wembanyama": [4.5, "Spurs"]
}

# --- APP PRINCIPAL ---
c1, c2 = st.columns([5, 1])
c1.title("NBA Terminal Pro v5.0 (LIVE)")
if c2.button("SCAN LIVE", type="primary"):
    st.cache_data.clear()
    st.rerun()

# Noticias
with st.expander("BREAKING NEWS", expanded=True):
    news = get_nba_news_translated()
    if news:
        cols = st.columns(4)
        for i, n in enumerate(news):
            css = "news-alert" if n['alerta'] else "news-card"
            with cols[i]: st.markdown(f"""<div class="{css} news-card"><div style="font-size:0.7em;color:#aaa">{n['hora']}</div>{n['titulo']}</div>""", unsafe_allow_html=True)

st.divider()

# Logica Principal
RATINGS = get_nba_ratings()
ODDS = get_odds(API_KEY)
LIVE_SCORES = get_nba_live_scores()

if not ODDS or isinstance(ODDS, dict):
    st.info("Mercado fechado ou sem creditos.")
else:
    # Cabecalho
    st.markdown("""<div style="display: flex; color: #666; font-size: 0.8em; padding: 0 15px; margin-bottom: 5px; font-weight: bold;"><div style="flex: 3;">JOGO & PLACAR</div><div style="flex: 2; text-align: center;">LINHAS (LIVE vs MODELO)</div><div style="flex: 2; padding-left: 10px;">FILTRO</div><div style="flex: 1.5; text-align: right;">DECISAO (+EV)</div></div>""", unsafe_allow_html=True)

    for game in ODDS:
        home = game['home_team']
        away = game['away_team']

        # 1. Busca Placar Ao Vivo (Match fuzzy simples)
        game_live_info = None
        for k, v in LIVE_SCORES.items():
            if k in home or home in k:
                game_live_info = v
                break

        is_live = game_live_info['live'] if game_live_info else False
        is_final = game_live_info['final'] if game_live_info else False

        # 2. Ratings & Modelo
        r_home = RATINGS.get(home, RATINGS.get(home.split()[-1], 0))
        r_away = RATINGS.get(away, RATINGS.get(away.split()[-1], 0))
        fair_line_pre = -((r_home + 2.5) - r_away)

        # 3. Market Odds
        market_line = 0.0
        for s in game.get('bookmakers', []):
            if s['key'] in ['pinnacle', 'bet365']:
                p = s['markets'][0]['outcomes'][0]['point']
                if s['markets'][0]['outcomes'][0]['name'] != home: p = -p
                market_line = p
                break
        if market_line == 0.0: continue

        # 4. Ajuste Lesao
        jogadores = [j for j, d in DB_LESAO_FULL.items() if d[1] in home or d[1] in away]

        # CONTAINER
        css_strip = "strip-live" if is_live else "trade-strip"
        with st.container():
            c_g, c_l, c_f, c_d = st.columns([3, 2.2, 2.2, 1.6], gap="small", vertical_alignment="center")

            with c_g:
                if is_live:
                    st.markdown(f"""
                    <div style="line-height:1.2;">
                        <span class="live-tag"><span class="live-dot"></span>AO VIVO - Q{game_live_info['period']} {game_live_info['clock']}</span><br>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                            <span class="team-name">{away}</span> <span class="score-live">{game_live_info['score_away']}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="team-name">{home}</span> <span class="score-live">{game_live_info['score_home']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    time_start = pd.to_datetime(game['commence_time']).strftime('%H:%M')
                    st.markdown(f"""<div style="line-height:1.5;"><span class="time-text">{time_start}</span><div>{away} <span style="font-size:0.8em;color:#aaa">({r_away:+.1f})</span></div><div style="color:#444">@</div><div>{home} <span style="font-size:0.8em;color:#aaa">({r_home:+.1f})</span></div></div>""", unsafe_allow_html=True)

            with c_f:
                p_out = st.selectbox("OUT?", ["-"]+jogadores, key=f"ls_{home}", label_visibility="collapsed")

            # Recalculo
            adj_fair = fair_line_pre
            if p_out != "-":
                imp, tm = DB_LESAO_FULL[p_out]
                if tm in home: adj_fair += imp
                else: adj_fair -= imp

            # DECISAO
            diff = abs(adj_fair - market_line)
            has_value = diff >= 1.5

            # Logica Especial LIVE
            note_live = ""
            if is_live:
                note_live = "<br><span style='color:#ff9900;font-size:0.7em'>Mercado Live</span>"

            with c_l:
                st.markdown(f"""<div style="display:flex;justify-content:space-around;text-align:center;"><div><div style="font-size:0.7em;color:#aaa">MODELO (PRE)</div><div style="font-weight:bold;color:#4da6ff">{adj_fair:+.1f}</div></div><div style="border-right:1px solid #444"></div><div><div style="font-size:0.7em;color:#aaa">MARKET</div><div style="font-weight:bold;color:#fff">{market_line:+.1f}</div></div></div>""", unsafe_allow_html=True)

            with c_d:
                if has_value:
                    color = "#00ff00" if diff < 5 else "#ff00ff"
                    pick = home if adj_fair < market_line else away
                    line = market_line if pick == home else -market_line

                    val_bet = valor_unidade * (1.5 if diff > 3 else 0.75)
                    st.markdown(f"""<div style="text-align:right;"><span style="background:{color};color:black;font-weight:bold;padding:2px 5px;border-radius:4px;">R$ {val_bet:.0f}</span><br><span style="color:{'#4da6ff' if pick==home else '#ffcc00'};font-weight:bold;">{pick} {line:+.1f}</span><div style="font-size:0.7em;color:#888">Edge: {diff:.1f}{note_live}</div></div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div style="text-align:right;color:#555;font-size:0.8em">Linha Justa{note_live}</div>""", unsafe_allow_html=True)

            st.markdown("<hr style='margin: 8px 0; border-color: #2d313a;'>", unsafe_allow_html=True)
