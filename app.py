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

# טעינת משתני סביבה (מפתח API)
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

        # 2. בניית ה-Meta-Prompt עבור Gemini
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

        # 3. הגדרות המודל (טמפרטורה נמוכה לדיוק מקסימלי)
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "max_output_tokens": 4096,
        }

        model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            generation_config=generation_config
        )

        # 4. יצירת הפרומפט המדויק באמצעות Gemini
        response = model.generate_content(meta_prompt)
        
        if not response.text:
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