from smbus2 import SMBus
import time
import sys

def get_user_setting(index, default):
    return int(sys.argv[index], 16) if len(sys.argv) > index else default

class AHTx0Error(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class AHTx0:
    AHTx0_I2CADDR = get_user_setting(1, 0x38)
    AHTx0_I2CBUS = get_user_setting(2, 1)  # Default value is 1 if not provided

    def __init__(self):
        # Initialize AHTx0
        self.cmd_soft_reset()
        
        # Check for calibration, if not done then do and wait 10 ms
        if not self.status_calibrated:
            self.cmd_initialize()
            while not self.status_calibrated:
                time.sleep(0.01)
    
    def cmd_soft_reset(self):
        # Send the command to soft reset
        with SMBus(self.AHTx0_I2CBUS) as i2c_bus:
            i2c_bus.write_i2c_block_data(self.AHTx0_I2CADDR, 0x0, [0xBA])
        time.sleep(0.04)    # Wait 40 ms after power on
    
    def cmd_initialize(self):
        # Send the command to initialize (calibrate)
        try:
            with SMBus(self.AHTx0_I2CBUS) as i2c_bus:
                i2c_bus.write_i2c_block_data(self.AHTx0_I2CADDR, 0x0 , [0xBE, 0x08, 0x00])
        except Exception as e:
            raise AHTx0Error(f"Failed to initialize the AHTx0 sensor: {e}")
    
    def cmd_measure(self):
        # Send the command to measure
        try:
            with SMBus(self.AHTx0_I2CBUS) as i2c_bus:
                i2c_bus.write_i2c_block_data(self.AHTx0_I2CADDR, 0, [0xAC, 0x33, 0x00])
        except Exception as e:
            raise AHTx0Error(f"Failed to measure with the AHTx0 sensor: {e}")
        time.sleep(0.08)    # Wait 80 ms after measure
    
    def get_status(self):
        # Get the full status byte
        with SMBus(self.AHTx0_I2CBUS) as i2c_bus:
            return i2c_bus.read_i2c_block_data(self.AHTx0_I2CADDR, 0x0, 1)[0]
    
    @property
    def status_calibrated(self):
        # Get the calibrated bit
        return (self.get_status() >> 3) & 1
    
    @property
    def status_busy(self):
        # Get the busy bit
        return (self.get_status() >> 7) & 1
    
    def get_measure(self):
        # Command a measure
        self.cmd_measure()
        
        # Check if busy bit = 0, otherwise wait 80 ms and retry
        while self.status_busy == 1:
            time.sleep(0.08) # Wait 80 ms
        
        # Read data and return it
        with SMBus(self.AHTx0_I2CBUS) as i2c_bus:
            data = i2c_bus.read_i2c_block_data(self.AHTx0_I2CADDR, 0x0, 7)
        Traw = ((data[3] & 0xf) << 16) + (data[4] << 8) + data[5]
        Hraw = ((data[3] & 0xf0) << 4) + (data[1] << 12) + (data[2] << 4)
        
        temperature = Traw / (pow(2, 20)) * 200 - 50
        humidity = Hraw * 100 / pow(2, 20)
        return temperature, humidity

def main():
    try:
        ahtx0 = AHTx0()
        temperature, humidity = ahtx0.get_measure()
        print('{0:0.1f} | {1:0.1f}'.format(temperature, humidity))
    except (IOError, OSError, ValueError):
        print('-1 | -1')

if __name__ == "__main__":
    main()
