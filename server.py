#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kick.com Subathon Server
Local olarak çalışır, OBS Browser Source ile kullanılabilir.
"""

import json
import websocket
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import os
import sys

# PyInstaller'da gömülü kaynak yolu (_MEIPASS) desteği
def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath('.'))
    return os.path.join(base_path, relative_path)

# Flask uygulaması (paketlenmiş şablon/static klasörlerini bulacak şekilde)
app = Flask(__name__, template_folder=resource_path('templates'), static_folder=resource_path('static'))
app.config['SECRET_KEY'] = 'subathon_secret_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global değişkenler
timer_data = {
    'end_time': None,  # Geri sayımın biteceği zaman
    'is_running': False,
    'total_seconds': 0,
    'events': []  # Son eventler
}

# Kick WebSocket bilgileri
WS_URL = "wss://ws-us2.pusher.com/app/32cbd69e4b950bf97679?protocol=7&client=js&version=8.4.0&flash=false"
HEADERS = {
    "Origin": "https://kick.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Subathon ayarları
SUBATHON_CONFIG = {
    'initial_minutes': 30,  # Başlangıç süresi (dakika)
    'sub_minutes': 30,  # Bir abone için eklenen süre (dakika)
    'gift_sub_minutes': 30,  # Bir hediye abone için eklenen süre (dakika)
    'kick_seconds_per_unit': 5,  # Her 1 kick için eklenen süre (saniye)
    'max_minutes': 180,  # Maksimum süre (dakika)
    'enable_subscription': True,
    'enable_gift_subscription': True,
    'enable_kick': True,
    'enable_max_limit': True,
}

# Statik Kick kanal bilgileri (varsayılan)
DEFAULT_CHANNEL_ID = 6684574
DEFAULT_CHATROOM_ID = 6628641
DEFAULT_CHANNEL_SLUG = "parzidev"

# Config doğrulama/normalizasyon yardımcıları
def clamp_int(value, min_value, max_value, default):
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        return default
    if ivalue < min_value:
        return min_value
    if ivalue > max_value:
        return max_value
    return ivalue

def sanitize_config(cfg):
    """Geçerli aralıklara göre ayarları temizler (dakika ve saniye limitleri)."""
    if not isinstance(cfg, dict):
        return {}
    # Mantıklı üst limit: 7 gün = 10080 dakika
    MAX_MINUTES_CAP = 10080
    clean_num = {
            'initial_minutes': clamp_int(cfg.get('initial_minutes', SUBATHON_CONFIG['initial_minutes']), 1, MAX_MINUTES_CAP, SUBATHON_CONFIG['initial_minutes']),
            'sub_minutes': clamp_int(cfg.get('sub_minutes', SUBATHON_CONFIG['sub_minutes']), 0, MAX_MINUTES_CAP, SUBATHON_CONFIG['sub_minutes']),
            'gift_sub_minutes': clamp_int(cfg.get('gift_sub_minutes', SUBATHON_CONFIG['gift_sub_minutes']), 0, MAX_MINUTES_CAP, SUBATHON_CONFIG['gift_sub_minutes']),
            'kick_seconds_per_unit': clamp_int(cfg.get('kick_seconds_per_unit', SUBATHON_CONFIG['kick_seconds_per_unit']), 1, 3600, SUBATHON_CONFIG['kick_seconds_per_unit']),
            'max_minutes': clamp_int(cfg.get('max_minutes', SUBATHON_CONFIG['max_minutes']), 1, MAX_MINUTES_CAP, SUBATHON_CONFIG['max_minutes']),
        }
    clean_bool = {}
    for bkey in ('enable_subscription', 'enable_gift_subscription', 'enable_kick', 'enable_max_limit'):
        if bkey in cfg:
            val = cfg.get(bkey)
            if isinstance(val, bool):
                clean_bool[bkey] = val
            elif isinstance(val, str):
                clean_bool[bkey] = val.lower() in ('1', 'true', 'yes', 'on')
            elif isinstance(val, (int, float)):
                clean_bool[bkey] = bool(val)
    merged = {**clean_num, **clean_bool}
    return {k: v for k, v in merged.items() if v is not None}

# UI görünüm ayarları (varsayılanlar)
UI_CONFIG = {
    'bg_start': '#667eea',
    'bg_end': '#764ba2',
    'timer_color': '#ffffff',
    'title_text': '⏱️ SUBATHON',
    'label_text': 'KALAN SÜRE',
    'font_family': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    'timer_font_family': "'Courier New', monospace",
    'timer_font_size_em': 7,
    'radius_px': 30,
    'shadow': True,
    'combo_top_px': 20,
    'combo_right_px': 20,
    'sub_name_color': '#ffeb3b',
}

def sanitize_ui_config(cfg):
    if not isinstance(cfg, dict):
        return {}
    clean = {}
    # colors and text
    for key in ('bg_start', 'bg_end', 'timer_color', 'title_text', 'label_text', 'font_family', 'timer_font_family', 'sub_name_color'):
        if key in cfg and isinstance(cfg[key], str):
            clean[key] = cfg[key][:200]
    # numeric
    if 'timer_font_size_em' in cfg:
        clean['timer_font_size_em'] = clamp_int(cfg['timer_font_size_em'], 2, 12, UI_CONFIG['timer_font_size_em'])
    if 'radius_px' in cfg:
        clean['radius_px'] = clamp_int(cfg['radius_px'], 0, 80, UI_CONFIG['radius_px'])
    if 'combo_top_px' in cfg:
        clean['combo_top_px'] = clamp_int(cfg['combo_top_px'], 0, 400, UI_CONFIG['combo_top_px'])
    if 'combo_right_px' in cfg:
        clean['combo_right_px'] = clamp_int(cfg['combo_right_px'], 0, 400, UI_CONFIG['combo_right_px'])
    if 'shadow' in cfg:
        clean['shadow'] = bool(cfg['shadow'])
    return clean

# Sadakat Ödülleri yapılandırması
REWARD_CONFIG = {
    'enable_rewards': True,
    'default_seconds': 5,
    'rewards': {
        # key: reward_id or reward_title → { 'title': str, 'seconds': int, 'enabled': bool }
    }
}

def sanitize_rewards_payload(data):
    if not isinstance(data, dict):
        return {}
    clean = {}
    if 'enable_rewards' in data:
        v = data.get('enable_rewards')
        clean['enable_rewards'] = bool(v) if not isinstance(v, str) else v.lower() in ('1','true','yes','on')
    if 'default_seconds' in data:
        clean['default_seconds'] = clamp_int(data.get('default_seconds'), 0, 3600, REWARD_CONFIG['default_seconds'])
    if 'rewards' in data and isinstance(data['rewards'], list):
        rewards = {}
        for item in data['rewards']:
            if not isinstance(item, dict):
                continue
            key = item.get('id') or item.get('reward_id') or item.get('title') or item.get('reward_title')
            title = item.get('title') or item.get('reward_title') or str(key)
            if not key:
                continue
            seconds = clamp_int(item.get('seconds', REWARD_CONFIG['default_seconds']), 0, 3600, REWARD_CONFIG['default_seconds'])
            enabled = item.get('enabled')
            if isinstance(enabled, str):
                enabled = enabled.lower() in ('1','true','yes','on')
            elif not isinstance(enabled, bool):
                enabled = False
            rewards[str(key)] = {
                'title': title[:200] if isinstance(title, str) else str(title),
                'seconds': seconds,
                'enabled': enabled,
            }
        clean['rewards'] = rewards
    return clean

# Kick mağaza (tier) yapılandırması: miktar->saniye
KICK_TIER_CONFIG = {
    'enable_kick_tiers': True,
    'tiers': {
        # Varsayılanlar: açık ve süre dolu
        1:  {'seconds': 5, 'enabled': True},                 # 5 saniye
        10: {'seconds': 60, 'enabled': True},                # 1 dakika
        50: {'seconds': 7 * 60, 'enabled': True},            # 7 dakika
        100:{'seconds': 15 * 60, 'enabled': True},           # 15 dakika
        500:{'seconds': 105 * 60, 'enabled': True},          # 1 saat 45 dakika
        1000:{'seconds': 4 * 3600, 'enabled': True},         # 4 saat
        2000:{'seconds': 8 * 3600, 'enabled': True},
        5000:{'seconds': 20 * 3600, 'enabled': True},
        10000:{'seconds': 40 * 3600, 'enabled': True},
        50000:{'seconds': 200 * 3600, 'enabled': True},
    }
}

def sanitize_kick_tiers_payload(data):
    if not isinstance(data, dict):
        return {}
    clean = {}
    if 'enable_kick_tiers' in data:
        v = data.get('enable_kick_tiers')
        clean['enable_kick_tiers'] = bool(v) if not isinstance(v, str) else v.lower() in ('1','true','yes','on')
    if 'tiers' in data and isinstance(data['tiers'], list):
        tiers = {}
        for item in data['tiers']:
            if not isinstance(item, dict):
                continue
            amt = item.get('amount')
            try:
                amt = int(amt)
            except (TypeError, ValueError):
                continue
            seconds = clamp_int(item.get('seconds', 0), 0, 3600, 0)
            enabled = item.get('enabled')
            if isinstance(enabled, str):
                enabled = enabled.lower() in ('1','true','yes','on')
            elif not isinstance(enabled, bool):
                enabled = False
            tiers[amt] = {'seconds': seconds, 'enabled': enabled}
        clean['tiers'] = tiers
    return clean

def try_process_reward_payload(payload):
    """Elimizdeki payload bir ödül (loyalty reward) redemption ise işler ve True döner."""
    try:
        if not isinstance(payload, dict):
            return False
        reward_id = payload.get('reward_id')
        reward_title = payload.get('reward_title') or payload.get('title')
        username = payload.get('username', 'Bilinmeyen')
        # Yaklaşık sezgisel kontrol: reward_id ya da reward_title varsa redemption sayalım
        if not reward_id and not reward_title:
            return False
        if not REWARD_CONFIG.get('enable_rewards', True):
            # Sadece listeye ekleyelim (devre dışı)
            key = str(reward_id or reward_title)
            if key and key not in REWARD_CONFIG['rewards']:
                REWARD_CONFIG['rewards'][key] = {
                    'title': reward_title or key,
                    'seconds': REWARD_CONFIG.get('default_seconds', 5),
                    'enabled': False
                }
                socketio.emit('rewards_update', REWARD_CONFIG)
            return False
        key = str(reward_id or reward_title)
        rec = REWARD_CONFIG['rewards'].get(key) or REWARD_CONFIG['rewards'].get(str(reward_title or ''))
        if not rec:
            # bilinmeyen ödül -> otomatik ekle devre dışı
            REWARD_CONFIG['rewards'][key] = {
                'title': reward_title or key,
                'seconds': REWARD_CONFIG.get('default_seconds', 5),
                'enabled': False
            }
            socketio.emit('rewards_update', REWARD_CONFIG)
            rec = REWARD_CONFIG['rewards'][key]
        if rec.get('enabled'):
            seconds = int(rec.get('seconds') or REWARD_CONFIG.get('default_seconds', 5))
            add_time(seconds, f"{username} '{rec.get('title', reward_title or key)}' ödülünü aldı!", 'reward', {'username': username, 'reward_title': rec.get('title', reward_title or key), 'reward_id': reward_id})
            print(f"[REWARD] {username} {rec.get('title', reward_title or key)} +{seconds}s")
        return True
    except Exception as _e:
        return False

class KickSubathonListener:
    """Kick eventlerini dinler ve subathon'a süre ekler"""
    
    def __init__(self, channel_id, chatroom_id):
        self.channel_id = channel_id
        self.chatroom_id = chatroom_id
        self.ws = None
        self.chat_channel = f"chatrooms.{self.chatroom_id}.v2"
        
    def start(self):
        """WebSocket dinlemeyi başlat"""
        print(f"[KICK] Bağlanılıyor... (Channel: {self.channel_id}, Chatroom: {self.chatroom_id})")
        
        self.ws = websocket.WebSocketApp(
            WS_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            header=HEADERS
        )
        
        # Ayrı thread'de çalıştır
        wst = threading.Thread(target=self.ws.run_forever, kwargs={'ping_interval': 30, 'ping_timeout': 10})
        wst.daemon = True
        wst.start()
        
    def on_open(self, ws):
        """Bağlantı açıldığında kanallara abone ol"""
        print("[KICK] Bağlantı kuruldu, kanallara abone olunuyor...")
        
        channels = [
            self.chat_channel,
            f"channel_{self.channel_id}",
            f"channel.{self.channel_id}",
            f"chatroom_{self.chatroom_id}"
        ]
        
        for channel in channels:
            sub = {
                "event": "pusher:subscribe",
                "data": {"channel": channel}
            }
            ws.send(json.dumps(sub))
        
        print("[KICK] ✓ Tüm kanallara abone olundu!")
        
    def on_message(self, ws, message):
        """Mesaj alındığında işle"""
        try:
            data = json.loads(message)
            event = data.get("event")
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Abone olma olayı
            if event == "App\\Events\\SubscriptionEvent":
                sub_data = data.get("data")
                if isinstance(sub_data, str):
                    sub_data = json.loads(sub_data)
                
                username = sub_data.get('username', 'Bilinmeyen')
                months = sub_data.get('months', 1)
                
                # Süre ekle
                if SUBATHON_CONFIG.get('enable_subscription', True):
                    minutes = SUBATHON_CONFIG['sub_minutes']
                    add_time(minutes * 60, f"{username} abone oldu!", 'subscription', {'username': username})
                    print(f"[SUB] {username} abone oldu! +{minutes} dakika eklendi")
                
            # Hediye abone olayı
            elif event == "App\\Events\\GiftedSubscriptionsEvent":
                gift_data = data.get("data")
                if isinstance(gift_data, str):
                    gift_data = json.loads(gift_data)
                
                gifter = gift_data.get('gifter_username', 'Bilinmeyen')
                quantity = gift_data.get('quantity', 1)
                
                # Her hediye abone için süre ekle
                if SUBATHON_CONFIG.get('enable_gift_subscription', True):
                    minutes = SUBATHON_CONFIG['gift_sub_minutes'] * quantity
                    add_time(minutes * 60, f"{gifter} {quantity} abonelik hediye etti!", 'gift_subscription', {'username': gifter, 'quantity': quantity})
                    print(f"[GIFT SUB] {gifter} {quantity} abonelik hediye etti! +{minutes} dakika eklendi")
                
            # Kick bağışı
            elif event == "KicksGifted":
                kick_data = data.get("data")
                if isinstance(kick_data, str):
                    kick_data = json.loads(kick_data)
                
                sender = kick_data.get('sender', {})
                gift = kick_data.get('gift', {})
                username = sender.get('username', 'Bilinmeyen')
                amount = gift.get('amount', 1)
                
                # Kick miktarına göre süre ekle (tier öncelikli)
                if SUBATHON_CONFIG.get('enable_kick', True):
                    seconds = None
                    if KICK_TIER_CONFIG.get('enable_kick_tiers', True):
                        tier = KICK_TIER_CONFIG['tiers'].get(int(amount))
                        if tier and tier.get('enabled'):
                            seconds = int(tier.get('seconds', 0))
                    if seconds is None:
                        seconds = amount * SUBATHON_CONFIG['kick_seconds_per_unit']
                    add_time(seconds, f"{username} {amount} Kick gönderdi!", 'kick', {'username': username, 'amount': amount})
                    print(f"[KICK] {username} {amount} Kick gönderdi! +{seconds} saniye eklendi")
            
            # Sohbet mesajları: test1kicks yazıldığında 1 kick simülasyonu
            elif event in ("App\\Events\\ChatMessageEvent", "App\\Events\\MessageEvent", "ChatMessageEvent", "App\\Events\\ChatMessageNew"):
                msg = data.get("data")
                if isinstance(msg, str):
                    try:
                        msg = json.loads(msg)
                    except Exception:
                        msg = {"content": msg}
                # Olası alan adları
                text = None
                for key in ("content", "message", "text", "body"):
                    if isinstance(msg, dict) and key in msg and isinstance(msg[key], str):
                        text = msg[key]
                        break
                if not text and isinstance(msg, dict) and isinstance(msg.get('message'), dict):
                    inner = msg.get('message')
                    for key in ("content", "text"):
                        if isinstance(inner.get(key), str):
                            text = inner[key]
                            break
                if isinstance(text, str) and 'test1kicks' in text.lower():
                    seconds = SUBATHON_CONFIG['kick_seconds_per_unit']
                    add_time(seconds, "TEST: +1 Kick (chat)", 'kick')
                    print(f"[TEST KICK] chat tetikledi: +{seconds}s")
            # Sadakat mağazası ödül olayı (reward redemption)
            elif event in ("LoyaltyRewardRedeemed", "App\\Events\\LoyaltyRewardRedeemed", "App\\Events\\LoyaltyStoreRedemptionEvent"):
                payload = data.get("data")
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        payload = {}
                reward_id = str(payload.get('reward_id') or '')
                reward_title = payload.get('reward_title', 'Ödül')
                username = payload.get('username', 'Bilinmeyen')
                if REWARD_CONFIG.get('enable_rewards', True):
                    # Kaydı/varsayılanı bul
                    rec = REWARD_CONFIG['rewards'].get(reward_id) or REWARD_CONFIG['rewards'].get(reward_title)
                    if not rec:
                        # Yeni ödülü otomatik listeye ekle (varsayılan devre dışı)
                        REWARD_CONFIG['rewards'][reward_id or reward_title] = {
                            'title': reward_title,
                            'seconds': REWARD_CONFIG.get('default_seconds', 5),
                            'enabled': False
                        }
                        rec = REWARD_CONFIG['rewards'][reward_id or reward_title]
                        # Kontrole güncel yapı gönder
                        socketio.emit('rewards_update', REWARD_CONFIG)
                    if rec.get('enabled'):
                        seconds = rec.get('seconds', REWARD_CONFIG.get('default_seconds', 5))
                        add_time(seconds, f"{username} '{reward_title}' ödülünü aldı!", 'reward', {'username': username, 'reward_title': reward_title, 'reward_id': reward_id})
                        print(f"[REWARD] {username} {reward_title} +{seconds}s")

            else:
                # Genel durumda, mesaj içeriği varsa test komutunu kontrol et
                payload = data.get("data")
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        payload = {"content": payload}
                # Önce reward redemption sezgisel kontrolü
                if try_process_reward_payload(payload):
                    return
                if isinstance(payload, dict):
                    text = None
                    for key in ("content", "message", "text", "body"):
                        if key in payload and isinstance(payload[key], str):
                            text = payload[key]
                            break
                    if isinstance(text, str) and 'test1kicks' in text.lower():
                        seconds = SUBATHON_CONFIG['kick_seconds_per_unit']
                        add_time(seconds, "TEST: +1 Kick (chat)", 'kick')
                        print(f"[TEST KICK] chat tetikledi: +{seconds}s")
                
        except Exception as e:
            print(f"[ERROR] Mesaj işlenirken hata: {e}")
    
    def on_error(self, ws, error):
        """Hata durumu"""
        print(f"[KICK ERROR] {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Bağlantı kapandı"""
        print(f"[KICK] Bağlantı kapandı, 5 saniye sonra yeniden denenecek...")
        time.sleep(5)
        self.start()

def add_time(seconds, message, event_type, extra=None):
    """Timer'a süre ekle"""
    global timer_data
    
    if not timer_data['is_running']:
        # İlk event, timer'ı başlat
        timer_data['end_time'] = datetime.now() + timedelta(seconds=SUBATHON_CONFIG['initial_minutes'] * 60)
        timer_data['is_running'] = True
        print(f"[TIMER] Başlatıldı! İlk süre: {SUBATHON_CONFIG['initial_minutes']} dakika")
    
    # Süre ekle
    if timer_data['end_time']:
        timer_data['end_time'] += timedelta(seconds=seconds)
        
        # Maksimum süreyi kontrol et (opsiyonel)
        if SUBATHON_CONFIG.get('enable_max_limit', True):
            safe_cfg = sanitize_config({'max_minutes': SUBATHON_CONFIG.get('max_minutes', 180)})
            safe_max_minutes = safe_cfg.get('max_minutes', 180)
            max_time = datetime.now() + timedelta(minutes=safe_max_minutes)
            if timer_data['end_time'] > max_time:
                timer_data['end_time'] = max_time
    
    # Event kaydet
    event = {
        'time': datetime.now().strftime('%H:%M:%S'),
        'message': message,
        'type': event_type,
        'seconds_added': seconds
    }
    if isinstance(extra, dict):
        try:
            event.update(extra)
        except Exception:
            pass
    timer_data['events'].insert(0, event)
    
    # Son 50 eventi tut
    if len(timer_data['events']) > 50:
        timer_data['events'] = timer_data['events'][:50]
    
    # WebSocket ile güncelleme gönder
    socketio.emit('timer_update', get_timer_status())
    socketio.emit('new_event', event)

def get_timer_status():
    """Mevcut timer durumunu döndür"""
    if not timer_data['is_running'] or not timer_data['end_time']:
        return {
            'is_running': False,
            'remaining_seconds': 0,
            'hours': 0,
            'minutes': 0,
            'seconds': 0,
            'formatted': '00:00:00'
        }
    
    remaining = timer_data['end_time'] - datetime.now()
    
    if remaining.total_seconds() <= 0:
        # Süre bitti
        timer_data['is_running'] = False
        return {
            'is_running': False,
            'remaining_seconds': 0,
            'hours': 0,
            'minutes': 0,
            'seconds': 0,
            'formatted': '00:00:00',
            'ended': True
        }
    
    total_seconds = int(remaining.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return {
        'is_running': True,
        'remaining_seconds': total_seconds,
        'hours': hours,
        'minutes': minutes,
        'seconds': seconds,
        'formatted': f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    }

# Flask Routes
@app.route('/')
def index():
    """Ana sayfa - OBS Browser Source için"""
    return render_template('timer.html')

@app.route('/control')
def control():
    """Kontrol paneli"""
    return render_template('control.html')

@app.route('/api/status')
def api_status():
    """Timer durumunu döndür"""
    return jsonify({
        'timer': get_timer_status(),
        'config': SUBATHON_CONFIG,
        'events': timer_data['events'][:10]  # Son 10 event
    })

@app.route('/api/start', methods=['POST'])
def api_start():
    """Timer'ı manuel başlat"""
    global timer_data
    
    if not timer_data['is_running']:
        minutes = request.json.get('minutes', SUBATHON_CONFIG['initial_minutes'])
        timer_data['end_time'] = datetime.now() + timedelta(minutes=minutes)
        timer_data['is_running'] = True
        
        event = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'message': f'Timer manuel olarak başlatıldı ({minutes} dakika)',
            'type': 'manual',
            'seconds_added': minutes * 60
        }
        timer_data['events'].insert(0, event)
        
        socketio.emit('timer_update', get_timer_status())
        socketio.emit('new_event', event)
        
        return jsonify({'success': True, 'message': 'Timer başlatıldı'})
    
    return jsonify({'success': False, 'message': 'Timer zaten çalışıyor'})

@app.route('/api/add_time', methods=['POST'])
def api_add_time():
    """Manuel süre ekle"""
    seconds = request.json.get('seconds', 0)
    message = request.json.get('message', 'Manuel süre eklendi')
    
    if seconds > 0:
        add_time(seconds, message, 'manual')
        return jsonify({'success': True, 'message': f'{seconds} saniye eklendi'})
    
    return jsonify({'success': False, 'message': 'Geçersiz süre'})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Timer'ı durdur"""
    global timer_data
    
    timer_data['is_running'] = False
    timer_data['end_time'] = None
    
    socketio.emit('timer_update', get_timer_status())
    
    return jsonify({'success': True, 'message': 'Timer durduruldu'})

@app.route('/api/config', methods=['POST'])
def api_config():
    """Ayarları güncelle"""
    global SUBATHON_CONFIG
    
    config = request.json or {}
    clean = sanitize_config(config)
    SUBATHON_CONFIG.update(clean)
    # Canlı yayınla
    socketio.emit('config_update', SUBATHON_CONFIG)
    
    return jsonify({'success': True, 'config': SUBATHON_CONFIG})

@app.route('/api/ui', methods=['GET', 'POST'])
def api_ui():
    """Görünüm ayarlarını al/güncelle"""
    global UI_CONFIG
    if request.method == 'GET':
        return jsonify({'success': True, 'ui': UI_CONFIG})
    data = request.json or {}
    clean = sanitize_ui_config(data)
    UI_CONFIG.update(clean)
    # İstemcilere canlı güncelleme gönder
    socketio.emit('ui_update', UI_CONFIG)
    return jsonify({'success': True, 'ui': UI_CONFIG})

@app.route('/api/rewards', methods=['GET', 'POST'])
def api_rewards():
    """Sadakat ödülleri yapılandırması"""
    global REWARD_CONFIG
    if request.method == 'GET':
        return jsonify({'success': True, 'rewards': REWARD_CONFIG})
    data = request.json or {}
    clean = sanitize_rewards_payload(data)
    # Merge logic
    if 'enable_rewards' in clean:
        REWARD_CONFIG['enable_rewards'] = clean['enable_rewards']
    if 'default_seconds' in clean:
        REWARD_CONFIG['default_seconds'] = clean['default_seconds']
    if 'rewards' in clean:
        for key, rec in clean['rewards'].items():
            existing = REWARD_CONFIG['rewards'].get(key, {})
            existing.update(rec)
            REWARD_CONFIG['rewards'][key] = existing
    socketio.emit('rewards_update', REWARD_CONFIG)
    return jsonify({'success': True, 'rewards': REWARD_CONFIG})

@app.route('/api/kick_tiers', methods=['GET', 'POST'])
def api_kick_tiers():
    """Kick mağaza miktar (tier) -> saniye ayarları"""
    global KICK_TIER_CONFIG
    if request.method == 'GET':
        return jsonify({'success': True, 'kick_tiers': KICK_TIER_CONFIG})
    data = request.json or {}
    clean = sanitize_kick_tiers_payload(data)
    if 'enable_kick_tiers' in clean:
        KICK_TIER_CONFIG['enable_kick_tiers'] = clean['enable_kick_tiers']
    if 'tiers' in clean:
        for amt, rec in clean['tiers'].items():
            existing = KICK_TIER_CONFIG['tiers'].get(int(amt), {'seconds': 0, 'enabled': False})
            existing.update(rec)
            KICK_TIER_CONFIG['tiers'][int(amt)] = existing
    socketio.emit('kick_tiers_update', KICK_TIER_CONFIG)
    return jsonify({'success': True, 'kick_tiers': KICK_TIER_CONFIG})

# --- Test endpoints (subscription / gift subscription) ---
@app.route('/api/test/sub', methods=['POST'])
def api_test_sub():
    try:
        payload = request.json or {}
        username = str(payload.get('username') or 'Tester')
        if SUBATHON_CONFIG.get('enable_subscription', True):
            minutes = SUBATHON_CONFIG['sub_minutes']
            add_time(minutes * 60, f"{username} abone oldu!", 'subscription', {'username': username})
            print(f"[TEST SUB] {username} +{minutes} dakika")
            return jsonify({'success': True, 'message': f'{username} abone oldu (+{minutes} dk)'}), 200
        return jsonify({'success': False, 'message': 'Abone süre ekleme kapalı'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/test/giftsub', methods=['POST'])
def api_test_giftsub():
    try:
        payload = request.json or {}
        gifter = str(payload.get('username') or 'Tester')
        quantity = int(payload.get('quantity') or 1)
        quantity = max(1, quantity)
        if SUBATHON_CONFIG.get('enable_gift_subscription', True):
            minutes = SUBATHON_CONFIG['gift_sub_minutes'] * quantity
            add_time(minutes * 60, f"{gifter} {quantity} abonelik hediye etti!", 'gift_subscription', {'username': gifter, 'quantity': quantity})
            print(f"[TEST GIFT SUB] {gifter} x{quantity} (+{minutes} dk)")
            return jsonify({'success': True, 'message': f'{gifter} x{quantity} hediye (+{minutes} dk)'}), 200
        return jsonify({'success': False, 'message': 'Hediye abone süre ekleme kapalı'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# SocketIO Events
@socketio.on('connect')
def handle_connect():
    """Client bağlandığında"""
    emit('timer_update', get_timer_status())
    emit('config_update', SUBATHON_CONFIG)
    emit('ui_update', UI_CONFIG)

def timer_broadcast_loop():
    """Her saniye timer güncellemesi gönder"""
    while True:
        if timer_data['is_running']:
            socketio.emit('timer_update', get_timer_status())
        time.sleep(1)

def main():
    """Ana program"""
    print("="*70)
    print("  KICK.COM SUBATHON SERVER")
    print("="*70)
    
    # Kick bilgileri: varsayılan statik değerler veya ortam değişkenleri
    try:
        channel_id = int(os.environ.get('KICK_CHANNEL_ID', DEFAULT_CHANNEL_ID))
        chatroom_id = int(os.environ.get('KICK_CHATROOM_ID', DEFAULT_CHATROOM_ID))
    except (ValueError, TypeError):
        print("\n✗ Geçersiz varsayılan ID.")
        return
    print(f"\n1. Kick kanal bilgileri (statik): slug={DEFAULT_CHANNEL_SLUG}, channel_id={channel_id}, chatroom_id={chatroom_id}")
    
    # Ayarları yapılandır
    print("\n2. Subathon ayarlarını yapılandırın (Enter = varsayılan):")
    print(f"\n   💰 Kick: {SUBATHON_CONFIG['kick_seconds_per_unit']} saniye/kick")
    print(f"   ⭐ Abone: {SUBATHON_CONFIG['sub_minutes']} dakika")
    print()
    
    try:
        initial = input(f"   Başlangıç süresi (dakika) [{SUBATHON_CONFIG['initial_minutes']}]: ").strip()
        if initial:
            SUBATHON_CONFIG['initial_minutes'] = sanitize_config({'initial_minutes': initial})['initial_minutes']
        
        kick_sec = input(f"   Her kick için eklenen süre (saniye) [{SUBATHON_CONFIG['kick_seconds_per_unit']}]: ").strip()
        if kick_sec:
            SUBATHON_CONFIG['kick_seconds_per_unit'] = sanitize_config({'kick_seconds_per_unit': kick_sec})['kick_seconds_per_unit']
        
        sub = input(f"   Abone başına eklenen süre (dakika) [{SUBATHON_CONFIG['sub_minutes']}]: ").strip()
        if sub:
            s_clean = sanitize_config({'sub_minutes': sub, 'gift_sub_minutes': sub})
            SUBATHON_CONFIG['sub_minutes'] = s_clean['sub_minutes']
            SUBATHON_CONFIG['gift_sub_minutes'] = s_clean['gift_sub_minutes']
        
        max_min = input(f"   Maksimum süre (dakika) [{SUBATHON_CONFIG['max_minutes']}]: ").strip()
        if max_min:
            SUBATHON_CONFIG['max_minutes'] = sanitize_config({'max_minutes': max_min})['max_minutes']
    except (ValueError, KeyboardInterrupt):
        print("\n⚠ Varsayılan ayarlar kullanılıyor...")
    
    # Kick listener'ı başlat
    print(f"\n3. Kick.com bağlantısı kuruluyor...")
    listener = KickSubathonListener(channel_id, chatroom_id)
    listener.start()
    
    # Timer broadcast thread'ini başlat
    broadcast_thread = threading.Thread(target=timer_broadcast_loop)
    broadcast_thread.daemon = True
    broadcast_thread.start()
    
    # Flask server'ı başlat
    print("\n" + "="*70)
    print("  SERVER BAŞLATILDI!")
    print("="*70)
    print(f"\n📺 OBS Browser Source URL:")
    print(f"   → http://localhost:5000/")
    print(f"\n🎮 Kontrol Paneli:")
    print(f"   → http://localhost:5000/control")
    print(f"\n{'='*70}\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    main()


