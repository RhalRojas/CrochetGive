from decimal import Decimal

import redis
from django.conf import settings
from django.db.models import Sum

_redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
)

CACHE_KEY = "total_donated"
CACHE_TTL_SECONDS = 60


def calculate_donation_split(order_total):
    """
    Tiered donation formula:
    - Orders under ₱500: donate 5%
    - Orders ₱500 - ₱1499.99: donate 8%
    - Orders ₱1500+: donate 12%

    Bigger orders donate a slightly higher percentage.
    """
    order_total = Decimal(order_total)

    if order_total < 500:
        rate = Decimal("0.05")
    elif order_total < 1500:
        rate = Decimal("0.08")
    else:
        rate = Decimal("0.12")

    donation_amount = (order_total * rate).quantize(Decimal("0.01"))
    seller_amount = order_total - donation_amount

    return donation_amount, seller_amount


def get_total_donated():
    """
    Returns the running total donated across all orders.
    Checks Redis first; only queries MySQL if the cache is empty/expired.
    """
    from .models import Order  # imported here to avoid circular import

    cached = _redis_client.get(CACHE_KEY)
    if cached:
        return {"total": float(cached), "from_cache": True}

    total = Order.objects.aggregate(total=Sum("donation_amount"))["total"] or 0
    _redis_client.setex(CACHE_KEY, CACHE_TTL_SECONDS, str(total))

    return {"total": float(total), "from_cache": False}


def invalidate_total_donated():
    _redis_client.delete(CACHE_KEY)
