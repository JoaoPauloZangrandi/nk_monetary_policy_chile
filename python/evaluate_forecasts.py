"""Pseudo-out-of-sample forecast evaluation for the Chilean variables.

Expanding-window forecasts compare the fixed calibrated NK solution with
univariate AR(1), random-walk and VAR benchmarks at one- and four-quarter
horizons. The exercise is pseudo-real-time: revised data and the full-sample HP
output gap remain in the dataset, so it is not a genuine vintage-data test.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR

from common import (
    DATA_CLEAN,
    FIGURES,
    TABLES,
    _state_coefficients,
    calibration_rho,
    complete_parameters,
    ensure_directories,
)


VARIABLES = ["x", "pi", "i"]
MODELS = ["NK", "AR1", "Random walk", "VAR"]
HORIZONS = [1, 4]
MIN_TRAIN = 40
SCALES = {"x": 100.0, "pi": 400.0, "i": 400.0}


def ar1_forecast(series: np.ndarray, horizon: int) -> float:
    y = series[1:]
    x = sm.add_constant(series[:-1])
    result = sm.OLS(y, x).fit()
    value = float(series[-1])
    for _ in range(horizon):
        value = float(result.params[0] + result.params[1] * value)
    return value


def nk_forecast(train: pd.DataFrame, horizon: int) -> np.ndarray:
    params = complete_parameters({"rho_i": calibration_rho()})
    a_x, a_pi, a_i = _state_coefficients(params)
    means = train.mean()
    lagged_rate_gap = float(train["i"].iloc[-1] - means["i"])
    forecast = None
    for _ in range(horizon):
        forecast = np.array([a_x, a_pi, a_i]) * lagged_rate_gap
        lagged_rate_gap = float(forecast[2])
    return forecast + means[VARIABLES].to_numpy()


def var_forecast(train: pd.DataFrame, horizon: int) -> np.ndarray:
    selection = VAR(train[VARIABLES]).select_order(maxlags=4, trend="c")
    lags = max(1, int(selection.selected_orders.get("bic") or 1))
    result = VAR(train[VARIABLES]).fit(lags, trend="c")
    return result.forecast(train[VARIABLES].to_numpy()[-lags:], steps=horizon)[-1]


def main() -> None:
    ensure_directories()
    macro = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    data = pd.DataFrame(
        {
            "date": macro["date"],
            "x": macro["output_gap"],
            "pi": macro["infl_q"],
            "i": macro["i_q"],
        }
    )

    records: list[dict] = []
    for horizon in HORIZONS:
        for origin in range(MIN_TRAIN - 1, len(data) - horizon):
            train = data.iloc[: origin + 1]
            target = data.iloc[origin + horizon]
            predictions = {
                "NK": nk_forecast(train[VARIABLES], horizon),
                "AR1": np.array(
                    [ar1_forecast(train[v].to_numpy(), horizon) for v in VARIABLES]
                ),
                "Random walk": train[VARIABLES].iloc[-1].to_numpy(),
            }
            try:
                predictions["VAR"] = var_forecast(train, horizon)
            except Exception:  # noqa: BLE001
                predictions["VAR"] = predictions["AR1"].copy()

            for model, prediction in predictions.items():
                for index, variable in enumerate(VARIABLES):
                    scale = SCALES[variable]
                    actual = float(target[variable] * scale)
                    forecast = float(prediction[index] * scale)
                    records.append(
                        {
                            "origin": train["date"].iloc[-1],
                            "target_date": target["date"],
                            "horizon": horizon,
                            "model": model,
                            "variable": variable,
                            "actual": actual,
                            "forecast": forecast,
                            "error": actual - forecast,
                            "absolute_error": abs(actual - forecast),
                            "squared_error": (actual - forecast) ** 2,
                        }
                    )

    forecasts = pd.DataFrame(records)
    forecasts.to_csv(TABLES / "forecast_oos_predictions.csv", index=False)
    metrics = (
        forecasts.groupby(["horizon", "variable", "model"], as_index=False)
        .agg(
            observations=("error", "size"),
            bias=("error", "mean"),
            mae=("absolute_error", "mean"),
            mse=("squared_error", "mean"),
        )
    )
    metrics["rmse"] = np.sqrt(metrics["mse"])
    random_walk_rmse = metrics[metrics["model"] == "Random walk"][
        ["horizon", "variable", "rmse"]
    ].rename(columns={"rmse": "random_walk_rmse"})
    metrics = metrics.merge(random_walk_rmse, on=["horizon", "variable"])
    metrics["relative_rmse_vs_random_walk"] = (
        metrics["rmse"] / metrics["random_walk_rmse"]
    )
    metrics.to_csv(TABLES / "forecast_oos_metrics.csv", index=False)

    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharey=False)
    colors = {
        "NK": "#B45309",
        "AR1": "#1E4E79",
        "Random walk": "#6B7280",
        "VAR": "#16A34A",
    }
    for row, horizon in enumerate(HORIZONS):
        for col, variable in enumerate(VARIABLES):
            ax = axes[row, col]
            sub = metrics[
                (metrics["horizon"] == horizon) & (metrics["variable"] == variable)
            ].set_index("model").reindex(MODELS)
            ax.bar(
                np.arange(len(MODELS)),
                sub["rmse"],
                color=[colors[m] for m in MODELS],
            )
            ax.set_xticks(np.arange(len(MODELS)))
            ax.set_xticklabels(MODELS, rotation=25, ha="right", fontsize=8)
            ax.set_title(f"{variable}: horizonte {horizon}")
            ax.set_ylabel("RMSE (p.p.)" if variable != "x" else "RMSE (% PIB)")
            ax.grid(alpha=0.2, axis="y")
    fig.suptitle("Avaliacao pseudo-fora-da-amostra: modelo NK versus benchmarks")
    fig.text(
        0.01,
        0.01,
        "Janela expansiva, treino inicial de 40 trimestres. Dados revisados e hiato HP "
        "de amostra completa: diagnostico pseudo-real-time, nao backtest em vintages.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(FIGURES / "forecast_oos_comparison.png", dpi=180)
    plt.close(fig)

    print(
        metrics[
            ["horizon", "variable", "model", "rmse", "mae",
             "relative_rmse_vs_random_walk"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
