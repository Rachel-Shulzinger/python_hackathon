import os
import json
import google.generativeai as genai
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# ייבוא הפרומפט הכללי מהקובץ שלך
try:
    from general_prompt import GENERIC_RULES as GENERAL_PROMPT
except ImportError:
    GENERAL_PROMPT = "חוקי סימולציה כלליים חסרים."

# טעינת משתני סביבה (מפתח API וכתובת שרת היעד)
load_dotenv()

# הגדרת מפתח ה-API של Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)

@app.route('/process-simulation', methods=['POST'])
def process_and_forward():
    try:
        # 1. קבלת כל ה-JSON שמגיע מה-React
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "לא התקבלו נתונים בבקשה"}), 400

        # 2. חילוץ בטוח של הנתונים העיקריים לשימוש פנימי (Metadata)
        # אנחנו משתמשים ב-.get() כדי למנוע קריסה אם שדה מסוים חסר
        # customer_name = data.get('customerName', 'לקוח')
        # reason = data.get('reason', 'לא צוין')
        
        # 3. בניית ה-Meta-Prompt עבור Gemini
        # כאן אנחנו שולחים את כל ה-data (כולל שאלות, פוליסה, וכל מה שיש ב-JSON)
        meta_prompt = f"""
        אתה מומחה להנדסת פרומפטים. עליך ליצור פרומפט מערכת (System Prompt) סופי לסימולציה.
        
        להלן חוקי הסימולציה הכלליים (הבסיס):
        {GENERAL_PROMPT}
        
        להלן נתוני התרחיש הספציפיים שקיבלנו (הטמע אותם בתוך החוקים):
        {json.dumps(data, ensure_ascii=False, indent=2)}
        
        המשימה שלך:
        צור פרומפט אחד מלוכד שבו ה-AI יודע בדיוק מי הוא, מה הסיפור שלו ומה החוקים עליהם הוא חייב לשמור.
        החזר אך ורק את הפרומפט הסופי, ללא הקדמות, ללא סימני Markdown (כמו ```) וללא הסברים.
        """

        # 4. הגדרות המודל (טמפרטורה נמוכה לדיוק מקסימלי)
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "max_output_tokens": 4096, # הגדלתי כדי שיהיה מקום לפרומפט ארוך
        }

        model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            generation_config=generation_config
        )

        # 5. יצירת הפרומפט המדויק באמצעות Gemini
        response = model.generate_content(meta_prompt)
        
        if not response.text:
            raise ValueError("הבינה המלאכותית לא הצליחה לייצר תוכן.")
            
        precise_prompt = response.text.strip()

        # 6. בניית האובייקט הסופי למשלוח
        final_payload = {
            "final_prompt": precise_prompt,
            "status": "ready",
            "metadata": {
                "customer": customer_name,
                "reason": reason,
                "raw_data_received": data # שומרים את הנתונים המקוריים לגיבוי
            },
            "generation_response": precise_prompt
        }

        # כאן את יכולה להפעיל את השליחה לשרת הבא במידת הצורך:
        # requests.post(os.getenv("OTHER_SERVER_URL"), json=final_payload)

        # 7. החזרת התוצאה ל-React
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
