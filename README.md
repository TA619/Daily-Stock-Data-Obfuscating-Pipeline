# Daily Stock Data Obfuscation Pipeline

## Overview

This project implements a multi-layer pipeline for **obfuscating daily stock opening-price data** while transforming the data into normalized statistical representations.

The pipeline downloads daily **Open prices** for four NSE-listed companies and applies a sequence of transformations:

1. Log-return transformation
2. 15-day rolling Z-score normalization
3. Fixed-range clipping
4. Laplace noise addition

The final output is a privacy-oriented **obfuscated statistical representation** of the stock data.

The dataset covers the period:

```text
September 1, 2025 – December 1, 2025
```

This corresponds to approximately **two months of trading data**.

---

## Stocks Used

Four NSE-listed companies are used in the experiment. They are divided into two broad groups based on their relative price-movement characteristics during the selected period.

| Category            | Company                               | Ticker     |
| ------------------- | ------------------------------------- | ---------- |
| Relatively Volatile | Hindustan Copper                      | HINDCOPPER |
| Relatively Volatile | Garden Reach Shipbuilders & Engineers | GRSE       |
| Relatively Stable   | ITC                                   | ITC        |
| Relatively Stable   | Hindustan Unilever                    | HINDUNILVR |

The purpose of using both groups is to evaluate the behavior of the obfuscation pipeline on stocks with different levels of price variability.

> **Note:** The volatile/stable classification is relative to the four stocks selected for this experiment and the chosen observation period; it is not intended as a permanent classification of the companies.

---

## Overall Pipeline

The data passes through the following sequence:

```text
Original Open Price
        |
        v
Layer 2: Log Return
        |
        v
Layer 3: 15-Day Rolling Z-Score
        |
        v
Layer 4: Fixed-Range Clipping
        |
        v
Layer 5: Laplace Noise
        |
        v
Obfuscated Statistical Representation
```

---

# Layer 2 — Log Returns

The original opening price is first converted into a daily log return:

```text
r_t = ln(P_t / P_(t-1))
```

where:

* `P_t` = opening price on the current trading day
* `P_(t-1)` = opening price on the previous trading day

Using log returns instead of absolute prices removes the direct dependence on the price scale of each company.

For example, a stock trading at ₹100 and another trading at ₹1,000 can have their daily movements represented on a comparable return scale.

The transformation therefore changes:

```text
Absolute Price
      ↓
Relative Daily Movement
```

---

# Layer 3 — 15-Day Rolling Z-Score

After calculating daily log returns, a rolling Z-score is calculated:

```text
z_t = (r_t - rolling_mean) / rolling_std
```

where the mean and standard deviation are calculated using a **15-trading-day rolling window**.

## Why 15 Days?

The dataset used in this experiment covers only a **short duration of approximately two months**.

Because the available dataset is short, a relatively small rolling window was selected:

```text
Dataset duration  → approximately 2 months
Rolling window    → 15 trading days
```

A larger rolling window would consume a substantial portion of the available data and would make the rolling statistics less responsive to recent changes in stock behavior.

The 15-day window provides a balance between:

* Having enough observations to calculate a meaningful mean and standard deviation.
* Keeping the normalization responsive to recent market behavior.
* Avoiding a rolling window that is too large relative to the overall dataset.

Thus, the 15-day window was selected specifically because the experiment uses a **short-duration dataset**.

The resulting Z-score represents how unusual the current daily return is relative to the stock's recent 15-day behavior.

---

# Layer 4 — Fixed-Range Clipping

The calculated Z-score is then clipped to a fixed range:

```text
[-2.3, 2.3]
```

This means:

```text
z < -2.3  →  -2.3

z >  2.3  →   2.3
```

The purpose of clipping is to limit the effect of extreme observations and establish a fixed range for the subsequent noise mechanism.

The transformation can be represented as:

```text
Original Z-score
      |
      v
   Clip
      |
      v
[-2.3, 2.3]
```

The fixed range also determines the sensitivity used in the Laplace noise step.

---

# Layer 5 — Laplace Noise

After clipping, Laplace noise is added to each day's value.

The privacy parameter is:

```text
epsilon = 13
```

The sensitivity is determined from the clipping range:

```text
Sensitivity = upper_bound - lower_bound

            = 2.3 - (-2.3)

            = 4.6
```

The Laplace noise scale is then calculated as:

```text
Scale = Sensitivity / epsilon

      = 4.6 / 13

      ≈ 0.354
```

Random Laplace noise with this scale is generated independently for each observation.

The final transformation is:

```text
Clipped Z-score + Laplace Noise
              |
              v
      Obfuscated Value
```

The resulting value is stored in the output as:

```text
Obfuscated_Open
```

---

# Complete Mathematical Pipeline

The complete transformation can be summarized as:

### Step 1 — Log Return

```text
r_t = ln(P_t / P_(t-1))
```

### Step 2 — Rolling Z-score

```text
z_t = (r_t - mean_15) / std_15
```

where `mean_15` and `std_15` are calculated using the previous 15 trading observations including the current observation.

### Step 3 — Clipping

```text
z_clipped = clip(z_t, -2.3, 2.3)
```

### Step 4 — Laplace Noise

```text
noise ~ Laplace(0, 4.6 / 13)
```

### Step 5 — Final Obfuscated Value

```text
obfuscated_value = z_clipped + noise
```

Therefore:

```text
Original Price
      ↓
Log Return
      ↓
15-Day Rolling Z-score
      ↓
Clip to [-2.3, 2.3]
      ↓
Add Laplace Noise
      ↓
Obfuscated Value
```

---

# Output File

The processed data is saved to:

```text
daily_open_obfuscated_sep_nov_2025.csv
```

The output CSV contains the following columns:

| Column               | Description                                |
| -------------------- | ------------------------------------------ |
| `Date`               | Trading date                               |
| `Company`            | Company name                               |
| `Ticker`             | NSE ticker symbol                          |
| `Original_Open`      | Original opening price                     |
| `Log_Return`         | Daily log return                           |
| `Rolling_ZScore_15d` | 15-day rolling Z-score                     |
| `Clipped_ZScore`     | Z-score after clipping to [-2.3, 2.3]      |
| `Obfuscated_Open`    | Clipped Z-score after adding Laplace noise |

---

# Important Note About `Obfuscated_Open`

Despite its name, `Obfuscated_Open` is **not an obfuscated version of the original opening price in rupees**.

The original price is transformed through several intermediate representations before noise is added:

```text
Original Open Price
        ↓
     Log Return
        ↓
  Rolling Z-score
        ↓
      Clipping
        ↓
    Laplace Noise
        ↓
 Obfuscated Statistical Value
```

Therefore, `Obfuscated_Open` represents an obfuscated **normalized return signal**, rather than an obfuscated stock price.

For example, an original price such as:

```text
₹250
```

will not result in an obfuscated value close to ₹250.

Instead, the final value will generally be on the scale of the normalized Z-score plus the added noise.

---

# Handling of Missing Values

The first observation cannot have a log return because there is no previous trading-day price.

Similarly, the first observations do not have enough historical data to calculate a complete 15-day rolling Z-score.

Consequently, the beginning of each stock's processed series may contain `NaN` values for:

```text
Log_Return
Rolling_ZScore_15d
Clipped_ZScore
Obfuscated_Open
```

The code does not explicitly remove these rows before exporting the CSV.

---

# Companies and Experimental Purpose

The four companies provide two different types of stock behavior for testing the pipeline.

### Relatively Volatile Stocks

**Hindustan Copper (HINDCOPPER)** and **Garden Reach Shipbuilders & Engineers (GRSE)** are included as the relatively volatile group.

These stocks provide observations with comparatively larger short-term movements, allowing the pipeline to be tested under more variable return behavior.

### Relatively Stable Stocks

**ITC** and **Hindustan Unilever (HINDUNILVR)** are included as the relatively stable group.

These provide comparatively smoother price behavior and allow the effect of the same transformation pipeline to be observed on lower-volatility data.

Using both groups allows the experiment to examine whether the obfuscation process behaves differently for:

```text
Higher Variability              Lower Variability
       |                               |
       v                               v
   HINDCOPPER                         ITC
      GRSE                         HINDUNILVR
```

---

# Configuration

The main parameters used in the experiment are:

```python
START_DATE = "2025-09-01"
END_DATE = "2025-12-01"

ROLLING_WINDOW = 15

FLOOR = -2.3
CEIL = 2.3

EPSILON = 13
```

### Parameter Summary

| Parameter      |      Value | Purpose                            |
| -------------- | ---------: | ---------------------------------- |
| Start Date     | 2025-09-01 | Beginning of dataset               |
| End Date       | 2025-12-01 | End of dataset                     |
| Rolling Window |    15 days | Short-term normalization           |
| Lower Bound    |       -2.3 | Lower clipping limit               |
| Upper Bound    |        2.3 | Upper clipping limit               |
| Epsilon        |         13 | Controls Laplace noise scale       |
| Sensitivity    |        4.6 | Difference between clipping bounds |
| Noise Scale    |    ≈ 0.354 | Laplace noise scale                |

---

# Requirements

The following Python libraries are required:

```bash
pip install numpy pandas yfinance
```

The code requires **Python 3.x**.

---

# Running the Code

Save the Python code as a `.py` file and run:

```bash
python your_script_name.py
```

The script will:

1. Download the stock data from Yahoo Finance.
2. Extract the daily opening prices.
3. Calculate log returns.
4. Calculate the 15-day rolling Z-score.
5. Clip the Z-score to `[-2.3, 2.3]`.
6. Add Laplace noise.
7. Combine the results for all four companies.
8. Save the final dataset as a CSV file.

The output file will be:

```text
daily_open_obfuscated_sep_nov_2025.csv
```

---

# Purpose of the Experiment

The objective of this pipeline is to investigate whether useful statistical information from stock-price data can be retained while reducing exposure of the original price information.

The experiment uses:

* Multiple companies
* Different levels of stock volatility
* A short-duration dataset
* Rolling normalization
* Fixed-range clipping
* Laplace noise

This provides a framework for studying the trade-off between **data utility and privacy/obfuscation** in financial time-series data.

---

# Summary

The complete methodology can be summarized as:

```text
4 NSE Stocks
     |
     v
Daily Open Prices
     |
     v
Log Returns
     |
     v
15-Day Rolling Z-score
     |
     v
Clip to [-2.3, 2.3]
     |
     v
Laplace Noise
     |
     v
Obfuscated Statistical Representation
     |
     v
CSV Output
```

The **15-day rolling window** was selected because the experiment operates on a **short approximately two-month dataset**, while the use of both relatively volatile and relatively stable stocks provides variation for evaluating the behavior of the obfuscation pipeline.
