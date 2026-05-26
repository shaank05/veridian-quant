import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def calculate_transition_matrix(z_scores: pd.Series) -> np.ndarray:
    """
    Takes a rolling series of Z-scores, maps them to categorical states,
    and computes a row-normalized 3x3 Markov transition probability matrix.
    
    States:
      State 0: Crater/Oversold Zone (Z <= -2.0) -> Primary setup search zone
      State 1: Mean Equivalence/Equilibrium Zone (-2.0 < Z < 1.5) -> Target zone
      State 2: Canopy/Overbought Exhaustion Zone (Z >= 1.5) -> Distribution zone
      
    Returns:
      A 3x3 numpy.ndarray representing transition probabilities.
      If lookback data is invalid or empty, returns a zero-initialized 3x3 matrix.
    """
    # Safeguard against insufficient lookback data sequences
    if z_scores.dropna().empty or len(z_scores) < 2:
        logger.warning("Insufficient Z-score data provided to compute Markov matrix. Returning zero matrix.")
        return np.zeros((3, 3))
        
    # 1. Map continuous Z-scores into discrete categorical states
    # Using numpy.select to efficiently vectorize across the historical lookback slice
    states = np.select(
        [
            z_scores <= -2.0, 
            (z_scores > -2.0) & (z_scores < 1.5), 
            z_scores >= 1.5
        ],
        [0, 1, 2],
        default=1  # Default to Equilibrium if values are unmapped
    )
    
    # 2. Structure transition sequence paths using vector shifting
    df_states = pd.DataFrame({'current': states})
    df_states['next'] = df_states['current'].shift(-1)
    df_states = df_states.dropna()
    
    # 3. Initialize an empty 3x3 frequency transition state table
    matrix = np.zeros((3, 3))
    
    # 4. Populate raw frequency transition tallies across historical coordinates
    for current_state, next_state in zip(df_states['current'], df_states['next']):
        matrix[int(current_state)][int(next_state)] += 1
        
    # 5. Row-normalize frequencies into probability decimals
    # We use numpy.divide with a condition guard flag to natively suppress division-by-zero 
    # errors in illiquid configurations or flatline regime intervals.
    row_sums = matrix.sum(axis=1, keepdims=True)
    normalized_matrix = np.divide(
        matrix, 
        row_sums, 
        out=np.zeros_like(matrix), 
        where=row_sums != 0
    )
    
    return normalized_matrix