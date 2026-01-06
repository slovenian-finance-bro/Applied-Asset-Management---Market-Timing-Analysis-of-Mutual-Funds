# Applied-Asset-Management---Market-Timing-Analysis-of-Mutual-Funds
Data inputs and structure

The analysis begins by importing a single CSV file containing (i) fund NAV series, (ii) benchmark total return index levels, and (iii) short-term risk-free rate series. The dataset is parsed such that the Date column is converted to a datetime format, sorted chronologically, and set as the time index. Columns are classified into two groups:

Price-like level series: all fund NAVs and the benchmark index levels (SPXT and SXXR), treated as strictly positive level variables.

Rate series: Euribor 3-month and 3-month U.S. T-bill yields, treated as interest-rate variables.

This distinction is used to determine the appropriate treatment of missing values and subsequent return construction.

A. Handling missing observations (internal gap filling)

Before returns are computed, the code fills internal missing observations (i.e., gaps between two valid observations), while leaving leading and trailing missing blocks unchanged. The gap-filling method depends on the variable type:

NAV and index levels (price-like series) are interpolated using a geometric (log-linear) interpolation. In code, this is implemented by taking the natural logarithm of the level series, applying time-based linear interpolation in log space, and exponentiating back. This corresponds to assuming constant compounded growth between two observed levels, which is appropriate for price/NAV/index series.

Risk-free rate series are interpolated using standard linear interpolation in levels, reflecting that yields are not compounded price levels but rates.

This step produces a filled dataset df_filled used as the basis for computing returns.

B. Return construction (quarterly arithmetic returns)

Using the filled NAV and index level series, the code constructs returns as simple period-to-period percentage changes:

𝑅
𝑡
=
𝑃
𝑡
𝑃
𝑡
−
1
−
1
R
t
	​

=
P
t−1
	​

P
t
	​

	​

−1

This is implemented via pct_change() applied to each fund NAV series and the two benchmark index level series. Because the dataset is quarterly (or treated as such), the resulting return series are interpreted as quarterly arithmetic returns.

C. Risk-free rate transformation to quarterly returns

The risk-free inputs are annualized yields expressed in percent. To construct quarterly risk-free returns consistent with the quarterly return frequency, the code applies the approximation:

𝑅
𝑓
,
𝑡
(
𝑞
)
≈
Yield
𝑡
100
⋅
4
R
f,t
(q)
	​

≈
100⋅4
Yield
t
	​

	​


Two separate risk-free series are constructed:

RF_US from the 3-month U.S. T-bill yield

RF_EU from Euribor 3-month

This step aligns the risk-free rate scale with the computed quarterly fund and benchmark returns.

D. Excess returns and benchmark excess returns

The regression dependent variable is the fund excess return:

𝑦
𝑡
=
𝑅
𝑝
,
𝑡
−
𝑅
𝑓
,
𝑡
y
t
	​

=R
p,t
	​

−R
f,t
	​


and the main market regressor is benchmark excess return:

𝑚
𝑡
=
𝑅
𝑚
,
𝑡
−
𝑅
𝑓
,
𝑡
m
t
	​

=R
m,t
	​

−R
f,t
	​


The code constructs two benchmark excess return series:

𝑀
𝐾
𝑇
_
𝑈
𝑆
=
𝑅
𝑆
𝑃
𝑋
𝑇
−
𝑅
𝐹
_
𝑈
𝑆
MKT_US=R
SPXT
	​

−RF_US

𝑀
𝐾
𝑇
_
𝐸
𝑈
=
𝑅
𝑆
𝑋
𝑋
𝑅
−
𝑅
𝐹
_
𝐸
𝑈
MKT_EU=R
SXXR
	​

−RF_EU

Each fund’s excess return is constructed against the relevant risk-free series depending on the benchmark used in that regression.

E. Model implementation

The timing models are estimated using OLS with a constant and are implemented as two Python functions:

Treynor–Mazuy (TM)

The TM regression is estimated as:

𝑦
𝑡
=
𝛼
+
𝛽
𝑚
𝑡
+
𝛾
𝑚
𝑡
2
+
𝜀
𝑡
y
t
	​

=α+βm
t
	​

+γm
t
2
	​

+ε
t
	​


In code, 
𝑚
𝑡
2
m
t
2
	​

 is constructed explicitly as m**2, and the regressor matrix is 
{
1
,
𝑚
𝑡
,
𝑚
𝑡
2
}
{1,m
t
	​

,m
t
2
	​

}.

Henriksson–Merton (HM)

The HM regression is estimated as:

𝑦
𝑡
=
𝛼
+
𝛽
𝑚
𝑡
+
𝛾
(
𝐷
𝑡
⋅
𝑚
𝑡
)
+
𝜀
𝑡
,
𝐷
𝑡
=
1
(
𝑚
𝑡
>
0
)
y
t
	​

=α+βm
t
	​

+γ(D
t
	​

⋅m
t
	​

)+ε
t
	​

,D
t
	​

=1(m
t
	​

>0)

In code, 
𝐷
𝑡
D
t
	​

 is created as (m > 0).astype(int) and multiplied by 
𝑚
𝑡
m
t
	​

 to form the interaction term Dm.

F. Estimation details: HAC (Newey–West) standard errors

Although coefficients are estimated via OLS, statistical inference is based on heteroskedasticity- and autocorrelation-consistent (HAC) standard errors using the Newey–West estimator. Specifically, the code fits:

sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 4})

The choice maxlags = 4 reflects quarterly data and allows inference that is robust to serial correlation up to four lags.

G. Benchmark matching and robustness design

The code produces two sets of results.

(i) Matched benchmark specification (primary)

Funds are assigned to a benchmark via a simple rule based on their identifier:

If the fund name contains " LX ", it is treated as European and matched to SXXR (STOXX Europe 600 TR) with RF_EU.

Otherwise, it is matched to SPXT (S&P 500 TR) with RF_US.

For each fund in this matched setting, both TM and HM regressions are estimated and stored.

(ii) All-benchmarks specification (robustness)

Independently of the matching rule, the code re-estimates both TM and HM models for each fund against:

the European benchmark (SXXR) using RF_EU, and

the U.S. benchmark (SPXT) using RF_US.

This provides a robustness check on benchmark choice.

H. Output and stored statistics

For each fitted regression, the code extracts and stores:

𝑁
N, 
𝑅
2
R
2
, adjusted 
𝑅
2
R
2
, F-statistic and its p-value

𝛼
α, 
𝛽
β, 
𝛾
γ and their HAC standard errors, t-statistics, and p-values

These are written into two CSV files:

timing_results_matched_benchmark.csv

timing_results_all_benchmarks.csv
