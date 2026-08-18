# Football Scouting & Data Analytics Dashboard

This project is a complete football analytics dashboard covering transfer market, club performance and using a machine learning model to identify over and under valued players across Europe's top 5 leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1).


---

## Dashboard Preview

The Power BI dashboard (.pbix) is included in this repo.

- **League Overview** — league tables, top scorers and assisters, goals + assists per 90 minutes
- **Transfer Market** — transfer spend by league over time (2014–2025), club net spend, average transfer fees
- **Player Valuation Model** — predicted vs actual market value, undervalued/overvalued player rankings

## Data Sources


Transfermarkt (via Kaggle) | Player valuations, transfers, clubs, games | Historical, all seasons |
FBref (via Kaggle) | Player performance stats (goals, assists, xG, xA, tackles, etc.) | 2017–18 to 2023–24 |

Transfermarkt dataset: [Football Data from Transfermarkt – Kaggle](https://www.kaggle.com/datasets/davidcariboo/player-scores)
FBref dataset: [FBRef 2017–2024 Top 5 Leagues – Kaggle](https://www.kaggle.com/datasets/akshankrithick/fbref-2017-2024-for-europes-top-5-leagues)


## How to Run

### 1. Install dependencies
```
pip install pandas scikit-learn
```

### 2. Download the data
- Download both Kaggle datasets above
- Place the 8 Transfermarkt CSVs in a `data/` folder
- Place the 7 FBref `cleaned_YYYY-YY.csv` files in the same `data/` folder

### 3. Run scripts
```
python loadDB.py           # builds transfermarkt.db from the 8 CSVs
python queries.py          # runs SQL analysis, outputs CSVs to outputs/
python build_ml_data.py    # joins FBref + Transfermarkt data, outputs model_data.csv
python train_model.py      # trains Random Forest model, outputs predictions
```

### 4. Open the dashboard

---

## Machine Learning Model

A **Random Forest Regressor** trained to predict player market value from FBref performance statistics, matched against Transfermarkt valuations by player name, birth year, and season.

**Features:** age, position, goals, assists, xG, xA, progressive carries/passes, tackles, interceptions, clearances, pass completion, key passes, take-ons, shots, aerial duels, GK-specific stats (saves, clean sheets, etc.)

**Target:** `market_value_in_eur` (Transfermarkt season-end valuation)

**Results:**
- Baseline R² (log scale): 0.662
- Tuned R² (log scale): **0.665** (RandomizedSearchCV, 20 iterations, 3-fold CV)
- MAE: ~€5.5M
