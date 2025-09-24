from nova.regime.detector import RegimeDetector
rd=RegimeDetector(atr_z_thresh=3.0, trend_thresh=0.3)
print("REGIME", rd.classify({"atr_z": 0.2, "trend": 0.6}))
print("REGIME", rd.classify({"atr_z": 3.5, "trend": 0.1}))
print("REGIME", rd.classify({"atr_z": 0.3, "trend": 0.05}))
print("REGIME", rd.classify({"atr_z": 1.5, "trend": 0.1}))
