"""
Standalone test: detect + crop face, THEN run EfficientNet-B4 inference.
This matches how the 140k-real-and-fake-faces training images were framed
(tight, centered face crops) instead of feeding the model a raw, uncropped photo.
"""
import sys
import torch
import timm
import mediapipe as mp
import numpy as np
from torchvision import transforms
from PIL import Image

def detect_and_crop_face(image_path, margin=0.3):
    """
    Detect the face using MediaPipe and crop a square region around it,
    with a margin so we don't cut off chin/forehead — similar to how
    face datasets are typically framed.
    """
    mp_face_detection = mp.solutions.face_detection
    img = Image.open(image_path).convert('RGB')
    img_np = np.array(img)
    h, w, _ = img_np.shape

    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as fd:
        results = fd.process(img_np)

        if not results.detections:
            print(f"  WARNING: no face detected in {image_path}, falling back to center crop")
            side = min(h, w)
            top = (h - side) // 2
            left = (w - side) // 2
            return img.crop((left, top, left + side, top + side))

        # Use the first detected face
        bbox = results.detections[0].location_data.relative_bounding_box
        x = int(bbox.xmin * w)
        y = int(bbox.ymin * h)
        box_w = int(bbox.width * w)
        box_h = int(bbox.height * h)

        # Add margin around the face box
        mx = int(box_w * margin)
        my = int(box_h * margin)
        x1 = max(0, x - mx)
        y1 = max(0, y - my)
        x2 = min(w, x + box_w + mx)
        y2 = min(h, y + box_h + my)

        # Make it square (crop to the smaller of width/height around center)
        crop_w, crop_h = x2 - x1, y2 - y1
        side = max(crop_w, crop_h)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        x1 = max(0, cx - side // 2)
        y1 = max(0, cy - side // 2)
        x2 = min(w, x1 + side)
        y2 = min(h, y1 + side)

        return img.crop((x1, y1, x2, y2))


def main(image_path):
    checkpoint = torch.load('efficientnet_b4_deepfake.pth', map_location='cpu')
    model = timm.create_model('efficientnet_b4', pretrained=False, num_classes=2)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    classes = checkpoint['classes']

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    print(f"Processing {image_path}...")
    cropped = detect_and_crop_face(image_path)
    cropped.save('debug_cropped_face.jpg')  # so you can visually check the crop
    print(f"  Cropped size: {cropped.size} (saved as debug_cropped_face.jpg — open it to check)")

    tensor = transform(cropped).unsqueeze(0)
    with torch.no_grad():
        output = model(tensor)
        probs = torch.softmax(output, dim=1)[0]

    print("  Prediction:")
    for i, c in enumerate(classes):
        print(f"    {c}: {probs[i].item()*100:.2f}%")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_with_crop.py <image_path>")
        sys.exit(1)
    main(sys.argv[1])