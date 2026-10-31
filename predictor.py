import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from supabase import create_client, Client
import xgboost as xgb

# THÔNG SỐ KẾT NỐI SUPABASE
SUPABASE_URL = "https://cnyrbeqaaaejavxvkgdt.supabase.co"
SUPABASE_KEY = "sb_publishable_7_ejttOPOW-vwbtAYaB5Lw_4CA18OjV"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_smart_prediction():
    print("--- KHỞI ĐỘNG HỆ THỐNG DỰ BÁO THÔNG MINH ---")
    
    try:
        # 1. Lấy dữ liệu lịch sử từ Supabase
        res = supabase.table("market_data_v2").select("*").order("date", desc=False).execute()
        data = res.data
        
        print(f"Đã tải thành công {len(data)} dòng dữ liệu từ bảng market_data_v2.")
        
        if not data or len(data) < 2:
            print("Cảnh báo: Dữ liệu quá ít, cần ít nhất 2 dòng để chạy dự báo!")
            return

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df['pig_price'] = pd.to_numeric(df['pig_price'])
        
        # 2. Tạo đặc trưng thời gian (Feature Engineering)
        df['lag_1'] = df['pig_price'].shift(1)
        df['lag_7'] = df['pig_price'].shift(7).fillna(df['pig_price'].iloc[0])
        df['rolling_mean_7'] = df['pig_price'].rolling(window=7, min_periods=1).mean()
        df['month'] = df['date'].dt.month
        df['day_of_week'] = df['date'].dt.dayofweek
        
        # Xóa các dòng NaN phát sinh do shift
        df = df.dropna()
        if df.empty:
            # Nếu lọc xong bị trống, lấy luôn dữ liệu gốc không dropna
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df['pig_price'] = pd.to_numeric(df['pig_price'])
            df['lag_1'] = df['pig_price'].iloc[-1]
            df['lag_7'] = df['pig_price'].iloc[0]
            df['rolling_mean_7'] = df['pig_price'].mean()
            df['month'] = datetime.now().month
            df['day_of_week'] = datetime.now().weekday()

        # 3. Huấn luyện mô hình XGBoost
        X = df[['lag_1', 'lag_7', 'rolling_mean_7', 'month', 'day_of_week']]
        y = df['pig_price']
        
        model = xgb.XGBRegressor(n_estimators=20, learning_rate=0.1, max_depth=2)
        model.fit(X, y)

        # 4. Dự đoán cho 7 ngày tiếp theo
        last_row = df.iloc[-1]
        current_lag_1 = float(last_row['pig_price'])
        current_lag_7 = float(df['pig_price'].iloc[0])
        current_rolling = float(df['pig_price'].mean())
        
        today = datetime.now().date()
        for i in range(1, 8):
            target_date = today + timedelta(days=i)
            X_infer = pd.DataFrame([[
                current_lag_1, 
                current_lag_7, 
                current_rolling, 
                target_date.month, 
                target_date.weekday()
            ]], columns=['lag_1', 'lag_7', 'rolling_mean_7', 'month', 'day_of_week'])
            
            predicted_price = float(model.predict(X_infer)[0])
            
            # Lưu kết quả dự đoán lên Supabase
            res_insert = supabase.table("advanced_predictions").insert({
                "target_date": str(target_date),
                "predicted_price": round(predicted_price, 2),
                "model_version": "XGBoost-v2",
                "horizon_days": i
            }).execute()
            
            print(f"-> Đã tạo và lưu dự đoán ngày {target_date}: {predicted_price:.2f} VNĐ")
            current_lag_1 = predicted_price

        print("--- HOÀN TẤT QUÁ TRÌNH DỰ BÁO ---")

    except Exception as e:
        print(f"Đã xảy ra lỗi trong quá trình chạy: {e}")

if __name__ == "__main__":
    run_smart_prediction()
