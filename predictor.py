import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from supabase import create_client, Client
import xgboost as xgb
import requests
from bs4 import BeautifulSoup

# THÔNG SỐ KẾT NỐI SUPABASE
SUPABASE_URL = "https://cnyrbeqaaaejavxvkgdt.supabase.co"
SUPABASE_KEY = "sb_publishable_7_ejttOPOW-vwbtAYaB5Lw_4CA18OjV"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def scrape_and_update_prices():
    print("--- ĐANG CÀO DỮ LIỆU TỰ ĐỘNG TỪ TRANG WEB ---")
    url = "https://trolyluat.vn/tien-ich/bieu-do-gia-heo-hoi"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("Không thể kết nối đến trang web lấy giá.")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        
        if not table:
            print("Không tìm thấy bảng dữ liệu trên trang.")
            return

        rows = table.find_all('tr')
        count = 0
        for row in rows[1:]:  # Bỏ qua hàng tiêu đề
            cols = row.find_all('td')
            if len(cols) >= 5:
                date_raw = cols[0].text.strip() # Dạng DD/MM/YYYY (ví dụ: 31/10/2026)
                mien_bac_raw = cols[4].text.strip() # Cột Miền Bắc
                
                try:
                    # Chuyển định dạng ngày từ DD/MM/YYYY sang YYYY-MM-DD
                    date_obj = datetime.strptime(date_raw, '%d/%m/%Y')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    
                    price = float(mien_bac_raw.replace(',', ''))
                    
                    # Đẩy dữ liệu vào Supabase (nếu trùng ngày thì tự động cập nhật)
                    supabase.table("market_data_v2").upsert({
                        "date": formatted_date,
                        "region": "Miền Bắc",
                        "pig_price": price,
                        "feed_price": 12500,
                        "cpi_index": 102.1
                    }, on_conflict="date").execute()
                    
                    count += 1
                except Exception as ex:
                    continue
                    
        print(f"Đã cập nhật thành công {count} bản ghi giá thực tế vào cơ sở dữ liệu!")

    except Exception as e:
        print(f"Lỗi khi cào dữ liệu: {e}")

def run_smart_prediction():
    # 1. Tự động cào dữ liệu mới nhất từ web trước khi dự đoán
    scrape_and_update_prices()
    
    print("--- KHỞI ĐỘNG HỆ THỐNG DỰ BÁO THÔNG MINH ---")
    
    try:
        # 2. Lấy dữ liệu lịch sử từ Supabase
        res = supabase.table("market_data_v2").select("*").order("date", desc=False).execute()
        data = res.data
        
        print(f"Đã tải thành công {len(data)} dòng dữ liệu từ bảng market_data_v2.")
        
        if not data or len(data) < 2:
            print("Cảnh báo: Dữ liệu quá ít để chạy dự báo!")
            return

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df['pig_price'] = pd.to_numeric(df['pig_price'])
        
        # 3. Tạo đặc trưng thời gian (Feature Engineering)
        df['lag_1'] = df['pig_price'].shift(1)
        df['lag_7'] = df['pig_price'].shift(7).fillna(df['pig_price'].iloc[0])
        df['rolling_mean_7'] = df['pig_price'].rolling(window=7, min_periods=1).mean()
        df['month'] = df['date'].dt.month
        df['day_of_week'] = df['date'].dt.day_of_week
        df = df.dropna()

        # 4. Huấn luyện mô hình XGBoost
        X = df[['lag_1', 'lag_7', 'rolling_mean_7', 'month', 'day_of_week']]
        y = df['pig_price']
        
        model = xgb.XGBRegressor(n_estimators=50, learning_rate=0.1, max_depth=3)
        model.fit(X, y)

        # 5. Dự đoán cho 7 ngày tiếp theo
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
            supabase.table("advanced_predictions").insert({
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
