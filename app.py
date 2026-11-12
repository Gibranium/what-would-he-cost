"""
What would he cost? — a fair transfer price per player (Premier League buyer, any other buyer, and the mix), learned from real fees.

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
def load(stamp):
    """stamp = the data files' modification times: new data after a push = a new cache entry (the server keeps the
    old cache alive across a redeploy, so without it the app showed the new code on the old data)."""
    p = pd.read_csv(HERE / "data" / "players.csv")
    m = json.loads((HERE / "data" / "market.json").read_text())
    return p, m


players, market = load(tuple((HERE / "data" / f).stat().st_mtime_ns for f in ("players.csv", "market.json")))


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
    f"<div class='lede'>A fair transfer price for {len(fin):,} players in {fin['league'].nunique()} leagues, "
    f"learned from {market['moves']:,} fees clubs actually paid: what a Premier League club would pay, what anyone else would, "
    f"and the one figure in between. Every price comes with a range, and I show how often the range was right.</div>"
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
                               "2026/27 so far = this season's games, leaning on his last full season until the minutes add up; "
                               "priced at today's market, with wider ranges.")
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
        st.info("Early in the season: a few games say little, so each price leans on the player's last full season "
                "(the fewer minutes this year, the more it leans). No full season behind him: this year's games only, "
                "and a wide range. Read them as a first look, not a number to quote.", icon="⏱️")

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
            h = float(r.get("history", 0) or 0)
            hist_note = "" if season == "2025/26" else (
                f" About {h:.0%} of his worth here comes from his last full season, the rest from this one."
                if h > 0 else " No full season behind him in my data: this rests on this season's games alone.")
            two = ""
            if pd.notna(r.get("price_pl", np.nan)) and abs(r["price_pl"] / r["price_other"] - 1) > 0.005:
                two = (f"<div class='rng'>If a Premier League club buys: <b>{eur(r['price_pl'])}</b> · anyone else: <b>{eur(r['price_other'])}</b> · "
                       f"players like him go to a Premier League club {r['pl_chance']:.0%} of the time</div>")
            st.markdown(f"""
<div class='price-card'>
  <div class='who'>{r['player']} · {r['team']} · {r['league']} · {r['role']} · {r['age']:.0f} · {r['minutes']:,} min ({r['season']})</div>
  <div class='big'>{eur(r['price'])}</div>
  <div class='rng'>80% range: {eur(r['price_low'])} – {eur(r['price_high'])}</div>
  {two}
  <div class='note'>What his profile is worth: {eur(r['worth'])} ({eur(r['worth_low'])} – {eur(r['worth_high'])}).
  The fair price is what clubs have paid for players like him: same worth, age, role, league and situation.{hist_note}</div>
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

    bu = market.get("buyer")
    if bu:
        st.subheader("Who buys")
        prem = pd.DataFrame(bu["premium"]).assign(worth=lambda x: x["worth"].map(lambda w: f"worth €{w:g}m"))
        st.markdown(f"The biggest effect of all. Premier League clubs make {bu['share_deals']:.0f}% of the deals and spend "
                    f"{bu['share_money']:.0f}% of the money in summer windows; {bu['big_fees_pl']} of the {bu['big_fees']} fees of "
                    f"€60m or more were theirs. For the same player sold by the same club, they pay more than any other "
                    f"buyer, and the extra is largest on cheap players: **{bu['premium'][0]['pct']:+.0f}%** at a worth of "
                    f"€{bu['premium'][0]['worth']:g}m, **{bu['premium'][-1]['pct']:+.0f}%** at €{bu['premium'][-1]['worth']:g}m. "
                    f"Every other buyer pays about {bu['others_ratio']:.2f} times the worth, at every level.")
        st.altair_chart(effect_bars(prem, "worth", sort=list(prem["worth"]), ref_note="Premier League buyer vs any other buyer"),
                        width="stretch", theme=None)
        st.markdown("How often a sold player goes to a Premier League club: "
                    + ", ".join(f"**{c['pct']:.0f}%** of those worth " + (f"€{c['worth'][:-1]}m or more" if c['worth'].endswith('+') else f"€{c['worth']}m") for c in bu["chance"])
                    + ". That share is what turns the two prices on a player's card into one fair price.")

    st.subheader("Where he's sold from")
    sl = {r["league"]: r["pct"] for r in market["sellers"]}
    top, low = max(sl, key=sl.get), min(sl, key=sl.get)
    st.markdown(f"Two players with the same worth don't sell for the same fee: it depends on the league that sells "
                f"them. Each bar is the fee compared with the same player sold by a Serie A club. A player "
                f"sold from {top} goes for **{sl[top]:+.0f}%**, one sold from {low} for **{sl[low]:+.0f}%**.")
    st.markdown("<div class='small'>These bars are with the Premier League buyer already taken out (see above). What is left "
                "is still partly about buyers the model doesn't name: players in England's lower leagues are bought by richer "
                "English clubs, South American clubs sell to Europe, and that shows up here under the seller's league.</div>", unsafe_allow_html=True)
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
        y=alt.Y("pct:Q", title="fee vs worth", axis=alt.Axis(labelExpr="datum.label + '%'"),
                scale=alt.Scale(domain=[min(0, infl["pct"].min()) - 5, max(0, infl["pct"].max()) + 5])),   # room for the labels
        color=alt.condition("datum.pct >= 0", alt.value(UP), alt.value(DOWN)),
        tooltip=[alt.Tooltip("label:N", title="Window"), alt.Tooltip("pct:Q", title="Fee vs worth, %", format="+.0f"),
                 alt.Tooltip("moves:Q", title="Moves")])
    txt = base.mark_text(fontSize=12, color=INK, dy=alt.expr("datum.pct >= 0 ? -8 : 12")).encode(
        y="pct:Q", text="txt:N")
    st.altair_chart(theme(alt.layer(bars, txt, alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=INK).encode(y="y:Q")),
                          height=240), width="stretch", theme=None)

    st.subheader("Age")
    ac = pd.DataFrame(market["age_curve"])
    ac["worth"] = ac["worth"].str.replace(r"^(€\S+) worth$", r"player worth \1", regex=True)
    order = list(dict.fromkeys(ac["worth"]))
    at = lambda w, a: float(ac[(ac["worth"] == w) & (ac["age"] == a)]["pct"].iloc[0])
    st.markdown(f"Young players cost more than their worth says, older ones less. The lines compare the fee with a "
                f"25-year-old of the same worth.\n\n"
                f"- A 19-year-old worth €2m sells for **{at(order[0], 19):+.0f}%**: about {1 + at(order[0], 19) / 100:.1f} times the fee of the 25-year-old.\n"
                f"- A 19-year-old worth €40m: **{at(order[-1], 19):+.0f}%**. The extra for youth is smaller on expensive players.\n"
                f"- A 30-year-old worth €2m: **{at(order[0], 30):+.0f}%**.")
    line = alt.Chart(ac).mark_line(strokeWidth=2).encode(
        x=alt.X("age:Q", title="age", scale=alt.Scale(domain=[18, 34]), axis=alt.Axis(values=list(range(18, 35, 2)), format="d")),
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
    blend = bt.get("blend (fair fee + Transfermarkt)", {})
    ck = market.get("checks", {})
    ten = ck.get("ten_million", {})
    st.markdown("Every transfer window since summer 2024, priced by a model trained only on the moves before it, "
                "then checked against the fee that was actually paid. The model is not told who bought him: "
                "it prices the move with the one fair price, as you would before a deal.")
    t1, t2, t3 = st.columns(3)
    t1.markdown(f"<div class='tile'><div class='v'>{fair.get('inside_80pct_range', 0):.0f}%</div>"
                f"<div class='l'>of real fees inside my 80% range. It should be about 80: the ranges are honest.</div></div>",
                unsafe_allow_html=True)
    t2.markdown(f"<div class='tile'><div class='v'>{fair.get('median_abs_pct_error', 0):.0f}%</div>"
                f"<div class='l'>typical miss on a single fee (median). "
                + (f"On a €10m price, half of the real fees fell between {eur(ten['fair']['q25'])} and {eur(ten['fair']['q75'])}."
                   if ten else "Fees are noisy: one player, one deal.") + "</div></div>",
                unsafe_allow_html=True)
    t3.markdown(f"<div class='tile'><div class='v'>{worth_only.get('median_abs_pct_error', 0):.0f}%</div>"
                f"<div class='l'>typical miss using his worth alone, without what I learned from fees.</div></div>",
                unsafe_allow_html=True)
    st.write("")
    w = pd.DataFrame(market["backtest_windows"])
    w["method"] = w["method"].replace({"fair fee": "My fair price", "worth alone": "My worth alone",
                                       "Transfermarkt value": "Transfermarkt value at the move",
                                       "blend (fair fee + Transfermarkt)": "Half and half"})
    order_m = [m for m in ["My fair price", "My worth alone", "Transfermarkt value at the move", "Half and half"]
               if m in set(w["method"])]
    order_w = list(dict.fromkeys(w["window"]))
    chart = alt.Chart(w).mark_bar(cornerRadiusEnd=3).encode(
        x=alt.X("window:N", sort=order_w, title=None, axis=alt.Axis(labelAngle=0, ticks=False)),
        xOffset=alt.XOffset("method:N", sort=order_m),
        y=alt.Y("median_abs_pct_error:Q", title="typical miss (median, %)"),
        color=alt.Color("method:N", sort=order_m, scale=alt.Scale(domain=order_m, range=[UP, NEUTRAL, DOWN, THIRD][:len(order_m)]), title=None),
        tooltip=[alt.Tooltip("window:N", title="Window"), alt.Tooltip("method:N", title=""),
                 alt.Tooltip("median_abs_pct_error:Q", title="Typical miss, %", format=".0f"),
                 alt.Tooltip("inside_80pct_range:Q", title="Inside range, %", format=".0f"),
                 alt.Tooltip("rows:Q", title="Moves")])
    st.altair_chart(theme(chart, height=280), width="stretch", theme=None)
    ww = w.pivot(index="window", columns="method", values="median_abs_pct_error").reindex(order_w)
    n_beat = int((ww["My fair price"] < ww["My worth alone"]).sum())
    beat_txt = "every window" if n_beat == len(ww) else f"{n_beat} of the {len(ww)} windows"
    hard = ww["My fair price"].idxmax()
    hard_txt = (f"The hardest window for my price was {hard} ({ww['My fair price'].max():.0f}%)"
                + (": winter windows have fewer, stranger deals." if hard.startswith("winter") else "."))
    st.markdown(f"""
**Where I lose, said plainly.** Across all moves, Transfermarkt's value at the time of the move misses less than my
price ({tm.get('median_abs_pct_error', 0):.0f}% against {fair.get('median_abs_pct_error', 0):.0f}%). It moves with the
news around a player and it knows his contract; my price knows neither for past moves.

The fair price beats my own worth number over all moves ({fair.get('median_abs_pct_error', 0):.0f}% against
{worth_only.get('median_abs_pct_error', 0):.0f}%) and in {beat_txt}: learning from fees is worth it. {hard_txt}
""")
    if ck:
        st.subheader("Where my price wins, and where it doesn't")
        wh = pd.DataFrame(ck["where"])
        seg = wh[wh["group"] != "All"]              # the sentence is read from the table, never typed
        lab = lambda r: ({"Fair price": "prices ", "Age": "ages "}.get(r["group"], "")
                         + (r["segment"].lower() + "s" if r["group"] == "Role" else r["segment"]))
        mine = [lab(r) for _, r in seg.iterrows() if r["fair"] < r["tm"]]
        theirs = [lab(r) for _, r in seg.iterrows() if r["fair"] >= r["tm"]]
        join = lambda xs: ", ".join(xs[:-1]) + " and " + xs[-1] if len(xs) > 1 else "".join(xs)
        if mine and theirs:
            where_txt = (f"Against Transfermarkt's value, my price misses less on {join(mine)}; Transfermarkt misses "
                         f"less on {join(theirs) if len(theirs) <= len(mine) else 'everything else'}.")
        else:
            where_txt = ("My price misses less than Transfermarkt's value in every group." if mine
                         else "Transfermarkt's value misses less than my price in every group.")
        st.markdown("The same test, split by the kind of deal. Each column is a typical miss: lower is better. " + where_txt)
        best = wh[["fair", "tm", "blend"]].idxmin(axis=1).map({"fair": "My fair price", "tm": "Transfermarkt", "blend": "Half and half"})
        st.dataframe(pd.DataFrame({
            "Deals": np.where(wh["group"].isin(["All", "Role"]), wh["segment"], wh["group"] + ": " + wh["segment"]),
            "Moves": wh["moves"], "My fair price": wh["fair"].map(lambda x: f"{x:.0f}%"),
            "Transfermarkt": wh["tm"].map(lambda x: f"{x:.0f}%"), "Half and half": wh["blend"].map(lambda x: f"{x:.0f}%"),
            "Lowest miss": best}), hide_index=True, width="stretch", height=38 + 35 * len(wh))
        if blend:
            st.markdown(f"""
**Half and half.** Averaging my price with Transfermarkt's value gives about the same typical miss as Transfermarkt alone
({blend.get('median_abs_pct_error', 0):.0f}% against {tm.get('median_abs_pct_error', 0):.0f}%), but fewer big misses, because the two get different players wrong.
I don't show that average here: this page carries my numbers only.
""")
        st.subheader("Does it see things first?")
        ah = pd.DataFrame(ck["ahead"])
        ah["group"] = ah["group"].replace({"My worth far above": "I rated him far higher", "Above": "Higher",
                                           "About equal": "About the same", "Below": "Lower",
                                           "My worth far below": "I rated him far lower"})
        st.markdown(f"""
When my worth and the public value disagree, who turns out right? I checked {ck['ahead_rows']:,} past player-seasons.

Players I rated far higher than their public value saw that value grow **{abs(ah['pct'].iloc[-1]):.0f}% more** than
similar players over the next year. Players I rated far lower: **{abs(ah['pct'].iloc[0]):.0f}% less**. So the model
does pick some things up early. Only some: most disagreements stay disagreements.
""")
        st.altair_chart(effect_bars(ah.rename(columns={"group": "gap"}), "gap", sort=list(ah["group"])[::-1],
                                    ref_note="public value a year later, against similar players (same age and value)"),
                        width="stretch", theme=None)
    st.markdown(f"If you think a number here is wrong, [tell me]({SITE}).")

# ---------------------------------------------------------------- 4. method and limits
with tab_method:
    fr = market.get("value_r2_forward", [])
    re_ = {r["role"]: r["pct"] for r in market.get("checks", {}).get("role_error", [])}
    far = sorted(re_, key=re_.get, reverse=True)[:2]          # the two roles furthest from public estimates, from the data
    role_err = (f" (typical gap {re_[far[0]]:.0f}% and {re_[far[1]]:.0f}%, against "
                f"{min(v for k, v in re_.items() if k not in far):.0f}–"
                f"{max(v for k, v in re_.items() if k not in far):.0f}% for the other roles)") if re_ else ""
    far_txt = (" and ".join(r.lower() + "s" for r in far)).capitalize() if re_ else "Goalkeepers and strikers"
    cb_txt = (" Defenders are no worse than midfielders."
              if re_ and re_.get("Centre-back", 0) <= re_.get("Central midfielder", 0) + 1 else "")
    bu = market.get("buyer")
    if bu:
        prem = {p["worth"]: p["pct"] for p in bu["premium"]}
        ch = {c["worth"]: c["pct"] for c in bu["chance"]}
        buyer_txt = f"""**One fair price, and the two behind it.** Nobody knows where a player goes next, but one thing about the buyer changes
the fee more than anything else I can measure: whether it is a Premier League club. They are {bu['share_deals']:.0f}% of the
deals and {bu['share_money']:.0f}% of the money spent in summer windows, and {bu['big_fees_pl']} of the {bu['big_fees']} fees of
€60m or more were paid by them. For the same player, same age, same selling club, a Premier League buyer pays about
{prem[5]:+.0f}% at a worth of €5m, {prem[15]:+.0f}% at €15m, {prem[40]:+.0f}% at €40m and {prem[100]:+.0f}% at €100m: the
premium is largest on cheap players and almost gone at the very top. Every other buyer pays close to the worth
(about {bu['others_ratio']:.2f} times it above €5m), at every level.

So each player has two prices, *if a Premier League club buys* and *anyone else*, and the fair price is the mix of
the two by how often players like him (worth, age, selling league) are bought by a Premier League club: {ch['0–5']:.0f}%
of players worth under €5m, {ch['5–15']:.0f}% at €5–15m, {ch['15–40']:.0f}% at €15–40m, {ch['40+']:.0f}% above €40m.
Why only this buyer: it is the only one big and frequent enough to measure. I don't price per club."""
    else:
        buyer_txt = """**One price, not one per buyer.** Nobody knows where a player goes next. The fees of similar players already carry
where players like him realistically went."""
    st.markdown(f"""
**Two steps.**

1. **Worth.** What a player's profile is worth: his numbers in his role from my own event-data models, age,
   minutes, league level, team strength (my Dixon-Coles ratings) and his club's standing with the market (how
   its squad was valued the season before, against its league). Trained on {market['value_rows']:,}
   player-seasons against public market-value estimates. Tested on the last {len(fr)} seasons, each priced by a
   model that had only seen the seasons before it, it explains {min(fr):.0%} to {max(fr):.0%} of the differences in
   value between players. Most of the level comes from age, league and club; what he does on the
   pitch decides where he sits among players like him. Early in a season, this year's games are mixed with his last
   full season: the fewer minutes so far, the more last season counts.
2. **Fair price.** What clubs actually paid for players of that worth: {market['moves']:,} permanent transfers with a
   reported fee. It learns where he's sold from, the selling club's strength, role, age, years at the club, the
   window, and football inflation (recent moves weigh more: half-life {market.get('half_life', 2):g} years). For this
   season's players, the actual years left on the contract replace the years at the club.

{buyer_txt}

**What it can't see.**
- Contract length for past moves (only current contracts are public), add-ons, sell-on clauses, and how badly a club
  needs to sell. The ranges are wide partly because of this.
- Undisclosed fees, free transfers and loans: no fee to learn from, and undisclosed fees aren't random, so the sample
  leans towards deals that made the news.
- Mid-season moves are left out of the training: my season numbers merge the time at both clubs.
- Injuries, character, the agent. That's what video and a phone call are for.
- Players of clubs new to their league this season: early on, their worth can run high, because there is no last
  season at that level to lean on. Read them with care until about half a season.
- {far_txt}: that's where my worth sits furthest from public estimates{role_err}.{cb_txt}

**Data.** Player numbers come from my own models on event data. Worth is trained on public market-value
estimates (Transfermarkt) and the fees they report. The prices on this page are my model's, not Transfermarkt's, and
nothing here republishes anyone's data. On paid work I can run the same pipeline on your licensed data.

Built with Python, XGBoost, CatBoost and Streamlit; AI helped me build and edit it, as usual, to be fair.
""")

# ---------------------------------------------------------------- footer
st.markdown(f"""
<div class='cta'>
<b>Looking at a player right now?</b> Send me the name and the league in two lines. A
<a href='{SITE}'>Second opinion</a> (€200) gives you the price, the role he actually plays, how his league move has
gone for others, the video checks to run and a sign / monitor / pass verdict, with the limits stated.
<br><br>Not buying yet? <a href='{NEWSLETTER}'>The Cutback</a> publishes this kind of work in full, misses included.
</div>
<div class='small' style='margin-top:10px'>Davide Gualano · Turin · <a href='{SITE}'>davidegualano.com</a></div>
""", unsafe_allow_html=True)
