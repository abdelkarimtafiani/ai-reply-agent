"""سيرفر موحد: Facebook + Instagram + Messenger + WhatsApp + TikTok -> دماغ AI واحد."""
import os
import requests
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()
from agent_core import generate_reply

app = FastAPI(title="AI Reply Agent - كل المنصات")

META_TOKEN = os.getenv("META_PAGE_TOKEN", "")
VERIFY = os.getenv("META_VERIFY_TOKEN", "my_secret_verify_123")
WA_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WA_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")

# ذاكرة محادثات بسيطة (للإنتاج استعمل Redis/DB)
HISTORY: dict[str, list] = {}

def chat(user_id: str, text: str, kind: str, platform: str) -> str:
    h = HISTORY.setdefault(f"{platform}:{user_id}", [])
    out = generate_reply(text, kind=kind, history=h)
    h += [{"role": "user", "content": text}, {"role": "assistant", "content": out["reply"]}]
    HISTORY[f"{platform}:{user_id}"] = h[-20:]
    if out.get("handoff"):
        return out["reply"] + "\n— تم إشعار الفريق البشري ✅"
    return out["reply"]

def send_meta(recipient_id: str, text: str):
    """إرسال عبر Messenger/Instagram (نفس API). Dry-run إذا لا يوجد توكن."""
    if not META_TOKEN:
        print(f"[DRY-RUN META -> {recipient_id}]: {text}")
        return {"dry_run": True}
    r = requests.post(
        "https://graph.facebook.com/v21.0/me/messages",
        params={"access_token": META_TOKEN},
        json={"recipient": {"id": recipient_id}, "message": {"text": text[:1900]}},
        timeout=20,
    )
    return r.json()

def send_whatsapp(to: str, text: str):
    if not (WA_TOKEN and WA_PHONE_ID):
        print(f"[DRY-RUN WA -> {to}]: {text}")
        return {"dry_run": True}
    r = requests.post(
        f"https://graph.facebook.com/v21.0/{WA_PHONE_ID}/messages",
        headers={"Authorization": f"Bearer {WA_TOKEN}"},
        json={"messaging_product": "whatsapp", "to": to, "text": {"body": text[:4000]}},
        timeout=20,
    )
    return r.json()

def reply_comment(object_id: str, text: str):
    """الرد على تعليق فيسبوك/انستغرام."""
    if not META_TOKEN:
        print(f"[DRY-RUN COMMENT {object_id}]: {text}")
        return {"dry_run": True}
    r = requests.post(
        f"https://graph.facebook.com/v21.0/{object_id}/comments",
        params={"access_token": META_TOKEN},
        json={"message": text},
        timeout=20,
    )
    return r.json()

@app.get("/")
def home():
    return {"status": "AI Agent شغال ✅", "platforms": ["messenger", "instagram", "facebook-comments", "whatsapp", "tiktok"], "mode": "ai" if os.getenv("OPENAI_API_KEY") else "rule-تجريبي"}

# ---- تحقق Webhook من Meta ----
@app.get("/webhook/meta")
def verify_meta(hub_mode: str = Query("", alias="hub.mode"), hub_token: str = Query("", alias="hub.verify_token"), hub_challenge: str = Query("", alias="hub.challenge")):
    if hub_mode == "subscribe" and hub_token == VERIFY:
        return PlainTextResponse(hub_challenge)
    return PlainTextResponse("forbidden", status_code=403)

# ---- استقبال Meta (رسائل + تعليقات) ----
@app.post("/webhook/meta")
async def receive_meta(req: Request):
    data = await req.json()
    results = []
    for entry in data.get("entry", []):
        # 1) تعليقات (changes)
        for ch in entry.get("changes", []):
            f = ch.get("field", "")
            v = ch.get("value", {})
            if f in ("feed", "comments", "live_comments"):
                ctext = v.get("message") or v.get("text") or ""
                cid = v.get("comment_id") or v.get("id")
                if ctext and cid:
                    reply = chat(cid, ctext, "comment", "fb-comment")
                    results.append({"type": "comment", "id": cid, "sent": reply_comment(cid, reply)})
        # 2) رسائل Messenger/Instagram
        for m in entry.get("messaging", []):
            sender = m.get("sender", {}).get("id", "")
            txt = (m.get("message") or {}).get("text", "")
            if sender and txt:
                plat = "instagram" if m.get("sender", {}).get("id") and "instagram" in str(data).lower() else "messenger"
                reply = chat(sender, txt, "message", plat)
                results.append({"type": plat, "id": sender, "sent": send_meta(sender, reply)})
    return JSONResponse({"ok": True, "handled": results})

# ---- WhatsApp ----
@app.post("/webhook/whatsapp")
async def receive_wa(req: Request):
    data = await req.json()
    out = []
    try:
        for entry in data.get("entry", []):
            for ch in entry.get("changes", []):
                for msg in ch.get("value", {}).get("messages", []):
                    frm = msg.get("from", "")
                    txt = msg.get("text", {}).get("body", "")
                    if frm and txt:
                        reply = chat(frm, txt, "message", "whatsapp")
                        out.append({"to": frm, "sent": send_whatsapp(frm, reply)})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})
    return JSONResponse({"ok": True, "handled": out})

# ---- TikTok (تعليقات عبر polling أو webhook حسب صلاحياتك) ----
@app.post("/webhook/tiktok")
async def receive_tiktok(req: Request):
    data = await req.json()
    # TikTok يرسل صيغ مختلفة حسب الـ API - نعالج الأشهر
    text = data.get("text") or data.get("comment") or data.get("message") or ""
    cid = data.get("comment_id") or data.get("id") or "tiktok_user"
    reply = chat(str(cid), str(text), "comment", "tiktok")
    print(f"[TIKTOK reply -> {cid}]: {reply} (انشره يدويا أو عبر TikTok Business API)")
    return JSONResponse({"ok": True, "reply": reply, "note": "TikTok يحتاج Business API لنشر الرد تلقائيا"})

# ---- تجربة سريعة بدون منصات ----
@app.get("/test")
def quick_test(q: str = "شحال السعر؟", kind: str = "message"):
    return generate_reply(q, kind=kind)
