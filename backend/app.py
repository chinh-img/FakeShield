from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional
import base64
import cv2
import numpy as np
import requests
from bs4 import BeautifulSoup
import io, os
import tempfile

# Import các model riêng
from news_model import load_news_model, predict_news_type
from image_model import load_image_model, predict_image_tampering, get_image_model, generate_gradcam_heatmap, overlay_heatmap, generate_ela_image

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

# ============================= REQUEST/RESPONSE MODELS =============================
class PredictionRequest(BaseModel):
    text: str

class PredictionResponse(BaseModel):
    prediction: str
    confidence: Optional[float] = None

class CombinedResponse(BaseModel):
    news_prediction: str
    image_prediction: str
    final_verdict: str
    confidence: float
    reason: str
    news_confidence: Optional[float] = None
    image_confidence: Optional[float] = None
    ela_image: Optional[str] = None
    heatmap_image: Optional[str] = None
    image_description: Optional[str] = None
    text_description: Optional[str] = None

# ============================= ENDPOINTS =============================

@app.post("/predictnews", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    prediction, confidence = predict_news_type(request.text)
    return PredictionResponse(prediction=prediction, confidence=confidence)

@app.post("/predictimage", response_model=PredictionResponse)
async def predict_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='File phải là ảnh.')

    try:
        prediction, confidence = await predict_image_tampering(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return PredictionResponse(prediction=prediction, confidence=confidence)

@app.post("/predicturl")
async def predict_from_url(url: str = Form(...)):
    try:
        # Dùng requests + BeautifulSoup thay vì newspaper
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Lấy title
        title = soup.find('title')
        title = title.get_text().strip() if title else "Không có tiêu đề"
        
        # Lấy nội dung text
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator='\n')
        text = '\n'.join([line.strip() for line in text.splitlines() if line.strip()])
        
        combined_text = title + ". " + text
        if len(combined_text) > 1000:
            combined_text = combined_text[:1000]
            print(f"📝 Đã cắt text xuống 1000 ký tự")
        
        print(f"📝 Text length: {len(combined_text)} chars")
        
        # Phân tích văn bản
        if len(combined_text) < 100:
            news_prediction = "No text"
            news_confidence = 0.0
        else:
            news_prediction, news_confidence = predict_news_type(combined_text)
        
        # Lấy ảnh đại diện
        top_image = None
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            top_image = og_image['content']
        
        # Phân tích ảnh (nếu có)
        image_result = "No image"
        image_confidence = 0.0
        if top_image:
            try:
                img_response = requests.get(top_image, timeout=10)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                    tmp.write(img_response.content)
                    tmp_path = tmp.name
                
                with open(tmp_path, 'rb') as f:
                    fake_file = UploadFile(filename='image.jpg', file=f)
                    image_result, image_confidence = await predict_image_tampering(fake_file)
                os.unlink(tmp_path)
            except Exception as e:
                print(f"Lỗi tải ảnh: {e}")
        
        # Kết luận
        if news_prediction == "Fake" or image_result == "Tampered":
            final_verdict = "FAKE"
            if news_prediction == "Fake" and image_result == "Tampered":
                confidence = 0.95
            elif news_prediction == "Fake":
                confidence = 0.85
            else:
                confidence = 0.80
            reason = "Phát hiện dấu hiệu bất thường trong nội dung hoặc hình ảnh"
        elif news_prediction == "Real" and image_result == "Authentic":
            final_verdict = "REAL"
            confidence = (news_confidence + image_confidence) / 2
            reason = "Nội dung và hình ảnh đều hợp lệ"
        else:
            final_verdict = "SUSPICIOUS"
            confidence = 0.60
            reason = "Kết quả phân tích không rõ ràng, cần kiểm tra thêm"
        
        return {
            "title": title,
            "url": url,
            "news_prediction": news_prediction,
            "image_prediction": image_result,
            "final_verdict": final_verdict,
            "confidence": confidence,
            "reason": reason,
            "text_preview": combined_text[:300] + "..." if len(combined_text) > 300 else combined_text,
            "top_image": top_image
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Không thể tải URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi phân tích: {str(e)}")

@app.post("/predictcombined", response_model=CombinedResponse)
async def predict_combined(image: UploadFile = File(None), text: Optional[str] = Form(None)):
    news_result = None
    news_confidence = 0.0
    image_result = None
    image_confidence = 0.0
    ela_base64 = None
    heatmap_base64 = None
    
    # Phân tích văn bản (nếu có)
    if text and text.strip():
        try:
            # ✅ XỬ LÝ TEXT: Cắt bớt nếu quá dài
            if len(text) > 2000:
                text = text[:2000]
                print(f"📝 Đã cắt text xuống 2000 ký tự")
            news_result, news_confidence = predict_news_type(text)
        except Exception as e:
            news_result = "Error"
            print(f"Lỗi phân tích văn bản: {e}")
    
    # Phân tích ảnh (nếu có)
    if image and image.filename:
        try:
            image_result, image_confidence = await predict_image_tampering(image)
        except Exception as e:
            image_result = "Error"
            print(f"Lỗi phân tích ảnh: {e}")

    # Tạo ELA và heatmap (nếu có ảnh)
    if image and image.filename:
        try:
            await image.seek(0)
            content = await image.read()
            
            # Tạo ảnh ELA
            ela_base64 = generate_ela_image(content)
            
            # Tạo heatmap Grad-CAM
            nparr = np.frombuffer(content, np.uint8)
            original_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if original_image is not None:
                image_model = get_image_model()
                if image_model is not None:
                    input_shape = image_model.input_shape
                    if input_shape and len(input_shape) >= 4 and input_shape[1] is not None and input_shape[2] is not None:
                        target_size = (input_shape[1], input_shape[2])
                    else:
                        target_size = (128, 128)
                    
                    img_resized = cv2.resize(original_image, target_size)
                    img_array = np.expand_dims(img_resized / 255.0, axis=0).astype(np.float32)
                    
                    heatmap = generate_gradcam_heatmap(image_model, img_array)
                    overlaid = overlay_heatmap(original_image, heatmap, alpha=0.4)
                    
                    _, buffer = cv2.imencode('.jpg', overlaid)
                    heatmap_base64 = base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            print(f"Lỗi tạo heatmap hoặc ELA: {e}")
    
    # ========== PHÁN QUYẾT THÔNG MINH HƠN ==========
    verdict = "REAL"
    confidence = 0.0
    reason = ""
    
    print(f"📊 News: {news_result} ({news_confidence:.2f}), Image: {image_result} ({image_confidence:.2f})")
    
    # TH1: Cả 2 đều có kết quả
    if news_result and image_result and news_result != "Error" and image_result != "Error":
        if news_result == "Fake" and image_result == "Tampered":
            verdict = "FAKE"
            confidence = 0.95
            reason = "Cả văn bản và hình ảnh đều có dấu hiệu giả mạo"
        elif news_result == "Fake":
            verdict = "FAKE"
            confidence = 0.85
            reason = "Nội dung văn bản có dấu hiệu là tin giả"
        elif image_result == "Tampered" and image_confidence > 0.75:
            verdict = "FAKE"
            confidence = 0.80
            reason = "Hình ảnh có dấu hiệu bị chỉnh sửa đáng kể"
        elif image_result == "Tampered":
            # Trường hợp ảnh báo Tampered nhưng confidence thấp (ảnh điện thoại)
            verdict = "SUSPICIOUS"
            confidence = 0.65
            reason = "Hình ảnh có thể bị ảnh hưởng bởi xử lý từ thiết bị, cần kiểm tra thêm"
        elif news_result == "Real" and image_result == "Authentic":
            verdict = "REAL"
            confidence = (news_confidence + image_confidence) / 2
            reason = "Cả văn bản và hình ảnh đều hợp lệ"
        else:
            verdict = "SUSPICIOUS"
            confidence = 0.60
            reason = "Kết quả phân tích không rõ ràng, cần kiểm tra thêm"
            
    # TH2: Chỉ có văn bản
    elif news_result and news_result != "Error":
        if news_result == "Fake":
            verdict = "FAKE"
            confidence = news_confidence
            reason = "Nội dung văn bản có dấu hiệu là tin giả"
        elif news_result == "Real":
            verdict = "REAL"
            confidence = news_confidence
            reason = "Nội dung văn bản có vẻ hợp lệ"
    
    # TH3: chỉ có ảnh
    elif image_result and image_result != "Error":
        if image_result == "Tampered" and image_confidence > 0.75:
            verdict = "FAKE"
            confidence = image_confidence
            reason = "Hình ảnh có dấu hiệu bị chỉnh sửa đáng kể"
        elif image_result == "Tampered":
            verdict = "SUSPICIOUS"
            confidence = 0.65
            reason = "Hình ảnh có thể bị ảnh hưởng bởi xử lý từ thiết bị, cần kiểm tra thêm"
        else:
            verdict = "REAL"
            confidence = image_confidence
            reason = "Hình ảnh có vẻ hợp lệ"
    
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
        news_confidence=news_confidence if news_result and news_result != "Error" else None,
        image_confidence=image_confidence if image_result and image_result != "Error" else None,
        ela_image=ela_base64,
        heatmap_image=heatmap_base64,
        image_description='Phân tích dựa trên ELA',
        text_description='Phân tích dựa trên mô hình BERT fine-tuned'
    )
    
@app.get("/")
async def home():
    return {
        "message": "FakeShield API đang chạy",
        "endpoints": {
            "/predictnews": "POST - Phân loại văn bản",
            "/predictimage": "POST - Phát hiện ảnh chỉnh sửa",
            "/predictcombined": "POST - Kết hợp cả 2",
            "/predicturl": "POST - Phân tích từ URL"
        }
    }

if __name__ == '__main__':
    uvicorn.run("app:app", host='0.0.0.0', port=5000, reload=True)