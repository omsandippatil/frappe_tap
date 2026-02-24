#!/bin/bash
set -e


BENCH_DIR="/workspaces/frappe-bench"
SITE_NAME="tap.localhost"
APP_SOURCE="/workspaces/frappe_tap"
MYSQL_ROOT_PASSWORD="admin"


echo "=========================================="
echo "Complete Frappe Bench Setup"
echo "=========================================="
echo ""


# Function to start bench Redis services
start_bench_redis() {
    echo "Starting bench Redis services..."
    cd "$BENCH_DIR"
    fuser -k 11000/tcp 2>/dev/null || true
    fuser -k 12000/tcp 2>/dev/null || true
    fuser -k 13000/tcp 2>/dev/null || true
    sleep 2
    redis-server config/redis_cache.conf &
    redis-server config/redis_queue.conf &
    redis-server config/redis_socketio.conf &
    sleep 3
    redis-cli -p 11000 ping && redis-cli -p 12000 ping && redis-cli -p 13000 ping || {
        echo "Failed to start bench Redis services"
        exit 1
    }
    echo "✓ Bench Redis services started"
}


# Function to stop bench Redis services
stop_bench_redis() {
    echo "Stopping bench Redis services..."
    fuser -k 11000/tcp 2>/dev/null || true
    fuser -k 12000/tcp 2>/dev/null || true
    fuser -k 13000/tcp 2>/dev/null || true
    sleep 2
}


# Function to fix frappe.Model to Document imports
fix_frappe_model_imports() {
    echo "Fixing frappe.Model imports to use Document..."
    
    # Find all Python files that use frappe.Model
    find "$APP_SOURCE" -name "*.py" -type f -exec grep -l "frappe.Model" {} \; | while read -r file; do
        echo "  Fixing: $file"
        # Add Document import if not present
        if ! grep -q "from frappe.model.document import Document" "$file"; then
            # Check if there's already a frappe import
            if grep -q "^import frappe" "$file"; then
                sed -i '/^import frappe/a from frappe.model.document import Document' "$file"
            else
                # Add at the top after any existing imports
                sed -i '1i from frappe.model.document import Document' "$file"
            fi
        fi
        
        # Replace frappe.Model with Document
        sed -i 's/class \([^(]*\)(frappe\.Model)/class \1(Document)/g' "$file"
        echo "  ✓ Fixed: $file"
    done
    
    echo "✓ All frappe.Model references fixed"
}


# Function to manually copy app and register it
manual_app_install() {
    echo "Manually installing tap_lms app..."
    cd "$BENCH_DIR"
    
    # Remove any existing tap_lms
    rm -rf apps/tap_lms
    
    # Fix imports in source before copying
    fix_frappe_model_imports
    
    # Copy the entire app
    echo "Copying app from $APP_SOURCE to apps/tap_lms..."
    cp -r "$APP_SOURCE" apps/tap_lms
    
    # Verify the copy
    if [ -f "apps/tap_lms/tap_lms/tap_lms/doctype/curriculum/curriculum.json" ]; then
        echo "✓ curriculum.json found after manual copy"
        
        # Fix module name if needed
        MODULE_NAME=$(grep '"module"' apps/tap_lms/tap_lms/tap_lms/doctype/curriculum/curriculum.json | cut -d'"' -f4 | head -1)
        echo "  Module in JSON: '$MODULE_NAME'"
        
        if [ "$MODULE_NAME" != "Tap Lms" ]; then
            echo "  Fixing module name..."
            sed -i 's/"module": "[^"]*"/"module": "Tap Lms"/' apps/tap_lms/tap_lms/tap_lms/doctype/curriculum/curriculum.json
            echo "  ✓ Fixed to 'Tap Lms'"
        fi
    else
        echo "✗ curriculum.json still not found!"
        echo "Looking for files..."
        find apps/tap_lms -name "curriculum.json" || echo "No curriculum.json found anywhere"
    fi
    
    # Install in editable mode
    echo "Installing tap_lms package..."
    cd "$BENCH_DIR"
    ./env/bin/pip install -e apps/tap_lms
    
    # Add app to apps.txt - THIS IS THE CRITICAL FIX
    echo "Fixing apps.txt..."
    
    # Backup existing apps.txt if it exists
    if [ -f sites/apps.txt ]; then
        cp sites/apps.txt sites/apps.txt.bak
    fi
    
    # Recreate apps.txt with proper format
    cat > sites/apps.txt <<APPSFILE
frappe
tap_lms
APPSFILE
    
    echo "✓ apps.txt recreated with proper format"
    
    # Verify apps.txt
    echo "Current apps.txt content:"
    cat sites/apps.txt
    echo ""
    echo "Line count: $(wc -l < sites/apps.txt)"
}


# Check if this is a fresh install or restart
if [ -d "$BENCH_DIR" ]; then
    echo "=========================================="
    echo "EXISTING BENCH DETECTED - REINSTALLING APP"
    echo "=========================================="
    echo ""
    
    echo "Starting system services..."
    sudo pkill -9 redis-server 2>/dev/null || true
    sleep 2
    sudo redis-server /etc/redis/redis.conf &
    sleep 3
    
    sudo pkill -9 mysql 2>/dev/null || true
    sudo pkill -9 mariadbd 2>/dev/null || true
    sleep 3
    sudo /usr/sbin/mysqld --user=mysql --datadir=/var/lib/mysql --bind-address=127.0.0.1 &
    sleep 10
    
    start_bench_redis
    
    cd "$BENCH_DIR"
    
    # Use manual copy and register in apps.txt
    manual_app_install
    
    echo ""
    echo "Uninstalling old tap_lms from site..."
    bench --site "$SITE_NAME" uninstall-app tap_lms --yes --no-backup --force || true
    
    echo "Installing tap_lms to site..."
    bench --site "$SITE_NAME" install-app tap_lms
    
    echo "Forcing Curriculum DocType sync..."
    bench --site "$SITE_NAME" console <<'PYEOF'
import frappe
from frappe.modules import reload_doc
import json
import os


# Find curriculum.json
json_path = None
for root, dirs, files in os.walk('apps/tap_lms'):
    if 'curriculum.json' in files and 'curriculum' in root:
        json_path = os.path.join(root, 'curriculum.json')
        break


if json_path:
    print(f'Found curriculum.json at: {json_path}')
    
    # Read and check the JSON
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    print(f"Module in JSON: {data.get('module')}")
    print(f"Name in JSON: {data.get('name')}")
    
    # Try reload_doc
    try:
        reload_doc('tap_lms', 'doctype', 'curriculum', force=True)
        frappe.db.commit()
        print('✓ Curriculum reloaded via reload_doc')
    except Exception as e:
        print(f'reload_doc failed: {str(e)}')
        
        # Try manual creation
        try:
            # Ensure module is correct
            data['module'] = 'Tap Lms'
            doc = frappe.get_doc(data)
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            frappe.db.commit()
            print('✓ Curriculum manually inserted')
        except Exception as e2:
            print(f'✗ Manual insert failed: {str(e2)}')
else:
    print('✗ curriculum.json not found anywhere in apps/tap_lms')


# Final verification
try:
    doc = frappe.get_doc('DocType', 'Curriculum')
    print(f'\n✓✓✓ SUCCESS! Curriculum exists')
    print(f'Module: {doc.module}')
    print(f'Fields: {len(doc.fields)}')
except Exception as e:
    print(f'\n✗✗✗ Curriculum not found: {str(e)}')
    print('\nAll Tap Lms DocTypes:')
    for dt in frappe.get_all('DocType', filters={'module': 'Tap Lms'}, fields=['name']):
        print(f'  - {dt.name}')
PYEOF
    
    echo ""
    echo "Running migration..."
    bench --site "$SITE_NAME" migrate --skip-search-index
    
    echo "Clearing caches..."
    bench --site "$SITE_NAME" clear-cache
    bench --site "$SITE_NAME" clear-website-cache
    
    echo "Rebuilding search index..."
    bench --site "$SITE_NAME" build-search-index
    
    echo "Building assets..."
    bench build --app tap_lms
    
    stop_bench_redis
    
    echo ""
    echo "=========================================="
    echo "REINSTALL COMPLETE!"
    echo "=========================================="
    echo ""
    echo "Site: https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    echo ""
    echo "Starting bench..."
    bench start
    exit 0
fi


echo "=========================================="
echo "FRESH INSTALLATION"
echo "=========================================="
echo ""


echo "Installing system dependencies..."
# Remove yarn repository if it exists to avoid GPG errors
sudo rm -f /etc/apt/sources.list.d/yarn.list 2>/dev/null || true


sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3-pip python3-dev python3-venv python3-setuptools \
    redis-server mariadb-server mariadb-client \
    libmariadb-dev libmariadb-dev-compat \
    git curl cron wkhtmltopdf xvfb libfontconfig1 software-properties-common


echo "Installing Node.js 18..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs


echo "Installing Yarn via npm..."
sudo npm install -g yarn


echo "Configuring Redis..."
sudo pkill -9 redis-server 2>/dev/null || true
sleep 2


sudo tee /etc/redis/redis.conf > /dev/null <<'REDISCONF'
bind 127.0.0.1
port 6379
protected-mode yes
daemonize no
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log
dir /var/lib/redis
save ""
stop-writes-on-bgsave-error no
rdbcompression yes
rdbchecksum yes
REDISCONF


sudo mkdir -p /var/run/redis /var/lib/redis /var/log/redis
sudo chown -R redis:redis /var/run/redis /var/lib/redis /var/log/redis
sudo chmod 755 /var/run/redis /var/lib/redis /var/log/redis


echo "Starting Redis..."
sudo redis-server /etc/redis/redis.conf &
sleep 3


redis-cli ping || {
    echo "Redis failed to start"
    exit 1
}


echo "Configuring MySQL..."
sudo pkill -9 mysql 2>/dev/null || true
sudo pkill -9 mariadbd 2>/dev/null || true
sleep 3


sudo rm -rf /var/lib/mysql/*
sudo rm -rf /var/run/mysqld/*


sudo mkdir -p /etc/mysql/mariadb.conf.d
sudo tee /etc/mysql/mariadb.conf.d/99-custom.cnf > /dev/null <<'MYSQLCONF'
[mysqld]
bind-address = 127.0.0.1
port = 3306
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
max_allowed_packet = 256M
innodb_file_per_table = 1
innodb_buffer_pool_size = 256M
skip-grant-tables
MYSQLCONF


sudo mkdir -p /var/run/mysqld /var/lib/mysql
sudo chown -R mysql:mysql /var/run/mysqld /var/lib/mysql


echo "Initializing MySQL..."
sudo mysql_install_db --user=mysql --datadir=/var/lib/mysql


echo "Starting MySQL..."
sudo /usr/sbin/mysqld --user=mysql --datadir=/var/lib/mysql --bind-address=127.0.0.1 &
sleep 10


for i in {1..30}; do
    if mysqladmin ping -h 127.0.0.1 --silent 2>/dev/null; then
        echo "MySQL started"
        break
    fi
    sleep 2
done


echo "Setting up root password..."
mysql -u root -h 127.0.0.1 <<EOF
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY '$MYSQL_ROOT_PASSWORD';
CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY '$MYSQL_ROOT_PASSWORD';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;
FLUSH PRIVILEGES;
EOF


echo "Restarting MySQL in normal mode..."
sudo pkill -9 mysql 2>/dev/null || true
sudo pkill -9 mariadbd 2>/dev/null || true
sleep 3


sudo tee /etc/mysql/mariadb.conf.d/99-custom.cnf > /dev/null <<'MYSQLCONF'
[mysqld]
bind-address = 127.0.0.1
port = 3306
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
max_allowed_packet = 256M
innodb_file_per_table = 1
innodb_buffer_pool_size = 256M
MYSQLCONF


sudo /usr/sbin/mysqld --user=mysql --datadir=/var/lib/mysql --bind-address=127.0.0.1 &
sleep 10


for i in {1..30}; do
    if mysqladmin ping -h 127.0.0.1 --silent 2>/dev/null; then
        echo "MySQL restarted"
        break
    fi
    sleep 2
done


mysql -u root -p${MYSQL_ROOT_PASSWORD} -h 127.0.0.1 -e "SELECT 1;" || {
    echo "Failed to connect to MySQL"
    exit 1
}


echo "Installing Frappe Bench..."
pip3 install --upgrade pip setuptools wheel
pip3 install frappe-bench


if [ -d "$BENCH_DIR" ]; then
    rm -rf "$BENCH_DIR"
fi


echo "Initializing bench..."
bench init "$BENCH_DIR" --frappe-branch version-15 --python python3


cd "$BENCH_DIR"


echo "Configuring Redis for bench..."
mkdir -p config/pids logs


cat > config/redis_cache.conf <<REDISCACHE
port 13000
bind 127.0.0.1
pidfile $BENCH_DIR/config/pids/redis_cache.pid
logfile $BENCH_DIR/logs/redis_cache.log
dir $BENCH_DIR/config/pids
save ""
stop-writes-on-bgsave-error no
REDISCACHE


cat > config/redis_queue.conf <<REDISQUEUE
port 11000
bind 127.0.0.1
pidfile $BENCH_DIR/config/pids/redis_queue.pid
logfile $BENCH_DIR/logs/redis_queue.log
dir $BENCH_DIR/config/pids
save ""
stop-writes-on-bgsave-error no
REDISQUEUE


cat > config/redis_socketio.conf <<REDISSOCKETIO
port 12000
bind 127.0.0.1
pidfile $BENCH_DIR/config/pids/redis_socketio.pid
logfile $BENCH_DIR/logs/redis_socketio.log
dir $BENCH_DIR/config/pids
save ""
stop-writes-on-bgsave-error no
REDISSOCKETIO


start_bench_redis


# Use manual copy and register in apps.txt
manual_app_install


echo "Creating site..."
bench new-site "$SITE_NAME" \
    --admin-password admin \
    --mariadb-root-password ${MYSQL_ROOT_PASSWORD} \
    --db-host 127.0.0.1


python3 <<PYEOF
import json
config_path = "sites/$SITE_NAME/site_config.json"
with open(config_path, 'r') as f:
    config = json.load(f)
config.update({
    "developer_mode": 1,
    "disable_website_cache": 1,
    "host_name": "https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
})
with open(config_path, 'w') as f:
    json.dump(config, f, indent=1)
PYEOF


echo "$SITE_NAME" > sites/currentsite.txt
bench use "$SITE_NAME"


echo "Installing tap_lms to site..."
bench --site "$SITE_NAME" install-app tap_lms


echo "Forcing Curriculum DocType sync..."
bench --site "$SITE_NAME" console <<'PYEOF'
import frappe
from frappe.modules import reload_doc
import json
import os


# Find curriculum.json
json_path = None
for root, dirs, files in os.walk('apps/tap_lms'):
    if 'curriculum.json' in files and 'curriculum' in root:
        json_path = os.path.join(root, 'curriculum.json')
        break


if json_path:
    print(f'Found curriculum.json at: {json_path}')
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    print(f"Module: {data.get('module')}")
    
    try:
        reload_doc('tap_lms', 'doctype', 'curriculum', force=True)
        frappe.db.commit()
        print('✓ Curriculum reloaded')
    except Exception as e:
        print(f'reload_doc failed: {str(e)}')
        try:
            data['module'] = 'Tap Lms'
            doc = frappe.get_doc(data)
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            frappe.db.commit()
            print('✓ Curriculum manually created')
        except Exception as e2:
            print(f'✗ Failed: {str(e2)}')
else:
    print('✗ curriculum.json not found')


try:
    doc = frappe.get_doc('DocType', 'Curriculum')
    print(f'\n✓✓✓ Curriculum exists! Module: {doc.module}')
except:
    print('\n✗✗✗ Curriculum not found')
PYEOF


echo "Running migration..."
bench --site "$SITE_NAME" migrate --skip-search-index


bench --site "$SITE_NAME" clear-cache
bench --site "$SITE_NAME" clear-website-cache
bench --site "$SITE_NAME" build-search-index


echo "Building assets..."
bench build --app tap_lms


echo "Setting up socketio..."
bench setup socketio


stop_bench_redis


echo ""
echo "=========================================="
echo "INSTALLATION COMPLETE!"
echo "=========================================="
echo ""
echo "Site: https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
echo ""
echo "Login:"
echo "  Username: Administrator"
echo "  Password: admin"
echo ""
echo "=========================================="
echo "Starting Frappe Bench..."
echo "=========================================="
echo ""


bench start

