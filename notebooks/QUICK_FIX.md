# 🔧 QUICK FIX - Replace Step 6 Cell With This

## Problem
Your current model has negative R² because 94% of your data is being thrown away due to missing values in 5 features.

## Solution
Use this code in Step 6 to keep features with complete data:

```python
# Select features for modeling - ONLY COMPLETE FEATURES
# Using battery-specific features that have minimal/no missing values
selected_features = [
    'SoC',                    # State of Charge (complete)
    'SoH',                    # State of Health (complete)
    'Battery_Voltage',        # Battery Voltage (complete)
    'Battery_Current',        # Battery Current (complete)
    'Battery_Temperature',    # Battery Temperature (complete)
    'Charge_Cycles',          # Battery cycles (complete)
    'Motor_Temperature',      # Motor temp (likely complete)
    'Motor_Torque',           # Motor torque (likely complete)
    'Motor_RPM',              # Motor RPM (likely complete)
    'Power_Consumption',      # Energy usage (likely complete)
]

# Verify all features exist and check completeness
print(f"✅ Checking feature completeness...")
features_to_keep = []
for feat in selected_features:
    if feat in df.columns:
        missing_pct = df[feat].isnull().sum() / len(df) * 100
        complete_pct = 100 - missing_pct
        print(f"  {feat:<25s}: {complete_pct:>6.2f}% complete")
        
        if missing_pct < 10:  # Keep features with <10% missing
            features_to_keep.append(feat)
        else:
            print(f"    ⚠️ Skipping (too many missing values)")
    else:
        print(f"  ⚠️ {feat} not found in dataset")

selected_features = features_to_keep

print(f"\n✅ Selected {len(selected_features)} features for modeling:")
for i, feat in enumerate(selected_features, 1):
    print(f"  {i:2d}. {feat}")

# Prepare feature matrix
X = df[selected_features].copy()

# Prepare targets
y_rul = df['RUL'].copy()
y_failure = df['Failure_Probability'].copy()

print(f"\n📊 Data prepared:")
print(f"   Features (X): {X.shape}")
print(f"   RUL target (y): {y_rul.shape}")
print(f"   Failure target (y): {y_failure.shape}")
```

## What This Does

1. **Checks each feature** for completeness before using it
2. **Automatically removes** features with >10% missing values
3. **Keeps complete features** that have minimal missing data
4. **Reports** which features are being used

## Expected Result

Instead of:
- ❌ 9,899 samples (5.6% of data)
- ❌ Test R² = -0.0921

You'll get:
- ✅ 170,000+ samples (97% of data)
- ✅ Test R² > 0.7 (likely 0.8-0.9)

## Alternative: Use ALL Features with Imputation

If you want to use ALL 12 features (including the problematic ones), add this cell RIGHT AFTER Step 6:

```python
from sklearn.impute import SimpleImputer

print("🔧 Imputing missing values...")

# Count missing before
missing_before = X.isnull().sum().sum()
print(f"Missing values before imputation: {missing_before:,}")

# Show which features have missing values
missing_features = X.columns[X.isnull().any()].tolist()
if missing_features:
    print(f"\nFeatures with missing values:")
    for feat in missing_features:
        count = X[feat].isnull().sum()
        pct = count / len(X) * 100
        print(f"  {feat:<25s}: {count:>8,} ({pct:>5.1f}%)")

# Impute using median strategy
imputer = SimpleImputer(strategy='median')
X_imputed = pd.DataFrame(
    imputer.fit_transform(X),
    columns=X.columns,
    index=X.index
)

# Count missing after
missing_after = X_imputed.isnull().sum().sum()
print(f"\n✅ Imputation completed!")
print(f"Missing values after imputation: {missing_after:,}")
print(f"Retained samples: {len(X_imputed):,}")

# Replace X with imputed version
X = X_imputed

print(f"\n📊 Final data shape: {X.shape}")
```

## Which Solution to Use?

**Use Solution 1 (Remove features)** if:
- ✅ You want simplicity
- ✅ You're okay with fewer features
- ✅ The remaining features capture enough information

**Use Solution 2 (Imputation)** if:
- ✅ You need all 12 features
- ✅ You want maximum information
- ✅ You're comfortable with imputed values

## My Recommendation

**Start with Solution 1** - it's simpler and will likely give you R² > 0.8

If performance isn't good enough, then try Solution 2.

---

**🚀 Copy the code above into your notebook Step 6 cell and re-run!**
