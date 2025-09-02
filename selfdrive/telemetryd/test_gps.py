from subscriber import *
import time

def main():
  while True:
    gps_data = get_imu()
    if gps_data:
      print(f"GPS Data: {gps_data}")
    else:
      print("No GPS Data Available")

    time.sleep(0.1)  # Adjust sleep as needed

if __name__ == "__main__":
  main()