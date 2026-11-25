"""Screen the relaxed C104/C204 tolerance using the original SPICE filter."""
from pathlib import Path
import json
import numpy as np

here = Path(__file__).resolve().parent
model = here.parent / "vhf-low-cost" / "spice_tolerance.py"
namespace = {"__file__": str(model)}
exec(model.read_text().split("rng=np.random.default_rng")[0], namespace)
frequency = namespace["F"]
values = namespace["VALUES"]
def transmission(parts):
    s = namespace["run"](("original", parts, 70))
    return 20 * np.log10(np.abs(s[:, 1, 0]))
nominal = transmission(values)
band = (frequency >= 30) & (frequency <= 55)
fm = (frequency >= 88) & (frequency <= 108)
result = {}
for scale in (.95, 1, 1.05):
    parts = values.copy()
    parts[5] *= scale
    traces = transmission(parts)
    result[str(scale)] = {
        "maximum_inband_change_dB": float(max(abs(traces[band] - nominal[band]))),
        "minimum_FM_rejection_dB": float(max(traces[band]) - max(traces[fm])),
    }
print(json.dumps(result, indent=2))
