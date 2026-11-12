import tensorflow as tf
import json
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

DATASET_DIR = '/Users/dhyandevaiah/AgroDirect_ML_Dataset' # ⚠️ Check this path!
IMG_SIZE = (224, 224)
BATCH_SIZE = 32

print("Loading dataset...")
train_dataset = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR, validation_split=0.2, subset="training", seed=42,
    image_size=IMG_SIZE, batch_size=BATCH_SIZE)
val_dataset = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR, validation_split=0.2, subset="validation", seed=42,
    image_size=IMG_SIZE, batch_size=BATCH_SIZE)

class_names = train_dataset.class_names
# Save class names so app.py always knows the exact order!
json.dump(class_names, open('class_names.json', 'w'))
print(f"Classes found and saved: {class_names}")

# Data Augmentation (Makes the model immune to different backgrounds)
data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal_and_vertical"),
    layers.RandomRotation(0.2),
    layers.RandomZoom(0.2),
    layers.RandomBrightness(0.2),
    layers.RandomContrast(0.2)
])

# Build Model
base = MobileNetV2(input_shape=IMG_SIZE + (3,), include_top=False, weights="imagenet")
base.trainable = False

inputs = layers.Input(shape=IMG_SIZE + (3,))
x = data_augmentation(inputs)
x = layers.Rescaling(1./127.5, offset=-1)(x) # Built-in preprocessing to fix the bug!
x = base(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.3)(x)
outputs = layers.Dense(len(class_names), activation="softmax")(x)
model = models.Model(inputs, outputs)

model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
              loss="sparse_categorical_crossentropy", metrics=["accuracy"])

print("Starting Training (Phase 1)...")
model.fit(train_dataset, validation_data=val_dataset, epochs=5)

# Phase 2: Fine-Tuning
print("Starting Fine-Tuning (Phase 2)...")
base.trainable = True
for layer in base.layers[:-30]:
    layer.trainable = False

model.compile(optimizer=tf.keras.optimizers.Adam(1e-5),
              loss="sparse_categorical_crossentropy", metrics=["accuracy"])
model.fit(train_dataset, validation_data=val_dataset, epochs=5)

model.save('leaf_disease_model.keras')
print("Success! Model saved.")