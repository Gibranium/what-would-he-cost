"""
What would he cost? — one fair transfer price per player, learned from real fees.

Davide Gualano · The Cutback. Data: data/players.csv and data/market.json, written by build_data.py from my
value model. Only my model's outputs are here: no third-party values, ids or event data.
"""
import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

HERE = Path(__file__).parent
SITE = "https://davidegualano.com"
NEWSLETTER = "https://the-cutback.beehiiv.com"

# palette: validated against the page surface (#D7D1CF) — up / down / third series; gray only for reference marks
UP, DOWN, THIRD, NEUTRAL, INK, MUTED = "#A8231C", "#2A52B0", "#2E7D4F", "#8A8380", "#1E1B1A", "#5C5552"
SURFACE, CARD = "#D7D1CF", "#E6E1DE"

st.set_page_config(page_title="What would he cost? · Davide Gualano", page_icon="⚽", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stDataFrame, button, input {{ font-family: 'Source Sans 3', sans-serif; }}
.block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1100px; }}
h1 {{ font-weight: 700; letter-spacing: -0.02em; margin-bottom: 0.2rem; }}
.lede {{ font-size: 1.15rem; color: {MUTED}; max-width: 720px; margin-bottom: 0.4rem; }}
.price-card {{ background: {CARD}; border-radius: 10px; padding: 18px 22px; margin: 6px 0 10px 0; }}
.price-card .who {{ font-size: 1.05rem; color: {MUTED}; }}
.price-card .big {{ font-size: 2.6rem; font-weight: 700; line-height: 1.1; color: {INK}; }}
.price-card .rng {{ font-size: 1.05rem; color: {INK}; }}
.price-card .note {{ font-size: 0.95rem; color: {MUTED}; margin-top: 6px; }}
.tile {{ background: {CARD}; border-radius: 10px; padding: 14px 18px; height: 100%; }}
.tile .v {{ font-size: 2rem; font-weight: 700; color: {INK}; line-height: 1.1; }}
.tile .l {{ font-size: 0.95rem; color: {MUTED}; }}
.cta {{ background: {INK}; color: #F3EFED; border-radius: 10px; padding: 18px 22px; margin-top: 28px; }}
.cta a {{ color: #F3EFED; font-weight: 600; }}
.small {{ font-size: 0.9rem; color: {MUTED}; }}
@media (max-width: 640px) {{ .price-card .big {{ font-size: 2.1rem; }} .block-container {{ padding-left: 1rem; padding-right: 1rem; }} }}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load():
    p = pd.read_csv(HERE / "data" / "players.csv")
    m = json.loads((HERE / "data" / "market.json").read_text())
    return p, m


players, market = load()


def eur(x):
    """€ in millions, readable at every scale."""
    if x >= 100:
        return f"€{x:,.0f}m"
    if x >= 10:
        return f"€{x:.0f}m"
    if x >= 1:
        return f"€{x:.1f}m"
    return f"€{x * 1000:,.0f}k"


def theme(chart, height=None):
    c = chart.configure_view(strokeWidth=0).configure(background="transparent", font="Source Sans 3, sans-serif",
                                                      autosize=alt.AutoSizeParams(type="fit-x", contains="padding"),
                                                      padding={"left": 28, "right": 34, "top": 6, "bottom": 4}) \
        .configure_axis(labelColor=MUTED, titleColor=MUTED, gridColor="#C4BDBA", domainColor="#B5ADA9",
                        tickColor="#B5ADA9", labelFontSize=12, titleFontSize=12, titleFontWeight="normal") \
        .configure_legend(labelColor=INK, titleColor=MUTED, labelFontSize=12, orient="top", labelLimit=320)
    return c.properties(height=height) if height else c


def effect_bars(df, label, value="pct", sort=None, ref_note=None):
    """Horizontal bars of a % effect vs a reference (0): red above, blue below, value at every bar end."""
    d = df.copy()
    short = {"Russian Premier League": "Russian PL", "Scottish Premiership": "Scotland", "Belgian Pro League": "Belgium",
             "Attacking mid / winger": "Att. mid / winger", "Full-back / wing-back": "Full-back / WB",
             "Central midfielder": "Central mid"}
    d[label] = d[label].replace(short)
    sort = [short.get(x, x) for x in sort] if sort else None
    order = sort or list(d.sort_values(value, ascending=False)[label])
    d["dir"] = np.where(d[value] >= 0, "more", "less")
    d["txt"] = d[value].map(lambda v: f"{v:+.0f}%")
    lo, hi = min(0, d[value].min()), max(0, d[value].max())
    pad = max(8, (hi - lo) * 0.14)                       # room for the value labels on both sides
    x = alt.X(f"{value}:Q", title=ref_note, scale=alt.Scale(domain=[lo - (pad if lo < 0 else 0), hi + pad], nice=False),
              axis=alt.Axis(labelExpr="(datum.value > 0 ? '+' : '') + datum.value + '%'", tickCount=6))
    base = alt.Chart(d).encode(
        y=alt.Y(f"{label}:N", sort=order, title=None,
                axis=alt.Axis(labelLimit=200, ticks=False, domain=False, labelPadding=8)),
        tooltip=[alt.Tooltip(f"{label}:N", title=label.capitalize()), alt.Tooltip(f"{value}:Q", title="Effect, %", format="+.0f")])
    bars = base.mark_bar(cornerRadiusEnd=4, height={"band": 0.7}).encode(
        x=x, color=alt.Color("dir:N", scale=alt.Scale(domain=["more", "less"], range=[UP, DOWN]), legend=None))
    text = base.mark_text(fontSize=12, color=INK, dx=alt.expr(f"datum.{value} >= 0 ? 5 : -5"),
                          align=alt.expr(f"datum.{value} >= 0 ? 'left' : 'right'")).encode(x=x, text="txt:N")
    rule = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=INK, strokeWidth=1).encode(x="x:Q")
    return theme(alt.layer(bars, text, rule).properties(height=alt.Step(26)))


# ---------------------------------------------------------------- header
fin = players[players["season"] == "2025/26"]
st.markdown("<h1>What would he cost?</h1>", unsafe_allow_html=True)
st.markdown(
    f"<div class='lede'>One fair transfer price for {len(fin):,} players in {fin['league'].nunique()} leagues, "
    f"learned from {market['moves']:,} fees clubs actually paid. Every price comes with a range, "
    f"and I show how often the range was right.</div>"
    f"<div class='small'>Everything I'd build for you, I've already built in public. This is the price part of a "
    f"<a href='{SITE}'>Second opinion</a>.</div>", unsafe_allow_html=True)
st.write("")

tab_price, tab_market, tab_check, tab_method = st.tabs(
    ["Price a player", "What moves a fee", "How often it's right", "Method and limits"])

# ---------------------------------------------------------------- 1. price a player
with tab_price:
    c1, c2 = st.columns([3, 2])
    with c1:
        q = st.text_input("Find a player or team", placeholder="e.g. Yildiz, Coventry")
    with c2:
        season = st.radio("Season", ["2025/26", "2026/27 so far"], horizontal=True,
                          help="2025/26 = full season, priced at the summer 2026 market. "
                               "2026/27 so far = a handful of games, priced at today's market: much wider ranges.")
    pool = players[players["season"] == season]
    with st.expander("Filters"):
        f1, f2 = st.columns(2)
        leagues = f1.multiselect("League", sorted(pool["league"].unique()))
        roles = f2.multiselect("Role", list(dict.fromkeys(["Goalkeeper", "Centre-back", "Full-back / wing-back",
                                                            "Central midfielder", "Attacking mid / winger", "Striker"])))
        f3, f4 = st.columns(2)
        ages = f3.slider("Age", 16, 40, (16, 40))
        min_default = 900 if season == "2025/26" else 600
        mins = f4.slider("Minutes at least", 600, 3000, min_default, step=100)
    v = pool[pool["minutes"] >= mins]
    if leagues:
        v = v[v["league"].isin(leagues)]
    if roles:
        v = v[v["role"].isin(roles)]
    v = v[v["age"].between(*ages)]
    if q:
        ql = q.strip().lower()
        v = v[v["player"].str.lower().str.contains(ql, regex=False) | v["team"].str.lower().str.contains(ql, regex=False)]
    v = v.sort_values("price", ascending=False).reset_index(drop=True)

    if season != "2025/26":
        st.info("Early in the season: these prices rest on a few games, so the ranges are wide on purpose. "
                "Read them as a first look, not a number to quote.", icon="⏱️")

    if v.empty:
        st.write("No players match. Loosen the filters or check the spelling.")
    else:
        show = pd.DataFrame({          # price first: on a phone the right-hand columns scroll off
            "Player": v["player"], "Fair price": v["price"].map(eur),
            "80% range": [f"{eur(a)} – {eur(b)}" for a, b in zip(v["price_low"], v["price_high"])],
            "Team": v["team"], "League": v["league"], "Role": v["role"],
            "Age": v["age"].map(lambda a: f"{a:.0f}"), "Min": v["minutes"]})
        st.caption(f"{len(v):,} player{'s' if len(v) != 1 else ''} · sorted by fair price · tap a row for his card")
        ev = st.dataframe(show.head(400), hide_index=True, width="stretch", height=min(360, 38 + 35 * min(len(v), 400)),
                          on_select="rerun", selection_mode="single-row",
                          column_config={"Min": st.column_config.NumberColumn("Min", help="Minutes played", format="%d")})
        sel = ev.selection.rows if ev and hasattr(ev, "selection") else []
        idx = sel[0] if sel else (0 if len(v) == 1 or q else None)
        if idx is not None:
            r = v.iloc[idx]
            st.markdown(f"""
<div class='price-card'>
  <div class='who'>{r['player']} · {r['team']} · {r['league']} · {r['role']} · {r['age']:.0f} · {r['minutes']:,} min ({r['season']})</div>
  <div class='big'>{eur(r['price'])}</div>
  <div class='rng'>80% range: {eur(r['price_low'])} – {eur(r['price_high'])}</div>
  <div class='note'>What his profile is worth: {eur(r['worth'])} ({eur(r['worth_low'])} – {eur(r['worth_high'])}).
  The fair price is what clubs have paid for players like him: same worth, age, role, league and situation.</div>
</div>""", unsafe_allow_html=True)
            band = pd.DataFrame([
                {"what": "Fair price", "lo": r["price_low"], "hi": r["price_high"], "mid": r["price"]},
                {"what": "Worth", "lo": r["worth_low"], "hi": r["worth_high"], "mid": r["worth"]}])
            lo_dom = max(0.05, min(band["lo"]) * 0.8)
            hi_dom = max(band["hi"]) * 1.2
            xs = alt.X("lo:Q", scale=alt.Scale(type="log", domain=[lo_dom, hi_dom]), title="€ million (log scale)",
                       axis=alt.Axis(grid=False, values=[v for v in [0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 500] if lo_dom <= v <= hi_dom],
                                     labelExpr="datum.value >= 1 ? '€' + datum.value + 'm' : '€' + datum.value * 1000 + 'k'"))
            rng = alt.Chart(band).mark_rule(strokeWidth=10, strokeCap="round").encode(
                y=alt.Y("what:N", title=None, sort=["Fair price", "Worth"], axis=alt.Axis(ticks=False, domain=False, labelPadding=8, labelFontSize=13, labelColor=INK)),
                x=xs, x2="hi:Q",
                color=alt.Color("what:N", scale=alt.Scale(domain=["Fair price", "Worth"], range=[UP, NEUTRAL]), legend=None),
                tooltip=[alt.Tooltip("what:N", title=""), alt.Tooltip("lo:Q", title="Low, €m", format=".1f"),
                         alt.Tooltip("mid:Q", title="Central, €m", format=".1f"), alt.Tooltip("hi:Q", title="High, €m", format=".1f")])
            mid = alt.Chart(band).mark_point(filled=True, size=160, color=INK, stroke=CARD, strokeWidth=2).encode(
                y=alt.Y("what:N", sort=["Fair price", "Worth"]), x="mid:Q")
            st.altair_chart(theme(alt.layer(rng, mid), height=110), width="stretch", theme=None)

            # players priced like him: same role, similar age, other leagues, nearest fair price
            like = players[(players["season"] == r["season"]) & (players["role"] == r["role"])
                           & (players["league"] != r["league"]) & (players["age"].sub(r["age"]).abs() <= 2)
                           & (players["minutes"] >= 900)].copy()
            if len(like):
                like["gap"] = (np.log(like["price"]) - np.log(r["price"])).abs()
                like = like.nsmallest(5, "gap")
                st.markdown("**Priced like him in other leagues** · same role, within two years of his age")
                st.dataframe(pd.DataFrame({"Player": like["player"], "Fair price": like["price"].map(eur),
                                           "League": like["league"], "Team": like["team"],
                                           "Age": like["age"].map(lambda a: f"{a:.0f}")}),
                             hide_index=True, width="stretch")

# ---------------------------------------------------------------- 2. what moves a fee
with tab_market:
    st.markdown(f"Same worth, different fee. Each chart shows how much more or less clubs paid, for the same "
                f"profile, from {market['moves']:,} permanent transfers with a reported fee "
                f"(to {market['trained_until'][:7]}). Recent moves count more, so this is today's market.")

    st.subheader("Where he's sold from")
    st.markdown("Against a player sold by a Serie A club. English clubs buy most players sold from English "
                "leagues, and they pay more: it shows up here as the selling league.")
    st.altair_chart(effect_bars(pd.DataFrame(market["sellers"]), "league", ref_note="vs a Serie A seller"),
                    width="stretch", theme=None)

    st.subheader("Football inflation")
    infl = pd.DataFrame(market["inflation"])
    infl["label"] = infl["window"].str.replace("summer ", "")
    infl["txt"] = infl["pct"].map(lambda v: f"{v:+.0f}%")
    st.markdown("Median fee against worth, every summer window. Not a straight line: fees sat below worth after Covid, "
                "jumped in 2024 and have held since. That's why the model weights recent moves more.")
    base = alt.Chart(infl).encode(x=alt.X("label:N", title="summer window", sort=list(infl["label"]),
                                          axis=alt.Axis(labelAngle=0, ticks=False)))
    bars = base.mark_bar(cornerRadiusEnd=4, width={"band": 0.6}).encode(
        y=alt.Y("pct:Q", title="fee vs worth", axis=alt.Axis(labelExpr="datum.label + '%'")),
        color=alt.condition("datum.pct >= 0", alt.value(UP), alt.value(DOWN)),
        tooltip=[alt.Tooltip("label:N", title="Window"), alt.Tooltip("pct:Q", title="Fee vs worth, %", format="+.0f"),
                 alt.Tooltip("moves:Q", title="Moves")])
    txt = base.mark_text(fontSize=12, color=INK, dy=alt.expr("datum.pct >= 0 ? -8 : 12")).encode(
        y="pct:Q", text="txt:N")
    st.altair_chart(theme(alt.layer(bars, txt, alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=INK).encode(y="y:Q")),
                          height=240), width="stretch", theme=None)

    st.subheader("Age")
    st.markdown("Against a 25-year-old of the same worth. Youth costs extra, but the premium shrinks as the price "
                "goes up: for a cheap teenager clubs pay roughly double, for an expensive one far less.")
    ac = pd.DataFrame(market["age_curve"])
    order = list(dict.fromkeys(ac["worth"]))
    line = alt.Chart(ac).mark_line(strokeWidth=2).encode(
        x=alt.X("age:Q", title="age", scale=alt.Scale(domain=[18, 34])),
        y=alt.Y("pct:Q", title="fee vs a 25-year-old", axis=alt.Axis(labelExpr="datum.label + '%'")),
        color=alt.Color("worth:N", sort=order, scale=alt.Scale(domain=order, range=[UP, DOWN, THIRD]), title=None),
        tooltip=[alt.Tooltip("worth:N", title=""), alt.Tooltip("age:Q", title="Age"),
                 alt.Tooltip("pct:Q", title="Fee vs 25-year-old, %", format="+.0f")])
    st.altair_chart(theme(alt.layer(line, alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=INK, strokeDash=[3, 3]).encode(y="y:Q")),
                          height=280), width="stretch", theme=None)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Role")
        st.markdown("Against a striker of the same worth.")
        st.altair_chart(effect_bars(pd.DataFrame(market["roles"]), "role", ref_note="vs a striker"),
                        width="stretch", theme=None)
    with c2:
        st.subheader("Years at the club")
        st.markdown("Against 2–3 years. Long stays often mean a contract running down, so a lower fee.")
        ten = pd.DataFrame(market["tenure"]).rename(columns={"years": "years at club"})
        st.altair_chart(effect_bars(ten, "years at club", sort=list(ten["years at club"]), ref_note="vs 2–3 years"),
                        width="stretch", theme=None)

    st.subheader("Summer or winter")
    st.markdown(f"The same player fetches **{market['summer_pct']:+.0f}%** in a summer window against a "
                f"December–February one (mostly the off-season of MLS, Brazil and Argentina). Each player is priced "
                f"with his league's usual mix: about {market['summer_share'].get('Serie A', 0.95):.0%} of Serie A sales "
                f"happen in summer, {market['summer_share'].get('MLS', 0.26):.0%} of MLS ones.")

# ---------------------------------------------------------------- 3. how often it's right
with tab_check:
    bt = {r["method"]: r for r in market["backtest"]}
    fair, worth_only, tm = bt.get("fair fee", {}), bt.get("worth alone", {}), bt.get("Transfermarkt value", {})
    st.markdown("Every transfer window since summer 2024, priced by a model trained only on the moves before it, "
                "then checked against the fee that was actually paid.")
    t1, t2, t3 = st.columns(3)
    t1.markdown(f"<div class='tile'><div class='v'>{fair.get('inside_80pct_range', 0):.0f}%</div>"
                f"<div class='l'>of real fees inside my 80% range. It should be about 80: the ranges are honest.</div></div>",
                unsafe_allow_html=True)
    t2.markdown(f"<div class='tile'><div class='v'>{fair.get('median_abs_pct_error', 0):.0f}%</div>"
                f"<div class='l'>typical miss on a single fee (median). Fees are noisy: one player, one deal.</div></div>",
                unsafe_allow_html=True)
    t3.markdown(f"<div class='tile'><div class='v'>{worth_only.get('median_abs_pct_error', 0):.0f}%</div>"
                f"<div class='l'>typical miss using his worth alone, without what I learned from fees.</div></div>",
                unsafe_allow_html=True)
    st.write("")
    w = pd.DataFrame(market["backtest_windows"])
    w["method"] = w["method"].replace({"fair fee": "My fair price", "worth alone": "My worth alone",
                                       "Transfermarkt value": "Transfermarkt value at the move"})
    order_m = ["My fair price", "My worth alone", "Transfermarkt value at the move"]
    order_w = list(dict.fromkeys(w["window"]))
    chart = alt.Chart(w).mark_bar(cornerRadiusEnd=3).encode(
        x=alt.X("window:N", sort=order_w, title=None, axis=alt.Axis(labelAngle=0, ticks=False)),
        xOffset=alt.XOffset("method:N", sort=order_m),
        y=alt.Y("median_abs_pct_error:Q", title="typical miss (median, %)"),
        color=alt.Color("method:N", sort=order_m, scale=alt.Scale(domain=order_m, range=[UP, NEUTRAL, DOWN]), title=None),
        tooltip=[alt.Tooltip("window:N", title="Window"), alt.Tooltip("method:N", title=""),
                 alt.Tooltip("median_abs_pct_error:Q", title="Typical miss, %", format=".0f"),
                 alt.Tooltip("inside_80pct_range:Q", title="Inside range, %", format=".0f"),
                 alt.Tooltip("rows:Q", title="Moves")])
    st.altair_chart(theme(chart, height=280), width="stretch", theme=None)
    st.markdown(f"""
**Where I lose, said plainly.** Transfermarkt's value at the time of the move misses less than my price
({tm.get('median_abs_pct_error', 0):.0f}% against {fair.get('median_abs_pct_error', 0):.0f}%). Two likely reasons: a
valuation can move with the rumours, so by the time a deal is signed it may already reflect the fee; and it takes
contract length into account for every past move, which my data can't. My price is built from what a player does on the pitch, so it can
price players before the market starts talking about them. That's the point of it, and also its limit.

The fair price beats my own worth number in every window ({fair.get('median_abs_pct_error', 0):.0f}% against
{worth_only.get('median_abs_pct_error', 0):.0f}%): learning from fees is worth it. January windows are the hardest
(fewer, stranger deals). If you think a number here is wrong, [tell me]({SITE}).
""")

# ---------------------------------------------------------------- 4. method and limits
with tab_method:
    fr = market.get("value_r2_forward", [])
    st.markdown(f"""
**Two steps.**

1. **Worth.** What a player's profile is worth: his numbers in his role from my own event-data models, age,
   minutes, league level and team strength (my Dixon-Coles ratings). Trained on {market['value_rows']:,}
   player-seasons against public market-value estimates, and checked forward in time on seasons it hadn't seen
   (R² {', '.join(f'{x:.2f}' for x in fr)}).
2. **Fair price.** What clubs actually paid for players of that worth: {market['moves']:,} permanent transfers with a
   reported fee. It learns where he's sold from, the selling club's strength, role, age, years at the club, the
   window, and football inflation (recent moves weigh more: half-life {market.get('half_life', 2):g} years). For this
   season's players, the actual years left on the contract replace the years at the club.

**One price, not one per buyer.** Nobody knows where a player goes next. The fees of similar players already carry
where players like him realistically went: a 2. Bundesliga striker is priced from what 2. Bundesliga strikers fetched,
not from what a Premier League club would pay.

**What it can't see.**
- Contract length for past moves (only current contracts are public), add-ons, sell-on clauses, and how badly a club
  needs to sell. The ranges are wide partly because of this.
- Undisclosed fees, free transfers and loans: no fee to learn from, and undisclosed fees aren't random, so the sample
  leans towards deals that made the news.
- Mid-season moves are left out of the training: my season numbers merge the time at both clubs.
- Injuries, character, the agent. That's what video and a phone call are for.
- Event data struggles with defenders and goalkeepers, so their worth is the least reliable part.

**Data.** Player numbers come from my own models on public event data. Worth is trained on public market-value
estimates (Transfermarkt) and the fees they report. The prices on this page are my model's, not Transfermarkt's, and
nothing here republishes anyone's data. On paid work I can run the same pipeline on your licensed data.

Built with Python, scikit-learn and Streamlit; AI helped me build and edit it, as usual, to be fair.
""")

# ---------------------------------------------------------------- footer
st.markdown(f"""
<div class='cta'>
<b>Looking at a player right now?</b> Send me the name and the league in two lines. A
<a href='{SITE}'>Second opinion</a> (€350) gives you the price, the role he actually plays, how his league move has
gone for others, the video checks to run and a sign / monitor / pass verdict, with the limits stated.
<br><br>Not buying yet? <a href='{NEWSLETTER}'>The Cutback</a> publishes this kind of work in full, misses included.
</div>
<div class='small' style='margin-top:10px'>Davide Gualano · Turin · <a href='{SITE}'>davidegualano.com</a></div>
""", unsafe_allow_html=True)
