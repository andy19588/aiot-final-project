import random
from datetime import datetime, timedelta

def generate_mock_logs(file_path="mock_logs.txt", num_records=50):
    start_time = datetime.now() - timedelta(minutes=num_records * 2)
    
    # Generate variations in current (A) and power (W)
    # SCT-013-000 sensor mock data
    with open(file_path, "w", encoding="utf-8") as f:
        for i in range(num_records):
            record_time = start_time + timedelta(minutes=i * 2)
            time_str = record_time.strftime("%H:%M:%S") + f".{random.randint(100, 999)}"
            
            # Base current between 0.05A and 2.5A
            # Add some noise/patterns (e.g. appliance turning on)
            if 15 < i < 30:
                # Heavy load (e.g. heater)
                current = round(random.uniform(5.5, 6.2), 3)
                power = round(current * 110.0 + random.uniform(-10, 10), 1) # ~110V grid
            else:
                # Normal standby load
                current = round(random.uniform(0.04, 0.15), 3)
                power = round(current * 110.0 + random.uniform(-1, 1), 1)
                if power < 0:
                    power = 0.0
                    
            line = f"{time_str} -> Current_RMS(A):{current:.3f},Apparent_Power(W):{power:.1f}\n"
            f.write(line)
            
    print(f"Generated {num_records} mock readings in {file_path}")

if __name__ == "__main__":
    generate_mock_logs()
