import os
import re
import argparse
import serial
from datetime import datetime
import db

# Regex to match optional time prefix: [09:49:15.511 -> ] Current_RMS(A):0.050,Apparent_Power(W):5.5
LOG_PATTERN = re.compile(
    r"(?:(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s*->\s*)?Current_RMS\(A\):(?P<current>[\d\.]+),Apparent_Power\(W\):(?P<power>[\d\.]+)"
)

def parse_line(line):
    """Parses a single line of log and returns (time_str, current_rms, apparent_power) or None."""
    match = LOG_PATTERN.search(line)
    if match:
        return (
            match.group("time"),
            float(match.group("current")),
            float(match.group("power"))
        )
    return None

def process_log_file(file_path, target_date=None, db_path=db.DEFAULT_DB_PATH):
    """Reads a log file, parses all lines, and imports them to SQLite."""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return
        
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")
        
    print(f"Processing log file: {file_path} with date: {target_date}")
    
    db.init_db(db_path)
    count = 0
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parsed = parse_line(line)
            if parsed:
                time_str, current, power = parsed
                if not time_str:
                    time_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                # Combine date and time
                timestamp = f"{target_date} {time_str}"
                db.insert_reading(timestamp, current, power, db_path=db_path)
                count += 1
                
    print(f"Successfully imported {count} readings to database.")

def read_serial_port(port, baudrate, db_path=db.DEFAULT_DB_PATH):
    """Connects to the specified COM port and listens for live readings."""
    print(f"Connecting to serial port: {port} at {baudrate} baud...")
    db.init_db(db_path)
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
    except serial.SerialException as e:
        print(f"Error opening serial port {port}: {e}")
        return
        
    print(f"Connected to {port}. Listening for SCT-013 data. Press Ctrl+C to stop.")
    
    try:
        while True:
            if ser.in_waiting > 0:
                raw_line = ser.readline()
                try:
                    line = raw_line.decode("utf-8").strip()
                except UnicodeDecodeError:
                    line = raw_line.decode("ascii", errors="ignore").strip()
                
                if not line:
                    continue
                    
                print(f"Raw: {line}")
                
                # Check for match
                parsed = parse_line(line)
                if parsed:
                    time_str, current, power = parsed
                    now = datetime.now()
                    current_date = now.strftime("%Y-%m-%d")
                    if not time_str:
                        time_str = now.strftime("%H:%M:%S.%f")[:-3]
                    timestamp = f"{current_date} {time_str}"
                    
                    db.insert_reading(timestamp, current, power, db_path=db_path)
                    print(f" Saved -> Time: {timestamp}, Current_RMS: {current} A, Apparent_Power: {power} W")
    except KeyboardInterrupt:
        print("\nStopping serial reader...")
    finally:
        ser.close()
        print("Serial port closed.")

def main():
    parser = argparse.ArgumentParser(description="ESP32 SCT-013-000 Serial Monitor and Log Parser")
    parser.add_argument("--db", type=str, default=db.DEFAULT_DB_PATH, help="Path to SQLite database file")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Path to an existing serial log text file to import")
    group.add_argument("--port", type=str, help="COM port to read live serial data (e.g. COM3)")
    
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate for serial connection (default 115200)")
    parser.add_argument("--date", type=str, help="Date string for file import logs YYYY-MM-DD (defaults to today)")
    
    args = parser.parse_args()
    
    if args.file:
        process_log_file(args.file, target_date=args.date, db_path=args.db)
    elif args.port:
        read_serial_port(args.port, args.baud, db_path=args.db)

if __name__ == "__main__":
    main()
