
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import asyncio
import io
import os
from dotenv import load_dotenv
import edge_tts

# 1. מייבאים את הספרייה של ג'מיני במקום זו של OpenAI
import google.generativeai as genai

# טעינת המשתנים מקובץ ה-.env לתוך סביבת הריצה
load_dotenv()

# 2. מגדירים את מפתח ה-API של גוגל
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 3. כאן בדיוק מגדירים את המודל!
model = genai.GenerativeModel('gemini-3-flash-preview')

app = FastAPI()

async def process_stt_hebrew(audio_bytes: bytes) -> str:
    print("STT Processing with Gemini...") # לוג התחלה
    try:
        # שולחים את האודיו ל-Gemini יחד עם הנחיה לתמלל
        response = await model.generate_content_async([
            {"mime_type": "audio/webm", "data": audio_bytes},
            "תמלל את ההקלטה הבאה לעברית במדויק. החזר רק את הטקסט המתומלל ללא שום תוספות."
        ])
        print(f"STT Result: {response.text}") # לוג תוצאה
        return response.text
    except Exception as e:
        print(f"Error during STT: {e}")
        return "סליחה, לא הצלחתי להבין את ההקלטה."

async def process_llm(text: str) -> str:
    print("Sending to LLM...") # לוג התחלה
    try:
        # אנו מצרפים את הוראות המערכת לבקשה של המשתמש
        prompt = f"הוראות מערכת: אתה נציג שירות לקוחות קולי. ענה בקצרה, לעניין ובעברית בלבד.\n\nדברי הלקוח: {text}"
        
        response = await model.generate_content_async(prompt)
        answer = response.text
        
        print(f"AI Response: {answer}") # לוג תוצאה
        return answer
    except Exception as e:
        print(f"Error in LLM: {e}")
        return "הייתה שגיאה בעיבוד התשובה."

async def process_tts_hebrew(text: str) -> bytes:
    print("Generating Audio with Edge-TTS...") # לוג התחלה
    try:
        # משתמשים בקול הגברי של אברי (אפשר להחליף ל "he-IL-HilaNeural" לקול נשי)
        communicate = edge_tts.Communicate(text, "he-IL-AvriNeural")
        
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
                
        print(f"Audio Ready - Size: {len(audio_bytes)} bytes") # לוג הצלחה
        return audio_bytes
    except Exception as e:
        print(f"Error in TTS: {e}")
        return b""

@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 1. קבלת מקטע האודיו מהלקוח (React)
            audio_bytes = await websocket.receive_bytes()

            #---------------------------------
            print(f"---> DEBUG: Raw data received! Size: {len(audio_bytes)} bytes", flush=True)
            #---------------------------------
            
            # 2. המרה לטקסט (STT)
            user_text = await process_stt_hebrew(audio_bytes)
            
            # 3. עיבוד שפה טבעית ויצירת תגובה (LLM)
            ai_response_text = await process_llm(user_text)

            # 4. המרה חזרה לקול (TTS)
            ai_audio_bytes = await process_tts_hebrew(ai_response_text)           

            # 5. שליחת האודיו המוכן חזרה ללקוח
            await websocket.send_bytes(ai_audio_bytes)
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)