# Surgical Multi-Task AI Assistant

A web-based platform for surgical multi-task scene understanding, focused on endoscopic image analysis.  
The system integrates multiple AI tasks (e.g., activity recognition, detection, and analysis) and provides an interactive interface for real-time inference.

---

## 🚀 Features

- Multi-task surgical scene understanding  
- Endoscopic frame analysis  
- Web-based interactive interface  
- Backend–frontend separation (FastAPI + React)  

---

## 🛠️ Installation

### 1. Clone this repository

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

---

### 2. Install backend dependencies

```bash
pip install -r backend/requirements.txt
```

---

### 3. Download model resources

```bash
git clone https://github.com/gkw0010/EndoARSS.git
```

Place or configure the model files according to your backend settings.

---

## ▶️ Usage

### 1. Start backend

```bash
python main.py
```

Backend runs at: http://127.0.0.1:8000

---

### 2. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://127.0.0.1:5173

---

### 3. Run inference

1. Open the frontend in your browser  
2. Upload an endoscopic image (frame)  
3. Select the desired task(s)  
4. The system will perform multi-task analysis and return results  

---

## 🧠 System Overview

Frontend (React) → Backend (FastAPI) → Multi-task AI Models (EndoARSS) → Visualization

---

## 📌 Notes

- Ensure backend is running before frontend  
- Configure model paths if needed  
- GPU is recommended for better performance  

---

## 🔮 Future Work

- Real-time video analysis  
- Model optimization  
- Better multi-task integration  
- Data persistence  

---

## 📄 License

This project is for academic and research purposes only.
