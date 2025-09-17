# KTM Live Status Dashboard

A Python script that creates and maintains a live dashboard for KTM (Keretapi Tanah Melayu Berhad) train statuses within a Taskade project.

## Features

- 🚌 Fetches real-time KTM train data from Malaysian government GTFS-R API
- 📊 Shows ALL active trains (no limits) with location and speed
- 🔄 Updates every 15 minutes via GitHub Actions
- 📱 Beautiful emoji-rich formatting in Taskade
- 🛡️ Robust error handling and retry logic

## Local Testing

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Test Suite

```bash
python test_local.py
```

This will test:
- ✅ Dependencies installation
- ✅ GTFS-R API connectivity
- ✅ Data parsing and formatting
- 📝 Show sample output

### 3. Test with Real Taskade API

Set your environment variables:

```bash
export TASKADE_API_TOKEN="your_taskade_token_here"
export TASKADE_PROJECT_ID="your_project_id_here"
```

Then run:

```bash
python scripts/ktm_taskade.py
```

## GitHub Actions Setup

### 1. Add Secrets

In your GitHub repository, go to Settings → Secrets and variables → Actions, and add:

- `TASKADE_API_TOKEN`: Your Taskade API token
- `TASKADE_PROJECT_ID`: Your Taskade project ID
- `TASKADE_TASK_ID`: (Optional) Task ID for updates (will be created on first run)

### 2. Manual Trigger

Go to Actions tab → "KTM Live Status Dashboard" → "Run workflow" to test.

### 3. Automatic Schedule

The workflow runs every 15 minutes automatically.

## API Endpoints

- **GTFS-R Source**: `https://api.data.gov.my/gtfs-realtime/vehicle-position/ktmb`
- **Taskade API**: `https://www.taskade.com/api/v1`

## Output Format

The dashboard shows:
- 🚌 Last updated timestamp (MYT)
- 📊 Total active trains count
- 🚂 For each train:
  - Train ID
  - Route ID  
  - Location (lat, lon)
  - Speed (km/h)

## Troubleshooting

### Common Issues

1. **Missing dependencies**: Run `pip install -r requirements.txt`
2. **API errors**: Check your Taskade token and project ID
3. **No trains shown**: The API might be temporarily down or no trains are active

### Debug Mode

Set environment variable for verbose logging:

```bash
export LOG_LEVEL=DEBUG
python scripts/ktm_taskade.py
```

## Files

- `scripts/ktm_taskade.py` - Main script
- `requirements.txt` - Python dependencies
- `.github/workflows/ktm_dashboard.yml` - GitHub Actions workflow
- `test_local.py` - Local testing script
- `PRD.md` - Product Requirements Document
