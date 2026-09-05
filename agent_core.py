"""العقل المركزي للـ AI Agent - يشتغل بدون مفتاح API أيضا (وضع تجريبي)."""
import json, os, re
from pathlib import Path

BASE = Path(__file__).parent
KNOW_PATH = BASE / "knowledge.json"

def load_knowledge():
    try:
        return json.loads(KNOW_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"business_name": "متجرك", "products": [], "faq": []}

KNOW = load_knowledge()
BUSINESS = os.getenv("BUSINESS_NAME", KNOW.get("business_name", "متجرك"))

SYSTEM_PROMPT = f"""أنت موظف مبيعات ذكي لـ "{BUSINESS}" ترد على رسائل وتعليقات الحملات الإعلانية (Facebook/Instagram/WhatsApp/TikTok).

قواعد صارمة:
1. اكتشف لغة العميل تلقائيا ورد بنفس اللغة: دارجة جزائرية / فصحى / فرنسية / إنجليزية. إذا كتب مزيج (عربية+فرنسية) رد بنفس المزيج.
2. الرد قصير: سطر-سطرين للتعليقات، max 4 أسطر للرسائل. مع إيموجي واحد فقط.
3. هدفك: الإجابة + دفع العميل للطلب. اطلب دائما: الاسم + الهاتف + الولاية + البلدية عند نية الشراء.
4. لا تخترع أسعارا. استعمل المعرفة التالية فقط:
{json.dumps(KNOW, ensure_ascii=False)[:4000]}
5. إذا شتم العميل أو غضب: اعتذر بهدوء وقل "نحولك لموظف بشري" ولا تشتم.
6. إذا طلب إنسان/موظف أو اشتكى: قل أنك ستحوله للفريق واطلب رقم هاتفه.
7. للتعليقات العامة: لا تذكر أسعار الجملة الخاصة، ادعُه للخاص لإتمام الطلب.
8. ممنوع: وعود طبية/قانونية كاذبة، خصومات وهمية، الكشف عن أنك AI إلا إذا سُئلت.
"""

HANDOFF_WORDS = ["إنسان", "موظف", "بشري", "اتصل", "شكوى", "مشكل كبير", "humain", "agent", "human", "réclamation", "plainte"]

def needs_human(text: str) -> bool:
    t = text.lower()
    return any(w.lower() in t for w in HANDOFF_WORDS)

def rule_based_reply(text: str, kind: str = "message") -> str:
    """رد احتياطي ذكي بدون API - يكفي للتجربة والحملات البسيطة."""
    t = text.lower()
    # كشف اللغة بسيط
    is_fr = any(w in t for w in ["prix", "livraison", "combien", "bonjour", "salam", "paiement", "commander"])
    is_en = any(w in t for w in ["price", "delivery", "how much", "order"])
    prods = KNOW.get("products", [{}])
    p = prods[0] if prods else {}
    price = p.get("price", "2900 دج")

    if needs_human(text):
        if is_fr: return "Désolé pour le dérangement 🙏 Je vous transfère à un agent humain, laissez votre numéro svp."
        if is_en: return "Sorry about that 🙏 Transferring you to a human agent, please leave your number."
        return "سمحلي على الإزعاج 🙏 نحولك لموظف بشري، خلي رقمك من فضلك."

    if any(w in t for w in ["سعر", "شحال", "prix", "price", "combien", "how much", "سومة"]):
        if is_fr: return f"Le prix est {price} 💰 Paiement à la livraison. Pour commander: nom + téléphone + wilaya + commune."
        if is_en: return f"Price is {price} 💰 Cash on delivery. To order send: name + phone + state + city."
        return f"السعر {price} 💰 الدفع عند الاستلام. للطلب ابعث: الاسم + الهاتف + الولاية + البلدية."
    if any(w in t for w in ["توصيل", "livraison", "delivery", "شحن", "توصلو"]):
        if is_fr: return "Oui, livraison 58 wilayas en 24-72h 🚚 Paiement à la réception. Donnez wilaya + commune."
        return "نعم، نوصل لـ 58 ولاية في 24-72 ساعة 🚚 الدفع كي يوصلك. ابعث الولاية + البلدية."
    if any(w in t for w in ["اطلب", "نطلب", "طلب", "نشري", "commander", "order", "حجز", "مهتم", "نحجز"]):
        if is_fr: return "Parfait 👍 Envoyez: nom + téléphone + wilaya + commune et on confirme votre commande."
        return "ممتاز 👍 ابعث: الاسم + الهاتف + الولاية + البلدية ونأكدولك الطلب."
    if any(w in t for w in ["سلام", "salam", "salut", "bonjour", "hello", "صباح", "مساء", "cc", "slm"]):
        # رد بنفس اللغة
        if is_fr: return "Salut et bienvenue 👋 Comment puis-je vous aider ? (prix / livraison / commande)"
        if is_en: return "Hello and welcome 👋 How can I help? (price / delivery / order)"
        return "وعليكم السلام ومرحبا بيك 👋 كيفاش نقدر نعاونك؟ (سعر / توصيل / طلب)"
    if kind == "comment":
        if is_fr: return "Merci pour votre commentaire 😊 Détails envoyés en privé, vérifiez vos messages 📩"
        return "شكرا على تعليقك 😊 بعثنالك التفاصيل في الخاص، شوف الرسائل 📩"
    if is_fr: return "Merci pour votre message 😊 Dites-moi: vous voulez le prix, la livraison ou commander ?"
    if is_en: return "Thanks for your message 😊 Tell me: do you want price, delivery or to order?"
    return "شكرا على رسالتك 😊 قولي: تحب تعرف السعر، التوصيل، ولا تحب تطلب؟"

def generate_reply(user_text: str, kind: str = "message", history: list | None = None) -> dict:
    """
    kind: "message" أو "comment"
    يرجع: {"reply": str, "handoff": bool, "lang": str}
    """
    user_text = (user_text or "").strip() or "..."
    handoff = needs_human(user_text)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    # بدون مفتاح -> وضع تجريبي
    if not api_key:
        return {"reply": rule_based_reply(user_text, kind), "handoff": handoff, "lang": "auto", "mode": "rule"}

    # مع مفتاح -> LLM
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in (history or [])[-8:]:
            msgs.append({"role": h.get("role", "user"), "content": h.get("content", "")[:1000]})
        prefix = "هذا تعليق عام (رد قصير جدا وادعه للخاص): " if kind == "comment" else "هذه رسالة خاصة: "
        msgs.append({"role": "user", "content": prefix + user_text})
        r = client.chat.completions.create(model=model, messages=msgs, temperature=0.6, max_tokens=250)
        return {"reply": r.choices[0].message.content.strip(), "handoff": handoff, "lang": "auto", "mode": "ai"}
    except Exception as e:
        # fallback حتى لا يتوقف البوت
        return {"reply": rule_based_reply(user_text, kind), "handoff": handoff, "lang": "auto", "mode": f"fallback:{e.__class__.__name__}"}
