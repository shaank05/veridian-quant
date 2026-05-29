import pandas as pd
import numpy as np
from src.veridian_quant.core.analytics.vectorized_math import calculate_wavelet_momentum_intensity

# Generate a dummy random series mimicking stock prices
mock_data = pd.Series(np.sin(np.linspace(0, 10, 100)) * 100 + 2000)

# Run the intensity check
result = calculate_wavelet_momentum_intensity(mock_data)
print("\n==============================")
print(f"🔬 Pre-flight CWT Result Check: {result}")
print("==============================\n")