#!/bin/bash
export PATH=$PREFIX/bin:$PATH
pkg install -y python
pip install --upgrade pip
pip install flask psutil httpx google-generativeai python-dotenv

mkdir -p ~/.termux/boot
cat << 'BOOT' > ~/.termux/boot/start_life_companion.sh
#!/bin/bash
termux-wake-lock
/data/data/com.termux/files/home/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_daemon.sh start
BOOT
chmod +x ~/.termux/boot/start_life_companion.sh

# Modify screen_life_daemon.sh to use Termux paths
sed -i 's|/Volumes/Lauburu-Monorepo/|/data/data/com.termux/files/home/|g' ~/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_daemon.sh
sed -i 's|/Users/aaron/\.lauburu|/data/data/com.termux/files/home/.lauburu|g' ~/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_daemon.sh

~/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_daemon.sh restart
