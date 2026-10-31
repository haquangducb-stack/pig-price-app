'use client';
import { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';

// KẾT NỐI SUPABASE CỦA BẠN
const SUPABASE_URL = "https://cnyrbeqaaaejavxvkgdt.supabase.co";
const SUPABASE_KEY = "sb_publishable_7_ejttOPOW-vwbtAYaB5Lw_4CA18OjV";
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

export default function PigPriceDashboard() {
  const [predictions, setPredictions] = useState([]);
  const [performances, setPerformances] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        // 1. Lấy danh sách dự đoán sắp tới
        const { data: predData } = await supabase
          .from('advanced_predictions')
          .select('*')
          .order('target_date', { ascending: true });
        if (predData) setPredictions(predData);

        // 2. Lấy lịch sử đối chứng độ chính xác
        const { data: perfData } = await supabase
          .from('model_performance')
          .select('*')
          .order('target_date', { descending: true });
        if (perfData) setPerformances(perfData);

      } catch (error) {
        console.error('Lỗi tải dữ liệu:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <main className="p-6 max-w-6xl mx-auto bg-gray-50 min-h-screen font-sans">
      <header className="mb-8">
        <h1 className="text-3xl font-extrabold text-gray-800">📊 Hệ Thống Dự Báo Giá Lợn Hơi Thông Minh</h1>
        <p className="text-gray-500 mt-1">Ứng dụng tích hợp AI (XGBoost) & Cơ chế tự động đối chứng độ chính xác</p>
      </header>

      {/* Khu vực hiển thị dự đoán sắp tới */}
      <section className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 mb-8">
        <h2 className="text-xl font-bold text-gray-700 mb-4 flex items-center gap-2">
          <span>🔮</span> Giá Lợn Hơi Dự Báo 7 Ngày Tới (VNĐ/kg)
        </h2>
        
        {loading ? (
          <p className="text-gray-400">Đang tải dữ liệu từ hệ thống...</p>
        ) : predictions.length === 0 ? (
          <p className="text-orange-500">Chưa có dữ liệu dự đoán. Hãy chạy script Python trước nhé!</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            {predictions.map((item, index) => (
              <div key={index} className="border border-blue-100 bg-blue-50/50 p-4 rounded-xl text-center shadow-xs">
                <p className="text-xs text-gray-500 font-medium">{item.target_date}</p>
                <p className="text-xl font-black text-blue-600 my-2">{item.predicted_price}</p>
                <span className="inline-block bg-blue-100 text-blue-700 text-[10px] px-2 py-0.5 rounded-full font-semibold">
                  {item.model_version}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Khu vực đối chứng độ chính xác (Backtest) */}
      <section className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <h2 className="text-xl font-bold text-gray-700 mb-4 flex items-center gap-2">
          <span>🎯</span> Bảng Đối Chuyển & Đánh Giá Sai Số (Backtest)
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wider">
                <th className="p-3 border-b">Ngày</th>
                <th className="p-3 border-b">Giá Thực Tế</th>
                <th className="p-3 border-b">Giá Đã Dự Báo</th>
                <th className="p-3 border-b">Sai Số Chênh Lệch</th>
                <th className="p-3 border-b">Độ Chính Xác (%)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm">
              {performances.length === 0 ? (
                <tr>
                  <td colSpan="5" className="p-4 text-center text-gray-400">
                    Chưa có dữ liệu đối chứng hôm nay (Hệ thống sẽ tự đối chứng khi đến ngày thực tế).
                  </td>
                </tr>
              ) : (
                performances.map((row, index) => (
                  <tr key={index} className="hover:bg-gray-50/50">
                    <td className="p-3 font-medium text-gray-700">{row.target_date}</td>
                    <td className="p-3 font-semibold text-green-600">{row.actual_price} đ</td>
                    <td className="p-3 font-semibold text-blue-600">{row.predicted_price} đ</td>
                    <td className="p-3 text-red-500 font-medium">± {row.error_amount} đ</td>
                    <td className="p-3">
                      <span className="bg-emerald-100 text-emerald-800 font-bold px-2.5 py-1 rounded-md text-xs">
                        {row.accuracy_rate}%
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}