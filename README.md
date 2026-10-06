# liq-cascade

A toy liquidation cascade simulator for a single-collateral lending market.

**What it is:** a small Python model (stdlib only, ~130 lines) of an Aave/Morpho-style market: borrowers post ETH collateral against USDC debt, and the borrow rate follows a kinked utilization curve.

**What it does:** feed it a collateral price shock and it simulates the cascade. Underwater positions get partially liquidated (close factor, liquidation bonus, seized collateral sold), the selling pushes the oracle price down further, and the next round begins. It reports per-round liquidations, total debt repaid, bad debt from underwater positions, and how utilization and the kinked borrow APY respond as the book shrinks.

**Why:** built as a weekend exercise to develop intuition for lending-market risk mechanics: LTV, health factors, close factors, liquidation bonuses, and kinked rate curves. These are the primitives underneath every lending protocol's risk model, and the best way to understand a risk engine is to build a small one.

Run it: `python3 liq_cascade.py [shock_pct]` (default shock is 25%).
