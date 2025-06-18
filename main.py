# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import redis
from playwright.async_api import async_playwright
import asyncio
import json
import re
from typing import Optional, List, Dict
from pydantic import BaseModel

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis configuration
redis_client = redis.Redis(
    host='your-redis-host',
    port=12345,
    password='your-redis-password',
    decode_responses=True
)

CACHE_TTL = 86400  # 24 hours cache

class EstimateResult(BaseModel):
    date: datetime
    confidence: str
    method: str

class AgeEstimate(BaseModel):
    estimated_date: datetime
    confidence: str
    method: str
    accuracy: str
    all_estimates: List[Dict]

class TikTokAgeEstimator:
    @staticmethod
    def estimate_from_user_id(user_id: str) -> Optional[datetime]:
        try:
            user_id_int = int(user_id)
            
            # TikTok user ID ranges (approximate)
            ranges = [
                {"min": 0, "max": 100000000, "date": datetime(2016, 9, 1)},  # Early beta
                {"min": 100000000, "max": 500000000, "date": datetime(2017, 1, 1)},  # Launch period
                {"min": 500000000, "max": 1000000000, "date": datetime(2017, 6, 1)},
                {"min": 1000000000, "max": 2000000000, "date": datetime(2018, 1, 1)},
                {"min": 2000000000, "max": 5000000000, "date": datetime(2018, 8, 1)},  # Growth period
                {"min": 5000000000, "max": 10000000000, "date": datetime(2019, 3, 1)},
                {"min": 10000000000, "max": 20000000000, "date": datetime(2019, 9, 1)},
                {"min": 20000000000, "max": 50000000000, "date": datetime(2020, 3, 1)},  # COVID boom
                {"min": 50000000000, "max": 100000000000, "date": datetime(2020, 9, 1)},
                {"min": 100000000000, "max": 200000000000, "date": datetime(2021, 3, 1)},
                {"min": 200000000000, "max": 500000000000, "date": datetime(2021, 9, 1)},
                {"min": 500000000000, "max": 1000000000000, "date": datetime(2022, 3, 1)},
                {"min": 1000000000000, "max": 2000000000000, "date": datetime(2022, 9, 1)},
                {"min": 2000000000000, "max": 5000000000000, "date": datetime(2023, 3, 1)},
                {"min": 5000000000000, "max": 10000000000000, "date": datetime(2023, 9, 1)},
                {"min": 10000000000000, "max": 20000000000000, "date": datetime(2024, 3, 1)},
                {"min": 20000000000000, "max": float('inf'), "date": datetime(2024, 9, 1)}
            ]
            
            for range in ranges:
                if range["min"] <= user_id_int < range["max"]:
                    return range["date"]
            
            return datetime.now()  # Default to current date
        
        except (ValueError, TypeError):
            return None

    @staticmethod
    def estimate_from_username(username: str) -> Optional[datetime]:
        if not username:
            return None
            
        # Early TikTok username patterns
        patterns = [
            {"regex": r"^user\d{7,9}$", "date": datetime(2016, 9, 1)},  # user1234567
            {"regex": r"^[a-z]{3,8}\d{2,4}$", "date": datetime(2017, 3, 1)},  # abc123
            {"regex": r"^\w{3,8}$", "date": datetime(2017, 9, 1)},  # simple names
            {"regex": r"^.{1,8}$", "date": datetime(2018, 6, 1)},  # very short names
        ]
        
        for pattern in patterns:
            if re.match(pattern["regex"], username):
                return pattern["date"]
        
        return None

    @staticmethod
    def estimate_from_metrics(followers: int, total_likes: int, verified: bool) -> Optional[datetime]:
        scores = []
        
        # High follower count suggests older account
        if followers > 1000000:
            scores.append(datetime(2018, 1, 1))
        elif followers > 100000:
            scores.append(datetime(2019, 1, 1))
        elif followers > 10000:
            scores.append(datetime(2020, 1, 1))
        else:
            scores.append(datetime(2021, 1, 1))
        
        # Very high likes suggest established account
        if total_likes > 10000000:
            scores.append(datetime(2018, 6, 1))
        elif total_likes > 1000000:
            scores.append(datetime(2019, 6, 1))
        elif total_likes > 100000:
            scores.append(datetime(2020, 6, 1))
        
        # Verified accounts are typically older
        if verified:
            scores.append(datetime(2018, 1, 1))
        
        if not scores:
            return None
        
        # Return the earliest date from scores
        return min(scores)

    @staticmethod
    def estimate_account_age(user_id: str, username: str, followers: int = 0, 
                           total_likes: int = 0, verified: bool = False) -> AgeEstimate:
        estimates = []
        confidence_weights = {"low": 1, "medium": 2, "high": 3}
        
        # Get estimates from different methods
        if user_id:
            user_id_est = TikTokAgeEstimator.estimate_from_user_id(user_id)
            if user_id_est:
                estimates.append({
                    "date": user_id_est,
                    "confidence": "high",
                    "method": "User ID Analysis",
                    "weight": confidence_weights["high"]
                })
        
        username_est = TikTokAgeEstimator.estimate_from_username(username)
        if username_est:
            estimates.append({
                "date": username_est,
                "confidence": "medium",
                "method": "Username Pattern",
                "weight": confidence_weights["medium"]
            })
        
        metrics_est = TikTokAgeEstimator.estimate_from_metrics(followers, total_likes, verified)
        if metrics_est:
            estimates.append({
                "date": metrics_est,
                "confidence": "low",
                "method": "Profile Metrics",
                "weight": confidence_weights["low"]
            })
        
        if not estimates:
            return AgeEstimate(
                estimated_date=datetime.now(),
                confidence="very_low",
                method="Default",
                accuracy="± 2 years",
                all_estimates=[]
            )
        
        # Weighted average calculation
        weighted_sum = sum(est["date"].timestamp() * est["weight"] for est in estimates)
        total_weight = sum(est["weight"] for est in estimates)
        final_date = datetime.fromtimestamp(weighted_sum / total_weight)
        
        # Determine overall confidence
        confidences = [est["weight"] for est in estimates]
        max_confidence = max(confidences)
        
        if max_confidence == confidence_weights["high"]:
            confidence_level = "high"
            accuracy = "± 6 months"
        elif max_confidence == confidence_weights["medium"]:
            confidence_level = "medium"
            accuracy = "± 1 year"
        else:
            confidence_level = "low"
            accuracy = "± 2 years"
        
        primary_method = next(
            (est["method"] for est in estimates if est["weight"] == max_confidence),
            "Combined"
        )
        
        return AgeEstimate(
            estimated_date=final_date,
            confidence=confidence_level,
            method=primary_method,
            accuracy=accuracy,
            all_estimates=estimates
        )

def calculate_age(created_date: datetime) -> str:
    now = datetime.now()
    delta = now - created_date
    
    years = delta.days // 365
    months = (delta.days % 365) // 30
    days = (delta.days % 365) % 30
    
    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if months > 0:
        parts.append(f"{months} month{'s' if months > 1 else ''}")
    if days > 0 and years == 0:  # Only show days if less than a month
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    
    return " ".join(parts) if parts else "Less than a day"

async def scrape_tiktok_profile(username: str):
    cached_data = redis_client.get(f"tiktok:{username}")
    if cached_data:
        return json.loads(cached_data)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(f"https://www.tiktok.com/@{username}")
            await page.wait_for_selector('h1', timeout=10000)
            
            # Extract basic profile info
            display_name = await page.inner_text('h1')
            profile_pic = await page.get_attribute('img.tiktok-avatar', 'src')
            verified = await page.query_selector('svg[aria-label="Verified account"]') is not None
            
            # Extract follower count
            followers_text = await page.inner_text('strong[title="Followers"] + span')
            followers = int(re.sub(r'[^0-9]', '', followers_text))
            
            # Extract user ID from page
            user_id = await page.evaluate('''() => {
                const scripts = Array.from(document.querySelectorAll('script'));
                const dataScript = scripts.find(script => 
                    script.textContent.includes('user-post') || 
                    script.textContent.includes('userInfo')
                );
                if (dataScript) {
                    const match = dataScript.textContent.match(/"userId":"(\d+)"/);
                    return match ? match[1] : null;
                }
                return null;
            }''')
            
            # Get total likes (approximate)
            total_likes = await page.evaluate('''() => {
                const likesElements = document.querySelectorAll('[data-e2e="like-count"]');
                let total = 0;
                likesElements.forEach(el => {
                    const text = el.textContent.trim();
                    const value = text.endsWith('K') ? parseFloat(text) * 1000 : 
                                 text.endsWith('M') ? parseFloat(text) * 1000000 : 
                                 parseInt(text.replace(/,/g, '')) || 0;
                    total += value;
                });
                return total;
            }''')
            
            # Use our enhanced estimation
            age_estimate = TikTokAgeEstimator.estimate_account_age(
                user_id=user_id,
                username=username,
                followers=followers,
                total_likes=total_likes,
                verified=verified
            )
            
            account_age = calculate_age(age_estimate.estimated_date)
            
            result = {
                "username": username,
                "display_name": display_name.strip(),
                "profile_picture": profile_pic,
                "verified": verified,
                "followers": followers,
                "total_likes": total_likes,
                "user_id": user_id,
                "estimated_creation_date": age_estimate.estimated_date.strftime('%d/%m/%Y'),
                "account_age": account_age,
                "estimation_confidence": age_estimate.confidence,
                "estimation_method": age_estimate.method,
                "accuracy_range": age_estimate.accuracy,
                "estimation_details": {
                    "all_estimates": [
                        {
                            "method": est["method"],
                            "date": est["date"].strftime('%d/%m/%Y'),
                            "confidence": est["confidence"]
                        } for est in age_estimate.all_estimates
                    ],
                    "note": "Estimated creation date based on multiple analysis methods"
                }
            }
            
            redis_client.setex(f"tiktok:{username}", CACHE_TTL, json.dumps(result))
            return result
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error scraping profile: {str(e)}")
        finally:
            await browser.close()

@app.get("/api/profile/{username}")
async def get_profile(username: str):
    return await scrape_tiktok_profile(username)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
