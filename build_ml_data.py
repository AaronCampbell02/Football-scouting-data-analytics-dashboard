import pandas as pd
import glob
import sqlite3
import unicodedata

def strip_accents(s):
    if pd.isna(s):
        return s
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

# load data from Fbref (csv - all start with cleaned)
files = glob.glob("data/cleaned_*.csv")
dfs = [pd.read_csv(f) for f in files]
fbref = pd.concat(dfs, ignore_index=True)
fbref["season_start_year"] = fbref["season"].str[:4].astype(int)
fbref["player_clean"] = fbref["player"].apply(strip_accents)

# get transfermarkt data
conn = sqlite3.connect("transfermarkt.db")

query = """
SELECT
    pv.player_id,
    p.name AS player_name,
    p.date_of_birth,
    pv.date,
    pv.market_value_in_eur,
    CASE
        WHEN CAST(strftime('%m', pv.date) AS INTEGER) >= 7
        THEN CAST(strftime('%Y', pv.date) AS INTEGER)
        ELSE CAST(strftime('%Y', pv.date) AS INTEGER) - 1
    END AS season_start_year
FROM player_valuations pv
JOIN players p ON p.player_id = pv.player_id
"""

valuations = pd.read_sql_query(query, conn)
valuations["born"] = pd.to_datetime(valuations["date_of_birth"]).dt.year

season_value = (
    valuations.sort_values("date")
    .groupby(["player_name", "born", "season_start_year"], as_index=False)
    .last()
)
season_value["player_name_clean"] = season_value["player_name"].apply(strip_accents)

print(f"Season values: {season_value.shape}")

merged = fbref.merge(
    season_value,
    left_on=["player_clean", "born", "season_start_year"],
    right_on=["player_name_clean", "born", "season_start_year"],
    how="left"
)

match_rate = merged["market_value_in_eur"].notna().mean()
print(f"Match rate: {match_rate:.1%}")
print(merged.shape)

model_data = merged[merged["market_value_in_eur"].notna()].copy()

feature_cols = [
    "age", "pos", "Matches Played", "Avg Mins per Match",
    "Goals", "Assists", "Non Penalty Goals", "Expected Goals", "Exp NPG",
    "Progressive Carries", "Progressive Passes", "Goals p 90", "Assists p 90",
    "Tackles attempted", "Tackles Won", "Interceptions", "Clearances",
    "Passes Completed", "Pass completion %", "Key passes",
    "Take ons attempted", "% Successful take-ons",
    "Total Shots", "Shots p 90", "Goals per shot",
    "Shot creating actions p 90", "Goal creating actions p 90",
    "% Aerial Duels won",
    "% Dribbles tackled", "Shots blocked", "Passes blocked",
    "Errors made", "touches_def_pen", "Possessions lost",
    "Goals Against", "Goals against p 90", "Saves", "Saves %",
    "Clean Sheets", "% Clean sheets", "% Penalty saves"
]

target_col = "market_value_in_eur"

final_df = model_data[feature_cols + [target_col, "player", "season"]].copy()
final_df.to_csv("outputs/model_data.csv", index=False)
print(f"Saved model_data.csv: {final_df.shape}")