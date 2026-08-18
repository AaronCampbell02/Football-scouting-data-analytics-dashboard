import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.model_selection import RandomizedSearchCV

model_df = pd.read_csv("outputs/model_data.csv")
print(model_df.shape)

# some players have multiple rows per season i.e mid season moves (jan transfer window)
# keep only the one with the most minutes played
model_df = (
    model_df.sort_values("Avg Mins per Match", ascending=False)
    .drop_duplicates(subset=["player", "season"], keep="first")
)
print("After dedup:", model_df.shape)

model_df = model_df.rename(columns={"Avg Mins per Match": "total_minutes"}) # fixed misnamed column

target_col = "market_value_in_eur"

model_df_encoded = pd.get_dummies(model_df, columns=["pos"], drop_first=True)

X = model_df_encoded.drop(columns=[target_col, "player", "season"]) # predicts for each season
y = model_df_encoded[target_col]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(X_train.shape, X_test.shape)

# market values are heavily right skewed use log transforms to counteract
y_train_log = np.log1p(y_train)
y_test_log = np.log1p(y_test)

model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
model.fit(X_train, y_train_log)

preds_log = model.predict(X_test)

r2_log = r2_score(y_test_log, preds_log)
mae_euros = mean_absolute_error(np.expm1(y_test_log), np.expm1(preds_log))

print(f"R² (log scale): {r2_log:.3f}") # first model test values
print(f"MAE: €{mae_euros:,.0f}")

# hyperparameter tuning - improve model ( slower to run )
param_dist = {
    "n_estimators": [200, 300, 500],
    "max_depth": [None, 10, 20, 30],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4],
    "max_features": ["sqrt", "log2", 0.5]
}

search = RandomizedSearchCV(
    RandomForestRegressor(random_state=42, n_jobs=-1),
    param_distributions=param_dist,
    n_iter=20,
    cv=3,
    scoring="r2",
    random_state=42,
    n_jobs=-1
)

search.fit(X_train, y_train_log)

print("Best params:", search.best_params_)

best_model = search.best_estimator_
preds_tuned = best_model.predict(X_test)
r2_tuned = r2_score(y_test_log, preds_tuned)
mae_tuned = mean_absolute_error(np.expm1(y_test_log), np.expm1(preds_tuned))

print(f"R² (tuned, log scale): {r2_tuned:.3f}")
print(f"MAE (tuned): €{mae_tuned:,.0f}")

# predict on full dataset to find (under/over)valued players and save to csv
X_all = model_df_encoded.drop(columns=[target_col, "player", "season"])
y_all_actual = model_df_encoded[target_col]

preds_all_log = best_model.predict(X_all)
preds_all = np.expm1(preds_all_log)

model_df["predicted_value"] = preds_all
model_df["actual_value"] = y_all_actual.values
model_df["value_gap"] = model_df["predicted_value"] - model_df["actual_value"]
model_df["value_gap_pct"] = model_df["value_gap"] / model_df["actual_value"] * 100 # percentage used orriginally but produced unreliable data

# remove implausible values e.g. caused by issues with naming conventions.
plausible = model_df[model_df["actual_value"] >= 500000].copy()

undervalued_unique = (
    plausible.sort_values("value_gap", ascending=False)
    .drop_duplicates(subset="player", keep="first")
)

overvalued_unique = (
    plausible.sort_values("value_gap", ascending=True)
    .drop_duplicates(subset="player", keep="first")
)

print("=== TOP 15 UNDERVALUED (unique players) ===")
print(undervalued_unique[["player", "season", "actual_value", "predicted_value", "value_gap"]]
      .head(15).to_string(index=False))

print("\n=== TOP 15 OVERVALUED (unique players) ===")
print(overvalued_unique[["player", "season", "actual_value", "predicted_value", "value_gap"]]
      .head(15).to_string(index=False))

undervalued_unique.head(100).to_csv("outputs/undervalued_players.csv", index=False)
overvalued_unique.head(100).to_csv("outputs/overvalued_players.csv", index=False)
print("\nSaved outputs/undervalued_players.csv and outputs/overvalued_players.csv")

model_df.to_csv("outputs/all_predictions.csv", index=False)
print("Saved outputs/all_predictions.csv")
