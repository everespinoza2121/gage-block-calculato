"""Small Flask application for finding practical gage-block stacks."""

from bisect import bisect_left
from decimal import Decimal, InvalidOperation
import re

from flask import Flask, jsonify, render_template, request


MICROINCHES_PER_INCH = 1_000_000
MIN_TARGET = 50_000
MAX_TARGET = 1_000_000
MAX_BLOCKS = 5

# The modeled inventory contains one of each block. Values are exact microinches,
# listed from largest to smallest so equal-rank results have a stable ordering.
GAGE_BLOCKS = (
    1_000_000,
    950_000, 900_000, 850_000, 800_000, 750_000, 700_000, 650_000,
    600_000, 550_000, 500_000, 450_000, 400_000, 350_000, 300_000,
    250_000, 200_000, 150_000,
    149_000, 148_000, 147_000, 146_000, 145_000, 144_000, 143_000,
    142_000, 141_000, 140_000, 139_000, 138_000, 137_000, 136_000,
    135_000, 134_000, 133_000, 132_000, 131_000, 130_000, 129_000,
    128_000, 127_000, 126_000, 125_000, 124_000, 123_000, 122_000,
    121_000, 120_000, 119_000, 118_000, 117_000, 116_000, 115_000,
    114_000, 113_000, 112_000, 111_000, 110_000, 109_000, 108_000,
    107_000, 106_000, 105_000, 104_000, 103_000, 102_000, 101_000,
    100_900, 100_800, 100_700, 100_600, 100_500, 100_400, 100_300,
    100_200, 100_000, 93_750, 78_125, 62_500, 50_000,
)

# Accept ordinary decimal notation with an optional leading zero. Scientific
# notation and signs are intentionally excluded to keep shop-floor input clear.
DECIMAL_INPUT = re.compile(r"^(?:[0-9]+(?:\.[0-9]{1,6})?|\.[0-9]{1,6})$")


def format_inches(microinches):
    """Format an integer microinch value as an exact inch measurement."""
    sign = "-" if microinches < 0 else ""
    magnitude = abs(microinches)
    whole, fraction = divmod(magnitude, MICROINCHES_PER_INCH)
    return f"{sign}{whole}.{fraction:06d}"


def format_deviation(microinches):
    """Format deviation with an explicit direction sign."""
    prefix = "+" if microinches > 0 else ""
    return f"{prefix}{format_inches(microinches)}"


def parse_target(raw_value):
    """Validate an inch measurement and return exact integer microinches."""
    if raw_value is None or not raw_value.strip():
        raise ValueError("A target measurement is required.")

    value = raw_value.strip()
    if not DECIMAL_INPUT.fullmatch(value):
        raise ValueError("Enter a decimal measurement with no more than 6 decimal places.")

    try:
        decimal_value = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("Enter a valid decimal measurement.") from error

    microinches = int(decimal_value * MICROINCHES_PER_INCH)
    if not MIN_TARGET <= microinches <= MAX_TARGET:
        raise ValueError("Target must be between 0.050000 and 1.000000 inches.")
    return microinches


def build_reachable_totals(
    blocks=GAGE_BLOCKS, max_total=MAX_TARGET, max_blocks=MAX_BLOCKS
):
    """Precompute the preferred stack for each reachable total up to 1 inch."""
    levels = [{0: ()}] + [{} for _ in range(max_blocks)]

    for index, block in enumerate(blocks):
        for count in range(max_blocks, 0, -1):
            for total, combination in tuple(levels[count - 1].items()):
                new_total = total + block
                if new_total > max_total:
                    continue
                candidate = combination + (index,)
                existing = levels[count].get(new_total)
                if existing is None or candidate < existing:
                    levels[count][new_total] = candidate

    # Iterating by count makes fewer blocks win when two stacks have equal totals.
    preferred = {}
    for count in range(1, max_blocks + 1):
        for total, combination in levels[count].items():
            preferred.setdefault(total, combination)

    return preferred, tuple(sorted(preferred))


REACHABLE_STACKS, REACHABLE_TOTALS = build_reachable_totals()


def find_closest_stack(target):
    """Return the globally closest stack, with deterministic practical ties."""
    insertion_point = bisect_left(REACHABLE_TOTALS, target)
    candidate_totals = []
    if insertion_point:
        candidate_totals.append(REACHABLE_TOTALS[insertion_point - 1])
    if insertion_point < len(REACHABLE_TOTALS):
        candidate_totals.append(REACHABLE_TOTALS[insertion_point])

    def rank(total):
        combination = REACHABLE_STACKS[total]
        # Closest wins, then fewer blocks, then the stable inventory ordering.
        return abs(total - target), len(combination), combination

    total = min(candidate_totals, key=rank)
    block_indexes = REACHABLE_STACKS[total]
    blocks = tuple(GAGE_BLOCKS[index] for index in block_indexes)
    return blocks, total


def result_payload(target, blocks, total):
    """Build the precision-safe JSON response used by the frontend."""
    deviation = total - target
    if deviation == 0:
        match_type = "exact"
    elif deviation > 0:
        match_type = "above"
    else:
        match_type = "below"

    return {
        "target": format_inches(target),
        "blocks": [format_inches(block) for block in blocks],
        "total": format_inches(total),
        "deviation": format_deviation(deviation),
        "deviation_microinches": deviation,
        "match_type": match_type,
        "block_count": len(blocks),
    }


app = Flask(__name__)


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/gage-block")
def gage_block():
    try:
        target = parse_target(request.args.get("value"))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    blocks, total = find_closest_stack(target)
    return jsonify(result_payload(target, blocks, total))


if __name__ == "__main__":
    app.run()
