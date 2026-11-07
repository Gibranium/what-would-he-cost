"""
build_data.py - export the app's data from the value model (Python FTBLData). Run after 3-TM-VALUE-MODEL.

What goes into the app, on purpose: only this model's own outputs (worth, fair price, ranges) and aggregate market
effects. No Transfermarkt values, ids or contract dates, no event data. Writes data/players.csv and data/market.json.
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
        "price_high": (v["fee_high"] / 1e6).round(2)})
    return out.sort_values(["season", "price"], ascending=[True, False]).reset_index(drop=True)


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
    ss = fm["spec"]["summer_share"]
    return {
        "moves": int(fm["rows"]), "trained_until": fm["trained_until"], "half_life": fm.get("half_life"),
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
    }


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    meta, fm = json.loads(tv.META_FILE.read_text()), tv.load_fee()
    p = players(meta, fm)
    p.to_csv(OUT / "players.csv", index=False)
    m = market(meta, fm)
    (OUT / "market.json").write_text(json.dumps(m, indent=1, default=float))
    print(f"players.csv: {len(p):,} rows ({p['season'].value_counts().to_dict()}) | market.json: {m['moves']:,} moves")
