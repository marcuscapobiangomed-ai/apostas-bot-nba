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

# --- CSS MODERNO & CLEAN ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; font-family: 'Roboto', sans-serif; }

    /* Animacao de Piscar */
    @keyframes blink {
        0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; }
    }
    .live-dot {
        display: inline-block; width: 8px; height: 8px;
        background-color: #ff0000; border-radius: 50%;
        margin-right: 6px; animation: blink 1.5s infinite;
        box-shadow: 0 0 6px #ff0000; vertical-align: middle;
    }

    /* Tags de Status */
    .status-live {
        background-color: #2d1b1b; color: #ff4b4b;
        padding: 2px 8px; border-radius: 4px;
        font-size: 0.75em; font-weight: bold; border: 1px solid #5e2a2a;
    }
    .status-clock {
        color: #ffcc00; font-weight: bold; margin-left: 8px; font-family: monospace; font-size: 0.9em;
    }
    .status-q {
        color: #aaa; margin-left: 8px; font-size: 0.8em; font-weight: bold;
    }

    /* Cards */
    .trade-strip {
        background-color: #1c1e26; border-radius: 8px; padding: 15px; margin-bottom: 12px;
        border-left: 4px solid #444; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .strip-live { border-left: 4px solid #ff4b4b; background-color: #1f1a1a; }
    .strip-value { border-left: 4px solid #00ff00; background-color: #1f291f; }

    .team-name { font-size: 1.1em; font-weight: 600; color: #eee; }
    .score-live { font-size: 1.4em; font-weight: bold; color: #fff; text-align: right; }
    .time-text { color: #888; font-size: 0.8em; font-weight: bold; }

    /* Noticias */
    .news-card { background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 3px solid #4da6ff; font-size: 0.9em; }
    .news-alert { border-left: 3px solid #ff4b4b; background-color: #2d1b1b; }
    .news-time { font-size: 0.75em; color: #aaa; margin-bottom: 4px; font-weight: bold; }

    /* Badges */
    .stake-badge { background-color: #00ff00; color: #000; font-weight: bold; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
    .stake-normal { background-color: #ffff00; color: black; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;}

    div[data-baseweb="select"] > div { background-color: #262730; border-color: #444; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Gestao")
    banca_total = st.number_input("Banca (R$)", value=1000.0, step=100.0, format="%.2f")
    pct_unidade = st.slider("Unidade (%)", 0.5, 5.0, 1.0, step=0.5)
    valor_unidade = banca_total * (pct_unidade / 100)
    st.markdown(f"""<div style="text-align:center; background-color: #1a1c24; padding: 10px; border-radius: 8px; margin-top:10px;"><small style="color:#888">1 UNIDADE</small><br><span style="font-size: 1.5em; color: #4da6ff; font-weight: bold;">R$ {valor_unidade:.2f}</span></div>""", unsafe_allow_html=True)

# --- FUNCAO DE LIMPEZA DO RELOGIO ---
def clean_nba_clock(raw_clock):
    # Transforma "PT07M03.00S" em "07:03"
    if not raw_clock: return ""
    try:
        clean = raw_clock.replace("PT", "").replace("S", "")
        if "M" in clean:
            parts = clean.split("M")
            mins = parts[0]
            secs = parts[1].split(".")[0]
            return f"{mins}:{secs}"
        return clean
    except:
        return raw_clock

# --- 1. DADOS AO VIVO ---
@st.cache_data(ttl=20)
def get_nba_live_scores():
    try:
        url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
        data = requests.get(url).json()
        games = data['scoreboard']['games']

        live_data = {}
        for g in games:
            status = g['gameStatus']
            home = g['homeTeam']['teamName']

            relogio_formatado = clean_nba_clock(g['gameClock'])

            info = {
                "live": status == 2,
                "period": g['period'],
                "clock": relogio_formatado,
                "score_home": g['homeTeam']['score'],
                "score_away": g['awayTeam']['score']
            }
            live_data[home] = info
            live_data[g['awayTeam']['teamName']] = info

        return live_data
    except: return {}

# --- 2. NOTICIAS TRADUZIDAS ---
@st.cache_data(ttl=600)
def get_news():
    try:
        feed = feedparser.parse("https://www.espn.com/espn/rss/nba/news")
        noticias = []
        keywords = ["injury", "out", "surgery", "suspended", "trade"]
        translator = GoogleTranslator(source='auto', target='pt')
        for entry in feed.entries[:4]:
            alerta = any(w in entry.title.lower() for w in keywords)
            try: tit = translator.translate(entry.title).replace("Fontes:", "").strip()
            except: tit = entry.title
            try: hora = datetime(*entry.published_parsed[:6]).strftime("%H:%M")
            except: hora = ""
            noticias.append({"titulo": tit, "hora": hora, "alerta": alerta})
        return noticias
    except: return []

# --- 3. DADOS ESTATICOS ---
@st.cache_data(ttl=86400)
def get_ratings():
    try:
        standings = leaguestandings.LeagueStandings(season='2024-25')
        df = standings.get_data_frames()[0]
        return {row['TeamName']: round(row['PointsPG'] - row['OppPointsPG'], 1) for _, row in df.iterrows()}
    except: return {"Celtics": 10.5, "Thunder": 9.0, "Nuggets": 7.0, "Lakers": 1.5, "Knicks": 4.0}

def get_odds(api_key):
    try: return requests.get(f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds', params={'api_key': api_key, 'regions': 'us,eu', 'markets': 'spreads', 'oddsFormat': 'decimal', 'bookmakers': 'pinnacle,bet365'}).json()
    except: return []

DB_LESAO_FULL = {
    "Nikola Jokic": [8.5, "Nuggets"], "Luka Doncic": [7.0, "Mavericks"], "Giannis": [6.5, "Bucks"],
    "SGA": [6.5, "Thunder"], "Embiid": [6.0, "76ers"], "Tatum": [5.0, "Celtics"], "LeBron": [4.5, "Lakers"],
    "AD": [4.5, "Lakers"], "Durant": [4.5, "Suns"], "Curry": [5.0, "Warriors"], "Morant": [4.0, "Grizzlies"],
    "Mitchell": [4.0, "Cavaliers"], "Brunson": [3.5, "Knicks"], "Wembanyama": [4.5, "Spurs"]
}

# --- INTERFACE ---
c1, c2 = st.columns([5, 1])
c1.title("NBA Terminal Pro v5.1")
if c2.button("LIVE SCAN", type="primary"):
    st.cache_data.clear()
    st.rerun()

# Noticias
with st.expander("BREAKING NEWS", expanded=True):
    news = get_news()
    if news:
        cols = st.columns(4)
        for i, n in enumerate(news):
            css = "news-alert" if n['alerta'] else "news-card"
            with cols[i]: st.markdown(f"""<div class="{css} news-card"><div class="news-time">{n['hora']}</div>{n['titulo']}</div>""", unsafe_allow_html=True)

st.divider()

RATINGS = get_ratings()
ODDS = get_odds(API_KEY)
LIVE_SCORES = get_nba_live_scores()

if not ODDS or isinstance(ODDS, dict):
    st.info("Mercado fechado.")
else:
    # Header da Tabela
    st.markdown("""
    <div style="display: flex; color: #666; font-size: 0.8em; padding: 0 15px; margin-bottom: 5px; font-weight: bold;">
        <div style="flex: 3;">JOGO & STATUS</div>
        <div style="flex: 2; text-align: center;">LINHAS</div>
        <div style="flex: 2; padding-left: 10px;">FILTRO</div>
        <div style="flex: 1.5; text-align: right;">DECISAO</div>
    </div>
    """, unsafe_allow_html=True)

    for game in ODDS:
        home = game['home_team']
        away = game['away_team']

        # Live Info
        live_info = None
        for k, v in LIVE_SCORES.items():
            if k in home or home in k: live_info = v; break

        is_live = live_info['live'] if live_info else False

        # Ratings & Lines
        r_home = RATINGS.get(home, RATINGS.get(home.split()[-1], 0))
        r_away = RATINGS.get(away, RATINGS.get(away.split()[-1], 0))
        fair_line = -((r_home + 2.5) - r_away)

        market_line = 0.0
        for s in game.get('bookmakers', []):
            if s['key'] in ['pinnacle', 'bet365']:
                p = s['markets'][0]['outcomes'][0]['point']
                if s['markets'][0]['outcomes'][0]['name'] != home: p = -p
                market_line = p; break
        if market_line == 0.0: continue

        # Container
        css_strip = "strip-live" if is_live else "trade-strip"
        with st.container():
            c_g, c_l, c_f, c_d = st.columns([3, 2.2, 2.2, 1.6], gap="small", vertical_alignment="center")

            with c_g:
                if is_live:
                    st.markdown(f"""
                    <div style="line-height:1.2;">
                        <div style="margin-bottom:6px;">
                            <span class="status-live"><span class="live-dot"></span>AO VIVO</span>
                            <span class="status-q">Q{live_info['period']}</span>
                            <span class="status-clock">{live_info['clock']}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #333; padding-bottom:2px; margin-bottom:2px;">
                            <span class="team-name">{away}</span> <span class="score-live">{live_info['score_away']}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="team-name">{home}</span> <span class="score-live">{live_info['score_home']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    time_start = pd.to_datetime(game['commence_time']).strftime('%H:%M')
                    st.markdown(f"""<div style="line-height:1.5;"><span class="time-text">{time_start}</span><div>{away} <span style="font-size:0.8em;color:#aaa">({r_away:+.1f})</span></div><div style="color:#444">@</div><div>{home} <span style="font-size:0.8em;color:#aaa">({r_home:+.1f})</span></div></div>""", unsafe_allow_html=True)

            with c_f:
                jogadores = [j for j, d in DB_LESAO_FULL.items() if d[1] in home or d[1] in away]
                p_out = st.selectbox("OUT?", ["-"]+jogadores, key=f"ls_{home}", label_visibility="collapsed")
                if p_out != "-":
                    imp, tm = DB_LESAO_FULL[p_out]
                    if tm in home: fair_line += imp
                    else: fair_line -= imp

            diff = abs(fair_line - market_line)
            has_value = diff >= 1.5

            with c_l:
                st.markdown(f"""<div style="display:flex;justify-content:space-around;text-align:center;"><div><div style="font-size:0.7em;color:#aaa">MODELO</div><div style="font-weight:bold;color:#4da6ff">{fair_line:+.1f}</div></div><div style="border-right:1px solid #444"></div><div><div style="font-size:0.7em;color:#aaa">MARKET</div><div style="font-weight:bold;color:#fff">{market_line:+.1f}</div></div></div>""", unsafe_allow_html=True)

            with c_d:
                if has_value:
                    pick = home if fair_line < market_line else away
                    line = market_line if pick == home else -market_line
                    units = 1.5 if diff > 3 else 0.75
                    val = valor_unidade * units
                    css_badge = "stake-badge" if diff > 3 else "stake-normal"

                    st.markdown(f"""<div style="text-align:right;"><span class="{css_badge}">R$ {val:.0f}</span><br><span style="color:{'#4da6ff' if pick==home else '#ffcc00'};font-weight:bold;">{pick} {line:+.1f}</span><div style="font-size:0.7em;color:#888">Edge: {diff:.1f}</div></div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div style="text-align:right;color:#555;font-size:0.8em">Justo</div>""", unsafe_allow_html=True)

            st.markdown("<hr style='margin: 8px 0; border-color: #2d313a;'>", unsafe_allow_html=True)
