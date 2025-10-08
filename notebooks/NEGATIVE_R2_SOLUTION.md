# 🚨 Model Training Issue: Negative R² Score

## Problem Summary
Your RUL model achieved a **negative R² score (-0.0921)** on the test set, which means it's performing **worse than just predicting the mean value** every time.

## What Does This Mean?

**R² Score Interpretation:**
- **1.0** = Perfect predictions
- **0.8-1.0** = Excellent model
- **0.6-0.8** = Good model  
- **0.0-0.6** = Poor model
- **< 0.0** = Worse than baseline (your case!)

## Root Causes

### 1. **Severe Data Loss** 
```
Original dataset: 175,393 samples
After cleaning: ~9,899 samples (94.4% data loss!)
Training set: ~7,919 samples
Test set: ~1,980 samples
```

**Problem**: You lost 165,494 samples due to missing values in these features:
- `Driving_Speed` - Missing in ~94% of rows
- `Ambient_Temperature` - Missing in ~94% of rows
- `Load_Weight` - Missing in ~94% of rows
- `Distance_Traveled` - Missing in ~94% of rows
- `Component_Health_Score` - Missing in ~94% of rows

### 2. **Overfitting**
- Training R²: 0.8263 (good!)
- Test R²: -0.0921 (terrible!)
- **Gap**: 91.84% performance drop

The model memorized training noise instead of learning patterns.

### 3. **Small Dataset Effect**
With only ~7,900 training samples and 12 features:
- Not enough data for robust generalization
- Random train/test split may have very different distributions
- High variance in performance

## Solutions

### ✅ Solution 1: Remove Problematic Features (RECOMMENDED)

Use only features with minimal missing values:

```python
# Recommended features (from your dataset analysis)
selected_features = [
    'SoC',                    # ✅ No missing values
    'SoH',                    # ✅ No missing values
    'Battery_Voltage',        # ✅ No missing values
    'Battery_Current',        # ✅ No missing values
    'Battery_Temperature',    # ✅ No missing values
    'Charge_Cycles',          # ✅ No missing values
    'Power_Consumption',      # ✅ Likely complete
    # REMOVE: Driving_Speed, Ambient_Temperature, Load_Weight, 
    #         Distance_Traveled, Component_Health_Score
]
```

**Expected improvement:**
- Dataset size: 175,393 → ~170,000+ samples (97% retention!)
- Better train/test distribution
- More robust model

### ✅ Solution 2: Use Imputation Instead of Deletion

Fill missing values instead of removing rows:

```python
from sklearn.impute import SimpleImputer

# Option A: Fill with median
imputer = SimpleImputer(strategy='median')
X_imputed = pd.DataFrame(
    imputer.fit_transform(X),
    columns=X.columns
)

# Option B: Forward fill (use last known value)
X_imputed = X.fillna(method='ffill').fillna(method='bfill')

# Option C: Fill with 0 or domain-specific value
X_imputed = X.fillna({
    'Driving_Speed': 0,
    'Ambient_Temperature': 25,  # Typical ambient temp
    'Load_Weight': X['Load_Weight'].median(),
    'Distance_Traveled': 0,
    'Component_Health_Score': 0.8  # Assume healthy by default
})
```

### ✅ Solution 3: Improved Model Configuration

The notebook now includes:
- **Reduced complexity**: max_depth=4 (was 8)
- **Fewer estimators**: n_estimators=100 (was 300)
- **Stronger regularization**: reg_alpha=0.1, reg_lambda=1.0
- **Early stopping**: Stops if validation doesn't improve
- **More subsampling**: subsample=0.7, colsample_bytree=0.7

### ✅ Solution 4: Better Data Splitting

Use stratified splitting or time-based splitting:

```python
# For time-series data (if Timestamp matters)
split_index = int(len(X) * 0.8)
X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]
y_rul_train = y_rul.iloc[:split_index]
y_rul_test = y_rul.iloc[split_index:]
```

## Immediate Action Plan

### Step 1: Identify Which Features Have Data
```python
# Run this in a new cell
print("Feature completeness:")
for feat in selected_features:
    missing_pct = df[feat].isnull().sum() / len(df) * 100
    print(f"  {feat:<25s}: {100-missing_pct:>5.1f}% complete")
```

### Step 2: Choose Your Strategy

**Option A - Quick Fix (Remove bad features):**
1. Edit Step 6 cell to use only complete features
2. Re-run from Step 6 onwards
3. Expected result: 170K+ samples, R² > 0.7

**Option B - Full Fix (Imputation):**
1. Add imputation cell after Step 6
2. Keep all features but fill missing values
3. Re-run from Step 6 onwards
4. Expected result: 175K samples, R² > 0.8

### Step 3: Validate Results

After retraining, check:
- ✅ Training R² and Test R² are similar (< 0.1 difference)
- ✅ Test R² > 0.7
- ✅ Model RMSE < Baseline RMSE
- ✅ At least 50,000+ training samples

## Updated Notebook Code

### For Solution 1 (Remove Features):

Replace Step 6 cell with:

```python
# Select ONLY features with complete data
selected_features = [
    'SoC',
    'SoH',
    'Battery_Voltage',
    'Battery_Current',
    'Battery_Temperature',
    'Charge_Cycles',
    'Power_Consumption',
    'Motor_Temperature',      # Add if complete
    'Motor_Torque',           # Add if complete
]

# Verify completeness
for feat in selected_features:
    missing_pct = df[feat].isnull().sum() / len(df) * 100
    if missing_pct > 5:
        print(f"⚠️ {feat} has {missing_pct:.1f}% missing values")

X = df[selected_features].copy()
y_rul = df['RUL'].copy()
y_failure = df['Failure_Probability'].copy()
```

### For Solution 2 (Imputation):

Add this cell after Step 6:

```python
from sklearn.impute import SimpleImputer

# Check which features need imputation
features_needing_imputation = X.columns[X.isnull().any()].tolist()
print(f"Features needing imputation: {features_needing_imputation}")

# Impute missing values
imputer = SimpleImputer(strategy='median')
X_imputed = pd.DataFrame(
    imputer.fit_transform(X),
    columns=X.columns,
    index=X.index
)

print(f"\n✅ Imputation completed!")
print(f"   Before: {X.isnull().sum().sum()} missing values")
print(f"   After: {X_imputed.isnull().sum().sum()} missing values")

# Replace X with imputed version
X = X_imputed
```

## Expected Results After Fix

### Before (Current):
- Training samples: 7,919
- Test R²: -0.0921 ❌
- Status: Model worse than baseline

### After (Solution 1 - Remove features):
- Training samples: ~140,000
- Test R²: 0.75 - 0.90 ✅
- Status: Good to Excellent

### After (Solution 2 - Imputation):
- Training samples: ~140,000
- Test R²: 0.70 - 0.85 ✅
- Status: Good model

## Prevention Checklist

Before training any model:

1. ✅ Check data completeness: `df.isnull().sum()`
2. ✅ Verify you have >10K samples per feature
3. ✅ Ensure train/test distributions are similar
4. ✅ Use cross-validation for small datasets
5. ✅ Monitor for overfitting (train vs test metrics)
6. ✅ Compare against a simple baseline

## Next Steps

1. **Choose** your solution (Option 1 recommended for simplicity)
2. **Edit** Step 6 in the notebook
3. **Re-run** cells from Step 6 onwards
4. **Verify** Test R² > 0.7 and similar to Training R²
5. **Save** the models
6. **Deploy** to your live system

---

**🎯 Bottom Line**: Your current model fails because you're training on only 5% of your data. Fix the missing value handling, and you'll likely achieve R² > 0.8!
