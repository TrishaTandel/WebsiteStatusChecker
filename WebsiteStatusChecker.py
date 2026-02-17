import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import socket
import ssl
import subprocess
import platform
import threading
import time
import json
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from collections import deque
import os
import re

# For notifications
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

# For charts
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class DatabaseManager:
    """Handle all database operations for history logging"""
    
    def __init__(self, db_name="website_monitor.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Websites table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS websites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                name TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Check history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS check_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_id INTEGER,
                status TEXT,
                status_code INTEGER,
                response_time REAL,
                check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (website_id) REFERENCES websites(id)
            )
        ''')
        
        # SSL certificates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ssl_certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_id INTEGER,
                issuer TEXT,
                subject TEXT,
                valid_from TIMESTAMP,
                valid_until TIMESTAMP,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (website_id) REFERENCES websites(id)
            )
        ''')
        
        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_id INTEGER,
                alert_type TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER DEFAULT 0,
                FOREIGN KEY (website_id) REFERENCES websites(id)
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_website(self, url, name=None):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO websites (url, name) VALUES (?, ?)", 
                          (url, name or url))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def get_websites(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM websites WHERE is_active = 1")
        websites = cursor.fetchall()
        conn.close()
        return websites
    
    def add_check_history(self, website_id, status, status_code, response_time, error_message=None):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO check_history 
            (website_id, status, status_code, response_time, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (website_id, status, status_code, response_time, error_message))
        conn.commit()
        conn.close()
    
    def get_check_history(self, website_id=None, limit=100):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        if website_id:
            cursor.execute('''
                SELECT ch.*, w.url FROM check_history ch
                JOIN websites w ON ch.website_id = w.id
                WHERE website_id = ?
                ORDER BY check_time DESC LIMIT ?
            ''', (website_id, limit))
        else:
            cursor.execute('''
                SELECT ch.*, w.url FROM check_history ch
                JOIN websites w ON ch.website_id = w.id
                ORDER BY check_time DESC LIMIT ?
            ''', (limit,))
        history = cursor.fetchall()
        conn.close()
        return history
    
    def save_ssl_info(self, website_id, issuer, subject, valid_from, valid_until):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO ssl_certificates 
            (website_id, issuer, subject, valid_from, valid_until, last_checked)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (website_id, issuer, subject, valid_from, valid_until))
        conn.commit()
        conn.close()
    
    def add_alert(self, website_id, alert_type, message):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alerts (website_id, alert_type, message)
            VALUES (?, ?, ?)
        ''', (website_id, alert_type, message))
        conn.commit()
        conn.close()
    
    def get_alerts(self, unread_only=False, limit=50):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        if unread_only:
            cursor.execute('''
                SELECT a.*, w.url FROM alerts a
                JOIN websites w ON a.website_id = w.id
                WHERE is_read = 0
                ORDER BY created_at DESC LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT a.*, w.url FROM alerts a
                JOIN websites w ON a.website_id = w.id
                ORDER BY created_at DESC LIMIT ?
            ''', (limit,))
        alerts = cursor.fetchall()
        conn.close()
        return alerts
    
    def mark_alerts_read(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("UPDATE alerts SET is_read = 1")
        conn.commit()
        conn.close()
    
    def get_uptime_stats(self, website_id, days=7):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Online' THEN 1 ELSE 0 END) as online_count,
                AVG(response_time) as avg_response_time
            FROM check_history
            WHERE website_id = ? 
            AND check_time >= datetime('now', ?)
        ''', (website_id, f'-{days} days'))
        stats = cursor.fetchone()
        conn.close()
        return stats
    
    def delete_website(self, website_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("UPDATE websites SET is_active = 0 WHERE id = ?", (website_id,))
        conn.commit()
        conn.close()
    
    def get_website_id(self, url):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM websites WHERE url = ?", (url,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def clear_old_history(self, days=30):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM check_history 
            WHERE check_time < datetime('now', ?)
        ''', (f'-{days} days',))
        conn.commit()
        conn.close()


class NotificationManager:
    """Handle all types of notifications"""
    
    def __init__(self):
        self.email_config = {
            'enabled': False,
            'smtp_server': '',
            'smtp_port': 587,
            'username': '',
            'password': '',
            'recipient': ''
        }
    
    def send_desktop_notification(self, title, message, timeout=10):
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    timeout=timeout,
                    app_icon=None
                )
            except Exception as e:
                print(f"Notification error: {e}")
        else:
            # Fallback for Windows
            if platform.system() == "Windows":
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(title, message, duration=timeout, threaded=True)
                except:
                    pass
    
    def send_email_alert(self, subject, message):
        if not self.email_config['enabled']:
            return False
        
        try:
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = self.email_config['username']
            msg['To'] = self.email_config['recipient']
            
            server = smtplib.SMTP(self.email_config['smtp_server'], 
                                  self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], 
                        self.email_config['password'])
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False
    
    def configure_email(self, smtp_server, smtp_port, username, password, recipient):
        self.email_config = {
            'enabled': True,
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'username': username,
            'password': password,
            'recipient': recipient
        }


class WebsiteChecker:
    """Core checking functionality"""
    
    @staticmethod
    def check_http(url, timeout=10):
        """Check HTTP/HTTPS status"""
        try:
            start_time = time.time()
            response = requests.get(url, timeout=timeout, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }, allow_redirects=True, verify=True)
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                'status': 'Online' if response.status_code == 200 else 'Error',
                'status_code': response.status_code,
                'response_time': response_time,
                'headers': dict(response.headers),
                'redirect_url': response.url if response.url != url else None,
                'content_length': len(response.content),
                'error': None
            }
        except requests.exceptions.Timeout:
            return {'status': 'Timeout', 'status_code': None, 'response_time': None, 'error': 'Connection timed out'}
        except requests.exceptions.SSLError as e:
            return {'status': 'SSL Error', 'status_code': None, 'response_time': None, 'error': str(e)}
        except requests.exceptions.ConnectionError:
            return {'status': 'Offline', 'status_code': None, 'response_time': None, 'error': 'Connection failed'}
        except Exception as e:
            return {'status': 'Error', 'status_code': None, 'response_time': None, 'error': str(e)}
    
    @staticmethod
    def ping(host, count=4):
        """Ping a host"""
        try:
            # Extract hostname from URL
            if host.startswith(('http://', 'https://')):
                host = host.split('//')[1].split('/')[0]
            
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            command = ['ping', param, str(count), host]
            
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            output = result.stdout
            
            # Parse ping results
            if platform.system().lower() == 'windows':
                # Windows parsing
                match = re.search(r'Average = (\d+)ms', output)
                avg_time = float(match.group(1)) if match else None
                
                match = re.search(r'Lost = (\d+)', output)
                packet_loss = int(match.group(1)) if match else 0
            else:
                # Linux/Mac parsing
                match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)/', output)
                avg_time = float(match.group(1)) if match else None
                
                match = re.search(r'(\d+)% packet loss', output)
                packet_loss = int(match.group(1)) if match else 0
            
            return {
                'success': result.returncode == 0,
                'avg_time': avg_time,
                'packet_loss': packet_loss,
                'output': output
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'avg_time': None, 'packet_loss': 100, 'output': 'Ping timeout'}
        except Exception as e:
            return {'success': False, 'avg_time': None, 'packet_loss': 100, 'output': str(e)}
    
    @staticmethod
    def check_ssl(url):
        """Check SSL certificate details"""
        try:
            if not url.startswith('https://'):
                return {'valid': False, 'error': 'Not HTTPS'}
            
            hostname = url.split('//')[1].split('/')[0]
            context = ssl.create_default_context()
            
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Parse dates
                    not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    
                    # Calculate days until expiry
                    days_until_expiry = (not_after - datetime.now()).days
                    
                    # Get issuer and subject
                    issuer = dict(x[0] for x in cert['issuer'])
                    subject = dict(x[0] for x in cert['subject'])
                    
                    return {
                        'valid': True,
                        'issuer': issuer.get('organizationName', 'Unknown'),
                        'subject': subject.get('commonName', hostname),
                        'valid_from': not_before.strftime('%Y-%m-%d'),
                        'valid_until': not_after.strftime('%Y-%m-%d'),
                        'days_until_expiry': days_until_expiry,
                        'is_expired': days_until_expiry < 0,
                        'expiring_soon': 0 < days_until_expiry <= 30,
                        'serial_number': cert.get('serialNumber', 'Unknown'),
                        'version': cert.get('version', 'Unknown')
                    }
        except ssl.SSLCertVerificationError as e:
            return {'valid': False, 'error': f'SSL Verification Error: {e}'}
        except socket.timeout:
            return {'valid': False, 'error': 'Connection timeout'}
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    @staticmethod
    def check_port(host, port, timeout=5):
        """Check if a specific port is open"""
        try:
            if host.startswith(('http://', 'https://')):
                host = host.split('//')[1].split('/')[0]
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            return {'port': port, 'open': result == 0}
        except Exception as e:
            return {'port': port, 'open': False, 'error': str(e)}
    
    @staticmethod
    def dns_lookup(hostname):
        """Perform DNS lookup"""
        try:
            if hostname.startswith(('http://', 'https://')):
                hostname = hostname.split('//')[1].split('/')[0]
            
            ip_addresses = socket.gethostbyname_ex(hostname)
            return {
                'hostname': ip_addresses[0],
                'aliases': ip_addresses[1],
                'ip_addresses': ip_addresses[2]
            }
        except socket.gaierror as e:
            return {'error': str(e)}


class WebsiteMonitor(tk.Tk):
    """Main Application GUI"""
    
    def __init__(self):
        super().__init__()
        
        self.title("🌐 Website Status Monitor")
        self.geometry("1400x800")
        self.configure(bg="#0f0f1a")
        
        # Initialize components
        self.db = DatabaseManager()
        self.notifier = NotificationManager()
        self.checker = WebsiteChecker()
        
        # State variables
        self.auto_refresh = False
        self.refresh_interval = 60
        self.websites = {}  # url -> website_id mapping
        self.check_threads = []
        self.response_times = {}  # url -> deque of recent response times
        
        # Setup UI
        self.setup_styles()
        self.create_menu()
        self.create_main_ui()
        self.load_websites()
        
        # Start background tasks
        self.update_clock()
        
        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Configure ttk styles"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Colors
        self.colors = {
            'bg_dark': '#0f0f1a',
            'bg_medium': '#1a1a2e',
            'bg_light': '#252540',
            'accent': '#e94560',
            'accent2': '#0f3460',
            'success': '#00d26a',
            'warning': '#ffc107',
            'error': '#ff4757',
            'text': '#ffffff',
            'text_dim': '#8892b0'
        }
        
        self.style.configure("TFrame", background=self.colors['bg_dark'])
        self.style.configure("Card.TFrame", background=self.colors['bg_medium'])
        self.style.configure("TLabel", background=self.colors['bg_dark'], 
                           foreground=self.colors['text'])
        self.style.configure("Card.TLabel", background=self.colors['bg_medium'],
                           foreground=self.colors['text'])
        self.style.configure("TNotebook", background=self.colors['bg_dark'])
        self.style.configure("TNotebook.Tab", background=self.colors['bg_medium'],
                           foreground=self.colors['text'], padding=[15, 8])
        self.style.map("TNotebook.Tab", background=[("selected", self.colors['accent'])])
        
        # Treeview style
        self.style.configure("Custom.Treeview",
                           background=self.colors['bg_medium'],
                           foreground=self.colors['text'],
                           fieldbackground=self.colors['bg_medium'],
                           rowheight=35)
        self.style.configure("Custom.Treeview.Heading",
                           background=self.colors['accent2'],
                           foreground=self.colors['text'],
                           font=('Arial', 10, 'bold'))
        self.style.map("Custom.Treeview", background=[("selected", self.colors['accent'])])
    
    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self, bg=self.colors['bg_medium'], fg=self.colors['text'])
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_medium'], 
                           fg=self.colors['text'])
        file_menu.add_command(label="📥 Import URLs", command=self.import_urls)
        file_menu.add_command(label="📤 Export Results", command=self.export_results)
        file_menu.add_command(label="📊 Export History", command=self.export_history)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Exit", command=self.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_medium'],
                               fg=self.colors['text'])
        settings_menu.add_command(label="📧 Email Notifications", command=self.configure_email)
        settings_menu.add_command(label="⏰ Auto-Refresh Settings", command=self.configure_refresh)
        settings_menu.add_command(label="🧹 Clear Old History", command=self.clear_old_history)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_medium'],
                           fg=self.colors['text'])
        help_menu.add_command(label="📖 About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=menubar)
    
    def create_main_ui(self):
        """Create the main user interface"""
        # Header
        header_frame = tk.Frame(self, bg=self.colors['accent2'], height=70)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title = tk.Label(header_frame, text="🌐 Website Status Monitor",
                        font=("Arial", 22, "bold"), bg=self.colors['accent2'],
                        fg=self.colors['text'])
        title.pack(side="left", padx=20, pady=15)
        
        # Clock
        self.clock_label = tk.Label(header_frame, font=("Arial", 12),
                                   bg=self.colors['accent2'], fg=self.colors['text'])
        self.clock_label.pack(side="right", padx=20)
        
        # Status indicator
        self.status_indicator = tk.Label(header_frame, text="● Ready",
                                        font=("Arial", 11), bg=self.colors['accent2'],
                                        fg=self.colors['success'])
        self.status_indicator.pack(side="right", padx=20)
        
        # Main container with notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_websites_tab()
        self.create_history_tab()
        self.create_ssl_tab()
        self.create_ping_tab()
        self.create_alerts_tab()
        
        # Status bar
        self.status_bar = tk.Label(self, text="Ready | Websites: 0 | Last check: Never",
                                  bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                                  anchor="w", padx=10, pady=5)
        self.status_bar.pack(side="bottom", fill="x")
    
    def create_dashboard_tab(self):
        """Create dashboard tab with statistics"""
        dashboard = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(dashboard, text="📊 Dashboard")
        
        # Stats cards
        stats_frame = tk.Frame(dashboard, bg=self.colors['bg_dark'])
        stats_frame.pack(fill="x", padx=20, pady=20)
        
        # Card 1 - Total Websites
        self.card_total = self.create_stat_card(stats_frame, "Total Websites", "0", "🌐")
        self.card_total.pack(side="left", padx=10, expand=True, fill="both")
        
        # Card 2 - Online
        self.card_online = self.create_stat_card(stats_frame, "Online", "0", "✅", self.colors['success'])
        self.card_online.pack(side="left", padx=10, expand=True, fill="both")
        
        # Card 3 - Offline
        self.card_offline = self.create_stat_card(stats_frame, "Offline", "0", "❌", self.colors['error'])
        self.card_offline.pack(side="left", padx=10, expand=True, fill="both")
        
        # Card 4 - Avg Response Time
        self.card_response = self.create_stat_card(stats_frame, "Avg Response", "0 ms", "⚡")
        self.card_response.pack(side="left", padx=10, expand=True, fill="both")
        
        # Card 5 - SSL Expiring
        self.card_ssl = self.create_stat_card(stats_frame, "SSL Expiring Soon", "0", "🔒", self.colors['warning'])
        self.card_ssl.pack(side="left", padx=10, expand=True, fill="both")
        
        # Chart area
        chart_frame = tk.Frame(dashboard, bg=self.colors['bg_medium'])
        chart_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        if MATPLOTLIB_AVAILABLE:
            self.create_charts(chart_frame)
        else:
            tk.Label(chart_frame, text="Install matplotlib for charts:\npip install matplotlib",
                    font=("Arial", 14), bg=self.colors['bg_medium'],
                    fg=self.colors['text_dim']).pack(expand=True)
    
    def create_stat_card(self, parent, title, value, icon, color=None):
        """Create a statistics card"""
        card = tk.Frame(parent, bg=self.colors['bg_medium'], padx=20, pady=15)
        
        tk.Label(card, text=icon, font=("Arial", 24),
                bg=self.colors['bg_medium'], fg=color or self.colors['accent']).pack()
        
        value_label = tk.Label(card, text=value, font=("Arial", 28, "bold"),
                              bg=self.colors['bg_medium'], 
                              fg=color or self.colors['text'])
        value_label.pack()
        card.value_label = value_label
        
        tk.Label(card, text=title, font=("Arial", 11),
                bg=self.colors['bg_medium'], fg=self.colors['text_dim']).pack()
        
        return card
    
    def create_charts(self, parent):
        """Create matplotlib charts"""
        fig = Figure(figsize=(12, 4), facecolor=self.colors['bg_medium'])
        
        # Response time chart
        self.ax1 = fig.add_subplot(121)
        self.ax1.set_facecolor(self.colors['bg_dark'])
        self.ax1.set_title("Response Times", color=self.colors['text'])
        self.ax1.tick_params(colors=self.colors['text_dim'])
        
        # Status distribution chart
        self.ax2 = fig.add_subplot(122)
        self.ax2.set_facecolor(self.colors['bg_dark'])
        self.ax2.set_title("Status Distribution", color=self.colors['text'])
        
        self.canvas = FigureCanvasTkAgg(fig, parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def create_websites_tab(self):
        """Create websites management tab"""
        websites_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(websites_tab, text="🌐 Websites")
        
        # Controls frame
        controls = tk.Frame(websites_tab, bg=self.colors['bg_dark'])
        controls.pack(fill="x", padx=20, pady=15)
        
        # URL Entry
        tk.Label(controls, text="URL:", font=("Arial", 11),
                bg=self.colors['bg_dark'], fg=self.colors['text']).pack(side="left", padx=5)
        
        self.url_entry = tk.Entry(controls, width=50, font=("Arial", 11),
                                 bg=self.colors['bg_light'], fg=self.colors['text'],
                                 insertbackground=self.colors['text'])
        self.url_entry.pack(side="left", padx=5)
        self.url_entry.insert(0, "https://")
        self.url_entry.bind("<Return>", lambda e: self.add_website())
        
        # Buttons
        self.create_button(controls, "➕ Add", self.add_website, self.colors['success']).pack(side="left", padx=5)
        self.create_button(controls, "🔍 Check All", self.check_all_websites, "#2196F3").pack(side="left", padx=5)
        self.create_button(controls, "🔍 Check Selected", self.check_selected, "#9c27b0").pack(side="left", padx=5)
        self.create_button(controls, "🗑️ Remove", self.remove_website, self.colors['error']).pack(side="left", padx=5)
        
        # Auto-refresh toggle
        self.auto_refresh_var = tk.BooleanVar()
        auto_check = tk.Checkbutton(controls, text="Auto-Refresh", variable=self.auto_refresh_var,
                                    command=self.toggle_auto_refresh, bg=self.colors['bg_dark'],
                                    fg=self.colors['text'], selectcolor=self.colors['bg_light'],
                                    font=("Arial", 10))
        auto_check.pack(side="right", padx=10)
        
        # Treeview
        tree_frame = tk.Frame(websites_tab, bg=self.colors['bg_dark'])
        tree_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        columns = ("URL", "Status", "Code", "Response Time", "Last Check", "Uptime")
        self.websites_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                         style="Custom.Treeview")
        
        for col in columns:
            self.websites_tree.heading(col, text=col, 
                                       command=lambda c=col: self.sort_treeview(self.websites_tree, c))
        
        self.websites_tree.column("URL", width=300)
        self.websites_tree.column("Status", width=100, anchor="center")
        self.websites_tree.column("Code", width=60, anchor="center")
        self.websites_tree.column("Response Time", width=120, anchor="center")
        self.websites_tree.column("Last Check", width=150, anchor="center")
        self.websites_tree.column("Uptime", width=100, anchor="center")
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.websites_tree.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.websites_tree.xview)
        self.websites_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.websites_tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        
        # Tags for colors
        self.websites_tree.tag_configure("online", foreground=self.colors['success'])
        self.websites_tree.tag_configure("offline", foreground=self.colors['error'])
        self.websites_tree.tag_configure("warning", foreground=self.colors['warning'])
        
        # Context menu
        self.create_context_menu()
    
    def create_history_tab(self):
        """Create history tab"""
        history_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(history_tab, text="📜 History")
        
        # Filter controls
        filter_frame = tk.Frame(history_tab, bg=self.colors['bg_dark'])
        filter_frame.pack(fill="x", padx=20, pady=15)
        
        tk.Label(filter_frame, text="Filter:", font=("Arial", 11),
                bg=self.colors['bg_dark'], fg=self.colors['text']).pack(side="left", padx=5)
        
        self.history_filter = ttk.Combobox(filter_frame, values=["All", "Online", "Offline", "Errors"],
                                          state="readonly", width=15)
        self.history_filter.set("All")
        self.history_filter.pack(side="left", padx=5)
        self.history_filter.bind("<<ComboboxSelected>>", lambda e: self.load_history())
        
        self.create_button(filter_frame, "🔄 Refresh", self.load_history, "#2196F3").pack(side="left", padx=10)
        self.create_button(filter_frame, "🗑️ Clear Old", 
                          lambda: self.clear_old_history(30), self.colors['warning']).pack(side="left", padx=5)
        
        # History treeview
        history_frame = tk.Frame(history_tab, bg=self.colors['bg_dark'])
        history_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        columns = ("Time", "URL", "Status", "Code", "Response Time", "Error")
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show="headings",
                                        style="Custom.Treeview")
        
        for col in columns:
            self.history_tree.heading(col, text=col)
        
        self.history_tree.column("Time", width=150)
        self.history_tree.column("URL", width=250)
        self.history_tree.column("Status", width=100, anchor="center")
        self.history_tree.column("Code", width=60, anchor="center")
        self.history_tree.column("Response Time", width=120, anchor="center")
        self.history_tree.column("Error", width=200)
        
        v_scroll = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=v_scroll.set)
        
        self.history_tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        
        self.history_tree.tag_configure("online", foreground=self.colors['success'])
        self.history_tree.tag_configure("offline", foreground=self.colors['error'])
    
    def create_ssl_tab(self):
        """Create SSL certificates tab"""
        ssl_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(ssl_tab, text="🔒 SSL Certificates")
        
        # Controls
        controls = tk.Frame(ssl_tab, bg=self.colors['bg_dark'])
        controls.pack(fill="x", padx=20, pady=15)
        
        self.create_button(controls, "🔍 Check All SSL", self.check_all_ssl, "#2196F3").pack(side="left", padx=5)
        self.create_button(controls, "🔍 Check Selected", self.check_selected_ssl, "#9c27b0").pack(side="left", padx=5)
        
        # SSL Treeview
        ssl_frame = tk.Frame(ssl_tab, bg=self.colors['bg_dark'])
        ssl_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        columns = ("URL", "Issuer", "Valid From", "Valid Until", "Days Left", "Status")
        self.ssl_tree = ttk.Treeview(ssl_frame, columns=columns, show="headings",
                                    style="Custom.Treeview")
        
        for col in columns:
            self.ssl_tree.heading(col, text=col)
        
        self.ssl_tree.column("URL", width=250)
        self.ssl_tree.column("Issuer", width=200)
        self.ssl_tree.column("Valid From", width=120, anchor="center")
        self.ssl_tree.column("Valid Until", width=120, anchor="center")
        self.ssl_tree.column("Days Left", width=100, anchor="center")
        self.ssl_tree.column("Status", width=120, anchor="center")
        
        v_scroll = ttk.Scrollbar(ssl_frame, orient="vertical", command=self.ssl_tree.yview)
        self.ssl_tree.configure(yscrollcommand=v_scroll.set)
        
        self.ssl_tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        
        self.ssl_tree.tag_configure("valid", foreground=self.colors['success'])
        self.ssl_tree.tag_configure("expiring", foreground=self.colors['warning'])
        self.ssl_tree.tag_configure("expired", foreground=self.colors['error'])
    
    def create_ping_tab(self):
        """Create ping monitoring tab"""
        ping_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(ping_tab, text="📡 Ping Monitor")
        
        # Controls
        controls = tk.Frame(ping_tab, bg=self.colors['bg_dark'])
        controls.pack(fill="x", padx=20, pady=15)
        
        tk.Label(controls, text="Host:", font=("Arial", 11),
                bg=self.colors['bg_dark'], fg=self.colors['text']).pack(side="left", padx=5)
        
        self.ping_entry = tk.Entry(controls, width=40, font=("Arial", 11),
                                  bg=self.colors['bg_light'], fg=self.colors['text'],
                                  insertbackground=self.colors['text'])
        self.ping_entry.pack(side="left", padx=5)
        self.ping_entry.insert(0, "google.com")
        
        tk.Label(controls, text="Count:", font=("Arial", 11),
                bg=self.colors['bg_dark'], fg=self.colors['text']).pack(side="left", padx=5)
        
        self.ping_count = tk.Spinbox(controls, from_=1, to=20, width=5,
                                    bg=self.colors['bg_light'], fg=self.colors['text'])
        self.ping_count.pack(side="left", padx=5)
        self.ping_count.delete(0, tk.END)
        self.ping_count.insert(0, "4")
        
        self.create_button(controls, "📡 Ping", self.run_ping, "#2196F3").pack(side="left", padx=10)
        self.create_button(controls, "🔍 Ping All Websites", self.ping_all_websites, "#9c27b0").pack(side="left", padx=5)
        
        # Results frame
        results_frame = tk.Frame(ping_tab, bg=self.colors['bg_dark'])
        results_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Ping output
        self.ping_output = tk.Text(results_frame, height=15, font=("Consolas", 10),
                                  bg=self.colors['bg_medium'], fg=self.colors['text'],
                                  insertbackground=self.colors['text'])
        self.ping_output.pack(fill="both", expand=True, pady=(0, 10))
        
        # Ping results treeview
        columns = ("Host", "Avg Time", "Packet Loss", "Status")
        self.ping_tree = ttk.Treeview(results_frame, columns=columns, show="headings",
                                     style="Custom.Treeview", height=8)
        
        for col in columns:
            self.ping_tree.heading(col, text=col)
        
        self.ping_tree.column("Host", width=300)
        self.ping_tree.column("Avg Time", width=150, anchor="center")
        self.ping_tree.column("Packet Loss", width=150, anchor="center")
        self.ping_tree.column("Status", width=150, anchor="center")
        
        self.ping_tree.pack(fill="x")
        
        self.ping_tree.tag_configure("good", foreground=self.colors['success'])
        self.ping_tree.tag_configure("bad", foreground=self.colors['error'])
    
    def create_alerts_tab(self):
        """Create alerts tab"""
        alerts_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(alerts_tab, text="🔔 Alerts")
        
        # Controls
        controls = tk.Frame(alerts_tab, bg=self.colors['bg_dark'])
        controls.pack(fill="x", padx=20, pady=15)
        
        self.create_button(controls, "🔄 Refresh", self.load_alerts, "#2196F3").pack(side="left", padx=5)
        self.create_button(controls, "✓ Mark All Read", self.mark_alerts_read, "#9c27b0").pack(side="left", padx=5)
        
        self.unread_only_var = tk.BooleanVar()
        unread_check = tk.Checkbutton(controls, text="Unread Only", variable=self.unread_only_var,
                                      command=self.load_alerts, bg=self.colors['bg_dark'],
                                      fg=self.colors['text'], selectcolor=self.colors['bg_light'])
        unread_check.pack(side="left", padx=10)
        
        # Alerts count
        self.alerts_count_label = tk.Label(controls, text="Unread: 0",
                                          bg=self.colors['bg_dark'], fg=self.colors['warning'],
                                          font=("Arial", 11, "bold"))
        self.alerts_count_label.pack(side="right", padx=10)
        
        # Alerts treeview
        alerts_frame = tk.Frame(alerts_tab, bg=self.colors['bg_dark'])
        alerts_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        columns = ("Time", "URL", "Type", "Message", "Read")
        self.alerts_tree = ttk.Treeview(alerts_frame, columns=columns, show="headings",
                                       style="Custom.Treeview")
        
        for col in columns:
            self.alerts_tree.heading(col, text=col)
        
        self.alerts_tree.column("Time", width=150)
        self.alerts_tree.column("URL", width=200)
        self.alerts_tree.column("Type", width=100, anchor="center")
        self.alerts_tree.column("Message", width=350)
        self.alerts_tree.column("Read", width=80, anchor="center")
        
        v_scroll = ttk.Scrollbar(alerts_frame, orient="vertical", command=self.alerts_tree.yview)
        self.alerts_tree.configure(yscrollcommand=v_scroll.set)
        
        self.alerts_tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        
        self.alerts_tree.tag_configure("unread", foreground=self.colors['warning'])
        self.alerts_tree.tag_configure("read", foreground=self.colors['text_dim'])
    
    def create_button(self, parent, text, command, color):
        """Create styled button"""
        btn = tk.Button(parent, text=text, command=command, bg=color,
                       fg="white", font=("Arial", 10, "bold"), padx=15, pady=5,
                       cursor="hand2", relief="flat", activebackground=color)
        return btn
    
    def create_context_menu(self):
        """Create right-click context menu"""
        self.context_menu = tk.Menu(self, tearoff=0, bg=self.colors['bg_medium'],
                                   fg=self.colors['text'])
        self.context_menu.add_command(label="🔍 Check Now", command=self.check_selected)
        self.context_menu.add_command(label="🔒 Check SSL", command=self.check_selected_ssl)
        self.context_menu.add_command(label="📡 Ping", command=self.ping_selected)
        self.context_menu.add_command(label="🌐 Open in Browser", command=self.open_in_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📊 View History", command=self.view_website_history)
        self.context_menu.add_command(label="📋 Copy URL", command=self.copy_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Remove", command=self.remove_website)
        
        self.websites_tree.bind("<Button-3>", self.show_context_menu)
    
    def show_context_menu(self, event):
        """Show context menu on right click"""
        item = self.websites_tree.identify_row(event.y)
        if item:
            self.websites_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    # ============== Core Functions ==============
    
    def add_website(self):
        """Add a new website to monitor"""
        url = self.url_entry.get().strip()
        if not url or url == "https://":
            messagebox.showwarning("Warning", "Please enter a valid URL")
            return
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        # Add to database
        website_id = self.db.add_website(url)
        if website_id:
            self.websites[url] = website_id
            self.websites_tree.insert("", "end", iid=str(website_id),
                                     values=(url, "Pending", "-", "-", "-", "-"))
            self.ssl_tree.insert("", "end", iid=f"ssl_{website_id}",
                                values=(url, "-", "-", "-", "-", "Pending"))
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, "https://")
            self.update_status(f"Added: {url}")
            self.response_times[url] = deque(maxlen=100)
        else:
            messagebox.showinfo("Info", "Website already exists")
    
    def load_websites(self):
        """Load websites from database"""
        for item in self.websites_tree.get_children():
            self.websites_tree.delete(item)
        for item in self.ssl_tree.get_children():
            self.ssl_tree.delete(item)
        
        websites = self.db.get_websites()
        for website in websites:
            website_id, url, name, added_date, is_active = website
            self.websites[url] = website_id
            self.websites_tree.insert("", "end", iid=str(website_id),
                                     values=(url, "Pending", "-", "-", "-", "-"))
            self.ssl_tree.insert("", "end", iid=f"ssl_{website_id}",
                                values=(url, "-", "-", "-", "-", "Pending"))
            self.response_times[url] = deque(maxlen=100)
        
        self.update_status(f"Loaded {len(websites)} websites")
    
    def check_website(self, item_id, url):
        """Check a single website"""
        result = self.checker.check_http(url)
        
        website_id = self.websites.get(url)
        if website_id:
            # Save to history
            self.db.add_check_history(
                website_id, result['status'], result['status_code'],
                result['response_time'], result['error']
            )
            
            # Track response time
            if result['response_time']:
                self.response_times[url].append(result['response_time'])
            
            # Calculate uptime
            stats = self.db.get_uptime_stats(website_id)
            uptime = "N/A"
            if stats and stats[0] > 0:
                uptime = f"{(stats[1] / stats[0] * 100):.1f}%"
            
            # Determine status display
            if result['status'] == 'Online':
                status_display = "✅ Online"
                tag = "online"
            elif result['status'] == 'Timeout':
                status_display = "⏱️ Timeout"
                tag = "warning"
            else:
                status_display = "❌ Offline"
                tag = "offline"
                
                # Create alert for offline
                self.db.add_alert(website_id, "OFFLINE", f"{url} is offline: {result['error']}")
                self.notifier.send_desktop_notification(
                    "Website Offline Alert",
                    f"{url} is not responding!",
                    timeout=10
                )
            
            # Update treeview
            check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            response_time = f"{result['response_time']} ms" if result['response_time'] else "-"
            code = str(result['status_code']) if result['status_code'] else "-"
            
            try:
                self.websites_tree.item(str(website_id), 
                                       values=(url, status_display, code, response_time, check_time, uptime),
                                       tags=(tag,))
            except tk.TclError:
                pass
    
    def check_all_websites(self):
        """Check all websites"""
        items = self.websites_tree.get_children()
        if not items:
            messagebox.showinfo("Info", "No websites to check")
            return
        
        self.status_indicator.config(text="● Checking...", fg=self.colors['warning'])
        
        def check_all():
            for item_id in items:
                try:
                    url = self.websites_tree.item(item_id)["values"][0]
                    self.check_website(item_id, url)
                except:
                    pass
            
            self.after(0, self.finish_checking)
        
        thread = threading.Thread(target=check_all, daemon=True)
        thread.start()
    
    def finish_checking(self):
        """Called when checking is complete"""
        self.status_indicator.config(text="● Ready", fg=self.colors['success'])
        self.update_dashboard()
        self.load_history()
        self.load_alerts()
        self.update_status(f"Checked {len(self.websites_tree.get_children())} websites")
    
    def check_selected(self):
        """Check selected website"""
        selected = self.websites_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a website")
            return
        
        for item_id in selected:
            url = self.websites_tree.item(item_id)["values"][0]
            threading.Thread(target=self.check_website, args=(item_id, url), daemon=True).start()
    
    def remove_website(self):
        """Remove selected website"""
        selected = self.websites_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a website to remove")
            return
        
        if messagebox.askyesno("Confirm", "Are you sure you want to remove selected websites?"):
            for item_id in selected:
                self.db.delete_website(int(item_id))
                self.websites_tree.delete(item_id)
                try:
                    self.ssl_tree.delete(f"ssl_{item_id}")
                except:
                    pass
            self.update_status("Removed selected websites")
    
    # ============== SSL Functions ==============
    
    def check_ssl(self, item_id, url):
        """Check SSL certificate for a website"""
        result = self.checker.check_ssl(url)
        website_id = self.websites.get(url)
        
        if result.get('valid'):
            # Save to database
            if website_id:
                self.db.save_ssl_info(
                    website_id, result['issuer'], result['subject'],
                    result['valid_from'], result['valid_until']
                )
            
            days = result['days_until_expiry']
            if days < 0:
                status = "❌ Expired"
                tag = "expired"
            elif days <= 30:
                status = "⚠️ Expiring Soon"
                tag = "expiring"
                # Create alert
                if website_id:
                    self.db.add_alert(website_id, "SSL_EXPIRING", 
                                     f"SSL certificate expires in {days} days")
                    self.notifier.send_desktop_notification(
                        "SSL Certificate Warning",
                        f"{url} SSL expires in {days} days!",
                        timeout=10
                    )
            else:
                status = "✅ Valid"
                tag = "valid"
            
            try:
                self.ssl_tree.item(f"ssl_{website_id}",
                                  values=(url, result['issuer'], result['valid_from'],
                                         result['valid_until'], f"{days} days", status),
                                  tags=(tag,))
            except:
                pass
        else:
            try:
                self.ssl_tree.item(f"ssl_{website_id}",
                                  values=(url, "-", "-", "-", "-", f"❌ {result.get('error', 'Error')}"),
                                  tags=("expired",))
            except:
                pass
    
    def check_all_ssl(self):
        """Check SSL for all websites"""
        def check():
            for url, website_id in self.websites.items():
                self.check_ssl(f"ssl_{website_id}", url)
            self.after(0, lambda: self.update_status("SSL check completed"))
        
        threading.Thread(target=check, daemon=True).start()
    
    def check_selected_ssl(self):
        """Check SSL for selected website"""
        selected = self.websites_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a website")
            return
        
        for item_id in selected:
            url = self.websites_tree.item(item_id)["values"][0]
            threading.Thread(target=self.check_ssl, args=(item_id, url), daemon=True).start()
    
    # ============== Ping Functions ==============
    
    def run_ping(self):
        """Run ping for entered host"""
        host = self.ping_entry.get().strip()
        if not host:
            messagebox.showwarning("Warning", "Please enter a host")
            return
        
        count = int(self.ping_count.get())
        
        self.ping_output.delete(1.0, tk.END)
        self.ping_output.insert(tk.END, f"Pinging {host}...\n\n")
        
        def ping():
            result = self.checker.ping(host, count)
            
            self.after(0, lambda: self.ping_output.insert(tk.END, result['output']))
            
            # Add to treeview
            status = "✅ Success" if result['success'] else "❌ Failed"
            avg_time = f"{result['avg_time']} ms" if result['avg_time'] else "-"
            packet_loss = f"{result['packet_loss']}%"
            tag = "good" if result['success'] and result['packet_loss'] < 50 else "bad"
            
            # Remove existing entry if exists
            for item in self.ping_tree.get_children():
                if self.ping_tree.item(item)["values"][0] == host:
                    self.ping_tree.delete(item)
            
            self.after(0, lambda: self.ping_tree.insert("", 0, 
                                                       values=(host, avg_time, packet_loss, status),
                                                       tags=(tag,)))
        
        threading.Thread(target=ping, daemon=True).start()
    
    def ping_all_websites(self):
        """Ping all monitored websites"""
        def ping_all():
            for url in self.websites.keys():
                host = url.split('//')[1].split('/')[0] if '//' in url else url
                result = self.checker.ping(host, 4)
                
                status = "✅ Success" if result['success'] else "❌ Failed"
                avg_time = f"{result['avg_time']} ms" if result['avg_time'] else "-"
                packet_loss = f"{result['packet_loss']}%"
                tag = "good" if result['success'] else "bad"
                
                self.after(0, lambda h=host, a=avg_time, p=packet_loss, s=status, t=tag:
                          self.ping_tree.insert("", "end", values=(h, a, p, s), tags=(t,)))
            
            self.after(0, lambda: self.update_status("Ping check completed"))
        
        # Clear existing
        for item in self.ping_tree.get_children():
            self.ping_tree.delete(item)
        
        threading.Thread(target=ping_all, daemon=True).start()
    
    def ping_selected(self):
        """Ping selected website"""
        selected = self.websites_tree.selection()
        if selected:
            url = self.websites_tree.item(selected[0])["values"][0]
            host = url.split('//')[1].split('/')[0] if '//' in url else url
            self.ping_entry.delete(0, tk.END)
            self.ping_entry.insert(0, host)
            self.notebook.select(4)  # Switch to ping tab
            self.run_ping()
    
    # ============== History Functions ==============
    
    def load_history(self):
        """Load check history"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        history = self.db.get_check_history(limit=200)
        
        filter_type = self.history_filter.get()
        
        for record in history:
            id_, website_id, status, code, response_time, check_time, error, url = record
            
            # Apply filter
            if filter_type == "Online" and status != "Online":
                continue
            elif filter_type == "Offline" and status not in ["Offline", "Timeout"]:
                continue
            elif filter_type == "Errors" and status == "Online":
                continue
            
            tag = "online" if status == "Online" else "offline"
            response = f"{response_time} ms" if response_time else "-"
            
            self.history_tree.insert("", "end",
                                    values=(check_time, url, status, code or "-", response, error or "-"),
                                    tags=(tag,))
    
    def view_website_history(self):
        """View history for selected website"""
        selected = self.websites_tree.selection()
        if selected:
            url = self.websites_tree.item(selected[0])["values"][0]
            # Switch to history tab and filter
            self.notebook.select(2)
            messagebox.showinfo("History", f"Showing history for: {url}")
    
    # ============== Alerts Functions ==============
    
    def load_alerts(self):
        """Load alerts"""
        for item in self.alerts_tree.get_children():
            self.alerts_tree.delete(item)
        
        unread_only = self.unread_only_var.get()
        alerts = self.db.get_alerts(unread_only=unread_only)
        
        unread_count = 0
        for alert in alerts:
            id_, website_id, alert_type, message, created_at, is_read, url = alert
            
            read_status = "No" if not is_read else "Yes"
            tag = "unread" if not is_read else "read"
            
            if not is_read:
                unread_count += 1
            
            self.alerts_tree.insert("", "end",
                                   values=(created_at, url, alert_type, message, read_status),
                                   tags=(tag,))
        
        self.alerts_count_label.config(text=f"Unread: {unread_count}")
    
    def mark_alerts_read(self):
        """Mark all alerts as read"""
        self.db.mark_alerts_read()
        self.load_alerts()
        self.update_status("Marked all alerts as read")
    
    # ============== Dashboard Functions ==============
    
    def update_dashboard(self):
        """Update dashboard statistics"""
        total = len(self.websites_tree.get_children())
        online = offline = 0
        total_response = []
        ssl_expiring = 0
        
        for item in self.websites_tree.get_children():
            values = self.websites_tree.item(item)["values"]
            if "Online" in str(values[1]):
                online += 1
            elif "Offline" in str(values[1]) or "Error" in str(values[1]):
                offline += 1
            
            # Get response time
            try:
                rt = values[3]
                if rt and rt != "-":
                    total_response.append(float(rt.replace(" ms", "")))
            except:
                pass
        
        # Check SSL expiring
        for item in self.ssl_tree.get_children():
            values = self.ssl_tree.item(item)["values"]
            if "Expiring" in str(values[5]):
                ssl_expiring += 1
        
        # Update cards
        self.card_total.value_label.config(text=str(total))
        self.card_online.value_label.config(text=str(online))
        self.card_offline.value_label.config(text=str(offline))
        self.card_ssl.value_label.config(text=str(ssl_expiring))
        
        avg_response = sum(total_response) / len(total_response) if total_response else 0
        self.card_response.value_label.config(text=f"{avg_response:.0f} ms")
        
        # Update charts
        if MATPLOTLIB_AVAILABLE:
            self.update_charts(online, offline, total - online - offline)
    
    def update_charts(self, online, offline, pending):
        """Update matplotlib charts"""
        try:
            # Clear axes
            self.ax1.clear()
            self.ax2.clear()
            
            # Response time chart
            self.ax1.set_facecolor(self.colors['bg_dark'])
            self.ax1.set_title("Recent Response Times", color=self.colors['text'])
            
            # Get recent response times
            all_times = []
            labels = []
            for url, times in self.response_times.items():
                if times:
                    all_times.append(list(times)[-10:])  # Last 10
                    labels.append(url.split('//')[1].split('/')[0][:15])
            
            if all_times:
                for i, times in enumerate(all_times[:5]):  # Max 5 websites
                    self.ax1.plot(times, label=labels[i], marker='o', markersize=3)
                self.ax1.legend(fontsize=7, facecolor=self.colors['bg_medium'], 
                               labelcolor=self.colors['text'])
            
            self.ax1.tick_params(colors=self.colors['text_dim'])
            self.ax1.set_ylabel("Response Time (ms)", color=self.colors['text_dim'])
            
            # Status pie chart
            self.ax2.set_facecolor(self.colors['bg_dark'])
            sizes = [online, offline, pending]
            labels = ['Online', 'Offline', 'Pending']
            colors = [self.colors['success'], self.colors['error'], self.colors['warning']]
            
            # Remove zero values
            non_zero = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]
            if non_zero:
                sizes, labels, colors = zip(*non_zero)
                self.ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                            textprops={'color': self.colors['text']})
            self.ax2.set_title("Status Distribution", color=self.colors['text'])
            
            self.canvas.draw()
        except Exception as e:
            print(f"Chart error: {e}")
    
    # ============== Auto-Refresh Functions ==============
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh"""
        self.auto_refresh = self.auto_refresh_var.get()
        if self.auto_refresh:
            self.status_indicator.config(text="● Auto-Refresh ON", fg=self.colors['warning'])
            self.auto_refresh_loop()
        else:
            self.status_indicator.config(text="● Ready", fg=self.colors['success'])
    
    def auto_refresh_loop(self):
        """Auto-refresh loop"""
        if self.auto_refresh:
            self.check_all_websites()
            self.after(self.refresh_interval * 1000, self.auto_refresh_loop)
    
    def configure_refresh(self):
        """Configure auto-refresh settings"""
        dialog = tk.Toplevel(self)
        dialog.title("Auto-Refresh Settings")
        dialog.geometry("300x150")
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Refresh Interval (seconds):",
                bg=self.colors['bg_medium'], fg=self.colors['text']).pack(pady=20)
        
        interval_entry = tk.Entry(dialog, font=("Arial", 12))
        interval_entry.pack(pady=10)
        interval_entry.insert(0, str(self.refresh_interval))
        
        def save():
            try:
                self.refresh_interval = int(interval_entry.get())
                dialog.destroy()
                messagebox.showinfo("Saved", f"Refresh interval set to {self.refresh_interval} seconds")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")
        
        self.create_button(dialog, "Save", save, self.colors['success']).pack(pady=10)
    
    # ============== Email Configuration ==============
    
    def configure_email(self):
        """Configure email notifications"""
        dialog = tk.Toplevel(self)
        dialog.title("Email Notification Settings")
        dialog.geometry("400x350")
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self)
        dialog.grab_set()
        
        fields = [
            ("SMTP Server:", "smtp.gmail.com"),
            ("SMTP Port:", "587"),
            ("Username:", ""),
            ("Password:", ""),
            ("Recipient Email:", "")
        ]
        
        entries = {}
        for label, default in fields:
            frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
            frame.pack(fill="x", padx=20, pady=5)
            
            tk.Label(frame, text=label, width=15, anchor="w",
                    bg=self.colors['bg_medium'], fg=self.colors['text']).pack(side="left")
            
            entry = tk.Entry(frame, font=("Arial", 10), width=25)
            if "Password" in label:
                entry.config(show="*")
            entry.insert(0, default)
            entry.pack(side="right")
            entries[label] = entry
        
        def save():
            self.notifier.configure_email(
                entries["SMTP Server:"].get(),
                int(entries["SMTP Port:"].get()),
                entries["Username:"].get(),
                entries["Password:"].get(),
                entries["Recipient Email:"].get()
            )
            dialog.destroy()
            messagebox.showinfo("Saved", "Email notifications configured")
        
        def test():
            save()
            if self.notifier.send_email_alert("Test Alert", "This is a test email from Website Monitor"):
                messagebox.showinfo("Success", "Test email sent successfully!")
            else:
                messagebox.showerror("Error", "Failed to send test email")
        
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=20)
        
        self.create_button(btn_frame, "Save", save, self.colors['success']).pack(side="left", padx=10)
        self.create_button(btn_frame, "Test", test, "#2196F3").pack(side="left", padx=10)
    
    # ============== Import/Export Functions ==============
    
    def import_urls(self):
        """Import URLs from file"""
        file = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file:
            with open(file, 'r') as f:
                count = 0
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#'):
                        if not url.startswith(('http://', 'https://')):
                            url = 'https://' + url
                        
                        website_id = self.db.add_website(url)
                        if website_id:
                            self.websites[url] = website_id
                            self.websites_tree.insert("", "end", iid=str(website_id),
                                                     values=(url, "Pending", "-", "-", "-", "-"))
                            self.response_times[url] = deque(maxlen=100)
                            count += 1
                
                messagebox.showinfo("Import Complete", f"Imported {count} URLs")
    
    def export_results(self):
        """Export current results to JSON"""
        file = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file:
            results = []
            for item in self.websites_tree.get_children():
                values = self.websites_tree.item(item)["values"]
                results.append({
                    "url": values[0],
                    "status": values[1],
                    "status_code": values[2],
                    "response_time": values[3],
                    "last_check": values[4],
                    "uptime": values[5]
                })
            
            with open(file, 'w') as f:
                json.dump(results, f, indent=2)
            
            messagebox.showinfo("Export Complete", f"Results exported to {file}")
    
    def export_history(self):
        """Export history to CSV"""
        file = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file:
            history = self.db.get_check_history(limit=10000)
            
            with open(file, 'w') as f:
                f.write("Time,URL,Status,Code,Response Time,Error\n")
                for record in history:
                    id_, website_id, status, code, response_time, check_time, error, url = record
                    f.write(f'"{check_time}","{url}","{status}","{code or ""}","{response_time or ""}","{error or ""}"\n')
            
            messagebox.showinfo("Export Complete", f"History exported to {file}")
    
    # ============== Utility Functions ==============
    
    def open_in_browser(self):
        """Open selected URL in browser"""
        selected = self.websites_tree.selection()
        if selected:
            url = self.websites_tree.item(selected[0])["values"][0]
            import webbrowser
            webbrowser.open(url)
    
    def copy_url(self):
        """Copy selected URL to clipboard"""
        selected = self.websites_tree.selection()
        if selected:
            url = self.websites_tree.item(selected[0])["values"][0]
            self.clipboard_clear()
            self.clipboard_append(url)
            self.update_status(f"Copied: {url}")
    
    def sort_treeview(self, tree, col):
        """Sort treeview by column"""
        items = [(tree.set(item, col), item) for item in tree.get_children()]
        items.sort()
        for index, (_, item) in enumerate(items):
            tree.move(item, "", index)
    
    def clear_old_history(self, days=30):
        """Clear old history records"""
        if messagebox.askyesno("Confirm", f"Delete history older than {days} days?"):
            self.db.clear_old_history(days)
            self.load_history()
            self.update_status(f"Cleared history older than {days} days")
    
    def update_status(self, message):
        """Update status bar"""
        count = len(self.websites_tree.get_children())
        self.status_bar.config(text=f"{message} | Websites: {count}")
    
    def update_clock(self):
        """Update clock display"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.config(text=now)
        self.after(1000, self.update_clock)
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", 
                           "Advanced Website Status Monitor\n\n"
                           "Version: 2.0\n\n"
                           "Features:\n"
                           "• HTTP/HTTPS monitoring\n"
                           "• SSL certificate checking\n"
                           "• Ping monitoring\n"
                           "• History logging\n"
                           "• Desktop & email notifications\n"
                           "• Auto-refresh\n"
                           "• Import/Export")
    
    def on_closing(self):
        """Handle window close"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.auto_refresh = False
            self.destroy()


# ============== Main Entry Point ==============

if __name__ == "__main__":
    app = WebsiteMonitor()
    app.mainloop()