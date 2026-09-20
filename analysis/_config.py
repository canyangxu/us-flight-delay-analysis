from pathlib import Path
import matplotlib.pyplot as plt


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_FILE = (
    BASE_DIR
    / "data"
    / "bts_2025_07_to_2026_06.csv"
)

CHART_DIR = BASE_DIR / "charts"
CHART_DATA_DIR = BASE_DIR / "chart_data"

CHART_DIR.mkdir(exist_ok=True)
CHART_DATA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------
# Color system
# ---------------------------------------------------------

NAVY = "#29486F"
TERRACOTTA = "#BE7656"
STEEL = "#75899E"
SKY = "#AFC5D8"
GRAY = "#9AA4AF"
LIGHT_GRAY = "#E8EDF2"
DARK_TEXT = "#202A35"


# ---------------------------------------------------------
# Delay cause colors
# Keep these consistent across every chart
# ---------------------------------------------------------

CAUSE_COLORS = {
    "Carrier": TERRACOTTA,
    "Weather": SKY,
    "NAS": STEEL,
    "Security": GRAY,
    "Late Aircraft": NAVY
}


# ---------------------------------------------------------
# Common source note
# ---------------------------------------------------------

SOURCE_NOTE = (
    "Source: U.S. DOT BTS, Reporting Carrier On-Time Performance, "
    "Jul 2025-Jun 2026."
)


# ---------------------------------------------------------
# Common chart style
# ---------------------------------------------------------

def apply_chart_style():

    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": LIGHT_GRAY,
        "axes.labelcolor": DARK_TEXT,
        "axes.titlecolor": DARK_TEXT,
        "xtick.color": DARK_TEXT,
        "ytick.color": DARK_TEXT,
        "text.color": DARK_TEXT,
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False
    })