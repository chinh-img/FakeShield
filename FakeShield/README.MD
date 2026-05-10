# 🛡️ FakeShield - Phát hiện tin giả đa phương thức

Hệ thống sử dụng AI để phân tích **văn bản** và **hình ảnh**, phát hiện tin giả và ảnh bị chỉnh sửa

## 🚀 Cách chạy

### 1. Chạy Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 2. Chạy Frontend
Mở file index.html bằng trình duyệt hoặc dùng live server

## 📊 Chức năng
- Phân loại văn bản: Xác định tin thật/giả từ nội dung
- Phát hiện ảnh chỉnh sửa: Nhận biết ảnh đã bị Photoshop
- Kết hợp đa phương thức: Tổng hợp kết quả từ cả 2 module

## 🧠 Công nghệ
- Text: DistilBERT (fine-tuned trên ISOT dataset)
- Image: ELA + CNN (train trên CASIA 2.0)
- Backend: FastAPI, Python
- Frontend: HTML/CSS/JS

## 📁 Cấu trúc
FakeShield/
|-- backend/
|   |-- app.py
|   |-- news_model.py
|   |-- image_model.py
|   |-- Models/
|   |-- requirements.txt
|-- frontend/
|   |-- index.html
|   |-- styles.css
|   |-- script.js
|-- README.md

## 👨‍🎓 Tác giả
- Hoàng Trọng Chính - Trường THPT Trần Quốc Tuấn