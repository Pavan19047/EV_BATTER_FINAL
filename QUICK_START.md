# 🚀 QUICK START GUIDE

## ✅ All Services Are Running!

Everything is ready. Follow these simple steps:

---

## 📋 Step 1: Start Simulator

**Open PowerShell Terminal 1:**

```powershell
cd C:\Users\pavan\OneDrive\Desktop\EV_BATTER_FINAL
.\.venv\Scripts\Activate.ps1
python src\simulator\publisher.py --mode synth --interval 1
```

✅ You should see: `"Connected to Kafka"`, `"Connected to MQTT"`, `"Connected to PostgreSQL"`

---

## 📋 Step 2: Start Predictor

**Open PowerShell Terminal 2 (NEW window):**

```powershell
cd C:\Users\pavan\OneDrive\Desktop\EV_BATTER_FINAL
.\.venv\Scripts\Activate.ps1
python src\inference\live_predictor.py --interval 5 --write-back
```

✅ You should see: `"Loaded RUL model"`, `"Loaded failure model"`, `"Starting Prometheus metrics server"`

---

## 📋 Step 3: Open Dashboards

Click these links:

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **MLflow**: http://localhost:5000

---

## 🎯 What to Expect

### In Terminal 1 (Simulator):
```
INFO - Generated telemetry: SOC=85.0%, SOH=95.0%, Speed=80.0km/h
INFO - Generated telemetry: SOC=84.5%, SOH=95.0%, Speed=75.2km/h
```

### In Terminal 2 (Predictor):
```
INFO - Predictions - RUL: 650.0 cycles, Failure Prob: 0.150
INFO - Predictions - RUL: 645.0 cycles, Failure Prob: 0.155
```

### In Grafana:
- See live RUL gauge updating
- View failure probability trends
- Monitor prediction rates

---

## 🛑 To Stop

Press `Ctrl+C` in both terminal windows

To stop Docker services:
```powershell
docker compose down
```

---

## ✅ Status Check

Run this anytime to check all services:
```powershell
docker compose ps
```

All should show "Up" and "(healthy)"

---

## 📚 Need Help?

- Check `SERVICE_STATUS.md` for detailed status
- Check `TROUBLESHOOTING.md` for common issues
- Check `README.md` for complete documentation

---

**🎉 ENJOY YOUR EV DIGITAL TWIN!**
