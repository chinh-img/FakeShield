from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional
import base64
import cv2
import numpy as np

# Import các model riêng
from news_model import load_news_model, predict_news_type
from image_model import load_image_model, predict_image_tampering

app = FastAPI(title="FakeShield API", description="API phát hiện tin giả đa phương thức", version="1.0.0")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tải mô hình khi ứng dụng khởi động
@app.on_event("startup")
async def startup_event():
    load_news_model()
    load_image_model()


# ============================= 1. REQUEST/ RESPONSE MODELS =============================
class PredictionRequest(BaseModel):
    text: str

class PredictionResponse(BaseModel):
    prediction: str

class CombinedResponse(BaseModel):
    news_prediction: str
    image_prediction: str
    final_verdict: str
    confidence: float
    ela_image: Optional[str] = None
    image_description: Optional[str] = None
    text_description: Optional[str] = None

@app.post("/predictnews", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    prediction = predict_news_type(request.text)
    return PredictionResponse(prediction=prediction)

@app.post("/predictimage", response_model=PredictionResponse)
async def predict_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='File phải là ảnh.')

    try:
        prediction = await predict_image_tampering(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return PredictionResponse(prediction=prediction)

@app.post("/predictcombined", response_model=CombinedResponse)
async def predict_combined(image: UploadFile = File(None), text: Optional[str] = Form(None)):
    news_result = None # Phân tích văn bản (nếu có)
    if text and text.strip():
        try:
            news_result = predict_news_type(text)
        except Exception as e:
            news_result = "Error"
            print(f"Lỗi phân tích văn bản: {e}")
    
    image_result = None # Phân tích ảnh (nếu có)
    if image and image.filename:
        try:
            image_result = await predict_image_tampering(image)
        except Exception as e:
            image_result = "Error"
            print(f"Lỗi phân tích ảnh: {e}")
            
    # Phán quyết
    verdict = "REAL"
    confidence = 0.0
    reason = ""
    
    # TH1: Cả 2 đều có kết quả
    if news_result and image_result:
        if news_result == "Fake" and image_result == "Tampered":
            verdict = "Fake"
            confidence = 0.95
            reason = "Cả văn bản và hình ảnh đều có dấu hiệu giả mạo. Độ tin cậy rất thấp"
        elif news_result == "Fake":
            verdict = "Fake"
            confidence = 0.85
            reason = "Nội dung văn bản có dấu hiệu là tin giả, dù ảnh chưa phát hiện vấn đề"
        elif image_result == "Tampered":
            verdict = "Fake"
            confidence = 0.8
            reason = "Hình ảnh có dấu hiệu bị chỉnh sửa, nội dung văn bản cần kiểm tra thêm"
        elif news_result == "Real" and image_result == "Authentic":
            verdict = "Real"
            confidence = 0.75
            reason = "Nội dung văn bản có độ tin cậy cao, hình ảnh bình thường"
        else:
            verdict = "SUSPICIOUS"
            confidence = 0.55
            reason = "Kết quả phân tích không rõ ràng, cần kiểm tra thêm từ nguồn khác"

    # TH2: Chỉ có văn bản
    elif news_result:
        if news_result == "Fake":
            verdict = "FAKE"
            confidence = 0.85
            reason = "Văn bản có dấu hiệu tin giả. (Không có ảnh để phân tích)"
        else:
            verdict = "REAL"
            confidence = 0.75
            reason = "Văn bản có độ tin cậy cao. (Không có ảnh để phân tích)"
            
    # TH3: Chỉ có ảnh
    elif image_result:
        if image_result == "Tampered":
            verdict = "FAKE"
            confidence = 0.80
            reason = "Hình ảnh có dấu hiệu bị chỉnh sửa. (Không có văn bản để phân tích)"
        else:
            verdict = "REAL"
            confidence = 0.70
            reason = "Hình ảnh hợp lệ, không phát hiện chỉnh sửa. (Không có văn bản để phân tích)"
            
    #TH4: không có dữ liệu
    else:
        verdict = "SUSPICIOUS"
        confidence = 0.0
        reason = "Không có dữ liệu để phân tích"
    return CombinedResponse(
        news_prediction=news_result or "No text provided",
        image_prediction=image_result or "No image provided",
        final_verdict=verdict,
        confidence=confidence,
        reason=reason,
        image_description='Phân tích dựa trên Error Level Analysis (ELA)',
        text_description='Phân tích dựa trên mô hình BERT fine-tuned'
    )
@app.get("/")
async def home():
    return {
        "message": "FakeShield API đang chạy",
        "endpoints":{
            "/predictnews": "POST: Phân loại văn bản tin thật/giả",
            "/predictimage": "POST: Phát hiện ảnh bị chỉnh sửa (gửi file)",
            "/predictioncombined": "POST: Kết hợp cả 2 (gửi text + file)"
        }
    }

if __name__ == '__main__':
    uvicorn.run("app:app", host='0.0.0.0', port=5000, reload=True)