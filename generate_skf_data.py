import pandas as pd
import numpy as np

np.random.seed(42)

months = pd.date_range(start='2025-01-01', end='2025-12-01', freq='MS')
num_months = len(months)

# Dimensions for variations
oems = ['OEM_A_Global', 'OEM_B_Euro', 'OEM_C_Eco']
powertrains = ['ICE', 'EV', 'Hybrid']

# Generate External Regressors for the year (macro levels baseline)
lv_prod = np.linspace(100, 115, num_months) + np.random.normal(0, 1.5, num_months)
ev_pen = np.linspace(18, 25, num_months) + np.random.normal(0, 0.3, num_months)
gdp_growth = np.linspace(2.1, 2.4, num_months) + np.random.normal(0, 0.05, num_months)
interest_rates = np.linspace(6.5, 5.8, num_months) + np.random.normal(0, 0.1, num_months)
steel_price = 120 + 25 * np.sin(np.pi * np.arange(num_months)/6) + np.random.normal(0, 3, num_months)
energy_index = np.linspace(112, 105, num_months) + np.random.normal(0, 1.5, num_months)
pv_sales = lv_prod * 0.96 + np.random.normal(0, 1, num_months)
emission_norms_active = ['Pre-Euro 7' if i < 5 else 'Euro 7 Transition' for i in range(num_months)]
oem_upgrades = ['Platform Upgrade' if i in [5, 10] else 'Normal Production' for i in range(num_months)]

external_data = pd.DataFrame({
    'Month': months.strftime('%Y-%m'),
    'Light_Vehicle_Production_Index': lv_prod,
    'EV_Hybrid_Penetration_Pct': ev_pen,
    'GDP_Growth_Pct': gdp_growth,
    'Interest_Rate_Pct': interest_rates,
    'Steel_Price_Index': steel_price,
    'Energy_Logistics_Index': energy_index,
    'Passenger_Vehicle_Sales_Index': pv_sales,
    'Emission_Norms_Status': emission_norms_active,
    'OEM_Production_Status': oem_upgrades
})

data = []

for i, row in external_data.iterrows():
    month = row['Month']
    steel_effect = max(0, (row['Steel_Price_Index'] - 120) / 100)
    
    for oem in oems:
        for pt in powertrains:
            # Variations logic based on OEM and Powertrain
            
            # OEM Modifiers (OEM A is biggest, OEM C is smallest but EV focused)
            oem_mod = 1.0
            if oem == 'OEM_A_Global': oem_mod = 1.2
            elif oem == 'OEM_B_Euro': oem_mod = 0.8
            elif oem == 'OEM_C_Eco': oem_mod = 0.5
            
            # EV penetration naturally favors EV/Hybrid
            ev_boost = (row['EV_Hybrid_Penetration_Pct'] / 20.0) if pt in ['EV', 'Hybrid'] else 1.0
            
            # Base logic adjusted for PT and OEM
            # 1. Deep Groove - Mostly universal, high volume
            vol_dg = 15000 * (row['Light_Vehicle_Production_Index']/100) * oem_mod + np.random.normal(0, 500)
            
            # 2. Angular Contact - Thrives in EV/Hybrid
            vol_ac = 4000 * oem_mod
            if pt in ['EV', 'Hybrid']:
                vol_ac += 1000 * ev_boost
            else:
                vol_ac -= 500 # Less used in standard ICE
            vol_ac += np.random.normal(0, 200)
            
            # 3. Self-Aligning - Spike in month 6 for regulations
            vol_sa = 2000 * oem_mod + np.random.normal(0, 100)
            if i >= 6: # Regulatory jump
                vol_sa += 800 * oem_mod 
                
            # 4. Thrust Ball Bearings - Declining due to MT mostly in ICE
            vol_th = 3500 * oem_mod + np.random.normal(0, 150)
            if pt == 'ICE':
                vol_th -= 100 * i # Slow decline for ICE
            else:
                vol_th *= 0.2 # Barely used in EV
                
            # 5. Wheel Hub Bearing Units - Universal
            vol_wh = 25000 * (row['Passenger_Vehicle_Sales_Index']/100) * oem_mod + np.random.normal(0, 600)
            
            # 6. Miniature & Hybrid Ceramic - Dominated by EV and high-tech
            vol_mc = 1000 * oem_mod + np.random.normal(0, 50)
            if pt == 'EV':
                vol_mc += 800 * ev_boost
            elif pt == 'Hybrid':
                vol_mc += 400 * ev_boost

            products = {
                'Deep Groove Ball Bearings': max(0, int(vol_dg * (1 - steel_effect * 0.1))),
                'Angular Contact Ball Bearings': max(0, int(vol_ac)),
                'Self-Aligning Ball Bearings': max(0, int(vol_sa)),
                'Thrust Ball Bearings': max(0, int(vol_th)),
                'Wheel Hub Bearing Units': max(0, int(vol_wh * (1 - steel_effect * 0.12))),
                'Miniature & Hybrid Ceramic Bearings': max(0, int(vol_mc))
            }
            
            for prod, vol in products.items():
                data.append({
                    'Month': month,
                    'OEM': oem,
                    'Powertrain': pt,
                    'Product_Category': prod,
                    'Sales_Volume': vol,
                    'Light_Vehicle_Production_Index': round(row['Light_Vehicle_Production_Index'], 2),
                    'EV_Hybrid_Penetration_Pct': round(row['EV_Hybrid_Penetration_Pct'], 2),
                    'GDP_Growth_Pct': round(row['GDP_Growth_Pct'], 2),
                    'Interest_Rate_Pct': round(row['Interest_Rate_Pct'], 2),
                    'Steel_Price_Index': round(row['Steel_Price_Index'], 2),
                    'Energy_Logistics_Index': round(row['Energy_Logistics_Index'], 2),
                    'Emission_Norms_Status': row['Emission_Norms_Status'],
                    'OEM_Production_Status': row['OEM_Production_Status']
                })

df_sales = pd.DataFrame(data)
output_path = 'skf_sample_data_v3_variations.csv'
df_sales.to_csv(output_path, index=False)
print(f"Sample data successfully generated with {len(df_sales)} rows across variations and saved to {output_path}")
