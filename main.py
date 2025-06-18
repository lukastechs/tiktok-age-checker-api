import asyncio
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from TikTokApi import TikTokApi
from TikTokApi.exceptions import TikTokException
from typing import Optional, List, Dict, Any
from age_estimator import AgeCalculator
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TikTok Age Checker API",
    description="Unofficial API to fetch TikTok user data and estimate account age. No affiliation with TikTok or ByteDance Ltd. By using this API, you agree to our Terms of Use.",
    version="1.0.0"
)

# Pydantic model for request
class UsernameRequest(BaseModel):
    username: str

# Pydantic model for estimation details
class EstimationDetail(BaseModel):
    date: str  # Formatted date string
    confidence: int
    method: str

# Pydantic model for response
class UserResponse(BaseModel):
    username: str
    nickname: Optional[str] = None
    user_id: Optional[str] = None
    sec_uid: Optional[str] = None
    avatar: Optional[str] = None
    follower_count: Optional[int] = None
    total_likes: Optional[int] = None
    description: Optional[str] = None
    region: Optional[str] = None
    verified: Optional[bool] = None
    estimated_creation_date: Optional[str] = None
    account_age: Optional[str] = None
    estimation_confidence: Optional[str] = None
    estimation_method: Optional[str] = None
    accuracy_range: Optional[str] = None
    estimation_details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Global TikTokApi instance
tiktok_api = None

# Initialize TikTokApi
async def init_tiktok_api():
    ms_token = os.environ.get("MS_TOKEN")
    if not ms_token:
        logger.error("MS_TOKEN environment variable is not set")
        raise ValueError("MS_TOKEN environment variable is not set")
    
    try:
        api = TikTokApi()
        await api.create_sessions(ms_tokens=[ms_token], num_sessions=1, sleep_after=3)
        logger.info("TikTokApi sessions created successfully")
        return api
    except TikTokException as e:
        logger.error(f"Failed to initialize TikTokApi: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TikTokApi initialization error: {str(e)}")

@app.on_event("startup")
async def startup_event():
    global tiktok_api
    tiktok_api = await init_tiktok_api()
    logger.info("TikTokApi initialized during startup")

@app.on_event("shutdown")
async def shutdown_event():
    global tiktok_api
    if tiktok_api:
        await tiktok_api.close()
        logger.info("TikTokApi sessions closed during shutdown")
        tiktok_api = None

@app.post("/age-check", response_model=UserResponse)
async def check_age(request: UsernameRequest):
    """
    Fetch TikTok user data and estimate account age for the given username.
    """
    try:
        logger.info(f"Processing request for username: {request.username}")
        user = tiktok_api.user(username=request.username)
        user_data = await user.info_full()  # Use info_full for complete data

        if not user_data or "user" not in user_data:
            logger.warning(f"User not found or invalid response for {request.username}")
            raise HTTPException(status_code=404, detail="User not found or invalid response")

        user_info = user_data["user"]
        stats = user_info.get("stats", {})

        # Estimate account age
        age_estimate = AgeCalculator.estimate_account_age(
            user_id=user_info.get("id", ""),
            username=user_info.get("uniqueId", request.username),
            followers=stats.get("followerCount", 0),
            total_likes=stats.get("heartCount", 0),
            verified=user_info.get("verified", False)
        )

        # Format all_estimates for response
        formatted_estimates = [
            {
                "date": AgeCalculator.format_date(est["date"]),
                "confidence": est["confidence"],
                "method": est["method"]
            }
            for est in age_estimate.get("all_estimates", [])
        ]

        response = UserResponse(
            username=user_info.get("uniqueId", request.username),
            nickname=user_info.get("nickname"),
            user_id=user_info.get("id"),
            sec_uid=user_info.get("secUid"),
            avatar=user_info.get("avatarLarger"),
            follower_count=stats.get("followerCount"),
            total_likes=stats.get("heartCount"),
            description=user_info.get("signature"),
            region=user_info.get("region"),
            verified=user_info.get("verified"),
            estimated_creation_date=AgeCalculator.format_date(age_estimate["estimated_date"]),
            account_age=AgeCalculator.calculate_age(age_estimate["estimated_date"]),
            estimation_confidence=age_estimate["confidence"],
            estimation_method=age_estimate["method"],
            accuracy_range=age_estimate["accuracy"],
            estimation_details={
                "all_estimates": formatted_estimates,
                "note": "This is an estimated creation date based on available data. Actual creation date may vary."
            }
        )
        logger.info(f"Successfully fetched data for {request.username}")
        return response

    except TikTokException as e:
        logger.error(f"TikTok API error for {request.username}: {str(e)}")
        return UserResponse(
            username=request.username,
            error=f"TikTok API error: {str(e)}"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error processing {request.username}: {str(e)}")
        return UserResponse(
            username=request.username,
            error=f"Unexpected error: {str(e)}"
        )

@app.get("/age-check/{username}", response_model=UserResponse)
async def check_age_get(username: str):
    """
    Fetch TikTok user data and estimate account age for the given username (GET method).
    """
    return await check_age(UsernameRequest(username=username))

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
