# AI used: GitHub Copilot through GitHub Education
"""Creates the timer-interval measurement figure used in the documentation."""

from pathlib import Path

import matplotlib.pyplot as plt


intervals = [1000, 3000, 5000, 10000]
character_delay_ms = [109.1, 108.3, 106.6, 106.4]
selected_interval = 5000

figure, delay_axis = plt.subplots(
    figsize=(7, 4.8),
    layout="constrained",
)

delay_axis.axvline(
    selected_interval,
    color="#2a7f62",
    linestyle="--",
    linewidth=1.5,
    label="Selected interval: 5,000",
)
delay_axis.set_xlabel("Timer interrupt interval (emulated instructions)")
delay_axis.grid(axis="y", alpha=0.3)

delay_axis.plot(
    intervals,
    character_delay_ms,
    marker="o",
    linewidth=2.2,
    color="#2066a8",
    label="Character appears",
)
delay_axis.set_title("Typed character appears in the shell")
delay_axis.set_ylabel("Delay (ms)")
delay_axis.set_ylim(100, 132)
delay_axis.legend(loc="upper right")

output_path = Path(__file__).parent / "images" / "timer_interval_measurements.png"
figure.savefig(output_path, dpi=180)
