from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Dict

Regime = Literal["trend","meanrev","highvol","lowvol"]

@dataclass
class RegimeDetector:
    atr_z_thresh: float = 3.0
    trend_thresh: float = 0.3

    def classify(self, feats: Dict[str, float]) -> Regime:
        atr_z = float(feats.get("atr_z", 0.0))
        trend = float(feats.get("trend", 0.0))  # [-1,1]
        if abs(atr_z) >= self.atr_z_thresh:
            return "highvol"
        if abs(trend) >= self.trend_thresh:
            return "trend"
        if abs(atr_z) < 1.0 and abs(trend) < self.trend_thresh/2:
            return "lowvol"
        return "meanrev"
