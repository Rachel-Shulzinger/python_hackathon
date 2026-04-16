import os
import json
import google.generativeai as genai
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# טעינת משתני סביבה (מפתח API)
load_dotenv()

# ייבוא הפרומפט הכללי מהקובץ שלך
try:
    from general_prompt import GENERIC_RULES as GENERAL_PROMPT
except ImportError:
    GENERAL_PROMPT = "חוקי סימולציה כלליים חסרים."

# הגדרת מפתח ה-API של Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)

@app.route('/process-simulation', methods=['POST'])
def process_and_forward():
    try:
        print(f"--- בקשה חדשה התקבלה! נתונים גולמיים: {request.data.decode('utf-8')} ---")
        # 1. קבלת כל ה-JSON שמגיע מה-React
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "לא התקבלו נתונים בבקשה"}), 400

        # 2. בניית ה-Meta-Prompt עבור Gemini
        meta_prompt = f"""
אתה סופר-אנליסט של מערכות למידה. המשימה שלך היא ליצור את ה-"SYSTEM PROMPT" האולטימטיבי עבור סימולציית שירות לקוחות.

קריטי: עליך למזג את שני המקורות הבאים ללא איבוד של אף פסיק או הנחיה טכנית.

1. חוקי הברזל והמשוב (חובה להעתיק את כל סעיפי הניקוד וה-JSON):
{GENERAL_PROMPT}

2. נתוני הדמות והתרחיש הספציפיים (הטמע אותם כזהות הלקוח):
{json.dumps(data, ensure_ascii=False, indent=2)}

הנחיות מחייבות ליצירת הפרומפט הסופי:
- איסור השמטה: אל תקצר, אל תסכם ואל תשמיט אף אחד מ-5 שלבי המשוב או כללי ניהול השיחה (כמו פנייה ראשונה ב"שלום" בלבד).
- זהות אחת: הפרומפט הסופי צריך להיכתב כהנחיה ישירה ל-AI (גוף שני - "אתה הלקוח").
- שילוב נתונים: הטמע את הפרטים מה-JSON (שם, פוליסה, בעיה) בתוך סעיפי התפקיד של הלקוח.
- פורמט סיום: ודא שההנחיה להחזיר JSON בסוף השיחה מופיעה בצורה מודגשת וברורה בסוף הפרומפט שאתה מייצר.

החזר אך ורק את טקסט הפרומפט המאוחד, ללא הקדמות, ללא Markdown וללא הערות שוליים.
"""

        # 3. הגדרות המודל (שימוש ב-Gemini 1.5 Flash)
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "max_output_tokens": 4096,
        }

        # model = genai.GenerativeModel(
        #     model_name="gemini-1.5-flash",
        #     generation_config=generation_config
        # )

        model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", # זה תמיד עובד
       generation_config=generation_config
      )

        # 4. יצירת הפרומפט המדויק באמצעות Gemini
        response = model.generate_content(meta_prompt)
        
        if not response or not response.text:
            raise ValueError("הבינה המלאכותית לא הצליחה לייצר תוכן.")
            
        precise_prompt = response.text.strip()

        # 5. בניית האובייקט הסופי למשלוח
        final_payload = {
            "final_prompt": precise_prompt,
            "status": "ready",
            "metadata": {
                "raw_data_received": data 
            },
            "generation_response": precise_prompt
        }

        # 6. החזרת התוצאה ל-React
        return jsonify({
            "status": "success",
            "message": "The precise prompt has been generated successfully.",
            "data": final_payload
        }), 200

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": "חלה שגיאה בעיבוד הנתונים",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    # הרצת השרת על פורט 5000
    app.run(host='0.0.0.0', port=5000, debug=True)