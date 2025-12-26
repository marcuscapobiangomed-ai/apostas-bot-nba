import streamlit as st
import pandas as pd
import numpy as np
import requests
import feedparser
from datetime import datetime
from deep_translator import GoogleTranslator
from nba_api.stats.endpoints import leaguestandings, commonteamroster, teamgamelog
from nba_api.stats.static import teams

# --- CONFIGURACAO INICIAL ---
# st.set_page_config removido - esta no Home.py
API_KEY = "e6a32983f406a1fbf89fda109149ac15"

# --- CSS VISUAL AVANCADO ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; font-family: 'Roboto', sans-serif; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    .live-dot { display: inline-block; width: 8px; height: 8px; background-color: #ff0000; border-radius: 50%; margin-right: 6px; animation: blink 1.5s infinite; box-shadow: 0 0 6px #ff0000; vertical-align: middle; }
    .status-live { background-color: #2d1b1b; color: #ff4b4b; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold; border: 1px solid #5e2a2a; }
    .status-clock { color: #ffcc00; font-weight: bold; margin-left: 8px; font-family: monospace; font-size: 0.9em; }
    .status-q { color: #aaa; margin-left: 8px; font-size: 0.8em; font-weight: bold; }
    .trade-strip { background-color: #1c1e26; border-radius: 8px; padding: 15px; margin-bottom: 12px; border-left: 4px solid #444; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    .strip-live { border-left: 4px solid #ff4b4b; background-color: #1f1a1a; }
    .strip-value { border-left: 4px solid #00ff00; background-color: #1f291f; }
    .team-name { font-size: 1.1em; font-weight: 600; color: #eee; }
    .score-live { font-size: 1.4em; font-weight: bold; color: #fff; text-align: right; }
    .time-text { color: #888; font-size: 0.8em; font-weight: bold; }
    .news-card { background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 3px solid #4da6ff; font-size: 0.9em; }
    .news-alert { border-left: 3px solid #ff4b4b; background-color: #2d1b1b; }
    .news-time { font-size: 0.75em; color: #aaa; margin-bottom: 4px; font-weight: bold; }
    .stake-badge { background-color: #00ff00; color: #000; font-weight: bold; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
    .stake-normal { background-color: #ffff00; color: black; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;}
    .xscore-hot { color: #ff6b6b; font-weight: bold; }
    .xscore-cold { color: #4dabf7; font-weight: bold; }
    .pace-badge { background-color: #9775fa; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; }
    .over-signal { background-color: #51cf66; color: black; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; font-weight: bold; }
    .under-signal { background-color: #ff6b6b; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; font-weight: bold; }
    div[data-baseweb="select"] > div { background-color: #262730; border-color: #444; color: white; }
    .model-tab { background-color: #1a1c24; border-radius: 8px; padding: 12px; margin: 8px 0; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("Gestao de Banca")
    banca_total = st.number_input("Banca (R$)", value=1000.0, step=100.0, format="%.2f")
    pct_unidade = st.slider("Unidade (%)", 0.5, 5.0, 1.0, step=0.5)
    valor_unidade = banca_total * (pct_unidade / 100)
    st.markdown(f"""<div style="text-align:center; background-color: #1a1c24; padding: 10px; border-radius: 8px; margin-top:10px;"><small style="color:#888">1 UNIDADE</small><br><span style="font-size: 1.5em; color: #4da6ff; font-weight: bold;">R$ {valor_unidade:.2f}</span></div>""", unsafe_allow_html=True)

    st.divider()
    st.subheader("Modelos Ativos")
    use_xscore = st.checkbox("xScore (Qualidade)", value=True, help="Detecta divergencia entre pontos reais e esperados")
    use_pace = st.checkbox("Ritmo Dinamico", value=True, help="Ajusta projecao de totais em tempo real")

# --- 1. IMPACTO DOS JOGADORES ---
PLAYER_IMPACTS = {
    "Estrela (Generico)": 4.5, "Titular Importante (Generico)": 2.5, "Role Player (Generico)": 1.5,
    "Nikola Jokic": 8.5, "Luka Doncic": 7.5, "Giannis Antetokounmpo": 7.0,
    "Shai Gilgeous-Alexander": 7.0, "Joel Embiid": 6.5, "Jayson Tatum": 5.5,
    "Stephen Curry": 5.5, "LeBron James": 5.0, "Kevin Durant": 5.0,
    "Anthony Davis": 5.0, "Victor Wembanyama": 5.0, "Anthony Edwards": 4.5,
    "Devin Booker": 4.0, "Ja Morant": 4.0, "Jalen Brunson": 4.0,
    "Donovan Mitchell": 4.0, "Tyrese Haliburton": 3.5, "Kyrie Irving": 3.5,
    "Trae Young": 3.5, "Jimmy Butler": 3.5, "Damian Lillard": 3.5,
    "Kawhi Leonard": 3.5, "James Harden": 3.5, "Zion Williamson": 3.5,
    "Paolo Banchero": 3.5, "De'Aaron Fox": 3.5, "Domantas Sabonis": 3.5,
    "Bam Adebayo": 3.0, "Jaylen Brown": 3.5, "LaMelo Ball": 3.0,
    "Cade Cunningham": 3.0, "Alperen Sengun": 3.0, "Tyrese Maxey": 3.0,
    "Paul George": 3.0, "Karl-Anthony Towns": 3.0, "Chet Holmgren": 3.0,
    "Jamal Murray": 2.5, "Darius Garland": 2.5, "Klay Thompson": 2.0
}

# --- 2. DADOS HISTORICOS DOS TIMES (PACE & EFFICIENCY) ---
@st.cache_data(ttl=86400)
def get_team_stats():
    """Busca estatisticas avancadas dos times para os modelos"""
    try:
        standings = leaguestandings.LeagueStandings(season='2024-25')
        df = standings.get_data_frames()[0]
        stats = {}
        for _, row in df.iterrows():
            team = row['TeamName']
            ppg = row['PointsPG']
            opp_ppg = row['OppPointsPG']
            # Estimativa de Pace baseado em PPG (simplificado)
            # Pace real = posses por 48 min, aqui usamos proxy
            estimated_pace = (ppg + opp_ppg) / 2 * 0.92  # Fator de ajuste
            stats[team] = {
                'ppg': ppg,
                'opp_ppg': opp_ppg,
                'net_rating': round(ppg - opp_ppg, 1),
                'pace': round(estimated_pace, 1),
                'off_rating': round(ppg * 100 / estimated_pace, 1),  # Pontos por 100 posses
                'def_rating': round(opp_ppg * 100 / estimated_pace, 1)
            }
        return stats
    except:
        # Fallback com dados aproximados
        return {
            "Celtics": {'ppg': 120, 'opp_ppg': 110, 'net_rating': 10, 'pace': 100, 'off_rating': 120, 'def_rating': 110},
            "Thunder": {'ppg': 118, 'opp_ppg': 108, 'net_rating': 10, 'pace': 98, 'off_rating': 120, 'def_rating': 110},
            "Nuggets": {'ppg': 115, 'opp_ppg': 110, 'net_rating': 5, 'pace': 97, 'off_rating': 118, 'def_rating': 113}
        }

# --- 3. xSCORE - DETECTOR DE DIVERGENCIA ---
def calculate_xscore(team_stats, current_score, minutes_played, is_home=True):
    """
    Calcula o xScore: pontos esperados vs pontos reais
    Retorna: divergencia (positivo = jogando acima do esperado)
    """
    if minutes_played <= 0:
        return 0, 0

    # Pontos esperados baseado no ritmo historico
    ppg = team_stats.get('ppg', 110)
    points_per_min = ppg / 48

    # Ajuste de Home Court (+2% de eficiencia)
    if is_home:
        points_per_min *= 1.02

    expected_score = points_per_min * minutes_played

    # Divergencia: quanto o time esta acima/abaixo do esperado
    divergence = current_score - expected_score

    # xScore normalizado (-10 a +10)
    xscore = np.clip(divergence / 3, -10, 10)

    return round(xscore, 1), round(expected_score, 1)

# --- 4. RITMO DINAMICO BAYESIANO ---
def calculate_dynamic_pace(home_stats, away_stats, current_total, minutes_played, period):
    """
    Modelo de Ritmo Dinamico para projecao de totais
    Usa atualizacao Bayesiana simples
    """
    if minutes_played <= 0:
        # Pre-game: usa media historica
        expected_pace = (home_stats.get('pace', 98) + away_stats.get('pace', 98)) / 2
        projected_total = (home_stats.get('ppg', 110) + away_stats.get('ppg', 110))
        return projected_total, expected_pace, 0

    # Pace historico combinado (prior)
    prior_pace = (home_stats.get('pace', 98) + away_stats.get('pace', 98)) / 2

    # Pace observado no jogo (likelihood)
    observed_pace = (current_total / minutes_played) * 48

    # Peso Bayesiano: comeca confiando no historico, vai confiando mais no observado
    # No 1Q: 70% historico, 30% observado
    # No 4Q: 30% historico, 70% observado
    obs_weight = min(0.7, 0.2 + (minutes_played / 48) * 0.6)

    # Pace atualizado (posterior)
    updated_pace = (prior_pace * (1 - obs_weight)) + (observed_pace * obs_weight)

    # Ajuste de 4o Quarto (fadiga/tatica)
    if period >= 4:
        # Times tendem a jogar mais lento no 4Q
        updated_pace *= 0.95

    # Projecao de total
    remaining_minutes = 48 - minutes_played
    projected_remaining = (updated_pace / 48) * remaining_minutes
    projected_total = current_total + projected_remaining

    # Divergencia do pace
    pace_divergence = observed_pace - prior_pace

    return round(projected_total, 1), round(updated_pace, 1), round(pace_divergence, 1)

# --- 5. FUNCOES AUXILIARES ---
@st.cache_data(ttl=3600)
def get_team_id(team_name):
    nba_teams = teams.get_teams()
    for t in nba_teams:
        if t['nickname'] in team_name or team_name in t['full_name']:
            return t['id']
    return None

@st.cache_data(ttl=3600)
def get_dynamic_roster(team_name):
    tid = get_team_id(team_name)
    if not tid:
        return []
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=tid, season='2024-25').get_data_frames()[0]
        players_list = roster['PLAYER'].tolist()
        return [p for p in players_list if p in PLAYER_IMPACTS]
    except:
        return []

def clean_nba_clock(raw_clock):
    if not raw_clock: return ""
    try:
        clean = raw_clock.replace("PT", "").replace("S", "")
        if "M" in clean:
            parts = clean.split("M")
            return f"{parts[0]}:{parts[1].split('.')[0]}"
        return clean
    except: return raw_clock

def parse_clock_to_minutes(clock_str, period):
    """Converte relogio + periodo em minutos jogados"""
    try:
        if not clock_str:
            return period * 12
        parts = clock_str.split(":")
        mins_left = int(parts[0])
        mins_played_in_period = 12 - mins_left
        total_mins = ((period - 1) * 12) + mins_played_in_period
        return max(0, min(48, total_mins))
    except:
        return period * 12

@st.cache_data(ttl=20)
def get_nba_live_scores():
    try:
        data = requests.get("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json").json()
        live_data = {}
        for g in data['scoreboard']['games']:
            clock = clean_nba_clock(g['gameClock'])
            period = g['period']
            mins_played = parse_clock_to_minutes(clock, period)

            info = {
                "live": g['gameStatus'] == 2,
                "period": period,
                "clock": clock,
                "minutes_played": mins_played,
                "score_home": g['homeTeam']['score'],
                "score_away": g['awayTeam']['score'],
                "total": g['homeTeam']['score'] + g['awayTeam']['score']
            }
            live_data[g['homeTeam']['teamName']] = info
            live_data[g['awayTeam']['teamName']] = info
        return live_data
    except: return {}

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

def get_odds(api_key):
    try:
        return requests.get(
            f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds',
            params={
                'api_key': api_key,
                'regions': 'us,eu',
                'markets': 'spreads,totals',  # Agora busca TOTALS tambem
                'oddsFormat': 'decimal',
                'bookmakers': 'pinnacle,bet365'
            }
        ).json()
    except: return []

# --- APP PRINCIPAL ---
c1, c2 = st.columns([5, 1])
c1.title("NBA Terminal Pro v7.0")
c1.caption("xScore + Ritmo Dinamico")
if c2.button("SCAN LIVE", type="primary"):
    st.cache_data.clear()
    st.rerun()

# Noticias
with st.expander("BREAKING NEWS", expanded=False):
    news = get_news()
    if news:
        cols = st.columns(4)
        for i, n in enumerate(news):
            css = "news-alert" if n['alerta'] else "news-card"
            with cols[i]: st.markdown(f"""<div class="{css} news-card"><div class="news-time">{n['hora']}</div>{n['titulo']}</div>""", unsafe_allow_html=True)

st.divider()

# Carrega dados
TEAM_STATS = get_team_stats()
ODDS = get_odds(API_KEY)
LIVE_SCORES = get_nba_live_scores()

if not ODDS or isinstance(ODDS, dict):
    st.info("Mercado fechado ou sem creditos na API.")
else:
    # Tabs para diferentes mercados
    tab_spread, tab_totals = st.tabs(["SPREADS (xScore)", "TOTALS (Ritmo)"])

    with tab_spread:
        st.markdown("""<div style="display: flex; color: #666; font-size: 0.8em; padding: 0 15px; margin-bottom: 5px; font-weight: bold;">
            <div style="flex: 2.5;">JOGO</div>
            <div style="flex: 1.5; text-align: center;">xSCORE</div>
            <div style="flex: 2; text-align: center;">LINHAS</div>
            <div style="flex: 2;">LESAO</div>
            <div style="flex: 1.5; text-align: right;">DECISAO</div>
        </div>""", unsafe_allow_html=True)

        for game in ODDS:
            home = game['home_team']
            away = game['away_team']

            # Live Info
            live_info = None
            for k, v in LIVE_SCORES.items():
                if k in home or home in k: live_info = v; break
            is_live = live_info['live'] if live_info else False

            # Team Stats
            home_stats = TEAM_STATS.get(home.split()[-1], TEAM_STATS.get(home, {'ppg': 110, 'net_rating': 0}))
            away_stats = TEAM_STATS.get(away.split()[-1], TEAM_STATS.get(away, {'ppg': 110, 'net_rating': 0}))

            # Fair Line baseada em Net Rating
            r_home = home_stats.get('net_rating', 0)
            r_away = away_stats.get('net_rating', 0)
            fair_line = -((r_home + 2.5) - r_away)

            # Market Line (Spread)
            market_line = 0.0
            for s in game.get('bookmakers', []):
                if s['key'] in ['pinnacle', 'bet365']:
                    for mkt in s.get('markets', []):
                        if mkt['key'] == 'spreads':
                            p = mkt['outcomes'][0]['point']
                            if mkt['outcomes'][0]['name'] != home: p = -p
                            market_line = p
                            break
            if market_line == 0.0: continue

            # xScore (se ao vivo)
            xscore_home, xscore_away = 0, 0
            if is_live and use_xscore:
                mins = live_info.get('minutes_played', 0)
                xscore_home, _ = calculate_xscore(home_stats, live_info['score_home'], mins, True)
                xscore_away, _ = calculate_xscore(away_stats, live_info['score_away'], mins, False)

            # Rosters
            roster_home = get_dynamic_roster(home)
            roster_away = get_dynamic_roster(away)
            generics = ["Estrela (Generico)", "Titular Importante (Generico)"]

            with st.container():
                c_g, c_x, c_l, c_f, c_d = st.columns([2.5, 1.5, 2, 2, 1.5], gap="small", vertical_alignment="center")

                with c_g:
                    if is_live:
                        st.markdown(f"""<div style="line-height:1.2;">
                            <span class="status-live"><span class="live-dot"></span>LIVE</span>
                            <span class="status-q">Q{live_info['period']}</span>
                            <span class="status-clock">{live_info['clock']}</span><br>
                            <span style="color:#aaa">{away}</span> <b>{live_info['score_away']}</b><br>
                            <span style="color:#fff">{home}</span> <b>{live_info['score_home']}</b>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<div style="line-height:1.4;">
                            <span style="color:#888;font-size:0.8em">{pd.to_datetime(game['commence_time']).strftime('%H:%M')}</span><br>
                            {away} <span style="color:#666">({r_away:+.1f})</span><br>
                            @ {home} <span style="color:#666">({r_home:+.1f})</span>
                        </div>""", unsafe_allow_html=True)

                with c_x:
                    if is_live and use_xscore:
                        # Mostra xScore de cada time
                        css_h = "xscore-hot" if xscore_home > 2 else ("xscore-cold" if xscore_home < -2 else "")
                        css_a = "xscore-hot" if xscore_away > 2 else ("xscore-cold" if xscore_away < -2 else "")
                        st.markdown(f"""<div style="text-align:center;font-size:0.85em;">
                            <span class="{css_a}">{xscore_away:+.1f}</span><br>
                            <span class="{css_h}">{xscore_home:+.1f}</span>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='text-align:center;color:#555;font-size:0.8em'>-</div>", unsafe_allow_html=True)

                with c_f:
                    p_out_h = st.selectbox(f"Fora {home.split()[-1]}?", ["-"]+roster_home+generics, key=f"sp_h_{home}", label_visibility="collapsed")
                    p_out_a = st.selectbox(f"Fora {away.split()[-1]}?", ["-"]+roster_away+generics, key=f"sp_a_{home}", label_visibility="collapsed")

                    if p_out_h != "-":
                        fair_line += PLAYER_IMPACTS.get(p_out_h, 2.5)
                    if p_out_a != "-":
                        fair_line -= PLAYER_IMPACTS.get(p_out_a, 2.5)

                # Ajuste xScore na linha justa (se ativo)
                if is_live and use_xscore:
                    # Se home esta jogando muito acima, ajusta linha
                    xscore_adj = (xscore_home - xscore_away) * 0.3
                    fair_line -= xscore_adj

                diff = abs(fair_line - market_line)
                has_value = diff >= 1.5

                with c_l:
                    st.markdown(f"""<div style="display:flex;justify-content:space-around;text-align:center;">
                        <div><div style="font-size:0.65em;color:#aaa">MODELO</div><div style="font-weight:bold;color:#4da6ff">{fair_line:+.1f}</div></div>
                        <div><div style="font-size:0.65em;color:#aaa">MARKET</div><div style="font-weight:bold;color:#fff">{market_line:+.1f}</div></div>
                    </div>""", unsafe_allow_html=True)

                with c_d:
                    if has_value:
                        pick = home if fair_line < market_line else away
                        line = market_line if pick == home else -market_line
                        units = 1.5 if diff > 3 else 0.75
                        val = valor_unidade * units
                        css_badge = "stake-badge" if diff > 3 else "stake-normal"
                        st.markdown(f"""<div style="text-align:right;">
                            <span class="{css_badge}">R$ {val:.0f}</span><br>
                            <span style="color:{'#4da6ff' if pick==home else '#ffcc00'};font-weight:bold;font-size:0.9em">{pick.split()[-1]} {line:+.1f}</span>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='text-align:right;color:#555;font-size:0.8em'>Justo</div>", unsafe_allow_html=True)

                st.markdown("<hr style='margin: 5px 0; border-color: #2d313a;'>", unsafe_allow_html=True)

    with tab_totals:
        st.markdown("""<div style="display: flex; color: #666; font-size: 0.8em; padding: 0 15px; margin-bottom: 5px; font-weight: bold;">
            <div style="flex: 2.5;">JOGO</div>
            <div style="flex: 2; text-align: center;">RITMO</div>
            <div style="flex: 2; text-align: center;">PROJECAO vs LINHA</div>
            <div style="flex: 1.5; text-align: right;">SINAL</div>
        </div>""", unsafe_allow_html=True)

        for game in ODDS:
            home = game['home_team']
            away = game['away_team']

            # Live Info
            live_info = None
            for k, v in LIVE_SCORES.items():
                if k in home or home in k: live_info = v; break
            is_live = live_info['live'] if live_info else False

            # Team Stats
            home_stats = TEAM_STATS.get(home.split()[-1], TEAM_STATS.get(home, {'ppg': 110, 'pace': 98}))
            away_stats = TEAM_STATS.get(away.split()[-1], TEAM_STATS.get(away, {'ppg': 110, 'pace': 98}))

            # Market Total
            market_total = 0.0
            for s in game.get('bookmakers', []):
                if s['key'] in ['pinnacle', 'bet365']:
                    for mkt in s.get('markets', []):
                        if mkt['key'] == 'totals':
                            market_total = mkt['outcomes'][0]['point']
                            break
            if market_total == 0.0: continue

            # Calcula Ritmo Dinamico
            if is_live and use_pace:
                mins = live_info.get('minutes_played', 0)
                current_total = live_info.get('total', 0)
                period = live_info.get('period', 1)
                projected_total, current_pace, pace_div = calculate_dynamic_pace(
                    home_stats, away_stats, current_total, mins, period
                )
            else:
                # Pre-game
                projected_total = home_stats.get('ppg', 110) + away_stats.get('ppg', 110)
                current_pace = (home_stats.get('pace', 98) + away_stats.get('pace', 98)) / 2
                pace_div = 0

            diff_total = projected_total - market_total
            has_signal = abs(diff_total) >= 3

            with st.container():
                c_g, c_p, c_t, c_s = st.columns([2.5, 2, 2, 1.5], gap="small", vertical_alignment="center")

                with c_g:
                    if is_live:
                        st.markdown(f"""<div style="line-height:1.2;">
                            <span class="status-live"><span class="live-dot"></span>LIVE</span>
                            <span class="status-q">Q{live_info['period']}</span>
                            <span class="status-clock">{live_info['clock']}</span><br>
                            <span style="color:#fff;font-size:1.1em"><b>{live_info['total']}</b> pts</span>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<div style="line-height:1.4;">
                            <span style="color:#888;font-size:0.8em">{pd.to_datetime(game['commence_time']).strftime('%H:%M')}</span><br>
                            {away} @ {home}
                        </div>""", unsafe_allow_html=True)

                with c_p:
                    pace_css = "color:#51cf66" if pace_div > 3 else ("color:#ff6b6b" if pace_div < -3 else "color:#aaa")
                    st.markdown(f"""<div style="text-align:center;">
                        <div style="font-size:0.7em;color:#888">PACE</div>
                        <div style="font-weight:bold;{pace_css}">{current_pace:.1f}</div>
                        <div style="font-size:0.7em;color:#666">({pace_div:+.1f} vs hist)</div>
                    </div>""", unsafe_allow_html=True)

                with c_t:
                    st.markdown(f"""<div style="display:flex;justify-content:space-around;text-align:center;">
                        <div><div style="font-size:0.65em;color:#aaa">PROJ</div><div style="font-weight:bold;color:#9775fa">{projected_total:.1f}</div></div>
                        <div><div style="font-size:0.65em;color:#aaa">LINHA</div><div style="font-weight:bold;color:#fff">{market_total:.1f}</div></div>
                    </div>""", unsafe_allow_html=True)

                with c_s:
                    if has_signal:
                        if diff_total > 0:
                            st.markdown(f"""<div style="text-align:right;">
                                <span class="over-signal">OVER</span><br>
                                <span style="font-size:0.8em;color:#51cf66">+{diff_total:.1f}</span>
                            </div>""", unsafe_allow_html=True)
                        else:
                            st.markdown(f"""<div style="text-align:right;">
                                <span class="under-signal">UNDER</span><br>
                                <span style="font-size:0.8em;color:#ff6b6b">{diff_total:.1f}</span>
                            </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='text-align:right;color:#555;font-size:0.8em'>Neutro</div>", unsafe_allow_html=True)

                st.markdown("<hr style='margin: 5px 0; border-color: #2d313a;'>", unsafe_allow_html=True)
