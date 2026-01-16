# <svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><title>Hackaday</title><path d="M0 4.124c0-.204.021-.401.06-.595l1.956 1.734 2.144-2.38L2.246 1.18c.259-.072.53-.114.812-.114a3.062 3.062 0 0 1 3.058 3.037v.021c0 .152-.012.304-.033.45l2.385 2.112a6.716 6.716 0 0 0-2.013 2.54L3.982 7.037a3.038 3.038 0 0 1-.924.145A3.06 3.06 0 0 1 0 4.124zm20.942 12.694c-.306 0-.601.045-.88.129l-2.308-2.044a6.862 6.862 0 0 1-1.819 2.706l1.993 1.765a3.05 3.05 0 0 0-.044.502 3.06 3.06 0 0 0 3.935 2.929l-1.992-1.77 2.14-2.365 1.981 1.76c.034-.181.052-.364.052-.554v-.026a3.057 3.057 0 0 0-3.058-3.032zm-3.397-7.592l2.473-2.189c.292.093.601.145.924.145A3.06 3.06 0 0 0 23.94 3.53l-1.956 1.734-2.144-2.38 1.914-1.703a3.049 3.049 0 0 0-.812-.114 3.062 3.062 0 0 0-3.058 3.037v.021c0 .152.012.304.033.45l-2.385 2.112a6.716 6.716 0 0 1 2.013 2.54zm-11.3 5.677l-2.307 2.044A3.057 3.057 0 0 0 0 19.85v.026c0 .19.018.373.052.554l1.982-1.76 2.14 2.365-1.993 1.77a3.06 3.06 0 0 0 3.935-2.929 3.05 3.05 0 0 0-.044-.502l1.993-1.765a6.862 6.862 0 0 1-1.82-2.706zm8.971 2.657a1.076 1.076 0 1 1-1.961.424h-.192a1.076 1.076 0 1 1-2.127 0h-.15A1.105 1.105 0 0 1 9.7 19.23c-.604 0-1.094-.5-1.094-1.115 0-.21.057-.405.156-.572-1.493-1.142-2.474-3.051-2.474-5.213 0-3.497 2.559-6.332 5.713-6.332s5.713 2.835 5.713 6.332c0 2.173-.991 4.091-2.497 5.231zm-4.194-5.914a1.995 1.995 0 0 0-.559-.66 1.804 1.804 0 0 0-.918-.264 1.45 1.45 0 0 0-.319.036c-.405.05-.747.327-.983.647-.207.257-.368.569-.372.905-.032.278.024.556.075.828.066.322.293.584.55.774.119.095.29.226.44.116.1-.134.016-.33.107-.478a.5.5 0 0 1 .258-.326c.263-.132.527-.262.808-.355.228-.067.416-.219.61-.349.255-.197.424-.558.303-.874zm.996 2.325c-.279-.007-.63 1.237-.574 1.78.175.72.237-.505.574-.506.323.014.275 1.255.53.504.078-.5-.224-1.77-.53-1.778zm4.036-.833c.051-.272.107-.55.075-.828-.004-.336-.165-.648-.372-.905-.236-.32-.578-.596-.983-.647a1.45 1.45 0 0 0-.319-.036c-.32-.001-.644.1-.918.264-.235.171-.42.406-.559.66-.121.316.048.677.303.874.194.13.382.282.61.35.28.092.545.222.808.354a.5.5 0 0 1 .258.326c.091.147.007.344.106.478.151.11.322-.021.44-.116.258-.19.485-.452.551-.774z"/></svg> Real-Time Fraud Detection Platform

> **Enterprise-style, end-to-end fintech fraud detection system built as a portfolio showcase project**

This project simulates a **real-world payment fraud detection platform** similar to what you would find inside banks, fintech startups, or payment processors.

It demonstrates:

- Streaming transaction ingestion  
- Feature engineering in real time  
- Risk scoring  
- Decisioning (approve / manual review / block)  
- Human review workflow  
- Operational dashboard  
- Full Dockerized deployment  

All designed to look and behave like a **production system solving a serious real-life problem**.

---

## 🎯 Project Goals

This repository is meant to be a **portfolio-level, high-impact showcase project** demonstrating:

- Backend engineering  
- Data engineering  
- Machine learning logic  
- DevOps / containerization  
- Frontend dashboard development  
- System design thinking  





---

# 🧠 What Problem Does This Solve?

Financial fraud costs companies **billions of dollars per year**.

Modern fintech systems must:

- Process thousands of transactions per second  
- Detect suspicious activity instantly  
- Balance fraud prevention with customer experience  
- Allow human reviewers to intervene  
- Track risk over time  

This platform mimics that environment.

---

# 🏗 System Architecture

```
+--------------------+
| Transaction Source |
+---------+----------+
          |
          v
+--------------------+       +-------------------+
| FastAPI Backend    | ----> | PostgreSQL DB     |
| (Scoring Engine)   |       |                   |
+---------+----------+       +-------------------+
          |
          v
+--------------------+
| React Dashboard    |
+--------------------+
```

---

# ⚙ Features Implemented

### ✅ Real-Time Feature Engineering

For every transaction, the system calculates:

- Transaction count in last 5 minutes  
- Transaction count in last 1 hour  
- Transaction count in last 24 hours  
- User average amount  
- Amount vs user average  
- Merchant fraud rate  
- Category fraud rate  
- Device usage patterns  
- Foreign country detection  

### 🤖 Fraud Scoring Engine

Each transaction receives:

- `fraud_probability` (0 – 1)
- `risk_score` (0 – 100)

Decision logic:

| Score | Result |
|------|-------|
| < 40 | APPROVE |
| 40–70 | MANUAL REVIEW |
| > 70 | BLOCK |

---

# 🚀 Quick Start

## Prerequisites

- Docker  
- Docker Compose  
- Node.js  
- Python 3.10+  

## 🐳 Run Everything with Docker

From project root:

```
docker compose -f docker-compose.full.yml up --build
```

### Access Points

| Service | URL |
|-------|-----|
| API | http://localhost:8000 |
| Dashboard | http://localhost:5173 |
| API Docs | http://localhost:8000/docs |

---

# 🧾 Example Usage

### Score a Transaction

```
curl -X POST "http://localhost:8000/transactions/score" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id":"demo_user_1",
    "card_id":"demo_card_1",
    "device_id":"demo_device_1",
    "amount": 2400.50,
    "currency":"USD",
    "merchant":"Binance",
    "merchant_category":"crypto",
    "country":"JP"
  }'
```

---

# 📂 Project Structure

```
fraud-detection-platform/
│
├── api/                    # FastAPI backend
│   ├── main.py
│   ├── features/
│   ├── models/
│   └── scoring/
│
├── dashboard/              # React frontend
│   ├── src/
│   ├── App.jsx
│   └── package.json
│
├── database/               # SQL schema
│   └── 00_init.sql
│
├── docker-compose.full.yml
└── README.md
```

---

# 🧩 Technologies Used

### Backend
- Python 3.12  
- FastAPI  
- psycopg2  
- PostgreSQL  

### Frontend
- React  
- Vite  
- TailwindCSS  

### DevOps
- Docker  
- Docker Compose  
- Nginx  

---

# 🔮 Future Improvements

Possible extensions:

- Replace rules with real ML model  
- Kafka streaming ingestion  
- Prometheus monitoring  
- Authentication system  
- User behavior profiling  
- Multi-currency normalization  
- Admin analytics dashboard  
- Alerting system  

---

# 👤 About This Project

This platform was built as a **high-impact portfolio project** to demonstrate:

- Full-stack engineering ability  
- Understanding of real-world fintech problems  
- System design skills  
- Practical machine learning application  
- Production mindset  

---

## 🤝 Contributing

Feel free to fork the project and extend it.

---

## 📜 License

MIT License – free to use for portfolio and learning purposes.

---

### ⭐ Final Note

If you are a recruiter or hiring manager:

This project demonstrates the ability to design and implement a complex, realistic, business‑critical system from scratch.
