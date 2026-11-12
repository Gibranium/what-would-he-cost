"""
build_data.py - export the app's data from the value model (Python FTBLData). Run after 3-TM-VALUE-MODEL.

What goes into the app, on purpose: only this model's own outputs (worth, fair price, ranges) and aggregate market
effects. No Transfermarkt values, ids or contract dates, no event data. Writes data/players.csv and data/market.json.
The blend fee (half fair fee, half Transfermarkt value) is NOT exported per player: with the fair price next to it
anyone could work his Transfermarkt value back out. Only its backtest scores go in.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent / "Python FTBLData"     # the analysis folder (sibling of this app)
sys.path.insert(0, str(BASE / "transfermarkt"))
import tm_common as tc   # noqa: E402
import tm_value as tv    # noqa: E402

OUT = Path(__file__).resolve().parent / "data"
FINISHED, RUNNING = "2526", "2627"
AHEAD_SEASONS = ["2122", "2223", "2324", "2425", "2022", "2023", "2024"]   # finished, with 12 months of valuations after them
MIN_MINUTES = 600
LEAGUE_NAMES = {
    "ENG-Premier League": "Premier League", "ENG-Championship": "Championship", "ENG-League One": "League One",
    "ENG-League Two": "League Two", "ITA-Serie A": "Serie A", "ESP-La Liga": "La Liga", "GER-Bundesliga": "Bundesliga",
    "GER-2. Bundesliga": "2. Bundesliga", "FRA-Ligue 1": "Ligue 1", "NED-Eredivisie": "Eredivisie",
    "POR-Liga Portugal": "Liga Portugal", "BEL-Jupiler Pro League": "Belgian Pro League", "TUR-Super Lig": "Süper Lig",
    "RUS-Premier League": "Russian Premier League", "SCO-Premiership": "Scottish Premiership",
    "USA-Major League Soccer": "MLS", "BRA-Brasileirão": "Brasileirão", "ARG-Liga Profesional": "Argentina",
}
ROLE_NAMES = {"GK": "Goalkeeper", "CB": "Centre-back", "WB": "Full-back / wing-back", "CDM": "Central midfielder",
              "AMW": "Attacking mid / winger", "ST": "Striker"}


def clean_name(x):
    x = str(x)
    return x[2:-2] if x.startswith("['") and x.endswith("']") else x


def players(meta, fm):
    parts = []
    for s in (FINISHED, RUNNING):
        v = pd.read_csv(tc.DATA / "tm_values" / f"tm_values{s}.csv", index_col=0, dtype={"season_id": str})
        v["running"] = v["ref_kind"].eq("today")
        v["log_pred"] = np.log(v["model_value"])
        v = tv.price(v, fm, meta)                          # fair fee with the latest range rule
        parts.append(v)
    v = pd.concat(parts, ignore_index=True)
    v = v[v["league"].isin(LEAGUE_NAMES) & (v["minutes_played"] >= MIN_MINUTES) & v["fair_fee"].notna()].copy()
    out = pd.DataFrame({
        "player": v["player_name"].map(clean_name), "team": v["team_name"].map(clean_name),
        "league": v["league"].map(LEAGUE_NAMES), "role": v["position_group"].map(ROLE_NAMES), "position": v["position"],
        "age": v["age"].round(1), "minutes": v["minutes_played"].round(0).astype(int),
        "season": np.where(v["running"], "2026/27 so far", "2025/26"),
        "worth": (v["model_value"] / 1e6).round(2), "worth_low": (v["model_low"] / 1e6).round(2),
        "worth_high": (v["model_high"] / 1e6).round(2),
        "price": (v["fair_fee"] / 1e6).round(2), "price_low": (v["fee_low"] / 1e6).round(2),
        "price_high": (v["fee_high"] / 1e6).round(2),
        # the two prices behind the fair price, and how often players like him are bought by a Premier League club
        "price_pl": (v["fee_pl"] / 1e6).round(2) if "fee_pl" in v else np.nan,
        "price_other": (v["fee_other"] / 1e6).round(2) if "fee_other" in v else np.nan,
        "pl_chance": v["p_pl"].round(2) if "p_pl" in v else np.nan,
        # share of the running-season worth that comes from his last full season (0 = this season's games only)
        "history": v["history_weight"].fillna(0).round(2) if "history_weight" in v else 0.0})
    return out.sort_values(["season", "price"], ascending=[True, False]).reset_index(drop=True)


def _miss(e):
    return round(float(np.expm1(np.abs(e).median()) * 100), 1)


def checks(sc, d):
    """Aggregates behind 'How often it's right': where each method wins, the miss in euros, worth error by role, and
    whether a gap between my worth and the public estimate closes over the next year. Aggregates only."""
    t = tv.fee_backtest_rows(d)
    b = t[t["p_tm"].notna() & t["p_blend"].notna()].copy()
    b["age_b"] = pd.cut(b["age"], [0, 21, 24, 27, 30, 99], labels=["21 and under", "22–24", "25–27", "28–30", "31 and over"]).astype(str)
    b["fee_b"] = pd.cut(np.exp(b["p_fair"]), [0, 2e6, 5e6, 15e6, 40e6, 1e12],
                        labels=["under €2m", "€2–5m", "€5–15m", "€15–40m", "€40m and over"]).astype(str)
    b["role_b"] = b["position_group"].map(ROLE_NAMES)

    def seg(group, label, g):
        return {"group": group, "segment": label, "moves": int(len(g)), "fair": _miss(g["y"] - g["p_fair"]),
                "tm": _miss(g["y"] - g["p_tm"]), "blend": _miss(g["y"] - g["p_blend"])}

    where = [seg("All", "All moves", b)]
    for group, col, order in (("Fair price", "fee_b", ["under €2m", "€2–5m", "€5–15m", "€15–40m", "€40m and over"]),
                              ("Age", "age_b", ["21 and under", "22–24", "25–27", "28–30", "31 and over"]),
                              ("Role", "role_b", list(ROLE_NAMES.values()))):
        where += [seg(group, k, b[b[col] == k]) for k in order if (b[col] == k).sum() >= 50]
    ratio = lambda p: np.exp(b["y"] - b[p])               # real fee / estimate
    ten = {name: {"q10": round(float(ratio(p).quantile(.10) * 10), 1), "q25": round(float(ratio(p).quantile(.25) * 10), 1),
                  "q75": round(float(ratio(p).quantile(.75) * 10), 1), "q90": round(float(ratio(p).quantile(.90) * 10), 1),
                  "within_half": round(float(((ratio(p) > 0.5) & (ratio(p) < 1.5)).mean() * 100), 0)}
           for name, p in (("fair", "p_fair"), ("tm", "p_tm"), ("blend", "p_blend"))}
    # worth against the public estimate, by role (finished seasons, players the model never saw)
    fin = sc[sc["in_training"].astype(bool) & (sc["tm_value"] > 0)].copy()
    role_error = [{"role": ROLE_NAMES[r], "pct": _miss(g["residual"])} for r, g in fin.groupby("position_group") if r in ROLE_NAMES]
    # does a gap close? worth vs the public estimate at the end of a season -> the estimate's move over the next 12
    # months, beyond what players of his age and value level did
    val = pd.read_csv(tc.TM_DATA / "valuations.csv", usecols=["player_id", "date", "market_value_in_eur"])
    val["t"] = pd.to_datetime(val["date"], errors="coerce", format="mixed").astype("datetime64[ns]")
    val = val.dropna(subset=["t"]).sort_values("t")[["player_id", "t", "market_value_in_eur"]]
    a = fin[fin["season_id"].isin(AHEAD_SEASONS) & (fin["minutes_played"] >= 900)].copy()
    a["t"] = pd.to_datetime(a["ref_date"], errors="coerce").astype("datetime64[ns]") + pd.Timedelta(days=365)
    a = pd.merge_asof(a.dropna(subset=["t"]).sort_values("t"), val, on="t", by="player_id", direction="backward",
                      tolerance=pd.Timedelta(days=120))
    a = a[a["market_value_in_eur"] > 0].copy()
    a["gap"] = -a["residual"]                              # log(worth / estimate): > 0 = my worth is above
    a["change"] = np.log(a["market_value_in_eur"] / a["tm_value"])
    a["age_b"] = pd.cut(a["age"], [15, 21, 24, 27, 30, 45])
    a["lv_b"] = pd.qcut(np.log(a["tm_value"]), 5, labels=False)
    a["excess"] = a["change"] - a.groupby(["age_b", "lv_b"], observed=True)["change"].transform("mean")
    labels = ["My worth far below", "Below", "About equal", "Above", "My worth far above"]
    a["q"] = pd.qcut(a["gap"], 5, labels=labels)
    ahead = [{"group": k, "players": int(len(g)), "gap_pct": round(float(np.expm1(g["gap"].median()) * 100), 0),
              "pct": round(float(np.expm1(g["excess"].mean()) * 100), 1)} for k, g in a.groupby("q", observed=True)]
    X = np.column_stack([np.ones(len(a)), a["gap"]])
    closed = float(np.linalg.lstsq(X, a["excess"].to_numpy(), rcond=None)[0][1])
    return {"where": where, "ten_million": ten, "role_error": sorted(role_error, key=lambda r: r["pct"]),
            "ahead": ahead, "ahead_rows": int(len(a)), "ahead_share_closed": round(closed, 2), "blend_rows": int(len(b))}


def market(meta, fm):
    terms = tv.fee_terms(fm)
    pct = lambda k: round(float(terms.loc[k, "effect_pct"]), 1)
    sellers = [{"league": LEAGUE_NAMES.get(k.split(":", 1)[1], k.split(":", 1)[1]), "pct": pct(k)}
               for k in terms.index if k.startswith("league:") and k != "league:other"]
    sellers.append({"league": "Serie A", "pct": 0.0})
    roles = [{"role": ROLE_NAMES[k.split(":", 1)[1]], "pct": pct(k)} for k in terms.index if k.startswith("role:")]
    roles.append({"role": ROLE_NAMES["ST"], "pct": 0.0})
    tenure = [{"years": k.split(":", 1)[1], "pct": pct(k)} for k in terms.index if k.startswith("tenure:")]
    tenure.append({"years": tv.TENURE_REF, "pct": 0.0})
    b = pd.Series(fm["beta"], index=fm["cols"])
    age_curve = []                                       # fee vs a 25-year-old of the same worth, at three worths
    for w in (2e6, 10e6, 40e6):
        for age in np.arange(18, 34.5, 0.5):
            a = age - 25
            eff = b["age"] * a + b["age2"] * a ** 2 + b["age_x_worth"] * a * (np.log(w) - np.log(5e6))
            age_curve.append({"worth": f"€{w / 1e6:g}m worth", "age": float(age), "pct": round(float(np.expm1(eff) * 100), 1)})
    # football inflation: median fee / worth in each summer window (aggregate of the training moves)
    sc = pd.concat([pd.read_csv(f, index_col=0, dtype={"season_id": str})
                    for f in sorted((tc.DATA / "tm_values").glob("tm_values*.csv"))], ignore_index=True)
    d = tv.fee_rows(sc)
    s = d[d["window"].str.startswith("summer") & (d["date"].dt.year >= 2021)]
    infl = (s.assign(r=np.log(s["fee_eur"] / s["worth"])).groupby("window")
             .agg(moves=("r", "size"), r=("r", "median")).reset_index())
    infl["pct"] = (np.expm1(infl["r"]) * 100).round(1)
    table, pooled = tv.fee_backtest(d)
    buyer = None
    if fm.get("buyer") and "buyer_pl" in d:                 # who pays: the Premier League premium, in aggregates
        bb = dict(zip(fm["cols"], fm["beta"]))
        pl, su = d["buyer_pl"] == 1, d["window"].str.startswith("summer") & (d["date"].dt.year >= 2021)
        big = d["fee_eur"] >= 60e6
        mid = d["worth"] >= 5e6
        buyer = {"share_deals": round(float(pl.mean() * 100), 0), "share_money": round(float(d.loc[pl & su, "fee_eur"].sum() / d.loc[su, "fee_eur"].sum() * 100), 0),
                 "big_fees": int(big.sum()), "big_fees_pl": int((big & pl).sum()),
                 "others_ratio": round(float(np.exp(np.log(d.loc[~pl & mid, "fee_eur"] / d.loc[~pl & mid, "worth"]).median())), 2),
                 "premium": [{"worth": w_, "pct": round(float(np.expm1(bb["buyer_pl"] + bb.get("buyer_x_worth", 0.0) * np.log(w_ / 5)) * 100), 0)}
                             for w_ in (5, 15, 40, 100)],
                 "chance": [{"worth": f"{lo}–{hi}" if hi < 999 else f"{lo}+", "pct": round(float(pl[(d["worth"] >= lo * 1e6) & (d["worth"] < hi * 1e6)].mean() * 100), 0)}
                            for lo, hi in ((0, 5), (5, 15), (15, 40), (40, 999))]}
    ss = fm["spec"]["summer_share"]
    return {
        "moves": int(fm["rows"]), "trained_until": fm["trained_until"], "half_life": fm.get("half_life"), "buyer": buyer,
        "value_rows": int(meta["train_rows"]), "value_r2_forward": [f["r2"] for f in meta["report"]["forward"]],
        "value_error_forward": [f["median_abs_pct_error"] for f in meta["report"]["forward"]],
        "summer_pct": pct("summer"), "year_pct": pct("year"), "club_strength_pct": pct("team_rel"),
        "summer_share": {LEAGUE_NAMES[k]: v for k, v in ss.items() if k in LEAGUE_NAMES},
        "sellers": sorted(sellers, key=lambda r: -r["pct"]), "roles": sorted(roles, key=lambda r: -r["pct"]),
        "tenure": sorted(tenure, key=lambda r: ["<1", "1-2", "2-3", "3-4", "4+"].index(r["years"])),
        "age_curve": age_curve,
        "inflation": [{"window": r.window, "moves": int(r.moves), "pct": float(r.pct)} for r in infl.itertuples()],
        "backtest": pooled.reset_index().to_dict("records"),
        "backtest_windows": table.to_dict("records"),
        "checks": checks(sc, d),
    }


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    meta, fm = json.loads(tv.META_FILE.read_text()), tv.load_fee()
    p = players(meta, fm)
    p.to_csv(OUT / "players.csv", index=False)
    m = market(meta, fm)
    (OUT / "market.json").write_text(json.dumps(m, indent=1, default=float))
    print(f"players.csv: {len(p):,} rows ({p['season'].value_counts().to_dict()}) | market.json: {m['moves']:,} moves")
