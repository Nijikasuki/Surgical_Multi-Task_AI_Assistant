print("Starting app_with_model_and_loading.py...")
import os
import numpy as np
import cv2
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory
import torch
import torch.nn as nn
import torch.nn.functional as F

print("All imports successful")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# 确保上传目录存在
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
    print("Upload directory created")
else:
    print("Upload directory exists")

# 模型定义
def double_conv(in_channels, out_channels):
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, 3, padding=1),
        nn.InstanceNorm2d(out_channels),
        nn.LeakyReLU(0.2, inplace=True),
        nn.Conv2d(out_channels, out_channels, 3, padding=1),
        nn.InstanceNorm2d(out_channels),
        nn.LeakyReLU(0.2, inplace=True),
        nn.Dropout(0.25)
    )

class Encoder(nn.Module):
    def __init__(self, n_class = 1):
        super().__init__()
                
        self.dconv_down1 = double_conv(1, 16)
        self.dconv_down2 = double_conv(16, 32)
        self.dconv_down3 = double_conv(32, 64)
        self.dconv_down4 = double_conv(64, 128)
        self.dconv_down5 = double_conv(128, 256)      
        self.avgpool = nn.AdaptiveAvgPool2d((1,1))       
        self.fc = nn.Linear(256, 2)

        self.maxpool = nn.MaxPool2d(2)

    def forward(self, x):
        conv1 = self.dconv_down1(x)
        x = self.maxpool(conv1)

        conv2 = self.dconv_down2(x)
        x = self.maxpool(conv2)
        
        conv3 = self.dconv_down3(x)
        x = self.maxpool(conv3)   

        conv4 = self.dconv_down4(x)
        x = self.maxpool(conv4)

        conv5 = self.dconv_down5(x)
        x1 = self.maxpool(conv5)
        
        avgpool = self.avgpool(x1)
        avgpool = avgpool.view(avgpool.size(0), -1)
        outC = self.fc(avgpool)
        
        return conv5, conv4, conv3, conv2, conv1, outC

class Decoder(nn.Module):
    def __init__(self, n_class = 1, nonlocal_mode='concatenation', attention_dsample = (2,2)):
        super().__init__()

        self.upsample = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)

        self.dconv_up4 = double_conv(256 + 128 + 2, 128)
        self.dconv_up3 = double_conv(128 + 64, 64)
        self.dconv_up2 = double_conv(64 + 32, 32)
        self.dconv_up1 = double_conv(32 + 16, 16)
        self.conv_last = nn.Conv2d(16, n_class, 1)
        self.conv_last_saliency = nn.Conv2d(17, n_class, 1)

    def forward(self, input, conv5, conv4, conv3, conv2, conv1, saliency):
  
        bridge = torch.cat([input, saliency], dim = 1)
        bridge = nn.functional.interpolate(bridge, scale_factor=0.125, mode='bilinear', align_corners=True)

        x = self.upsample(conv5)        
        x = torch.cat([x, conv4, bridge], dim=1)

        x = self.dconv_up4(x)
        x = self.upsample(x)        
        x = torch.cat([x, conv3], dim=1)       

        x = self.dconv_up3(x)
        x = self.upsample(x)        
        x = torch.cat([x, conv2], dim=1)

        x = self.dconv_up2(x)
        x = self.upsample(x)        
        x = torch.cat([x, conv1], dim=1) 

        x = self.dconv_up1(x)
        
        out = self.conv_last(x)
        
        return out

class MultiMix(nn.Module):
    def __init__(self, n_class = 1):
        super().__init__()

        self.encoder = Encoder(1)
        self.decoder = Decoder(1)
        
    def forward(self, x):
        # 简化版本，不使用 generate_saliency
        conv5, conv4, conv3, conv2, conv1, outC = self.encoder(x)
        # 创建一个假的 saliency 张量
        saliency = torch.zeros_like(x)
        outSeg = self.decoder(x, conv5, conv4, conv3, conv2, conv1, saliency)

        return outSeg, outC

# 加载模型
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

print("Creating MultiMix model...")
model = MultiMix(1).to(device)
print("Model created successfully")

# 加载预训练模型
checkpoint_path = 'MultiMix/sample_data/multimix_trained_model.pth'
print(f"Loading model from: {checkpoint_path}")
try:
    if os.path.exists(checkpoint_path):
        print("Model file exists, loading...")
        model.load_state_dict(torch.load(checkpoint_path, map_location=device))
        model.eval()
        print("Model loaded successfully!")
    else:
        print(f"Model file not found: {checkpoint_path}")
except Exception as e:
    print(f"Error loading model: {e}")
    import traceback
    traceback.print_exc()

# 图像变换函数，不使用 torchvision
def transform_image(img):
    # 转换为灰度图
    img = img.convert('L')
    # 调整大小为 256x256
    img = img.resize((256, 256))
    # 转换为 numpy 数组
    img_array = np.array(img)
    # 归一化到 [0, 1]
    img_array = img_array / 255.0
    # 转换为 torch 张量
    img_tensor = torch.tensor(img_array, dtype=torch.float32)
    # 添加通道维度和批次维度
    img_tensor = img_tensor.unsqueeze(0).unsqueeze(0)
    return img_tensor

# 静态文件服务
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# 预测 API
@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    
    # 处理文件名，去除空格
    original_filename = file.filename
    print(f"Original file filename: '{original_filename}'")
    print(f"Original file filename length: {len(original_filename)}")
    
    # 去除文件名中的空格
    cleaned_filename = original_filename.replace(' ', '_')
    print(f"Cleaned file filename: '{cleaned_filename}'")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    # 保存上传的文件
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], cleaned_filename)
    print(f"Saving file to: {filepath}")
    print(f"Upload folder absolute path: {os.path.abspath(app.config['UPLOAD_FOLDER'])}")
    
    # 确保上传目录存在
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        print("Upload directory created")
    else:
        print("Upload directory exists")
    
    file.save(filepath)
    
    # 检查文件是否存在
    if os.path.exists(filepath):
        print(f"File saved successfully: {os.path.getsize(filepath)} bytes")
        print(f"File absolute path: {os.path.abspath(filepath)}")
    else:
        print("Error: File not saved")
    
    # 列出上传目录中的文件
    print("Files in upload directory:")
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        print(f"  - {filename}")
    
    # 处理图像
    img = Image.open(filepath)
    img_tensor = transform_image(img).to(device)
    
    # 预测
    with torch.no_grad():
        outSeg, outC = model(img_tensor)
        
        # 分类结果
        _, predicted = torch.max(outC.data, 1)
        class_result = 'PNEUMONIA' if predicted.item() == 1 else 'NORMAL'
        
        # 分割结果
        pred = torch.sigmoid(outSeg)
        pred = pred.data.cpu().numpy()[0, 0]
        pred = (pred > 0.5).astype(np.uint8) * 255
        
        # 保存分割结果
        seg_filename = 'seg_' + cleaned_filename
        print(f"Segmented filename: '{seg_filename}'")
        seg_filepath = os.path.join(app.config['UPLOAD_FOLDER'], seg_filename)
        print(f"Saving segmented file to: {seg_filepath}")
        cv2.imwrite(seg_filepath, pred)
        
        # 检查分割文件是否存在
        if os.path.exists(seg_filepath):
            print(f"Segmented file saved successfully: {os.path.getsize(seg_filepath)} bytes")
        else:
            print("Error: Segmented file not saved")
    
    # 构建响应
    original_image_url = f'/static/uploads/{cleaned_filename}'
    segmented_image_url = f'/static/uploads/{seg_filename}'
    
    # 确保URL中没有空格
    original_image_url = original_image_url.replace(' ', '')
    segmented_image_url = segmented_image_url.replace(' ', '')
    
    print(f"Original image URL: '{original_image_url}'")
    print(f"Segmented image URL: '{segmented_image_url}'")
    
    response_data = {
        'original_image': original_image_url,
        'segmented_image': segmented_image_url,
        'prediction': class_result
    }
    print(f"Response data: {response_data}")
    
    return jsonify(response_data)

# 健康检查
@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

# 主页面
@app.route('/')
def index():
    return send_from_directory('app/templates', 'index.html')

print("All setup complete, ready to run app...")
if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True, host='127.0.0.1', port=5001)