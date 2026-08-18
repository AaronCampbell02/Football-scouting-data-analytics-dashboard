import sqlite3
import pandas as pd
import os

DATA_DIR = "data"          # folder containing the 8 Kaggle CSVs
DB_PATH = "transfermarkt.db"

#define leagues selected (top 5 leagues)

TOP5 = ['GB1', 'ES1', 'L1', 'IT1', 'FR1']  # Premier League, La Liga, Bundesliga, Serie A, Ligue 1

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)

def load(name, filter_competition_col=None):
    df = pd.read_csv(f"{DATA_DIR}/{name}.csv", low_memory=False)
    if filter_competition_col and filter_competition_col in df.columns:
        df = df[df[filter_competition_col].isin(TOP5)]
    df.to_sql(name, conn, if_exists="replace", index=False)
    print(f"{name}: loaded {len(df)} rows")
    return df


"""
Remove all values from non top 5 leagues - simplifying the db
"""

# competitions & clubs: keep only top 5 leagues + their clubs
competitions = load("competitions")
competitions_top5 = competitions[competitions["competition_id"].isin(TOP5)]
competitions_top5.to_sql("competitions", conn, if_exists="replace", index=False)
clubs = pd.read_csv(f"{DATA_DIR}/clubs.csv", low_memory=False)
clubs_top5 = clubs[clubs["domestic_competition_id"].isin(TOP5)]
clubs_top5.to_sql("clubs", conn, if_exists="replace", index=False)
top5_club_ids = set(clubs_top5["club_id"])

# players: keep ALL players (unfiltered) so historical top-5 seasons still match
# even if their current club has since moved outside the top 5 leagues - for determining undervalued players
players = pd.read_csv(f"{DATA_DIR}/players.csv", low_memory=False)
players.to_sql("players", conn, if_exists="replace", index=False)
print(f"players: loaded {len(players)} rows (unfiltered)")
top5_player_ids = set(players["player_id"])

# appearances: keep games in top 5 competitions
appearances = pd.read_csv(f"{DATA_DIR}/appearances.csv", low_memory=False)
appearances_top5 = appearances[appearances["competition_id"].isin(TOP5)]
appearances_top5.to_sql("appearances", conn, if_exists="replace", index=False)

# games: keep top 5 competitions
games = pd.read_csv(f"{DATA_DIR}/games.csv", low_memory=False)
games_top5 = games[games["competition_id"].isin(TOP5)]
games_top5.to_sql("games", conn, if_exists="replace", index=False)
top5_game_ids = set(games_top5["game_id"])

# club_games: keep games tied to top5 games
club_games = pd.read_csv(f"{DATA_DIR}/club_games.csv", low_memory=False)
club_games_top5 = club_games[club_games["game_id"].isin(top5_game_ids)]
club_games_top5.to_sql("club_games", conn, if_exists="replace", index=False)

# transfers: keep transfers involving top5 clubs
transfers = pd.read_csv(f"{DATA_DIR}/transfers.csv", low_memory=False)
transfers_top5 = transfers[
    transfers["from_club_id"].isin(top5_club_ids) | transfers["to_club_id"].isin(top5_club_ids)
]
transfers_top5.to_sql("transfers", conn, if_exists="replace", index=False)

# player_valuations: keep all (unfiltered) - same reasoning as players
valuations = pd.read_csv(f"{DATA_DIR}/player_valuations.csv", low_memory=False)
valuations.to_sql("player_valuations", conn, if_exists="replace", index=False)
print(f"player_valuations: loaded {len(valuations)} rows (unfiltered)")

# indexes for query speed
cur = conn.cursor()
idx_statements = [
    "CREATE INDEX idx_appearances_player ON appearances(player_id)",
    "CREATE INDEX idx_appearances_game ON appearances(game_id)",
    "CREATE INDEX idx_appearances_comp ON appearances(competition_id)",
    "CREATE INDEX idx_games_comp ON games(competition_id)",
    "CREATE INDEX idx_club_games_game ON club_games(game_id)",
    "CREATE INDEX idx_club_games_club ON club_games(club_id)",
    "CREATE INDEX idx_transfers_player ON transfers(player_id)",
    "CREATE INDEX idx_valuations_player ON player_valuations(player_id)",
    "CREATE INDEX idx_players_club ON players(current_club_id)",
]

#execute commands
for stmt in idx_statements:
    cur.execute(stmt)
conn.commit()
print("\nIndexes created.")

conn.close()
print(f"\nDone. saved DB")