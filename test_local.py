"""تجربة محلية بدون مفاتيح - python test_local.py"""
import os
os.environ.setdefault("BUSINESS_NAME", "متجر تجريبي")
from agent_core import generate_reply

tests = [
    ("سلام عليكم شحال السعر؟", "message"),
    ("Prix svp ?", "message"),
    ("How much is delivery?", "message"),
    ("توصلو لوهران؟", "message"),
    ("حاب نطلب", "message"),
    ("ممتاز، شكرا", "comment"),
    ("نحب نهدر مع إنسان", "message"),
    ("Wach kayen livraison l Alger ?", "message"),
]

for t, k in tests:
    r = generate_reply(t, kind=k)
    print(f"👤 [{k}] {t}\n🤖 {r['reply']}  (mode={r['mode']})\n")
print("✅ إذا ظهرت الردود فوق، فالوكيل جاهز.")
