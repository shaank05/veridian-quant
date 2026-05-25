import os
from src.veridian_quant.data.providers.upstox import UpstoxProvider

def get_active_provider():
    """
    Factory function to retrieve the configured data provider.
    Strictly requires MARKET_MODE and ACTIVE_DATA_PROVIDER to be set in .env.
    """
    # 1. Retrieve variables without defaults
    market_mode = os.getenv("MARKET_MODE")
    provider_name = os.getenv("ACTIVE_DATA_PROVIDER")

    # 2. Strict Validation: Fail early if .env is not fully configured
    if not market_mode:
        raise EnvironmentError(
            "❌ 'MARKET_MODE' is missing from your .env file. "
            "Please add MARKET_MODE=INDIA, CRYPTO, or GLOBAL"
        )

    if not provider_name:
        raise EnvironmentError(
            "❌ 'ACTIVE_DATA_PROVIDER' is missing from your .env file. "
            "Please add ACTIVE_DATA_PROVIDER=UPSTOX"
        )

    market_mode = market_mode.upper()
    provider_name = provider_name.upper()

    # --- INDIA DOMAIN ---
    if market_mode == "INDIA":
        if provider_name == "UPSTOX":
            return UpstoxProvider()
        else:
            raise ValueError(f"❌ Unsupported Indian provider: {provider_name}")

    # --- CRYPTO DOMAIN ---
    elif market_mode == "CRYPTO":
        raise NotImplementedError("❌ Crypto providers are not yet implemented.")

    # --- GLOBAL/US DOMAIN ---
    elif market_mode == "GLOBAL":
        raise NotImplementedError("❌ Global providers are not yet implemented.")

    else:
        raise ValueError(f"❌ Unsupported MARKET_MODE: {market_mode}")