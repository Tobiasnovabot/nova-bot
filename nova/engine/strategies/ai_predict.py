from . import Strategy, register
@register("ai_predict")
class AIPredictStrategy(Strategy):
    def on_bar(self, bar):
        s=float(bar.get("ai_score",0.0))
        side="buy" if s>0 else "sell" if s<0 else "flat"
        return {"symbol":bar["symbol"],"side":side,"score":float(s)}
