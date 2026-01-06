import pandas as pd
import numpy as np
import statsmodels.api as sm

# -----------------------------
# 1) Load data
# -----------------------------
PATH = "Data.csv"  # <-- change
df = pd.read_csv(PATH)

df.columns = df.columns.str.strip()  # helps with accidental spaces
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date").set_index("Date")

# -----------------------------
# 2) Columns
# -----------------------------
fund_cols = [
    "FIDLEUI LX Equity  (R2)",
    "DODGX US Equity  (L1)",
    "PRDGX US Equity  (R1)",
    "AGTHX US Equity  (L4)",
    "JACTX US Equity  (R3)",
    "FCNTX US Equity  (L2)",
    "AIVSX US Equity  (R4)",
    "FBGRX US Equity  (R1)",
    "SCHEUMA LX Equity  (R1)",
    "SISEEIA LX Equity  (R1)",
    "SCHEMAA LX Equity  (L3)",
]

col_spxt = "SPXT Index  (R1)"
col_sxxr = "SXXR Index  (R1)"
col_euribor = "EURIBOR 3 month"
col_tbill = "3 month - t bill"

price_like_cols = fund_cols + [col_spxt, col_sxxr]
rate_cols = [col_euribor, col_tbill]

# -----------------------------
# 3) Gap handling
#    - NAV/Index levels: geometric interpolation (log-linear)
#    - Rates: linear interpolation
#    Only fills INTERNAL gaps; leading/trailing NaNs remain NaN
# -----------------------------
def geometric_interpolate_internal(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    # Only makes sense for strictly positive levels
    s = s.where(s > 0)
    log_s = np.log(s)
    # linear interpolation in log-space -> geometric in level space
    log_s_interp = log_s.interpolate(method="time", limit_area="inside")
    return np.exp(log_s_interp)

def linear_interpolate_internal(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    return s.interpolate(method="time", limit_area="inside")

df_filled = df.copy()

for c in price_like_cols:
    df_filled[c] = geometric_interpolate_internal(df_filled[c])

for c in rate_cols:
    df_filled[c] = linear_interpolate_internal(df_filled[c])

# -----------------------------
# 4) Returns (quarterly arithmetic)
# -----------------------------
ret = pd.DataFrame(index=df_filled.index)
for c in price_like_cols:
    ret[c] = df_filled[c].pct_change()

# -----------------------------
# 5) Risk-free (annualized % -> quarterly return)
# Quarterly rf ≈ (yield/100)/4
# NOTE: if your yields are already decimals, remove /100
# -----------------------------
rf = pd.DataFrame(index=df_filled.index)
rf["RF_EU"] = (df_filled[col_euribor] / 100.0) / 4.0
rf["RF_US"] = (df_filled[col_tbill] / 100.0) / 4.0

# Market excess returns
mkt_ex = pd.DataFrame(index=df_filled.index)
mkt_ex["MKT_US"] = ret[col_spxt] - rf["RF_US"]
mkt_ex["MKT_EU"] = ret[col_sxxr] - rf["RF_EU"]

# -----------------------------
# 6) Models (HAC / Newey-West)
# -----------------------------
def run_tm(y_excess: pd.Series, m_excess: pd.Series, hac_lags: int = 4):
    data = pd.concat([y_excess, m_excess], axis=1).dropna()
    y = data.iloc[:, 0]
    m = data.iloc[:, 1]
    X = pd.DataFrame({"const": 1.0, "m": m, "m2": m**2}, index=data.index)
    return sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})

def run_hm(y_excess: pd.Series, m_excess: pd.Series, hac_lags: int = 4):
    data = pd.concat([y_excess, m_excess], axis=1).dropna()
    y = data.iloc[:, 0]
    m = data.iloc[:, 1]
    D = (m > 0).astype(int)
    X = pd.DataFrame({"const": 1.0, "m": m, "Dm": D * m}, index=data.index)
    return sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})

def is_eu_fund(name: str) -> bool:
    return " LX " in name

def pack_results(model, fund, benchmark, model_name, gamma_name):
    # statsmodels already gives t-tests (tvalues + pvalues) and F-test for overall regression
    return {
        "Fund": fund,
        "Benchmark": benchmark,
        "Model": model_name,
        "N": int(model.nobs),
        "R2": model.rsquared,
        "Adj_R2": model.rsquared_adj,
        "F_stat": model.fvalue,
        "F_pvalue": model.f_pvalue,

        "alpha": model.params.get("const", np.nan),
        "alpha_se": model.bse.get("const", np.nan),
        "alpha_t": model.tvalues.get("const", np.nan),
        "alpha_p": model.pvalues.get("const", np.nan),

        "beta": model.params.get("m", np.nan),
        "beta_se": model.bse.get("m", np.nan),
        "beta_t": model.tvalues.get("m", np.nan),
        "beta_p": model.pvalues.get("m", np.nan),

        "gamma": model.params.get(gamma_name, np.nan),
        "gamma_se": model.bse.get(gamma_name, np.nan),
        "gamma_t": model.tvalues.get(gamma_name, np.nan),
        "gamma_p": model.pvalues.get(gamma_name, np.nan),
    }

# -----------------------------
# 7) Run regressions
# -----------------------------
HAC_LAGS = 4

matched_results = []
all_benchmark_results = []

for f in fund_cols:
    # Matched benchmark analysis
    if is_eu_fund(f):
        y_ex = ret[f] - rf["RF_EU"]
        m_ex = mkt_ex["MKT_EU"]
        bmk = "SXXR (Europe 600 TR)"
    else:
        y_ex = ret[f] - rf["RF_US"]
        m_ex = mkt_ex["MKT_US"]
        bmk = "SPXT (S&P 500 TR)"

    tm = run_tm(y_ex, m_ex, hac_lags=HAC_LAGS)
    hm = run_hm(y_ex, m_ex, hac_lags=HAC_LAGS)

    matched_results.append(pack_results(tm, f, bmk, "Treynor–Mazuy", gamma_name="m2"))
    matched_results.append(pack_results(hm, f, bmk, "Henriksson–Merton", gamma_name="Dm"))

    # Robustness: run each fund vs both benchmarks (EU and US)
    # EU benchmark
    tm_eu = run_tm(ret[f] - rf["RF_EU"], mkt_ex["MKT_EU"], hac_lags=HAC_LAGS)
    hm_eu = run_hm(ret[f] - rf["RF_EU"], mkt_ex["MKT_EU"], hac_lags=HAC_LAGS)
    all_benchmark_results.append(pack_results(tm_eu, f, "SXXR (Europe 600 TR)", "Treynor–Mazuy", "m2"))
    all_benchmark_results.append(pack_results(hm_eu, f, "SXXR (Europe 600 TR)", "Henriksson–Merton", "Dm"))

    # US benchmark
    tm_us = run_tm(ret[f] - rf["RF_US"], mkt_ex["MKT_US"], hac_lags=HAC_LAGS)
    hm_us = run_hm(ret[f] - rf["RF_US"], mkt_ex["MKT_US"], hac_lags=HAC_LAGS)
    all_benchmark_results.append(pack_results(tm_us, f, "SPXT (S&P 500 TR)", "Treynor–Mazuy", "m2"))
    all_benchmark_results.append(pack_results(hm_us, f, "SPXT (S&P 500 TR)", "Henriksson–Merton", "Dm"))

res_matched = pd.DataFrame(matched_results).sort_values(["Benchmark", "Fund", "Model"])
res_all = pd.DataFrame(all_benchmark_results).sort_values(["Benchmark", "Fund", "Model"])

res_matched.to_csv("timing_results_matched_benchmark.csv", index=False)
res_all.to_csv("timing_results_all_benchmarks.csv", index=False)

print("Done.")
print("Saved: timing_results_matched_benchmark.csv")
print("Saved: timing_results_all_benchmarks.csv")
