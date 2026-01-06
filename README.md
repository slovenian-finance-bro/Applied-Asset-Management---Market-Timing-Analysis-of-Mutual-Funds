# Applied-Asset-Management---Market-Timing-Analysis-of-Mutual-Funds
This repository contains a Python-based implementation of classical market-timing tests using the Treynor–Mazuy (1966) and Henriksson–Merton (1981) regression frameworks. The project evaluates fund managers’ market-timing and stock-selection abilities using quarterly excess returns constructed from fund NAVs, benchmark total return indices, and short-term risk-free rates.

The analysis is fully reproducible and is designed to accompany an academic research paper or thesis.

Project Overview

The empirical workflow implemented in this repository includes:

Importing fund NAVs, benchmark index levels, and risk-free rate series

Handling missing observations using interpolation methods appropriate to variable type

Constructing quarterly arithmetic returns from raw level data

Computing excess returns relative to market-specific risk-free rates

Estimating Treynor–Mazuy and Henriksson–Merton regressions

Applying Newey–West (HAC) standard errors for robust statistical inference

Exporting regression results for matched-benchmark and robustness specifications

The primary focus is on the statistical significance and economic interpretation of the market-timing coefficient.
