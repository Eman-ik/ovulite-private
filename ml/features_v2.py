"""
Enhanced Feature Engineering v2 for Ovulite
Addresses weak correlations and data scarcity issues identified in quality analysis.
"""

import numpy as np
import pandas as pd
from datetime import datetime

from ml.config import DATA_CSV, TARGET_COL


def build_enhanced_feature_matrix(db_conn=None, fit_mask=None):
    """
    Build enhanced feature matrix with domain-specific engineered features.

    Focus on:
    - Removing constant/useless features
    - Creating meaningful ratios and interactions
    - Temporal features
    - Quality indicators

    Parameters
    ----------
    fit_mask : boolean pd.Series aligned to the loaded dataframe's index, or None.
        Rows where technician/farm success-rate encodings and the median-fill
        values are *learned* from. Required for any leakage-safe use — without
        it, those steps are fit on the full dataset (train + holdout together),
        which leaks the target into the features. Pass the training-split mask
        here; when omitted this prints a loud warning and falls back to
        fitting on the whole frame, which is only acceptable for ad-hoc
        exploration, never for a model whose metrics will be reported.
    """
    if fit_mask is None:
        print(
            "WARNING: build_enhanced_feature_matrix() called without fit_mask — "
            "technician/farm success-rate encoding and median imputation will be "
            "fit on the full dataset, including any holdout rows. This leaks the "
            "target and must not be used for a model whose metrics get reported."
        )
    
    # Load base features
    if db_conn:
        df = pd.read_sql("SELECT * FROM vw_et_features", db_conn)
    else:
        from ml.features import build_feature_matrix
        df = build_feature_matrix(None)
    
    print(f"Starting with {len(df)} samples, {len(df.columns)} columns")
    
    # ═══════════════════════════════════════════════════════════
    # STEP 1: Remove useless features
    # ═══════════════════════════════════════════════════════════
    
    # Remove constant features (identified in analysis)
    if 'embryo_grade' in df.columns and df['embryo_grade'].nunique() == 1:
        df = df.drop(columns=['embryo_grade'])
        print("✓ Removed constant feature: embryo_grade")
    
    # Remove features with >70% missing
    high_missing = df.columns[df.isnull().mean() > 0.7]
    if len(high_missing) > 0:
        df = df.drop(columns=high_missing)
        print(f"✓ Removed {len(high_missing)} high-missing features: {list(high_missing)}")
    
    # ═══════════════════════════════════════════════════════════
    # STEP 2: Create domain-specific engineered features
    # ═══════════════════════════════════════════════════════════
    
    # --- Timing features ---
    if 'days_opu_to_et' in df.columns:
        # Optimal timing indicator (5-7 days is typical)
        df['timing_optimal'] = ((df['days_opu_to_et'] >= 5) & 
                                 (df['days_opu_to_et'] <= 7)).astype(int)
        df['timing_deviation'] = (df['days_opu_to_et'] - 6).abs()  # Distance from ideal
    
    if 'heat_day' in df.columns:
        # Heat synchronization quality
        df['heat_in_range'] = ((df['heat_day'] >= 0) & (df['heat_day'] <= 1)).astype(int)
    
    # --- Corpus luteum (CL) quality indicators ---
    if 'cl_measure_mm' in df.columns:
        # CL size categories (larger is generally better)
        df['cl_size_adequate'] = (df['cl_measure_mm'] >= 15).astype(int)
        df['cl_size_category'] = pd.cut(df['cl_measure_mm'], 
                                         bins=[0, 12, 18, 100], 
                                         labels=['small', 'medium', 'large'])
    
    # --- Body condition score engineering ---
    if 'bc_score' in df.columns:
        # Optimal BCS is 5-7 for cattle
        df['bc_optimal'] = ((df['bc_score'] >= 5) & (df['bc_score'] <= 7)).astype(int)
        df['bc_deviation'] = (df['bc_score'] - 6).abs()  # Distance from ideal
        
        # Keep missing indicator (had surprisingly strong correlation -0.153)
        if 'bc_missing' not in df.columns:
            df['bc_missing'] = df['bc_score'].isnull().astype(int)
    
    # --- Embryo stage optimization ---
    if 'embryo_stage' in df.columns:
        # Blastocyst stages (typically 6-8 are best)
        df['embryo_stage_advanced'] = (df['embryo_stage'] >= 6).astype(int)
    
    # --- Recipient type ---
    if 'cow_or_heifer' in df.columns:
        # Cows typically have better success than heifers
        df['is_cow'] = (df['cow_or_heifer'] == 'Cow').astype(int)
    
    # --- Protocol adherence ---
    if 'protocol_name' in df.columns:
        # Group similar protocols (reduce cardinality)
        df['protocol_group'] = df['protocol_name'].fillna('Unknown')
        # Could add protocol effectiveness if we had historical data
    
    # --- Fresh vs Frozen ---
    if 'fresh_or_frozen' in df.columns:
        df['is_fresh'] = (df['fresh_or_frozen'] == 'Fresh').astype(int)
    
    # --- Genetic potential (EPD) ---
    if 'donor_bw_epd' in df.columns and 'sire_bw_epd' in df.columns:
        # Combined genetic potential
        df['combined_epd'] = df['donor_bw_epd'].fillna(0) + df['sire_bw_epd'].fillna(0)
        df['epd_interaction'] = df['donor_bw_epd'].fillna(0) * df['sire_bw_epd'].fillna(0)
    
    # --- Temporal features (seasonality) ---
    if 'et_date' in df.columns:
        df['et_date'] = pd.to_datetime(df['et_date'], errors='coerce')
        df['et_month'] = df['et_date'].dt.month
        df['et_quarter'] = df['et_date'].dt.quarter
        
        # Breeding season indicator (spring/early summer best for cattle)
        df['in_breeding_season'] = df['et_month'].isin([3, 4, 5, 6]).astype(int)
        
        # Year trend (may capture improving techniques over time)
        df['et_year'] = df['et_date'].dt.year
        if df['et_year'].min() != df['et_year'].max():
            df['years_since_start'] = df['et_year'] - df['et_year'].min()
    
    # --- Interaction features (multiply related factors) ---
    if 'cl_size_adequate' in df.columns and 'bc_optimal' in df.columns:
        # Both CL and BC optimal = best outcome potential
        df['cl_bc_optimal'] = df['cl_size_adequate'] * df['bc_optimal']
    
    if 'embryo_stage_advanced' in df.columns and 'is_fresh' in df.columns:
        # Advanced fresh embryo = gold standard
        df['advanced_fresh'] = df['embryo_stage_advanced'] * df['is_fresh']
    
    if 'timing_optimal' in df.columns and 'heat_in_range' in df.columns:
        # Perfect synchronization
        df['perfect_sync'] = df['timing_optimal'] * df['heat_in_range']
    
    # --- Technician experience proxy ---
    # Success-rate encodings must be learned only from fit_mask rows (the
    # training split) — computing them over the full frame lets a row's own
    # outcome (via its technician/farm peers, including itself) leak into its
    # features. Unseen categories and, when no fit_mask is given, all rows
    # fall back to the fit population's overall mean.
    fit_rows = df[fit_mask] if fit_mask is not None else df

    if 'technician_name' in df.columns:
        tech_success = fit_rows.groupby('technician_name')[TARGET_COL].mean()
        overall_rate = fit_rows[TARGET_COL].mean()
        df['technician_success_rate'] = df['technician_name'].map(tech_success).fillna(overall_rate)

    # --- Farm/Location historical performance ---
    if 'farm_location' in df.columns:
        farm_success = fit_rows.groupby('farm_location')[TARGET_COL].mean()
        overall_rate = fit_rows[TARGET_COL].mean()
        df['farm_success_rate'] = df['farm_location'].map(farm_success).fillna(overall_rate)
    
    print(f"✓ Created {len(df.columns) - len(df.select_dtypes(include=[object]).columns)} numeric features")
    
    # ═══════════════════════════════════════════════════════════
    # STEP 3: Fill missing values strategically
    # ═══════════════════════════════════════════════════════════
    
    # For numeric features, fill with the fit population's median (never the
    # full dataset's — that would leak holdout-row values into training rows).
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    numeric_cols = [c for c in numeric_cols if c != TARGET_COL]

    for col in numeric_cols:
        if df[col].isnull().any():
            df[col] = df[col].fillna(fit_rows[col].median())
    
    print(f"Final feature matrix: {len(df)} samples × {len(df.columns)} features")
    
    return df


def select_top_features(df, target_col=TARGET_COL, max_features=15):
    """
    Select top features based on correlation with target.
    Reduces overfitting risk with limited data.
    """
    from sklearn.feature_selection import SelectKBest, f_classif
    
    # Separate features and target
    feature_cols = [c for c in df.columns if c != target_col and df[c].dtype in [np.number, 'int64', 'float64']]
    X = df[feature_cols]
    y = df[target_col]
    
    # Remove any remaining NaN
    X = X.fillna(X.median())
    
    # Select top K features
    selector = SelectKBest(f_classif, k=min(max_features, len(feature_cols)))
    selector.fit(X, y)
    
    # Get selected feature names
    selected_mask = selector.get_support()
    selected_features = [feat for feat, selected in zip(feature_cols, selected_mask) if selected]
    
    print(f"✓ Selected top {len(selected_features)} features from {len(feature_cols)} candidates")
    print(f"  Selected: {selected_features}")
    
    return selected_features


if __name__ == "__main__":
    # Test the enhanced features
    df = build_enhanced_feature_matrix(None)
    print("\nEnhanced feature matrix shape:", df.shape)
    print("\nFeature columns:")
    for col in sorted(df.columns):
        print(f"  - {col}")
