#!/usr/bin/env python3
from nova.sentiment_guard.guard import score_sentiment, guard_sentiment
def main()->int:
    s1=score_sentiment({"fg_index":80,"news_bias":0.2,"vol_spike":0.0})
    ok,_=guard_sentiment(s1)
    assert ok
    s2=score_sentiment({"fg_index":20,"news_bias":-0.5,"vol_spike":1.0})
    ok,why=guard_sentiment(s2)
    assert not ok and why=="sentiment_veto"
    print("sentiment_guard selftest: OK"); return 0
if __name__=="__main__": raise SystemExit(main())
