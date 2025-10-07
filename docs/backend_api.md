# 🌊 WaveWarn V2 Backend API Docs

## 🩺 Health & Ping
**GET `/health`**  
→ returns `{"status": "ok", "service": "wavewarn-backend"}`  

**GET `/ping`**  
→ quick service check, returns `{"status": "ok"}`  

---

## 🔥 Live Risk Endpoint
**GET `/live-risk?lat=12.97&lon=77.59`**

### Parameters
| Name | Type | Required | Description |
|:------|:------|:------|:------|
| `lat` | float | ✅ | Latitude |
| `lon` | float | ✅ | Longitude |
| `ts` | int | ❌ | Optional UNIX timestamp (seconds) |

### Example Response
```json
{
  "ok": true,
  "when": "2025-10-07T15:40:00Z",
  "location": {"lat": 12.97, "lon": 77.59},
  "score": 58,
  "tier": "risk",
  "drivers": {"heat_index": 34.8, "wbgt": 29.0, "lst_anomaly": 11.6}
}

