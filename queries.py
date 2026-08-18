import sqlite3
import pandas as pd
import os

DB_PATH = "transfermarkt.db"
OUT_DIR = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)


def run(name, query):
    """Run a query, save to CSV, print a preview."""
    df = pd.read_sql_query(query, conn)
    df.to_csv(f"{OUT_DIR}/{name}.csv", index=False)
    print(f"\n=== {name} ({len(df)} rows) -> outputs/{name}.csv ===")
    print(df.head(10).to_string(index=False))
    return df


#top scores in each league
run("top_scorers", """
SELECT
    c.name AS league,
    a.player_name,
    SUM(a.goals) AS total_goals,
    SUM(a.assists) AS total_assists,
    COUNT(DISTINCT a.game_id) AS appearances
FROM appearances a
JOIN competitions c ON c.competition_id = a.competition_id
GROUP BY a.player_id, a.competition_id
ORDER BY total_goals DESC
LIMIT 100
""")

#most assists in each league
run("top_assisters", """
SELECT
    c.name AS league,
    a.player_name,
    SUM(a.assists) AS total_assists,
    SUM(a.goals) AS total_goals,
    COUNT(DISTINCT a.game_id) AS appearances
FROM appearances a
JOIN competitions c ON c.competition_id = a.competition_id
GROUP BY a.player_id, a.competition_id
ORDER BY total_assists DESC
LIMIT 100
""")

#league spending on transfers each season
run("league_transfer_spend", """
SELECT
    cl.domestic_competition_id AS league,
    t.transfer_season AS season,
    SUM(COALESCE(t.transfer_fee, 0)) AS total_spend,
    COUNT(*) AS num_transfers,
    SUM(CASE WHEN t.transfer_fee IS NOT NULL AND t.transfer_fee > 0 THEN 1 ELSE 0 END) AS num_paid_transfers,
    AVG(CASE WHEN t.transfer_fee > 0 THEN t.transfer_fee END) AS avg_paid_fee
FROM transfers t
JOIN clubs cl ON cl.club_id = t.to_club_id
WHERE cl.domestic_competition_id IN ('GB1','ES1','L1','IT1','FR1')
GROUP BY league, season
ORDER BY season DESC, total_spend DESC
""")

#club net spend
run("club_net_spend", """
WITH bought AS (
    SELECT to_club_id AS club_id, SUM(transfer_fee) AS spend
    FROM transfers
    GROUP BY to_club_id
),
sold AS (
    SELECT from_club_id AS club_id, SUM(transfer_fee) AS income
    FROM transfers
    GROUP BY from_club_id
)
SELECT
    cl.name AS club,
    cl.domestic_competition_id AS league,
    COALESCE(b.spend, 0) AS total_spend,
    COALESCE(s.income, 0) AS total_income,
    COALESCE(b.spend, 0) - COALESCE(s.income, 0) AS net_spend
FROM clubs cl
LEFT JOIN bought b ON b.club_id = cl.club_id
LEFT JOIN sold s ON s.club_id = cl.club_id
WHERE cl.domestic_competition_id IN ('GB1','ES1','L1','IT1','FR1')
ORDER BY net_spend DESC
""")

# league table from season (can change below)
SEASON = 2022

run(f"league_table_{SEASON}", f"""
SELECT
    g.competition_id AS league,
    cg.club_id,
    cl.name AS club,
    COUNT(*) AS played,
    SUM(CASE WHEN cg.is_win = 1 THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN cg.own_goals = cg.opponent_goals THEN 1 ELSE 0 END) AS draws,
    SUM(CASE WHEN cg.is_win = 0 AND cg.own_goals != cg.opponent_goals THEN 1 ELSE 0 END) AS losses,
    SUM(cg.own_goals) AS goals_for,
    SUM(cg.opponent_goals) AS goals_against,
    SUM(cg.own_goals) - SUM(cg.opponent_goals) AS goal_diff,
    SUM(CASE WHEN cg.is_win = 1 THEN 3
             WHEN cg.own_goals = cg.opponent_goals THEN 1
             ELSE 0 END) AS points
FROM club_games cg
JOIN games g ON g.game_id = cg.game_id
JOIN clubs cl ON cl.club_id = cg.club_id
WHERE g.season = {SEASON}
GROUP BY g.competition_id, cg.club_id
ORDER BY g.competition_id, points DESC, goal_diff DESC
""")

#undervalued players

run("player_value_vs_output", """
WITH latest_val AS (
    SELECT player_id, market_value_in_eur,
           ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY date DESC) AS rn
    FROM player_valuations
),
output AS (
    SELECT player_id, player_name,
           SUM(goals) AS total_goals,
           SUM(assists) AS total_assists,
           COUNT(DISTINCT game_id) AS apps
    FROM appearances
    GROUP BY player_id
)
SELECT
    o.player_name,
    p.position,
    lv.market_value_in_eur AS current_value,
    o.total_goals,
    o.total_assists,
    o.apps,
    ROUND(1.0 * (o.total_goals + o.total_assists) / NULLIF(o.apps,0), 3) AS goal_contrib_per_app
FROM output o
JOIN latest_val lv ON lv.player_id = o.player_id AND lv.rn = 1
JOIN players p ON p.player_id = o.player_id
WHERE o.apps >= 30
ORDER BY goal_contrib_per_app DESC
LIMIT 100
""")

conn.close()
print("\nAll queries complete. CSVs are in ./outputs/")