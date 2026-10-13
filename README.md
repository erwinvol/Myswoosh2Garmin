# Myswoosh2Garmin 🚴‍♂️💨 ➡️ ⌚

Automated sync service that downloads your cycling activities from **MyWhoosh**, enhances the `.fit` files with Garmin Edge device signatures to enable Garmin **Physio TrueUp** (Training Load, Training Effect, VO2 Max, Recovery Time), and uploads them directly to **Garmin Connect**.

Packaged as a lightweight, containerized Docker service suitable for running on home servers, NAS devices (Synology, Unraid, TrueNAS), Raspberry Pis, or any system with Docker.

---

## 🌟 Key Features

* **🔄 Automated Synchronization**: Runs as a set-and-forget background daemon polling MyWhoosh for new rides at configurable intervals (e.g., every 60 minutes).
* **🎯 Garmin Physio TrueUp & Training Metrics**: By default, standard third-party virtual rides uploaded to Garmin Connect do not calculate Training Load or Training Effect. **Myswoosh2Garmin** patches the FIT file metadata (`FileIdMessage` and `DeviceInfoMessage`) to identify as a **Garmin Edge 1040** (or Edge 840), unlocking full physiological training metrics in Garmin Connect.
* **🛡️ Multi-Tier Duplicate Prevention**:
  1. **Persistent SQLite Store**: Remembers synced activity IDs across reboots and container restarts.
  2. **Garmin Connect Time Window**: Checks Garmin Connect for activities matching within a ±2 hour window (preventing duplicates if you also recorded on your watch/bike computer).
  3. **HTTP 409 Conflict Protection**: Gracefully catches Garmin's upload duplicate response.
* **🔑 Secure Token Caching**: Stores Garmin session tokens inside the `data/garmin_tokens` directory, preventing repetitive 2FA prompts and avoiding account lockouts.
* **🐳 Docker & Docker Compose Ready**: Single-command startup with minimal resource overhead and only a single volume mount (`./data:/data`).
* **🛠️ Flexible CLI Controls**: Supports single-ride sync (`--sync-latest`), batch backfills (`--batch 10`), database inspection (`--status`), and simulations (`--dry-run`).

---

## 🏗️ Architecture

```
┌─────────────────────────┐
│      MyWhoosh API       │
│  - REST Session Auth    │
│  - Activity Discovery   │
│  - S3 Pre-signed URL    │
└────────────┬────────────┘
             │ Raw .fit download
             ▼
┌─────────────────────────┐
│   FIT Device Enhancer   │
│  - fit-tool processor   │
│  - Edge 1040/840 spoof  │
│  - NP / IF / TSS work   │
└────────────┬────────────┘
             │ Enhanced .fit
             ▼
┌─────────────────────────┐
│     Garmin Connect      │
│  - Cached Token Auth    │
│  - Duplicate Checking   │
│  - FIT Binary Upload    │
└────────────┬────────────┘
             │ Upload Confirmation
             ▼
┌─────────────────────────┐
│   SQLite Sync Store     │
│  (/data/sync_state.db)  │
└─────────────────────────┘
```

---

## 🚀 Quick Start with Docker Compose (Recommended)

### 1. Clone the repository

```bash
git clone https://github.com/erwinvol/Myswoosh2Garmin.git
cd Myswoosh2Garmin
```

### 2. Configure Environment Variables in `docker-compose.yml`

Edit `docker-compose.yml` directly under the `environment:` section:

```yaml
services:
  myswoosh2garmin:
    build: .
    image: myswoosh2garmin:latest
    container_name: myswoosh2garmin
    restart: unless-stopped
    environment:
      - MYWHOOSH_EMAIL=your_mywhoosh_email@example.com
      - MYWHOOSH_PASSWORD=your_mywhoosh_password
      - GARMIN_USERNAME=your_garmin_email@example.com
      - GARMIN_PASSWORD=your_garmin_password
      - DATA_DIR=/data
      - GARMIN_TOKEN_DIR=/data/garmin_tokens
      - SYNC_INTERVAL_MINUTES=60
    volumes:
      - ./data:/data
```

> [!NOTE]
> All SQLite activity tracking and Garmin session tokens are self-contained inside the `./data` volume. Only a single volume mount (`./data:/data`) is required!

### 3. Launch with Docker Compose

```bash
docker compose up -d
```

View the logs in real time:

```bash
docker compose logs -f
```

---

## 🐳 Running with Docker CLI

### Build the Image:

```bash
docker build -t myswoosh2garmin:latest .
```

### Run as a Background Daemon (60m interval):

```bash
docker run -d \
  --name myswoosh2garmin \
  --restart unless-stopped \
  -e MYWHOOSH_EMAIL="your_email@example.com" \
  -e MYWHOOSH_PASSWORD="your_password" \
  -v $(pwd)/data:/data \
  myswoosh2garmin:latest
```

### Run a One-Off Sync (Latest Ride):

```bash
docker run --rm \
  -e MYWHOOSH_EMAIL="your_email@example.com" \
  -e MYWHOOSH_PASSWORD="your_password" \
  -v $(pwd)/data:/data \
  myswoosh2garmin:latest --sync-latest
```

---

## ⚙️ Configuration Reference

All settings can be specified either via a `.env` file or environment variables in `docker-compose.yml`:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MYWHOOSH_EMAIL` | *(required)* | MyWhoosh account email |
| `MYWHOOSH_PASSWORD` | *(required)* | MyWhoosh account password |
| `GARMIN_USERNAME` | *(optional)* | Garmin Connect email (only required on initial setup if tokens absent) |
| `GARMIN_PASSWORD` | *(optional)* | Garmin Connect password |
| `DATA_DIR` | `/data` | Path to persistent storage directory for SQLite database |
| `GARMIN_TOKEN_DIR` | `/data/garmin_tokens` | Path to store cached Garmin session tokens |
| `SYNC_INTERVAL_MINUTES`| `60` | Polling frequency for the daemon in minutes |
| `SYNC_BATCH_SIZE` | `10` | Number of recent MyWhoosh activities to examine on startup |
| `CHECK_DUPLICATES` | `true` | Query Garmin Connect API to verify if ride already exists |
| `DUPLICATE_THRESHOLD_HOURS`| `2` | Time window (± hours) to detect existing Garmin activities |
| `SPOOF_GARMIN_DEVICE` | `true` | Enhance FIT files with Garmin Edge device signatures |
| `DEVICE_PRODUCT_ID` | `3927` | Garmin Product ID (`3927` = Edge 1040, `4063` = Edge 840) |
| `DEVICE_SOFTWARE_VERSION` | `27.10` | Firmware version embedded into FIT file |
| `ATHLETE_FTP` | `0` | Athlete FTP for Normalized Power / Intensity Factor calculations |
| `LOG_LEVEL` | `INFO` | Console output level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 💻 Local Installation (Without Docker)

If you prefer to run the script directly on your host machine:

### 1. Requirements

* Python 3.10+
* pip

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Commands

```bash
# Check installed version
python -m src.main --version

# Sync only the single latest activity
python -m src.main --sync-latest

# Batch sync the last 10 activities
python -m src.main --batch 10

# Test run without uploading (simulation)
python -m src.main --dry-run

# Run as background daemon
python -m src.main --daemon --interval 60

# Show sync history database
python -m src.main --status
```

---

## 🧪 Running Tests

Unit tests are included and can be executed via:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

This is an unofficial community project and is not affiliated with, maintained, or endorsed by MyWhoosh or Garmin. Use at your own discretion.
