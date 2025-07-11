
from flask import Flask, request, Response
from itertools import combinations

app = Flask(__name__)

gage_block_sizes = sorted([
    0.050, 0.0625, 0.078125, 0.09375, 0.100, 0.1002, 0.1003, 0.1004, 0.1005,
    0.1006, 0.1007, 0.1008, 0.1009, 0.101, 0.102, 0.103, 0.104, 0.105, 0.106,
    0.107, 0.108, 0.109, 0.110, 0.111, 0.112, 0.113, 0.114, 0.115, 0.116,
    0.117, 0.118, 0.119, 0.120, 0.121, 0.122, 0.123, 0.124, 0.125, 0.126,
    0.127, 0.128, 0.129, 0.130, 0.131, 0.132, 0.133, 0.134, 0.135, 0.136,
    0.137, 0.138, 0.139, 0.140, 0.141, 0.142, 0.143, 0.144, 0.145, 0.146,
    0.147, 0.148, 0.149, 0.150, 0.200, 0.250, 0.300, 0.350, 0.400, 0.450,
    0.500, 0.550, 0.600, 0.650, 0.700, 0.750, 0.800, 0.850, 0.900, 0.950,
    1.000
], reverse=True)

def find_gage_block_combination(target_value, max_blocks=5, tolerance=0.00005):
    for r in range(1, max_blocks + 1):
        for combo in combinations(gage_block_sizes, r):
            if abs(sum(combo) - target_value) <= tolerance:
                return combo, sum(combo)
    return None, None

@app.route("/")
def home():
    return Response(html_code, mimetype='text/html')

@app.route("/gage-block")
def gage_block():
    value = request.args.get("value")
    try:
        target = float(value)
        combo, total = find_gage_block_combination(target)
        if combo:
            return {
                "target_value": target,
                "block_combination": combo,
                "total": total,
                "status": "Success"
            }
        else:
            return {
                "target_value": target,
                "block_combination": [],
                "total": None,
                "status": "No combination found"
            }
    except:
        return {
            "error": "Invalid input. Use like this: /gage-block?value=0.6453"
        }

html_code = """
<!DOCTYPE html>
<html>
<head>
    <title>Gage Block Calculator</title>
</head>
<body style=\"font-family: Arial, sans-serif; text-align: center; padding-top: 50px;\">
    <h2>Gage Block Combination Finder</h2>
    <p>Enter a number from 0.0500 to 1.0000 inches:</p>
    <input type=\"number\" id=\"inputValue\" step=\"0.0001\" min=\"0.0500\" max=\"1.0000\" placeholder=\"e.g., 0.6453\">
    <button onclick=\"getGageBlocks()\">Calculate</button>

    <h3>Result:</h3>
    <pre id=\"resultArea\" style=\"white-space: pre-wrap;\"></pre>

    <script>
        function getGageBlocks() {
            const val = document.getElementById('inputValue').value;
            if (!val) {
                alert(\"Please enter a number.\");
                return;
            }

            fetch(`/gage-block?value=${val}`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === \"Success\") {
                        document.getElementById('resultArea').textContent =
                            \"Target: \" + data.target_value + \" inches\\n\" +
                            \"Blocks: \" + data.block_combination.join(\" , \") + \"\\n\" +
                            \"Total: \" + data.total + \" inches\";
                    } else {
                        document.getElementById('resultArea').textContent = data.status || \"No result.\";
                    }
                })
                .catch(err => {
                    document.getElementById('resultArea').textContent = \"Error contacting server.\";
                });
        }
    </script>
</body>
</html>
"""
