#!/bin/bash
# ==============================================================================
# IntanWave Audio Server — Linux Docker Setup & Deployment Script
# PT Pelindo Multi Terminal — Tanjung Intan
# ==============================================================================

set -e

echo "=========================================================="
echo "   🔊 Menyiapkan IntanWave Audio Server (Linux Docker)    "
echo "=========================================================="

# 1. Pastikan Docker terinstall
if ! command -v docker &> /dev/null; then
    echo "[!] Docker tidak ditemukan. Silakan pasang Docker terlebih dahulu."
    exit 1
fi

# 2. Siapkan direktori storage & permissions
echo "[*] Menyiapkan direktori penyimpanan persistent..."
git update-index --assume-unchanged backend/storage/pa_system.db 2>/dev/null || true
git config core.filemode false 2>/dev/null || true
mkdir -p backend/storage/audio
chmod -R 775 backend/storage

# 3. Build & Jalankan Container via Docker Compose
echo "[*] Membangun image Docker & menjalankan container..."
if docker compose version &> /dev/null; then
    docker compose up -d --build
else
    docker-compose up -d --build
fi

echo ""
echo "=========================================================="
echo "   ✅ IntanWave Audio Server Berhasil Dijalankan!          "
echo "=========================================================="
echo "   🌐 Web Dashboard   : http://localhost:7080"
echo "   🌐 Akses dari Jaringan: http://$(hostname -I | awk '{print $1}'):7080"
echo "   📡 Multicast RTP   : rtp://239.255.0.1:5004"
echo "=========================================================="
echo "   Cek status container : docker compose ps"
echo "   Lihat log siaran     : docker compose logs -f"
echo "=========================================================="
