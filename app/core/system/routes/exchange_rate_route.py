from datetime import datetime, timedelta
from typing import Optional, TypedDict

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

exchange_rate_router = APIRouter()


class ExchangeRateCache(TypedDict):
    rate: Optional[float]
    timestamp: Optional[str]


# In-memory cache (you could use Redis in production)
_exchange_rate_cache: ExchangeRateCache = {
    "rate": None,
    "timestamp": None
}

CBN_API_URL = "https://www.cbn.gov.ng/api/GetAllExchangeRatesGRAPH"
CACHE_DURATION = timedelta(hours=5)


@exchange_rate_router.get("/usd-rate", response_model=dict)
async def get_usd_exchange_rate():
    """
    Get USD to NGN exchange rate from CBN API.
    Returns the most recent US DOLLAR central rate.
    Cached for 1 hour to reduce API calls.
    """
    try:
        # Check cache first
        if _exchange_rate_cache["rate"] and _exchange_rate_cache["timestamp"]:
            cache_time = datetime.fromisoformat(_exchange_rate_cache["timestamp"])
            if datetime.now() - cache_time < CACHE_DURATION:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "rate": _exchange_rate_cache["rate"],
                        "cached": True,
                        "timestamp": _exchange_rate_cache["timestamp"]
                    }
                )

        # Fetch from CBN API
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(CBN_API_URL)
            response.raise_for_status()
            data = response.json()

        # Find the most recent US DOLLAR rate
        usd_rates = [item for item in data if item.get("currency") == "US DOLLAR"]
        
        if not usd_rates:
            # Return fallback rate if USD not found
            fallback_rate = 1463.0
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "rate": fallback_rate,
                    "cached": False,
                    "fallback": True,
                    "message": "USD rate not found, using fallback"
                }
            )

        # Sort by date (most recent first)
        sorted_rates = sorted(
            usd_rates,
            key=lambda x: datetime.strptime(x.get("ratedate", ""), "%Y-%m-%d"),
            reverse=True
        )

        latest_rate = sorted_rates[0]
        rate = float(latest_rate.get("centralrate", 1463.0))

        # Update cache
        _exchange_rate_cache["rate"] = rate
        _exchange_rate_cache["timestamp"] = datetime.now().isoformat()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "rate": rate,
                "cached": False,
                "date": latest_rate.get("ratedate"),
                "timestamp": _exchange_rate_cache["timestamp"]
            }
        )

    except httpx.TimeoutException:
        # Return cached rate if available, otherwise fallback
        if _exchange_rate_cache["rate"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "rate": _exchange_rate_cache["rate"],
                    "cached": True,
                    "fallback": False,
                    "message": "Using cached rate due to timeout"
                }
            )
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "rate": 1463.0,
                "cached": False,
                "fallback": True,
                "message": "API timeout, using fallback rate"
            }
        )
    except Exception as e:
        # Return cached rate if available, otherwise fallback
        if _exchange_rate_cache["rate"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "rate": _exchange_rate_cache["rate"],
                    "cached": True,
                    "fallback": False,
                    "message": f"Using cached rate due to error: {str(e)}"
                }
            )
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "rate": 1463.0,
                "cached": False,
                "fallback": True,
                "message": f"Error fetching rate: {str(e)}, using fallback"
            }
        )

