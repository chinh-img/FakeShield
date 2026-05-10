import tensorflow as tf
import numpy as np
import os

# Đường dẫn tới mô hình image
image_model_path = "./Models/ela_tampering_model.keras"

# Biến global cho mô hình image
image_model = None

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

async def predict_image_tampering(file) -> str:
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
        return 'Authentic' if score >= 0.5 else 'Tampered'
    else:
        label_id = int(np.argmax(predictions, axis=-1)[0])
        return 'Authentic' if label_id == 1 else 'Tampered'