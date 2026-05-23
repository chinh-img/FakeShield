import tensorflow as tf
import numpy as np
import os
import cv2
import base64

# Đường dẫn tới mô hình image
image_model_path = "./Models/ela_tampering_model.keras"

# Biến global cho mô hình image
image_model = None
THRESHOLD = 0.7 # Ngưỡng phát hiển ảnh giả (tăng để giảm false positive)

def load_image_model():
    global image_model
    if not os.path.exists(image_model_path):
        print(f"Lỗi: Mô hình image '{image_model_path}' không tồn tại.")
        return False

    try:
        image_model = tf.keras.models.load_model(image_model_path)
        print("Mô hình image đã tải thành công!")
        return True
    except Exception as e:
        print(f"Lỗi khi tải mô hình image: {e}")
        return False

def get_image_model():
    global image_model
    return image_model

async def predict_image_tampering(file) -> str:
    global image_model, THRESHOLD
    if image_model is None:
        raise RuntimeError('Mô hình ảnh chưa được tải.')

    content = await file.read()
    image = tf.io.decode_image(content, channels=3, expand_animations=False)

    input_shape = image_model.input_shape
    if input_shape and len(input_shape) >= 4 and input_shape[1] is not None and input_shape[2] is not None:
        target_size = (input_shape[1], input_shape[2])
    else:
        target_size = (224, 224)

    image = tf.image.resize(image, target_size)
    image = tf.cast(image, tf.float32) / 255.0
    image = tf.expand_dims(image, axis=0)

    predictions = image_model.predict(image)
    if predictions.shape[-1] == 1:
        score = float(predictions[0][0])
        # Theo label_mapping: {0: 'Au', 1: 'Tp'}
        # Tính cònidence: càng xa threshold càng tin cậy
        if score < THRESHOLD:
            confidence = 0.5 + (THRESHOLD - score) / 2 # score càng thấp, confidence càng cao
            confidence = min(0.95, max(0.60, confidence))
            return ('Authentic', confidence)
        else:
            confidence = 0.5 + (score - THRESHOLD) / 2
            confidence = min(0.95, max(0.60, confidence))
            return ('Tampered', confidence)
    else:
        label_id = int(np.argmax(predictions, axis=-1)[0])
        confidence = float(np.max(predictions))
        return 'Authentic' if label_id == 0 else 'Tampered', confidence


def generate_ela_image(content: bytes) -> str:
    """Tạo ảnh ELA base64 từ nội dung ảnh gốc."""
    np_img = np.frombuffer(content, np.uint8)
    original = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
    if original is None:
        raise ValueError('Không thể đọc ảnh để tạo ELA')

    _, encoded = cv2.imencode('.jpg', original, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    compressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    ela = cv2.absdiff(original, compressed)
    ela_gray = cv2.cvtColor(ela, cv2.COLOR_BGR2GRAY)
    ela_scaled = cv2.normalize(ela_gray, None, 0, 255, cv2.NORM_MINMAX)
    ela_color = cv2.cvtColor(ela_scaled, cv2.COLOR_GRAY2BGR)

    _, buffer = cv2.imencode('.jpg', ela_color)
    return base64.b64encode(buffer).decode('utf-8')
    

def generate_gradcam_heatmap(model, img_array, last_conv_layer_name='conv2d_3'):
    """Tạo heatmap để khoanh vùng vùng bị chỉnh sửa"""
    
    if last_conv_layer_name is None:
        for layer in reversed(model.layers):
            if 'conv' in layer.name.lower():
                last_conv_layer_name = layer.name
                print(f"Dùng layer: {last_conv_layer_name}")
                break
    if last_conv_layer_name is None:
        raise ValueError("Không tìm thấy conv layer trong model")
    
    # Model mới để lấy gradient
    grad_model = tf.keras.models.Model(
        [model.inputs],
        [model.get_layer(last_conv_layer_name).output, model.output]
    )
    
    with tf.GradientTape() as tape:
        conv_output, predictions = grad_model(img_array)
        if predictions.shape[-1] == 1:
            loss = predictions[:, 0]
        else:
            loss = tf.reduce_max(predictions, axis=-1)
        
    grads = tape.gradient(loss, conv_output)
    if grads is None:
        print("Không tính được gradient")
        return np.zeros((img_array.shape[1], img_array.shape[2]))
    
    weights = tf.reduce_mean(grads, axis=(1,2))
    heatmap = tf.reduce_sum(tf.multiply(weights, conv_output), axis=-1)
    
    # Normalize về [0, 1]
    heatmap = tf.maximum(heatmap, 0)
    max_val = tf.math.reduce_max(heatmap)
    if max_val >  0:
        heatmap = heatmap / max_val
    heatmap = heatmap.numpy()[0]
    
    return heatmap

def overlay_heatmap(original_img, heatmap, alpha=0.5):
    # Resize heatmap to match original image size
    heatmap = cv2.resize(heatmap, (original_img.shape[1], original_img.shape[0]))
    
    heatmap = np.uint8(255 * heatmap)
    heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    
    overlayed = cv2.addWeighted(original_img, alpha, heatmap, 1 - alpha, 0)
    return overlayed
