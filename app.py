"""
Pet AI Triage & First-Aid Assistant (ระบบคัดกรองอาการและปฐมพยาบาลสัตว์เลี้ยงอัจฉริยะ)
พัฒนาด้วย Python เชื่อมต่อกับ AI for Thai (TextQA / Thai LLM)
"""

import os
import sys
import json
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

os.makedirs(PUBLIC_DIR, exist_ok=True)

# ฐานข้อมูลคัดกรองอาการสัตว์เลี้ยงฉุกเฉิน (Veterinary Emergency Triage Protocol)
PET_TRIAGE_DATABASE = {
    "emergency_keywords": [
        "ชัก", "เกร็ง", "หมดสติ", "ไม่หายใจ", "หายใจหอบ", "ลิ้นม่วง", "เหงือกซีด", "เหงือกขาว",
        "พารา", "พาราเซตามอล", "ช็อกโกแลต", "ชอกโกแลต", "ยาเบื่อ", "สารพิษ", "สารเคมี", "ดอกลิลลี่",
        "ฉี่ไม่ออก", "ปัสสาวะไม่ออก", "เบ่งฉี่", "ท้องกาง", "ท้องป่องเฉียบพลัน", "เลือดออกไม่หยุด",
        "โดนรถชน", "ตกตึก", "ตกที่สูง", "ฮีทสโตรก", "ตัวร้อนจัด", "น้ำลายฟูมปาก"
    ],
    "urgent_keywords": [
        "อาเจียนหลายครั้ง", "อ้วกเป็นเลือด", "อ้วกสีเขียว", "ถ่ายเป็นเลือด", "ท้องเสียรุนแรง",
        "ไม่กินน้ำเกิน 24 ชม", "ไม่กินข้าวเกิน 2 วัน", "ตาปิด", "ตาบวม", "แผลลึก", "เดินไม่ได้"
    ]
}

PET_FIRST_AID_GUIDE = {
    "พาราเซตามอล": {
        "title": "ภาวะพิษจากพาราเซตามอล (อันตรายถึงชีวิตในแมวและสุนัข)",
        "urgency": "critical",
        "urgency_label": "🔴 ฉุกเฉินวิกฤต (ต้องพบแพทย์ทันที)",
        "explanation": "ยาพาราเซตามอลเป็นพิษร้ายแรงมากโดยเฉพาะในแมว ทำให้เม็ดเลือดแดงแตก ตับวายเฉียบพลัน และขาดออกซิเจน แม้ได้รับเพียง 1/4 เม็ดก็อาจเสียชีวิตได้",
        "first_aid": [
            "รีบพาไปโรงพยาบาลสัตว์ที่ใกล้ที่สุดทันทีภายใน 1-2 ชั่วโมง",
            "นำแผงยาหรือซองยาที่สัตว์เลี้ยงกินเข้าไปให้สัตวแพทย์ดูด้วย",
            "หากเพิ่งกินไม่เกิน 30 นาที ให้โทรปรึกษา รพ.สัตว์ เรื่องการป้อนผงถ่าน (Activated Charcoal) หากมี"
        ],
        "donts": [
            "ห้ามรอดูอาการที่บ้านเด็ดขาด เพราะอาการตับวายจะเริ่มแสดงเมื่อสายเกินไป",
            "ห้ามพยายามทำให้อาเจียนเองหากไม่มีสัตวแพทย์แนะนำทางโทรศัพท์"
        ]
    },
    "ช็อกโกแลต": {
        "title": "ภาวะพิษจากสารธีโอโบรมีนในช็อกโกแลต",
        "urgency": "critical",
        "urgency_label": "🔴 ฉุกเฉินวิกฤต (ต้องพบแพทย์ทันที)",
        "explanation": "สาร Theobromine ในโกโก้/ช็อกโกแลต สุนัขและแมวไม่สามารถย่อยสลายได้ ส่งผลต่อหัวใจเต้นผิดจังหวะ กล้ามเนื้อเกร็งกระตุก และไตวาย",
        "first_aid": [
            "จดจำชนิดของช็อกโกแลต (ดาร์กช็อกโกแลตอันตรายที่สุด) และปริมาณที่กิน",
            "รีบนำส่งโรงพยาบาลสัตว์ทันที เพื่อให้หมอล้างท้องหรือให้ยาแก้พิษ"
        ],
        "donts": [
            "ห้ามป้อนไข่ขาวดิบหรือนม เพราะไม่ช่วยล้างพิษช็อกโกแลต",
            "ห้ามชะล่าใจแม้สัตว์เลี้ยงจะยังวิ่งเล่นได้ปกติหลังกินเข้าไปใหม่ๆ"
        ]
    },
    "ฉี่ไม่ออก": {
        "title": "ภาวะท่อปัสสาวะอุดตัน (โดยเฉพาะแมวเพศผู้)",
        "urgency": "critical",
        "urgency_label": "🔴 ฉุกเฉินวิกฤต (อันตรายถึงชีวิตภายใน 24-48 ชม.)",
        "explanation": "หากแมวหรือสุนัขพยายามเข้ากระบะทราย เบ่งฉี่ มีเสียงร้องเจ็บปวดแต่ไม่มีปัสสาวะออก อาจเกิดจากนิ่วอุดตัน ทำให้ของเสียและโพแทสเซียมคั่งในกระแสเลือด ส่งผลให้หัวใจหยุดเต้นได้",
        "first_aid": [
            "ตรวจดูบริเวณกระบะทรายว่ามีปัสสาวะหรือไม่ หรือมีเลือดปนไหม",
            "รีบนำส่ง รพ.สัตว์ 24 ชั่วโมง เพื่อสวนปัสสาวะระบายของเสียทันที"
        ],
        "donts": [
            "ห้ามกดหรือบีบบริเวณกระเพาะปัสสาวะเองเด็ดขาด เพราะอาจทำให้กระเพาะปัสสาวะแตกได้",
            "ห้ามรอดูอาการข้ามคืน"
        ]
    },
    "ฮีทสโตรก": {
        "title": "ภาวะลมแดด / ฮีทสโตรก (Heatstroke)",
        "urgency": "critical",
        "urgency_label": "🔴 ฉุกเฉินวิกฤต (ต้องลดอุณหภูมิทันที)",
        "explanation": "อุณหภูมิร่างกายสูงเกิน 40°C สัตว์เลี้ยงจะหอบรุนแรง น้ำลายเหนียว เหงือกแดงเข้ม และอาจหมดสติ",
        "first_aid": [
            "ย้ายสัตว์เลี้ยงเข้าที่ร่ม มีพัดลมหรืออากาศถ่ายเททันที",
            "ใช้ผ้าชุบน้ำอุณหภูมิห้อง (ไม่ใช่ผ้าเย็นจัด) เช็ดตามอุ้งเท้า ขาหนีบ และใบหู",
            "รีบพาไปคลินิกสัตว์ระหว่างที่เปิดแอร์ในรถตลอดเวลา"
        ],
        "donts": [
            "ห้ามใช้น้ำแข็งหรือน้ำเย็นจัดราดตัวเด็ดขาด เพราะจะทำให้หลอดเลือดหดตัวจนระบายความร้อนไม่ได้และเกิดภาวะช็อก"
        ]
    },
    "อาเจียน": {
        "title": "อาการอาเจียน / ขย้อนอาหาร",
        "urgency": "moderate",
        "urgency_label": "🟡 เฝ้าระวังอย่างใกล้ชิด (ควรพบแพทย์)",
        "explanation": "อาจเกิดจากการเปลี่ยนอาหารเร็วเกินไป กินเร็ว มีสิ่งแปลกปลอม หรือการติดเชื้อในระบบทางเดินอาหาร",
        "first_aid": [
            "หากอาเจียนเพียง 1 ครั้งและยังร่าเริง ให้งดอาหาร 6-8 ชม. แต่วางน้ำสะอาดไว้",
            "สังเกตสีและสิ่งที่ออกมา (เช่น มีเศษพลาสติก เส้นผม เลือด หรือฟองสีเหลือง/ขาว)",
            "หากเริ่มมีอาการซึม หรืออาเจียนติดต่อกันมากกว่า 2-3 ครั้งใน 24 ชม. ให้พาไปพบแพทย์"
        ],
        "donts": [
            "ห้ามป้อนยาแก้เมารถหรือยาแก้คลื่นไส้ของคนเด็ดขาด",
            "ห้ามบังคับให้กินอาหารแข็งทันทีหลังจากเพิ่งอาเจียน"
        ]
    },
    "ท้องเสีย": {
        "title": "อาการท้องเสีย / ถ่ายเหลว",
        "urgency": "moderate",
        "urgency_label": "🟡 เฝ้าระวัง (ระวังภาวะขาดน้ำ)",
        "explanation": "อาจเกิดจากอาหารเป็นพิษ การเปลี่ยนอาหาร พยาธิ หรือเชื้อไวรัสลำไส้อักเสบ",
        "first_aid": [
            "สังเกตลักษณะอุจจาระ (ถ่ายเหลวเป็นน้ำ, มีมูกเลือด, หรือสีดำคล้ำ)",
            "จัดเตรียมน้ำสะอาดให้กินตลอดเวลาเพื่อป้องกันภาวะขาดน้ำ",
            "หากเป็นลูกสัตว์อายุน้อยกว่า 6 เดือน ควรรีบพาไปตรวจเชื้อพาโวไวรัส/โคโรนาไวรัส"
        ],
        "donts": [
            "ห้ามให้ยาหยุดถ่ายของคน (เช่น Imodium, นอร์ฟล็อกซาซิน) เพราะมีผลข้างเคียงรุนแรงต่อสัตว์"
        ]
    },
    "ซึม": {
        "title": "อาการซึม ไม่ร่าเริง เบื่ออาหาร",
        "urgency": "moderate",
        "urgency_label": "🟡 เฝ้าระวัง (สัญญาณเริ่มต้นของการเจ็บป่วย)",
        "explanation": "สัตว์เลี้ยงมักซ่อนความเจ็บป่วยไว้ เมื่อเริ่มแสดงอาการซึม มักมีความผิดปกติภายใน เช่น มีไข้ ปวดท้อง หรือติดเชื้อ",
        "first_aid": [
            "ตรวจดูอุณหภูมิเบื้องต้น สังเกตว่าตัวร้อน หูร้อน หรือจมูกแห้งผิดปกติไหม",
            "ลองกระตุ้นด้วยขนมหรือของโปรด หากไม่ยอมกินเกิน 24 ชม. ควรพบแพทย์เพื่อเจาะเลือดตรวจ"
        ],
        "donts": [
            "ห้ามให้ยาลดไข้ของคนเด็ดขาด ยาของคนหลายชนิดเป็นพิษร้ายแรงต่อสัตว์เลี้ยง"
        ]
    }
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"aiforthai_api_key": os.environ.get("AIFORTHAI_API_KEY", "")}

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

def evaluate_pet_triage(pet_type, symptoms, details, duration, api_key=None):
    """
    ประเมินอาการสัตว์เลี้ยงด้วย Triage Engine ร่วมกับ AI for Thai
    """
    all_text = f"{pet_type} {' '.join(symptoms)} {details} {duration}".lower()
    
    # 1. ตรวจสอบภาวะฉุกเฉินระดับวิกฤต (Critical)
    critical_match = None
    for kw in PET_TRIAGE_DATABASE["emergency_keywords"]:
        if kw in all_text:
            critical_match = kw
            break

    # 2. ค้นหาคำแนะนำปฐมพยาบาลเฉพาะโรค
    matched_guide = None
    for key, guide in PET_FIRST_AID_GUIDE.items():
        if key in all_text:
            matched_guide = guide
            break

    # 3. หากมี AI Key สามารถเสริมคำแนะนำจาก AI for Thai / Thai LLM ได้
    ai_enhanced_advice = ""
    if not api_key:
        config = load_config()
        api_key = config.get("aiforthai_api_key", "").strip()

    if api_key:
        try:
            import aift
            from aift import setting
            setting.set_api_key(api_key)
            from aift.multimodal import textqa
            prompt = f"สัตว์เลี้ยงชนิด {pet_type} มีอาการ {', '.join(symptoms)} รายละเอียด: {details} ขอคำแนะนำสัตวแพทย์สั้นๆ 2 ประโยค"
            ai_res = textqa.generate(prompt)
            if ai_res:
                ai_enhanced_advice = str(ai_res).strip()
        except Exception as e:
            print(f"[AIFT TextQA Error] {e}")

    # สรุปผลการคัดกรอง
    if critical_match or (matched_guide and matched_guide["urgency"] == "critical"):
        urgency = "critical"
        urgency_label = "🔴 ฉุกเฉินวิกฤต (Emergency - ต้องพบแพทย์ทันที)"
        urgency_color = "red"
        action_summary = "อาการนี้จัดเป็นภาวะฉุกเฉินที่มีอันตรายต่อชีวิต กรุณานำสัตว์เลี้ยงส่งโรงพยาบาลสัตว์ตลอด 24 ชม. ที่ใกล้ที่สุดทันที!"
    elif any(kw in all_text for kw in PET_TRIAGE_DATABASE["urgent_keywords"]) or len(symptoms) >= 3:
        urgency = "urgent"
        urgency_label = "🟡 ความเสี่ยงปานกลาง (Urgent - ควรพบแพทย์ใน 24 ชม.)"
        urgency_color = "amber"
        action_summary = "สัตว์เลี้ยงมีอาการผิดปกติที่ควรได้รับการตรวจวินิจฉัยอย่างละเอียดโดยสัตวแพทย์ ควรนัดหมายพบแพทย์ภายในวันนี้หรือพรุ่งนี้"
    else:
        urgency = "mild"
        urgency_label = "🟢 เฝ้าระวังเบื้องต้น (Mild - ดูแลและสังเกตอาการที่บ้านได้)"
        urgency_color = "emerald"
        action_summary = "อาการเบื้องต้นยังไม่พบสัญญาณอันตรายเฉียบพลัน สามารถดูแลปฐมพยาบาลตามคำแนะนำและเฝ้าดูอาการอย่างใกล้ชิด 24-48 ชม."

    # ดึงข้อมูล Guide
    title = matched_guide["title"] if matched_guide else f"การประเมินอาการเบื้องต้นสำหรับ {pet_type}"
    explanation = matched_guide["explanation"] if matched_guide else f"จากอาการ {', '.join(symptoms) if symptoms else 'ที่ระบุ'} สัตว์เลี้ยงอาจมีความผิดปกติที่ระบบทางเดินอาหาร กล้ามเนื้อ หรือภูมิคุ้มกัน"
    first_aid = matched_guide["first_aid"] if matched_guide else [
        "จัดให้อยู่ในที่เงียบ อบอุ่น มีอากาศถ่ายเทสะดวกและไม่มีสิ่งรบกวน",
        "เตรียมน้ำสะอาดไว้ใกล้ตัว และสังเกตปริมาณการกินน้ำและการขับถ่าย",
        "จดบันทึกเวลาที่เริ่มมีอาการ จำนวนครั้ง และถ่ายรูปอุจจาระหรืออาเจียนไว้ให้สัตวแพทย์ดู"
    ]
    donts = matched_guide["donts"] if matched_guide else [
        "⚠️ ห้ามป้อนยาของคนเด็ดขาด (เช่น พาราเซตามอล แอสไพริน ไอบูโพรเฟน) เพราะเป็นพิษถึงตาย",
        "⚠️ ห้ามบังคับป้อนอาหารแข็งหรือน้ำหากสัตว์เลี้ยงเริ่มหมดสติหรือหายใจลำบาก"
    ]

    return {
        "pet_type": pet_type,
        "symptoms": symptoms,
        "urgency": urgency,
        "urgency_label": urgency_label,
        "urgency_color": urgency_color,
        "title": title,
        "explanation": explanation,
        "action_summary": action_summary,
        "first_aid": first_aid,
        "donts": donts,
        "ai_advice": ai_enhanced_advice or "คำแนะนำเสริมจาก AI: ให้ดูแลความชุ่มชื้นในร่างกายและวัดอุณหภูมิ หากพบอาการซึมลงอย่างรวดเร็วให้รีบพาไปพบแพทย์",
        "mode": "live_api" if ai_enhanced_advice else "triage_engine"
    }


class PetTriageHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            file_path = os.path.join(PUBLIC_DIR, "index.html")
            self.serve_file(file_path, "text/html; charset=utf-8")
        elif path == "/api/status":
            config = load_config()
            has_key = bool(config.get("aiforthai_api_key", "").strip())
            self.send_json({
                "has_api_key": has_key,
                "api_key_masked": (config.get("aiforthai_api_key", "")[:4] + "..." + config.get("aiforthai_api_key", "")[-4:]) if has_key and len(config.get("aiforthai_api_key", "")) > 8 else ("ตั้งค่าแล้ว" if has_key else "")
            })
        elif path.startswith("/public/"):
            rel_path = path.replace("/public/", "", 1)
            file_path = os.path.join(PUBLIC_DIR, rel_path)
            self.serve_static(file_path)
        else:
            file_path = os.path.join(PUBLIC_DIR, path.lstrip("/"))
            if os.path.isfile(file_path):
                self.serve_static(file_path)
            else:
                self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        if path == "/api/save-key":
            try:
                data = json.loads(post_data.decode("utf-8"))
                key = data.get("api_key", "").strip()
                save_config({"aiforthai_api_key": key})
                self.send_json({"success": True, "message": "บันทึก API Key สำเร็จ"})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status=400)

        elif path == "/api/triage":
            try:
                data = json.loads(post_data.decode("utf-8"))
                pet_type = data.get("pet_type", "สุนัข")
                symptoms = data.get("symptoms", [])
                details = data.get("details", "")
                duration = data.get("duration", "ไม่เกิน 24 ชั่วโมง")

                res = evaluate_pet_triage(pet_type, symptoms, details, duration)
                self.send_json({"success": True, "data": res})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status=500)
        else:
            self.send_error(404, "Not Found")

    def serve_file(self, file_path, content_type):
        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, "File not found")

    def serve_static(self, file_path):
        if os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            self.serve_file(file_path, mime_type or "application/octet-stream")
        else:
            self.send_error(404, "Static file not found")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(port=8080):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, PetTriageHandler)
    print("=" * 65)
    print("🐾 Pet AI Triage & First-Aid Assistant Server")
    print(f"👉 เปิดใช้งานที่: http://localhost:{port}")
    print("=" * 65)
    print("กด Ctrl + C เพื่อหยุดการทำงาน")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nหยุดเซิร์ฟเวอร์เรียบร้อย")

if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
