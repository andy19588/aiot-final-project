/**
 * @file sct013_esp32.ino
 * @brief 使用 ESP32 與 SCT-013-000 (100A:50mA) 電流感測器進行交流電流偵測的程式
 * 
 * 本程式使用 ESP32 內建並經過校正的 analogReadMilliVolts() API 來讀取毫伏特電壓，
 * 避免了傳統 analogRead() 的非線性誤差。透過數位高通濾波器自動濾除 1.65V DC 偏置，
 * 計算出交流電的 RMS 電壓，進而換算出實際的 RMS 電流值。
 * 
 * 本版本針對 **低電流家電** (電扇、筆電充電器等，通常 < 2A) 進行優化，
 * 使用 1kΩ 負擔電阻以獲得更高的 ADC 解析度與更低的雜訊。
 */

// ==================== 參數設定 ====================
const int ADC_PIN = 34;                // 連接到 ESP32 的類比輸入腳位 (建議使用 GPIO 34, 35, 36, 39，因為它們僅供輸入且不受 Wi-Fi 干擾)
const double BURDEN_RESISTOR = 1000.0; // 負擔電阻阻值 (單位：歐姆 Ω)。使用 1kΩ 電阻，適合量測 0~2.33A 的低電流家電 (電扇、筆電等)
const double CT_RATIO = 2000.0;        // 比流器變比 (SCT-013-000 為 100A : 50mA = 2000 : 1)
const double MAINS_VOLTAGE = 110.0;    // 市電電壓 (單位：伏特 V)，台灣通常為 110.0V 或 220.0V

// 取樣設定
const unsigned long SAMPLING_PERIOD_MS = 200;  // 每次計算的取樣時間 (毫秒)，200ms 正好是 50Hz 的 10 個週期，或 60Hz 的 12 個週期
const double CALIBRATION_FACTOR = 1.00;        // 校正係數，用於微調實測誤差 (預設為 1.00)
const double NOISE_GATE_A = 0.05;              // 雜訊門檻 (單位：安培 A)。使用 1kΩ 負擔電阻時雜訊很低，0.05A 即可有效濾除

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ; // 等待串口連接
  }
  
  Serial.println(F("========================================="));
  Serial.println(F("ESP32 + SCT-013-000 電流偵測程式啟動中..."));
  Serial.println(F("(低電流家電優化版 - 電扇/筆電適用)"));
  Serial.print(F("讀取腳位 GPIO: ")); Serial.println(ADC_PIN);
  Serial.print(F("負擔電阻: ")); Serial.print(BURDEN_RESISTOR); Serial.println(F(" Ohm"));
  Serial.print(F("比流器變比: ")); Serial.println(CT_RATIO);
  Serial.print(F("預設市電電壓: ")); Serial.print(MAINS_VOLTAGE); Serial.println(F(" V"));
  
  // 計算並顯示最大可量測電流
  double maxCurrent = (1.65 / sqrt(2.0)) / BURDEN_RESISTOR * CT_RATIO;
  Serial.print(F("最大可量測電流: ")); Serial.print(maxCurrent, 2); Serial.println(F(" A RMS"));
  Serial.print(F("雜訊門檻: ")); Serial.print(NOISE_GATE_A, 3); Serial.println(F(" A"));
  Serial.println(F("========================================="));
  
  // 設定 ESP32 的 ADC 解析度與衰減度
  // 12-bit 解析度 (0 ~ 4095)
  analogReadResolution(12);
}

void loop() {
  // 檢測 SCT-013 是否連接
  // 當 SCT 未連接時，ADC 讀數非常穩定（因為 burden 電阻直接把偏壓傳過來）
  // 已連接時，即使無負載，AC 雜訊也會讓讀數有一定的變異
  bool sctConnected = isSCTConnected();
  
  double Irms = 0.0;
  if (sctConnected) {
    Irms = readCurrentRMS();
  }
  
  // 計算估算視在功率 (Apparent Power, S = V * I)
  double apparentPower = MAINS_VOLTAGE * Irms;
  
  // 輸出至 Serial Monitor / Serial Plotter
  // 格式化輸出以便在 Serial Plotter 中繪製波形
  if (!sctConnected) {
    Serial.println("[警告] SCT-013 未連接或未偵測到信號");
  }
  Serial.print("Current_RMS(A):");
  Serial.print(Irms, 3);          // 顯示到小數點後三位
  Serial.print(",");
  Serial.print("Apparent_Power(W):");
  Serial.println(apparentPower, 1);
  
  delay(1000); // 每秒量測並更新一次
}

/**
 * @brief 檢測 SCT-013 是否已連接
 * @return bool true 表示已連接，false 表示未連接
 * 
 * 原理：當 SCT 未連接時，ADC 透過 burden 電阻讀到穩定的偏壓 (~1650mV)，
 * 讀數變異量極小。當 SCT 已連接（即使無負載），環境中的電磁雜訊
 * 會讓讀數有明顯的 AC 變異。我們利用短時間取樣的標準差來區分。
 */
bool isSCTConnected() {
  const int CHECK_SAMPLES = 50;
  double sum = 0;
  double sumSq = 0;
  
  for (int i = 0; i < CHECK_SAMPLES; i++) {
    double v = (double)analogReadMilliVolts(ADC_PIN);
    sum += v;
    sumSq += v * v;
    delayMicroseconds(200);
  }
  
  double mean = sum / CHECK_SAMPLES;
  double variance = (sumSq / CHECK_SAMPLES) - (mean * mean);
  double stddev = sqrt(variance);
  
  // 當 SCT 未連接時，標準差通常 < 2mV（只有 ADC 本身的量化噪音）
  // 當 SCT 已連接時，即使無負載，60Hz 環境耦合也會讓標準差 > 5mV
  // 使用 3mV 作為門檻值（可依實際環境微調）
  return (stddev > 3.0);
}

/**
 * @brief 讀取並計算交流電流的有效值 (RMS)
 * @return double 計算出的 RMS 電流 (安培 A)
 */
double readCurrentRMS() {
  double sumV_sq = 0;
  int sampleCount = 0;
  
  // 初始化高通濾波器的變數
  // 用於動態濾除分壓電路產生的 1.65V DC 偏置
  double filteredV = 0.0;
  double lastFilteredV = 0.0;
  double sampleV = (double)analogReadMilliVolts(ADC_PIN);
  double lastSampleV = sampleV;
  
  unsigned long startTime = millis();
  
  // 在設定的取樣時間內持續採樣
  while ((millis() - startTime) < SAMPLING_PERIOD_MS) {
    sampleV = (double)analogReadMilliVolts(ADC_PIN);
    
    // 數位一階高通濾波器 (移除 DC 偏置)
    // 0.9961 是濾波器係數，適用於約 1-2kHz 的取樣率
    filteredV = 0.9961 * (lastFilteredV + sampleV - lastSampleV);
    
    // 累加電壓平方和 (mV^2)
    sumV_sq += (filteredV * filteredV);
    
    // 記錄本次數據供下次迭代使用
    lastSampleV = sampleV;
    lastFilteredV = filteredV;
    sampleCount++;
    
    // 微小延遲以穩定取樣率 (約 10kHz 取樣頻率)
    delayMicroseconds(100);
  }
  
  if (sampleCount == 0) return 0.0;
  
  // 計算 RMS 電壓 (單位：毫伏特 mV)
  double rmsV_mV = sqrt(sumV_sq / sampleCount);
  
  // 將毫伏特轉換為伏特 (V)
  double rmsV = rmsV_mV / 1000.0;
  
  // 依據變比與負擔電阻計算 RMS 電流 (I = V / R)
  // 二次側電流 Is = rmsV / BURDEN_RESISTOR
  // 一次側電流 Ip = Is * CT_RATIO
  double Irms = (rmsV / BURDEN_RESISTOR) * CT_RATIO;
  
  // 乘上微調校正係數
  Irms = Irms * CALIBRATION_FACTOR;
  
  // 雜訊門檻處理 (防漂移)
  if (Irms < NOISE_GATE_A) {
    Irms = 0.0;
  }
  
  return Irms;
}
