import re
from datetime import datetime
import pytz
from typing import Optional, List, Dict, Any
import logging
from dateutil.relativedelta import relativedelta
from functools import lru_cache
import math

logger = logging.getLogger(__name__)

# Configuration constants
USER_ID_RANGES = [
    (0, 100000000, datetime(2016, 9, 1, tzinfo=pytz.UTC)),  # Early beta
    (100000000, 500000000, datetime(2017, 1, 1, tzinfo=pytz.UTC)),  # Launch period
    (500000000, 1000000000, datetime(2017, 6, 1, tzinfo=pytz.UTC)),
    (1000000000, 2000000000, datetime(2018, 1, 1, tzinfo=pytz.UTC)),
    (2000000000, 5000000000, datetime(2018, 8, 1, tzinfo=pytz.UTC)),  # Growth period
    (5000000000, 10000000000, datetime(2019, 3, 1, tzinfo=pytz.UTC)),
    (10000000000, 20000000000, datetime(2019, 9, 1, tzinfo=pytz.UTC)),
    (20000000000, 50000000000, datetime(2020, 3, 1, tzinfo=pytz.UTC)),  # COVID boom
    (50000000000, 100000000000, datetime(2020, 9, 1, tzinfo=pytz.UTC)),
    (100000000000, 200000000000, datetime(2021, 3, 1, tzinfo=pytz.UTC)),
    (200000000000, 500000000000, datetime(2021, 9, 1, tzinfo=pytz.UTC)),
    (500000000000, 1000000000000, datetime(2022, 3, 1, tzinfo=pytz.UTC)),
    (1000000000000, 2000000000000, datetime(2022, 9, 1, tzinfo=pytz.UTC)),
    (2000000000000, 5000000000000, datetime(2023, 3, 1, tzinfo=pytz.UTC)),
    (5000000000000, 10000000000000, datetime(2023, 9, 1, tzinfo=pytz.UTC)),
    (10000000000000, 20000000000000, datetime(2024, 3, 1, tzinfo=pytz.UTC)),
    (20000000000000, float('inf'), datetime(2024, 9, 1, tzinfo=pytz.UTC)),
]

USERNAME_PATTERNS = [
    (r'^user\d{7,9}$', datetime(2016, 9, 1, tzinfo=pytz.UTC)),  # user1234567
    (r'^[a-z]{3,8}\d{2,4}$', datetime(2017, 3, 1, tzinfo=pytz.UTC)),  # abc123
    (r'^\w{3,8}$', datetime(2017, 9, 1, tzinfo=pytz.UTC)),  # simple names
    (r'^.{1,8}$', datetime(2018, 6, 1, tzinfo=pytz.UTC)),  # very short names
    (r'^[\w.]{1,15}$', datetime(2019, 1, 1, tzinfo=pytz.UTC)),  # modern usernames with dots
    (r'.*', datetime(2020, 1, 1, tzinfo=pytz.UTC)),  # fallback for complex usernames
]

class AgeCalculator:
    @staticmethod
    def estimate_from_user_id(user_id: str) -> Optional[datetime]:
        """
        Estimate account creation date from user ID using predefined TikTok ranges.

        Args:
            user_id: String representation of TikTok user ID.

        Returns:
            datetime: Estimated creation date (UTC) or None if invalid.

        Raises:
            None: Errors are logged and None is returned.
        """
        if not user_id or not user_id.isdigit():
            logger.warning(f"Invalid user_id: {user_id}")
            return None

        try:
            user_id_int = int(user_id)
            for min_id, max_id, date in USER_ID_RANGES:
                if min_id <= user_id_int < max_id:
                    return date
            logger.warning(f"User ID {user_id} out of known ranges")
            return None
        except (ValueError, TypeError) as e:
            logger.error(f"User ID estimation error: {e}")
            return None

    @staticmethod
    def estimate_from_username(username: str) -> Optional[datetime]:
        """
        Estimate creation date from username patterns.

        Args:
            username: TikTok username string.

        Returns:
            datetime: Estimated creation date (UTC) or None if invalid.
        """
        if not username or not isinstance(username, str):
            logger.warning(f"Invalid username: {username}")
            return None

        try:
            for pattern, date in USERNAME_PATTERNS:
                if re.match(pattern, username, re.UNICODE):
                    return date
            logger.debug(f"No username pattern matched for {username}")
            return USERNAME_PATTERNS[-1][1]  # Fallback to latest pattern
        except re.error as e:
            logger.error(f"Username pattern error: {e}")
            return None

    @staticmethod
    def estimate_from_metrics(followers: int, total_likes: int, verified: bool) -> Optional[datetime]:
        """
        Estimate creation date from profile metrics using logarithmic scaling.

        Args:
            followers: Number of followers.
            total_likes: Total likes received.
            verified: Whether the account is verified.

        Returns:
            datetime: Estimated creation date (UTC) or None if invalid.
        """
        if followers < 0 or total_likes < 0:
            logger.warning(f"Invalid metrics: followers={followers}, total_likes={total_likes}")
            return None

        scores = []
        base_date = datetime(2021, 1, 1, tzinfo=pytz.UTC)  # Default for new accounts
        earliest_date = datetime(2016, 9, 1, tzinfo=pytz.UTC)  # TikTok launch

        # Logarithmic follower scaling
        if followers > 0:
            log_followers = math.log10(followers + 1)
            follower_year = 2021 - min(int(log_followers * 0.5), 4)  # Scale to 2017-2021
            scores.append(datetime(follower_year, 1, 1, tzinfo=pytz.UTC))

        # Logarithmic likes scaling
        if total_likes > 0:
            log_likes = math.log10(total_likes + 1)
            likes_year = 2021 - min(int(log_likes * 0.4), 4)  # Scale to 2017-2021
            scores.append(datetime(likes_year, 6, 1, tzinfo=pytz.UTC))

        # Verified accounts
        if verified:
            scores.append(datetime(2018, 1, 1, tzinfo=pytz.UTC))

        if not scores:
            logger.debug("No metrics available for estimation")
            return base_date

        return max(min(scores, default=base_date), earliest_date)

    @staticmethod
    @lru_cache(maxsize=1000)
    def estimate_account_age(
        user_id: str,
        username: str,
        followers: int = 0,
        total_likes: int = 0,
        verified: bool = False
    ) -> Dict[str, Any]:
        """
        Combine estimates with confidence scoring to determine account age.

        Args:
            user_id: TikTok user ID string.
            username: TikTok username.
            followers: Number of followers (default: 0).
            total_likes: Total likes received (default: 0).
            verified: Whether the account is verified (default: False).

        Returns:
            Dict containing:
                - estimated_date: datetime (UTC)
                - confidence: str (high, medium, low, very_low)
                - method: str (estimation method)
                - accuracy: str (error range)
                - all_estimates: List of individual estimates
        """
        estimates = []
        confidence_scores = {'low': 1, 'medium': 2, 'high': 3}
        now = datetime.now(pytz.UTC)

        user_id_est = AgeCalculator.estimate_from_user_id(user_id)
        if user_id_est and user_id_est <= now:
            estimates.append({
                'date': user_id_est,
                'confidence': confidence_scores['high'],
                'method': 'User ID Analysis'
            })

        username_est = AgeCalculator.estimate_from_username(username)
        if username_est and username_est <= now:
            estimates.append({
                'date': username_est,
                'confidence': confidence_scores['medium'],
                'method': 'Username Pattern'
            })

        metrics_est = AgeCalculator.estimate_from_metrics(followers, total_likes, verified)
        if metrics_est and metrics_est <= now:
            estimates.append({
                'date': metrics_est,
                'confidence': confidence_scores['low'],
                'method': 'Profile Metrics'
            })

        if not estimates:
            logger.warning(f"No valid estimates for user_id={user_id}, username={username}")
            return {
                'estimated_date': now,
                'confidence': 'very_low',
                'method': 'Default',
                'accuracy': '± 2 years',
                'all_estimates': []
            }

        weighted_sum = sum(est['date'].timestamp() * est['confidence'] for est in estimates)
        total_weight = sum(est['confidence'] for est in estimates)
        final_timestamp = weighted_sum / total_weight
        final_date = datetime.fromtimestamp(final_timestamp, tz=pytz.UTC)

        max_confidence = max(est['confidence'] for est in estimates)
        confidence_level = (
            'high' if max_confidence == 3 else
            'medium' if max_confidence == 2 else 'low'
        )
        primary_method = next(
            (est['method'] for est in estimates if est['confidence'] == max_confidence), 'Combined'
        )
        accuracy = (
            '± 6 months' if confidence_level == 'high' else
            '± 1 year' if confidence_level == 'medium' else '± 2 years'
        )

        return {
            'estimated_date': final_date,
            'confidence': confidence_level,
            'method': primary_method,
            'accuracy': accuracy,
            'all_estimates': estimates
        }

    @staticmethod
    def format_date(date: datetime) -> str:
        """
        Format datetime as 'Month Day, Year'.

        Args:
            date: datetime object (naive or aware).

        Returns:
            str: Formatted date string.
        """
        if not isinstance(date, datetime):
            logger.warning(f"Invalid date for formatting: {date}")
            return ""
        try:
            return date.astimezone(pytz.UTC).strftime('%B %d, %Y')
        except ValueError as e:
            logger.error(f"Date formatting error: {e}")
            return ""

    @staticmethod
    def calculate_age(created_date: datetime) -> str:
        """
        Calculate account age in years, months, or days using relativedelta.

        Args:
            created_date: datetime object (naive or aware).

        Returns:
            str: Human-readable age string (e.g., "2 years and 3 months").
        """
        if not isinstance(created_date, datetime):
            logger.warning(f"Invalid created_date: {created_date}")
            return "0 days"

        now = datetime.now(pytz.UTC)
        if created_date.tzinfo is None:
            created_date = created_date.replace(tzinfo=pytz.UTC)

        if created_date > now:
            logger.warning(f"Future created_date: {created_date}")
            return "0 days"

        diff = relativedelta(now, created_date)
        years = diff.years
        months = diff.months
        days = diff.days

        if years > 0:
            parts = [f"{years} year{'s' if years > 1 else ''}"]
            if months > 0:
                parts.append(f"{months} month{'s' if months > 1 else ''}")
            return " and ".join(parts)
        elif months > 0:
            return f"{months} month{'s' if months > 1 else ''}"
        elif days > 0:
            return f"{days} day{'s' if days > 1 else ''}"
        else:
            return "0 days"
