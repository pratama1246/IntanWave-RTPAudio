import sys
import os
from pathlib import Path

# Set Python path to backend
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7080"))
    print("=" * 60)
    print("   [*] IntanWave Audio Server")
    print(f"   [*] Akses Web Dashboard : http://localhost:{port}")
    print(f"   [*] Akses dari LAN / HP : http://<IP-PC-INI>:{port}")
    print("   [*] FFmpeg Multicast    : rtp://239.255.0.1:5004")
    print("=" * 60)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
