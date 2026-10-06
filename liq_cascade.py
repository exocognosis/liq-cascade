#!/usr/bin/env python3
"""
Kinked-IRM liquidation cascade simulator.

Toy model of a single-collateral lending market (Aave/Morpho-style):
- borrowers post ETH collateral, borrow USDC
- the borrow rate follows a kinked utilization curve
- a collateral price shock triggers liquidations; liquidation selling
  pushes the price down further, which triggers more liquidations

Stdlib only. Run:  python3 liq_cascade.py [shock_pct]
"""

import random
import sys

# ---------------- market parameters ----------------
ETH_PRICE_0 = 3000.0     # starting ETH/USD
LTV_MAX = 0.75           # max borrow = 75% of collateral value
LIQ_THRESHOLD = 0.80     # liquidatable when debt > 80% of collateral value
LIQ_BONUS = 0.05         # liquidators buy seized collateral at a 5% discount
CLOSE_FACTOR = 0.50      # at most 50% of a position's debt per liquidation

# kinked borrow-rate model: rate as a function of utilization
BASE_RATE, SLOPE1, SLOPE2, KINK = 0.02, 0.08, 0.60, 0.80
SUPPLY_USDC = 20_000_000  # fixed USDC supply pool; utilization = debt / supply

PRICE_IMPACT = 0.15      # liquidating 100% of collateral would move price 15%
MAX_ROUNDS = 20


def borrow_rate(utilization):
    if utilization <= KINK:
        return BASE_RATE + SLOPE1 * utilization
    return BASE_RATE + SLOPE1 * KINK + SLOPE2 * (utilization - KINK)


def health_factor(collateral_eth, debt_usdc, price):
    if debt_usdc <= 0:
        return float("inf")
    return collateral_eth * price * LIQ_THRESHOLD / debt_usdc


def build_book(n=60, seed=7):
    """Borrowers with random size and leverage just under the max LTV."""
    rng = random.Random(seed)
    book = []
    for _ in range(n):
        collateral = rng.uniform(10, 100)                      # ETH
        ltv = rng.uniform(0.55, LTV_MAX - 0.01)                # borrowed fraction
        debt = collateral * ETH_PRICE_0 * ltv                   # USDC
        book.append({"collateral": collateral, "debt": debt})
    return book


def simulate(shock_pct):
    book = build_book()
    price = ETH_PRICE_0 * (1 - shock_pct)
    total_collateral_0 = sum(b["collateral"] for b in book)

    liquidated_borrowers = 0
    liquidated_debt = 0.0
    bad_debt = 0.0

    for rnd in range(1, MAX_ROUNDS + 1):
        victims = [b for b in book
                   if b["debt"] > 0 and health_factor(b["collateral"], b["debt"], price) < 1.0]
        if not victims:
            break
        sold_this_round = 0.0
        for b in victims:
            repay = b["debt"] * CLOSE_FACTOR                  # USDC repaid by liquidator
            seize = repay * (1 + LIQ_BONUS) / price            # ETH seized at a discount
            seize = min(seize, b["collateral"])
            # underwater check: seized collateral worth less than repaid debt
            shortfall = max(0.0, repay - seize * price)
            bad_debt += shortfall
            b["debt"] -= repay
            b["collateral"] -= seize
            sold_this_round += seize
            liquidated_debt += repay
            if b["debt"] < 1.0:                               # dust: position closed
                liquidated_borrowers += 1
                b["debt"] = 0.0
        # liquidation selling pressure moves the oracle price
        price *= 1 - PRICE_IMPACT * (sold_this_round / total_collateral_0)
        print(f"  round {rnd:2d}: {len(victims):2d} liquidated, "
              f"price ${price:7.2f}, debt repaid ${liquidated_debt:,.0f}")

    debt_left = sum(b["debt"] for b in book)
    util_0 = sum(b["debt"] for b in build_book()) / SUPPLY_USDC
    util_1 = debt_left / SUPPLY_USDC
    return {
        "shock": shock_pct,
        "price_final": price,
        "borrowers_liquidated": liquidated_borrowers,
        "debt_repaid": liquidated_debt,
        "bad_debt": bad_debt,
        "util_before": util_0,
        "util_after": util_1,
        "rate_before": borrow_rate(util_0),
        "rate_after": borrow_rate(util_1),
    }


def main():
    shock = float(sys.argv[1]) if len(sys.argv) > 1 else 0.25
    print(f"ETH ${ETH_PRICE_0:,.0f} -> shock -{shock:.0%}, "
          f"LTV {LTV_MAX:.0%}, liq threshold {LIQ_THRESHOLD:.0%}, "
          f"bonus {LIQ_BONUS:.0%}, close factor {CLOSE_FACTOR:.0%}\n")
    r = simulate(shock)
    print(f"""
result after {shock:.0%} shock:
  final ETH price        ${r['price_final']:,.2f}
  borrowers liquidated    {r['borrowers_liquidated']}
  debt repaid via liq.    ${r['debt_repaid']:,.0f}
  bad debt (underwater)   ${r['bad_debt']:,.0f}
  utilization             {r['util_before']:.1%} -> {r['util_after']:.1%}
  borrow APY (kinked IRM) {r['rate_before']:.1%} -> {r['rate_after']:.1%}""")


if __name__ == "__main__":
    main()
