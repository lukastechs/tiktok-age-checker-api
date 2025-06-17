import re
  from datetime import datetime
  from typing import Optional, List, Dict, Any
  import logging

  logger = logging.getLogger(__name__)

  class AgeCalculator:
      @staticmethod
      def estimate_from_user_id(user_id: str) -> Optional[datetime]:
          """Estimate account creation date from user ID using TikTok ranges."""
          try:
              user_id_int = int(user_id)
              ranges = [
                  (0, 100000000, datetime(2016, 9, 1)),  # Early beta
                  (100000000, 500000000, datetime(2017, 1, 1)),  # Launch period
                  (500000000, 1000000000, datetime(2017, 6, 1)),
                  (1000000000, 2000000000, datetime(2018, 1, 1)),
                  (2000000000, 5000000000, datetime(2018, 8, 1)),  # Growth period
                  (5000000000, 10000000000, datetime(2019, 3, 1)),
                  (10000000000, 20000000000, datetime(2019, 9, 1)),
                  (20000000000, 50000000000, datetime(2020, 3, 1)),  # COVID boom
                  (50000000000, 100000000000, datetime(2020, 9, 1)),
                  (100000000000, 200000000000, datetime(2021, 3, 1)),
                  (200000000000, 500000000000, datetime(2021, 9, 1)),
                  (500000000000, 1000000000000, datetime(2022, 3, 1)),
                  (1000000000000, 2000000000000, datetime(2022, 9, 1)),
                  (2000000000000, 5000000000000, datetime(2023, 3, 1)),
                  (5000000000000, 10000000000000, datetime(2023, 9, 1)),
                  (10000000000000, 20000000000000, datetime(2024, 3, 1)),
                  (20000000000000, float('inf'), datetime(2024, 9, 1)),
              ]

              for min_id, max_id, date in ranges:
                  if min_id <= user_id_int < max_id:
                      return date
              return datetime.now()
          except (ValueError, TypeError) as e:
              logger.error(f"User ID estimation error: {e}")
              return None

      @staticmethod
      def estimate_from_username(username: str) -> Optional[datetime]:
          """Estimate creation date from username patterns."""
          if not username:
              return None
          patterns = [
              (r'^user\d{7,9}$', datetime(2016, 9, 1)),  # user1234567
              (r'^[a-z]{3,8}\d{2,4}$', datetime(2017, 3, 1)),  # abc123
              (r'^\w{3,8}$', datetime(2017, 9, 1)),  # simple names
              (r'^.{1,8}$', datetime(2018, 6, 1)),  # very short names
          ]

          for pattern, date in patterns:
              if re.match(pattern, username):
                  return date
          return None

      @staticmethod
      def estimate_from_metrics(followers: int, total_likes: int, verified: bool) -> Optional[datetime]:
          """Estimate creation date from profile metrics."""
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

          # High likes suggest established account
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
          return min(scores)

      @staticmethod
      def estimate_account_age(
          user_id: str,
          username: str,
          followers: int = 0,
          total_likes: int = 0,
          verified: bool = False
      ) -> Dict[str, Any]:
          """Combine estimates with confidence scoring."""
          estimates = []
          confidence_scores = {'low': 1, 'medium': 2, 'high': 3}

          user_id_est = AgeCalculator.estimate_from_user_id(user_id)
          if user_id_est:
              estimates.append({
                  'date': user_id_est,
                  'confidence': confidence_scores['high'],
                  'method': 'User ID Analysis'
              })

          username_est = AgeCalculator.estimate_from_username(username)
          if username_est:
              estimates.append({
                  'date': username_est,
                  'confidence': confidence_scores['medium'],
                  'method': 'Username Pattern'
              })

          metrics_est = AgeCalculator.estimate_from_metrics(followers, total_likes, verified)
          if metrics_est:
              estimates.append({
                  'date': metrics_est,
                  'confidence': confidence_scores['low'],
                  'method': 'Profile Metrics'
              })

          if not estimates:
              return {
                  'estimated_date': datetime.now(),
                  'confidence': 'very_low',
                  'method': 'Default',
                  'accuracy': '± 2 years',
                  'all_estimates': []
              }

          weighted_sum = sum(est['date'].timestamp() * est['confidence'] for est in estimates)
          total_weight = sum(est['confidence'] for est in estimates)
          final_date = datetime.fromtimestamp(weighted_sum / total_weight)

          max_confidence = max(est['confidence'] for est in estimates)
          confidence_level = (
              'high' if max_confidence == 3 else
              'medium' if max_confidence == 2 else 'low'
          )
          primary_method = next((est['method'] for est in estimates if est['confidence'] == max_confidence), 'Combined')
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
          """Format date as 'Month Day, Year'."""
          return date.strftime('%B %d, %Y')

      @staticmethod
      def calculate_age(created_date: datetime) -> str:
          """Calculate account age in years, months, or days."""
          now = datetime.now()
          diff = now - created_date
          diff_days = diff.days
          diff_months = diff_days // 30
          diff_years = diff_months // 12

          if diff_years > 0:
              remaining_months = diff_months % 12
              return (f"{diff_years} year{'s' if diff_years > 1 else ''}"
                      f"{f' and {remaining_months} month{'s' if remaining_months > 1 else ''}' if remaining_months > 0 else ''}")
          elif diff_months > 0:
              return f"{diff_months} month{'s' if diff_months > 1 else ''}"
          else:
              return f"{diff_days} day{'s' if diff_days > 1 else ''}"
