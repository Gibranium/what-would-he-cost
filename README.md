# What would he cost?

A fair transfer price per player, learned from real fees: what a Premier League club would pay, what anyone else would, and the mix of the two. Streamlit app by Davide Gualano (The Cutback).

- `app.py`: the app. Run locally with `streamlit run app.py`.
- `data/players.csv`, `data/market.json`: the only data the app reads.
- `build_data.py`: rebuilds both files from the value model in `../Python FTBLData` (run after
  `transfermarkt/3-TM-VALUE-MODEL`). Not needed on the server.

What is published, on purpose: only my model's outputs (worth, fair price and their ranges) and aggregate market
effects. No third-party values, ids or contract dates, and no event data.
