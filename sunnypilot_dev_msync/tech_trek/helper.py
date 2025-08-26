import tty
import sys
import os
import termios
from typing import Optional
try:
    from bleak import BleakClient, BleakScanner
except Exception as e:
    raise RuntimeError("Bleak is required. Install with: pip install bleak") from e

# Nordic UART Service (matches the ESP32 sketch I gave you)
UART_SERVICE_UUID      = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_WRITE_CHAR_UUID   = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # write to ESP32 RX

def get_char():
    """Get a single character from stdin without pressing Enter"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def ns_to_ms(nanoseconds):
    """Convert nanoseconds to milliseconds"""
    return nanoseconds / 1e6

def get_data_directory():
    """Get the path to the data directory relative to this script"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    # Create data directory if it doesn't exist
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir


def resolve_filename(filename):
    """Resolve filename to check data directory first, then current directory"""
    if filename is None:
        return None

    # If it's an absolute path, use it as-is
    if os.path.isabs(filename):
        return filename

    # First check in the data directory
    data_dir = get_data_directory()
    data_path = os.path.join(data_dir, filename)
    if os.path.exists(data_path):
        return data_path

    # Then check in current directory
    if os.path.exists(filename):
        return filename

    # If file doesn't exist anywhere, default to data directory for new files
    return data_path

def map_command_to_seat_control(command_char):
    """Map scrubber command characters to seat control commands"""
    # Command mapping from scrubber.py
    lateral_command = 'neutral'
    longitudinal_command = 'neutral'

    if command_char == 'l':  # left
        lateral_command = 'mildLeft'
    elif command_char == 'r':  # right
        lateral_command = 'mildRight'
    elif command_char == '[':  # hard left
        lateral_command = 'hardLeft'
    elif command_char == ']':  # hard right
        lateral_command = 'hardRight'
    elif command_char == 'b':  # back
        longitudinal_command = 'back'
    elif command_char == 'f':  # forward
        longitudinal_command = 'forward'
    elif command_char == 'n':  # neutral
        lateral_command = 'neutral'
        longitudinal_command = 'neutral'

    return lateral_command, longitudinal_command

async def _connected(client: BleakClient) -> bool:
    """Return True if connected (works for both property and coroutine styles)."""
    val = getattr(client, "is_connected", None)
    if callable(val):          # older Bleak
        return await val()
    return bool(val)           # newer Bleak (property)
async def find_device(
    device_name: Optional[str] = None,
    device_address: Optional[str] = None,
    scan_timeout: float = 8.0,
):
    """Find a BLE device by name or address."""
    devs = await BleakScanner.discover(timeout=scan_timeout)
    if device_address:
        for d in devs:
            if d.address.lower() == device_address.lower():
                return d
    if device_name:
        for d in devs:
            if (d.name or "").strip() == device_name:
                return d
    raise RuntimeError("Target BLE device not found (check name/address and advertising).")
async def connect_ble(
    device_name: Optional[str] = "HapticPillow",
    device_address: Optional[str] = None,
    timeout: float = 10.0,
) -> BleakClient:
    """Scan and connect. Returns a connected BleakClient."""
    dev = await find_device(device_name, device_address)
    client = BleakClient(dev)
    print(f"[BLE] Connecting to {dev.name} @ {dev.address} ...")
    await client.connect(timeout=timeout)
    if not await _connected(client):
        raise RuntimeError("Failed to connect to BLE device.")
    print("[BLE] Connected.")
    return client
async def send_ble_command(
    client: BleakClient,
    cmd: str,
    write_char_uuid: str = UART_WRITE_CHAR_UUID,
    append_newline: bool = True,
    response: bool = False,
):
    """Send a short command string (e.g., 'L', 'R', 'B') to the ESP32."""
    payload = (cmd + "\n").encode("utf-8") if append_newline and not cmd.endswith("\n") else cmd.encode("utf-8")
    await client.write_gatt_char(write_char_uuid, payload, response=response)
    print(f"[BLE] Sent: {cmd!r}")
# Optional: a small convenience context manager
class BleHapticClient:
    def __init__(
        self,
        device_name: Optional[str] = "HapticPillow",
        device_address: Optional[str] = None,
        write_char_uuid: str = UART_WRITE_CHAR_UUID,
    ):
        self.device_name = device_name
        self.device_address = device_address
        self.write_char_uuid = write_char_uuid
        self.client: Optional[BleakClient] = None
    async def __aenter__(self):
        self.client = await connect_ble(self.device_name, self.device_address)
        return self
    async def __aexit__(self, exc_type, exc, tb):
        try:
            if self.client and await _connected(self.client):
                await self.client.disconnect()
        finally:
            self.client = None
    async def send(self, cmd: str):
        if not self.client or not await _connected(self.client):
            raise RuntimeError("BLE client not connected.")
        await send_ble_command(self.client, cmd, self.write_char_uuid)