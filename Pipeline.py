import os
import sys
import numpy as np
import pandas as pd
import yfinance as yf

# ============================================================
# 1. CONFIGURATION
# ============================================================
COMPANIES = {
    "Hindustan Copper": "HINDCOPPER.NS",
    "Garden Reach Shipbuilders": "GRSE.NS",
    "ITC": "ITC.NS",
    "Hindustan Unilever": "HINDUNILVR.NS",
}

START_DATE = "2025-09-01"
END_DATE = "2025-12-01"

ROLLING_WINDOW = 15
FLOOR = -2.3
CEIL = 2.3
EPSILON = 13
# 4.6 / 13 = 0.35
OUTPUT_FILE = "daily_open_obfuscated_sep_nov_2025.csv"

# ============================================================
# 2. LAYER FUNCTIONS (EVALUATED PER DAY)
# ============================================================
def layer_2_log_returns(price_series: pd.Series) -> pd.Series:
    """Layer 2: Daily log returns r_t = ln(P_t / P_{t-1})."""
    return np.log(price_series / price_series.shift(1))


def layer_3_rolling_zscore(
    return_series: pd.Series, window: int = ROLLING_WINDOW
) -> pd.Series:
    """
    Layer 3: 15-day rolling Z-score computed per day:
    z_t = (r_t - mean_{t-14..t}) / std_{t-14..t}
    """
    rolling_mean = return_series.rolling(window=window).mean()
    rolling_std = (
        return_series.rolling(window=window).std().replace(0.0, np.nan)
    )
    z = (return_series - rolling_mean) / rolling_std
    return z.replace([np.inf, -np.inf], np.nan)


def layer_4_floor_ceil(
    series: pd.Series, lower: float = FLOOR, upper: float = CEIL
) -> pd.Series:
    """Layer 4: Global fixed-range clipping to [lower, upper]."""
    return series.clip(lower=lower, upper=upper)


def layer_5_laplace_dp_noise(
    series: pd.Series,
    lower: float = FLOOR,
    upper: float = CEIL,
    epsilon: float = EPSILON,
) -> pd.Series:
    """
    Layer 5: Laplace DP noise added to each day's clipped score:
    sensitivity = upper - lower, scale = sensitivity / epsilon
    """
    sensitivity = upper - lower
    scale = sensitivity / epsilon
    noise = np.random.laplace(loc=0.0, scale=scale, size=len(series))
    return series + noise


# ============================================================
# 3. PIPELINE EXECUTION & GUARANTEED CSV EXPORT
# ============================================================
def main():
    all_data = []

    for company, ticker in COMPANIES.items():
        try:
            data = yf.download(
                ticker,
                start=START_DATE,
                end=END_DATE,
                auto_adjust=False,
                progress=False,
            )
        except Exception:
            continue

        if data is None or data.empty:
            continue

        # Flatten multi-index column headers from newer yfinance versions
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        if "Open" not in data.columns:
            continue

        # Extract opening prices as a numeric 1D Series indexed by trading date
        open_series = data["Open"].squeeze().astype(float)
        open_series.index = pd.to_datetime(open_series.index)

        # Sequential daily transformations (Layers 2 to 5)
        log_ret = layer_2_log_returns(open_series)
        z_score = layer_3_rolling_zscore(log_ret, window=ROLLING_WINDOW)
        clipped_z = layer_4_floor_ceil(z_score, lower=FLOOR, upper=CEIL)
        noisy_z = layer_5_laplace_dp_noise(
            clipped_z, lower=FLOOR, upper=CEIL, epsilon=EPSILON
        )

        # Build day-by-day record table
        result = pd.DataFrame(
            {
                "Date": open_series.index.strftime("%Y-%m-%d"),
                "Company": company,
                "Ticker": ticker.replace(".NS", ""),
                "Original_Open": open_series.values,
                "Log_Return": log_ret.values,
                "Rolling_ZScore_15d": z_score.values,
                "Clipped_ZScore": clipped_z.values,
                "Obfuscated_Open": noisy_z.values,
            }
        )

        all_data.append(result)

    # Ensure output directory exists
    output_dir = os.path.dirname(OUTPUT_FILE)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Guarantee CSV creation even if downloads fail or data is empty
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
    else:
        final_df = pd.DataFrame(
            columns=[
                "Date",
                "Company",
                "Ticker",
                "Original_Open",
                "Log_Return",
                "Rolling_ZScore_15d",
                "Clipped_ZScore",
                "Obfuscated_Open",
            ]
        )

    # Save to disk without printing the data
    final_df.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()
