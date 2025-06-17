An unofficial API to fetch TikTok user data and estimate account age. **No affiliation with TikTok or ByteDance Ltd. By using this API, you agree to our Terms of Use.**

## Features

- Fetch user data: username, nickname, user ID, avatar, followers, likes, bio, region, verified status.
- Estimate account creation date using:
  - User ID range analysis (high confidence)
  - Username pattern analysis (medium confidence)
  - Profile metrics (followers, likes, verified) analysis (low confidence)
- Returns formatted creation date, account age, confidence, and accuracy range.

## Setup

1. **Clone the repo**:
   ```bash
   git clone https://github.com/lukastechs/tiktok-age-checker-api.git
   cd tiktok-age-checker-api
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   playwright install-deps
   ```

3. **Get ms_token**:
   - Visit `https://www.tiktok.com` in a browser.
   - Open DevTools (F12 > Application > Cookies).
   - Copy the `msToken` value.
   - Set as environment variable:
     ```bash
     export MS_TOKEN=your_ms_token
     ```

4. **Run locally**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
   Access at `http://localhost:8000/docs` for Swagger UI.

## Deployment on Render

1. **Push to GitHub**:
   - Create a GitHub repo named `tiktok-age-checker-api`.
   - Push code:
     ```bash
     git push origin main
     ```

2. **Create Render service**:
   - Sign in to [Render](https://render.com).
   - New > Web Service > Connect GitHub repo.
   - Settings:
     - Runtime: Docker
     - Region: Your choice (e.g., Oregon)
     - Branch: `main`
     - Auto-deploy: Yes
   - Environment:
     - Add `MS_TOKEN=your_ms_token`
     - Add `PORT=8000`

3. **Deploy**:
   - Render builds and deploys automatically.
   - Access at `https://your-service-name.onrender.com/docs`.

## Usage

- **Endpoint**: `/age-check`
- **Methods**: `POST`, `GET`
- **Request** (POST):
  ```json
  {
    "username": "therock"
  }
  ```
- **Request** (GET):
  ```
  https://your-service-name.onrender.com/age-check/therock
  ```
- **Response**:
  ```json
  {
    "username": "therock",
    "nickname": "The Rock",
    "user_id": "123456789",
    "sec_uid": "MS4wLjABAAAA...",
    "avatar": "https://p16-sign-va.tiktokcdn.com/...",
    "follower_count": 12345678,
    "total_likes": 1000000,
    "description": "Can you smell what The Rock is cooking?",
    "region": "US",
    "verified": true,
    "estimated_creation_date": "January 1, 2018",
    "account_age": "7 years and 5 months",
    "estimation_confidence": "high",
    "estimation_method": "User ID Analysis",
    "accuracy_range": "± 6 months",
    "estimation_details": {
      "all_estimates": [
        {
          "date": "January 1, 2018",
          "confidence": 3,
          "method": "User ID Analysis"
        },
        {
          "date": "June 1, 2018",
          "confidence": 1,
          "method": "Profile Metrics"
        }
      ],
      "note": "This is an estimated creation date based on available data. Actual creation date may vary."
    },
    "error": null
  }
  ```

- **Health Check**:
  ```
  https://your-service-name.onrender.com/health
  ```

## Notes

- **Rate Limits**: TikTok may block requests. Use proxies or services like SadCaptcha for stability.
- **Age Estimation**: Heuristic-based (user ID, username, metrics). Not exact.
- **Legal**: Unofficial API. Use at your own risk.
- **Disclaimer**: No affiliation with TikTok/ByteDance. Terms of Use apply.

## License

MIT
