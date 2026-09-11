#!/usr/bin/env bash
# ScalpKit — macOS / Linux uchun o'rnatish.
# Windows'da `install_windows.bat` ni ikki marta bosing.
set -euo pipefail

cd "$(dirname "$0")"
echo
echo "=================================================================="
echo "   SCALPKIT — AVTOMATIK O'RNATISH"
echo "=================================================================="
echo
echo "Papka: $(pwd)"
echo

# --- 1. Python ---
echo "[1/6] Python qidirilmoqda..."
PYEXE=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
            PYEXE="$candidate"
            break
        fi
    fi
done
if [ -z "$PYEXE" ]; then
    echo
    echo "  XATO: Python 3.10+ topilmadi."
    echo "  macOS:  brew install python@3.12"
    echo "  Ubuntu: sudo apt install python3 python3-venv python3-pip"
    echo
    exit 1
fi
echo "  topildi: $($PYEXE --version)"
echo

# --- 2. Virtual muhit ---
echo "[2/6] Virtual muhit (.venv) tayyorlanmoqda..."
if [ -x ".venv/bin/python" ]; then
    echo "  mavjud — qayta ishlatiladi"
else
    "$PYEXE" -m venv .venv
    echo "  yaratildi"
fi
VPY="$(pwd)/.venv/bin/python"
echo

# --- 3. pip ---
echo "[3/6] pip yangilanmoqda..."
"$VPY" -m pip install --quiet --upgrade pip setuptools wheel
echo "  tayyor"
echo

# --- 4. Kutubxonalar ---
echo "[4/6] Kutubxonalar o'rnatilmoqda..."
"$VPY" -m pip install --quiet -r requirements.txt
echo "  numpy, pandas, PyYAML, requests — tayyor"
"$VPY" -m pip install --quiet pytest
echo "  pytest — tayyor"
echo "  MetaTrader5 — o'tkazib yuborildi (u faqat Windows uchun)"
"$VPY" -m pip install --quiet -e .
echo

# --- 5. Tekshiruv ---
echo "[5/6] Testlar ishga tushirilmoqda..."
if "$VPY" -m pytest -q; then
    echo
    echo "  HAMMA TEST O'TDI"
else
    echo
    echo "  OGOHLANTIRISH: ba'zi testlar yiqildi — yuqoridagi matnni yuboring."
fi
echo

# --- 6. Qulaylik ---
echo "[6/6] scalpkit.sh yorlig'i yaratilmoqda..."
# Nomi `scalpkit` EMAS: shu papkada `scalpkit/` paketi turibdi va
# fayl bilan papka to'qnashadi.
cat > scalpkit.sh <<'WRAPPER'
#!/usr/bin/env bash
exec "$(dirname "$0")/.venv/bin/python" -m scalpkit "$@"
WRAPPER
chmod +x scalpkit.sh
echo "  tayyor"
echo

echo "=================================================================="
echo "   O'RNATILDI"
echo "=================================================================="
echo
echo "Endi shu papkada ishlatishingiz mumkin:"
echo
echo "   ./scalpkit.sh profiles"
echo "   ./scalpkit.sh costs --profile btcusd_5m"
echo "   ./scalpkit.sh backtest --profile btcusd_4h --data data/BTCUSD_5m.csv"
echo
echo "DIQQAT: MT5 ga ulanish (mt5-test, mt5-bars, trade) faqat Windows'da"
echo "ishlaydi — MetaTrader5 paketi boshqa tizimlarda mavjud emas."
echo
