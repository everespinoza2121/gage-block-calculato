from bisect import bisect_left
from itertools import combinations

import pytest

import main


def test_inventory_is_preserved_and_exact():
    assert len(main.GAGE_BLOCKS) == 80
    assert len(set(main.GAGE_BLOCKS)) == 80
    assert main.GAGE_BLOCKS == tuple(sorted(main.GAGE_BLOCKS, reverse=True))
    assert main.GAGE_BLOCKS[-4:] == (93_750, 78_125, 62_500, 50_000)


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (".25", 250_000),
        (".250", 250_000),
        ("0.25", 250_000),
        ("0.250000", 250_000),
        (".387", 387_000),
        (".387000", 387_000),
        ("0.387", 387_000),
        ("0.387000", 387_000),
        ("0.050000", 50_000),
        ("0.6453", 645_300),
        ("0.078125", 78_125),
        ("1", 1_000_000),
        (" 0.500000 ", 500_000),
    ],
)
def test_parse_target_returns_exact_microinches(raw_value, expected):
    assert main.parse_target(raw_value) == expected


@pytest.mark.parametrize(
    "raw_value",
    [
        None,
        "",
        " ",
        "words",
        ".",
        "+",
        "-",
        "+.25",
        "0.25.0",
        "..25",
        "0.0500000",
        ".2500000",
        "1e-1",
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_parse_target_rejects_invalid_values(raw_value):
    with pytest.raises(ValueError):
        main.parse_target(raw_value)


@pytest.mark.parametrize("raw_value", ["0.049999", "1.000001", "-0.5"])
def test_parse_target_enforces_supported_range(raw_value):
    with pytest.raises(ValueError):
        main.parse_target(raw_value)


def test_formatting_has_stable_six_place_precision():
    assert main.format_inches(78_125) == "0.078125"
    assert main.format_inches(645_300) == "0.645300"
    assert main.format_deviation(25) == "+0.000025"
    assert main.format_deviation(-25) == "-0.000025"
    assert main.format_deviation(0) == "0.000000"


def test_exact_match_uses_fewest_blocks():
    blocks, total = main.find_closest_stack(500_000)
    assert blocks == (500_000,)
    assert total == 500_000


def test_closest_match_reports_nonzero_deviation():
    blocks, total = main.find_closest_stack(50_001)
    assert blocks == (50_000,)
    assert total == 50_000


def test_equal_distance_prefers_fewer_blocks():
    # 112250 is equally distant from 112000 (one block) and 112500
    # (two blocks: 62500 + 50000).
    blocks, total = main.find_closest_stack(112_250)
    assert blocks == (112_000,)
    assert total == 112_000


def test_stack_never_reuses_a_physical_block_and_stays_within_limit():
    blocks, _ = main.find_closest_stack(645_300)
    assert len(blocks) <= main.MAX_BLOCKS
    assert len(blocks) == len(set(blocks))


def brute_force_closest(blocks, target, max_total, max_blocks):
    best = None
    for count in range(1, max_blocks + 1):
        for indexes in combinations(range(len(blocks)), count):
            total = sum(blocks[index] for index in indexes)
            if total > max_total:
                continue
            rank = (abs(total - target), count, indexes)
            if best is None or rank < best[0]:
                best = rank, indexes, total
            if rank[0] == 0 and count == 1:
                return best
    return best


def test_index_builder_matches_brute_force_reference_for_small_inventory():
    blocks = (500_000, 300_000, 200_000, 125_000, 75_000, 50_000)
    max_total = 700_000
    max_blocks = 3
    stacks, totals = main.build_reachable_totals(blocks, max_total, max_blocks)

    for target in range(50_000, max_total + 1, 12_345):
        _, expected_indexes, expected_total = brute_force_closest(
            blocks, target, max_total, max_blocks
        )
        position = bisect_left(totals, target)
        adjacent = totals[max(0, position - 1) : position + 1]
        actual_total = min(
            adjacent,
            key=lambda total: (
                abs(total - target),
                len(stacks[total]),
                stacks[total],
            ),
        )
        assert actual_total == expected_total
        assert stacks[actual_total] == expected_indexes


@pytest.fixture()
def client():
    main.app.config.update(TESTING=True)
    return main.app.test_client()


def test_home_uses_authoritative_template(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Gage Block Calculator" in response.data
    assert b'id="inputValue"' in response.data
    assert b"Use these blocks" in response.data
    assert b'className = "gage-block"' in response.data
    assert b"toFixed(4)" in response.data
    assert b"function stepInput(direction)" in response.data
    assert b"function parseInputMicroinches(value)" in response.data
    assert b'step="any"' in response.data
    assert b"updateDynamicStep" not in response.data
    assert b'event.key === "ArrowUp"' in response.data
    assert b'input.addEventListener("wheel"' in response.data
    assert b'window.location.protocol === "file:"' in response.data
    assert b"This calculator must be served by Flask" in response.data
    assert b'class="maker-signature"' in response.data
    assert b"Built by Ever Espinoza \xc2\xb7 2026" in response.data
    result_position = response.data.index(b'id="result"')
    signature_position = response.data.index(b'class="maker-signature"')
    main_end_position = response.data.index(b"</main>")
    assert result_position < signature_position < main_end_position
    assert b"position: absolute" not in response.data
    assert b"position: fixed" not in response.data
    assert b"position: sticky" not in response.data


def test_gage_block_route_returns_precision_safe_contract(client):
    response = client.get("/gage-block?value=0.6453")
    assert response.status_code == 200
    data = response.get_json()
    assert data == {
        "target": "0.645300",
        "blocks": ["0.400000", "0.145000", "0.100300"],
        "total": "0.645300",
        "deviation": "0.000000",
        "deviation_microinches": 0,
        "match_type": "exact",
        "block_count": 3,
    }


@pytest.mark.parametrize(
    "value",
    [".1", ".10", "0.1", "0.10", ".9", ".90", "0.9", "0.90"],
)
def test_gage_block_route_accepts_one_and_two_decimal_shorthand(client, value):
    response = client.get("/gage-block", query_string={"value": value})
    assert response.status_code == 200
    assert response.get_json()["target"] == f"{float(value):.6f}"


@pytest.mark.parametrize(
    "query",
    ["", "?value=", "?value=not-a-number", "?value=0.049999", "?value=1.000001"],
)
def test_gage_block_route_rejects_invalid_input(client, query):
    response = client.get(f"/gage-block{query}")
    assert response.status_code == 400
    assert response.get_json()["error"]


def test_result_payload_identifies_direction():
    assert main.result_payload(100_000, (100_000,), 100_000)["match_type"] == "exact"
    assert main.result_payload(100_000, (100_200,), 100_200)["match_type"] == "above"
    assert main.result_payload(100_200, (100_000,), 100_000)["match_type"] == "below"
