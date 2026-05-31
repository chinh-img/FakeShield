import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

# Đường dẫn tới thư mục mô hình text
news_model_dir = "./Models/fine_tuned_model"

# Biến global cho mô hình text
loaded_tokenizer = None
loaded_model = None

def load_news_model():
    global loaded_tokenizer, loaded_model
    if not os.path.exists(news_model_dir):
        print(f"Lỗi: Thư mục mô hình text '{news_model_dir}' không tồn tại.")
        return False

    try:
        loaded_tokenizer = AutoTokenizer.from_pretrained(news_model_dir)
        loaded_model = AutoModelForSequenceClassification.from_pretrained(news_model_dir)
        loaded_model.eval()
        print("Mô hình text và tokenizer đã tải thành công!")
        return True
    except Exception as e:
        print(f"Lỗi khi tải mô hình text hoặc tokenizer: {e}")
        return False

def predict_news_type(text: str, threshold: float = 0.40) -> str:
    if loaded_tokenizer is None or loaded_model is None:
        raise RuntimeError('Mô hình text chưa được tải.')

    inputs = loaded_tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)

    with torch.no_grad():
        outputs = loaded_model(**inputs)
        
    logits = outputs.logits
    probs = torch.softmax(logits, dim=-1)

    fake_prob = probs[0][0].item()
    real_prob = probs[0][1].item()
    
    print(f"Text probs - Fake: {fake_prob:.4f}, Real: {real_prob:.4f}")
    
    #label_map = {0: 'Fake', 1: 'Real'}
    if real_prob > threshold:
        return ('Real', real_prob)
    else:
        return ('Fake', fake_prob)