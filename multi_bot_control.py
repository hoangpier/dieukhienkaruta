# multi_bot_control_horror_theme.py
import discum
import threading
import time
import os
import random
import re
import requests
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

load_dotenv()

# --- CẤU HÌNH ---
main_token = os.getenv("MAIN_TOKEN")
main_token_2 = os.getenv("MAIN_TOKEN_2")
main_token_3 = os.getenv("MAIN_TOKEN_3")
tokens = os.getenv("TOKENS").split(",") if os.getenv("TOKENS") else []

main_channel_id = "1301401315208986657"
other_channel_id = "1389525218216640574"
ktb_channel_id = "1389525255269384252"
karuta_id = "646937666251915264"
karibbit_id = "1274445226064220273"

# --- BIẾN TRẠNG THÁI ---
bots = []
main_bot, main_bot_2, main_bot_3 = None, None, None
auto_grab_enabled, auto_grab_enabled_2, auto_grab_enabled_3 = False, False, False
heart_threshold, heart_threshold_2, heart_threshold_3 = 50, 50, 50
last_drop_msg_id = ""
acc_names = ["fiu","fiuthuhai","fiuthuba","fiuthubay","songoku","saitama"]
spam_enabled, spam_message, spam_delay, spam_channel_id = False, "", 10, "1389525697084526592"
auto_work_enabled, work_channel_id, work_delay_between_acc, work_delay_after_all = False, "1390851619016671246", 10, 44100

auto_reboot_enabled = False
auto_reboot_delay = 3600
auto_reboot_thread = None
auto_reboot_stop_event = None

bots_lock = threading.Lock()

def reboot_bot(target_id):
    global main_bot, main_bot_2, main_bot_3, bots
    with bots_lock:
        print(f"[Reboot] Nhận được yêu cầu reboot cho target: {target_id}")
        if target_id == 'main_1' and main_bot:
            print("[Reboot] Đang xử lý Acc Chính 1...")
            try: main_bot.gateway.close()
            except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Chính 1: {e}")
            main_bot = create_bot(main_token, is_main=True)
            print("[Reboot] Acc Chính 1 đã được khởi động lại.")
        elif target_id == 'main_2' and main_bot_2:
            print("[Reboot] Đang xử lý Acc Chính 2...")
            try: main_bot_2.gateway.close()
            except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Chính 2: {e}")
            main_bot_2 = create_bot(main_token_2, is_main_2=True)
            print("[Reboot] Acc Chính 2 đã được khởi động lại.")
        elif target_id == 'main_3' and main_bot_3:
            print("[Reboot] Đang xử lý Acc Chính 3...")
            try: main_bot_3.gateway.close()
            except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Chính 3: {e}")
            main_bot_3 = create_bot(main_token_3, is_main_3=True)
            print("[Reboot] Acc Chính 3 đã được khởi động lại.")
        elif target_id.startswith('sub_'):
            try:
                index = int(target_id.split('_')[1])
                if 0 <= index < len(bots):
                    print(f"[Reboot] Đang xử lý Acc Phụ {index}...")
                    try: bots[index].gateway.close()
                    except Exception as e: print(f"[Reboot] Lỗi khi đóng Acc Phụ {index}: {e}")
                    token_to_reboot = tokens[index]
                    bots[index] = create_bot(token_to_reboot.strip())
                    print(f"[Reboot] Acc Phụ {index} đã được khởi động lại.")
                else: print(f"[Reboot] Index không hợp lệ: {index}")
            except (ValueError, IndexError) as e: print(f"[Reboot] Lỗi xử lý target Acc Phụ: {e}")
        else:
            print(f"[Reboot] Target không xác định: {target_id}")

def create_bot(token, is_main=False, is_main_2=False, is_main_3=False):
    bot = discum.Client(token=token, log=False)
    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_id = resp.raw["user"]["id"]
                bot_type = "(Acc chính)" if is_main else "(Acc chính 2)" if is_main_2 else "(Acc chính 3)" if is_main_3 else ""
                print(f"Đã đăng nhập: {user_id} {bot_type}")
            except Exception as e:
                print(f"Lỗi lấy user_id: {e}")
    if is_main:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled, heart_threshold, last_drop_msg_id
            if resp.event.message:
                msg = resp.parsed.auto(); author = msg.get("author", {}).get("id"); content = msg.get("content", ""); channel = msg.get("channel_id"); mentions = msg.get("mentions", [])
                if author == karuta_id and channel == main_channel_id and "is dropping" not in content and not mentions and auto_grab_enabled:
                    print("\n[Bot 1] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n"); last_drop_msg_id = msg["id"]
                    def read_karibbit():
                        time.sleep(0.5); messages = bot.getMessages(main_channel_id, num=5).json()
                        for msg_inner in messages:
                            if msg_inner.get("author", {}).get("id") == karibbit_id and "embeds" in msg_inner and len(msg_inner["embeds"]) > 0:
                                desc = msg_inner["embeds"][0].get("description", ""); print(f"\n[Bot 1] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 1] ===== Kết thúc tin nhắn =====\n")
                                lines = desc.split('\n'); heart_numbers = []
                                for i, line in enumerate(lines[:3]):
                                    matches = re.findall(r'`([^`]*)`', line)
                                    if len(matches) >= 2 and matches[1].isdigit(): heart_numbers.append(int(matches[1])); print(f"[Bot 1] Dòng {i+1} số tim: {int(matches[1])}")
                                    else: heart_numbers.append(0); print(f"[Bot 1] Dòng {i+1} không tìm thấy số tim, mặc định 0")
                                if sum(heart_numbers) == 0: print("[Bot 1] Không có số tim nào, bỏ qua.\n")
                                else:
                                    max_num = max(heart_numbers)
                                    if max_num < heart_threshold: print(f"[Bot 1] Số tim lớn nhất {max_num} < {heart_threshold}, không grab!\n")
                                    else:
                                        max_index = heart_numbers.index(max_num); emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]; delay = {"1️⃣": 0.5, "2️⃣": 1.5, "3️⃣": 2.2}[emoji]
                                        print(f"[Bot 1] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")
                                        def grab():
                                            try: bot.addReaction(main_channel_id, last_drop_msg_id, emoji); print("[Bot 1] Đã thả emoji grab!"); bot.sendMessage(ktb_channel_id, "kt b"); print("[Bot 1] Đã nhắn 'kt b'!")
                                            except Exception as e: print(f"[Bot 1] Lỗi khi grab hoặc nhắn kt b: {e}")
                                        threading.Timer(delay, grab).start()
                                break
                    threading.Thread(target=read_karibbit).start()
    if is_main_2:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled_2, heart_threshold_2, last_drop_msg_id
            if resp.event.message:
                msg = resp.parsed.auto(); author = msg.get("author", {}).get("id"); content = msg.get("content", ""); channel = msg.get("channel_id"); mentions = msg.get("mentions", [])
                if author == karuta_id and channel == main_channel_id and "is dropping" not in content and not mentions and auto_grab_enabled_2:
                    print("\n[Bot 2] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n"); last_drop_msg_id = msg["id"]
                    def read_karibbit_2():
                        time.sleep(0.5); messages = bot.getMessages(main_channel_id, num=5).json()
                        for msg_inner in messages:
                            if msg_inner.get("author", {}).get("id") == karibbit_id and "embeds" in msg_inner and len(msg_inner["embeds"]) > 0:
                                desc = msg_inner["embeds"][0].get("description", ""); print(f"\n[Bot 2] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 2] ===== Kết thúc tin nhắn =====\n")
                                lines = desc.split('\n'); heart_numbers = []
                                for i, line in enumerate(lines[:3]):
                                    matches = re.findall(r'`([^`]*)`', line)
                                    if len(matches) >= 2 and matches[1].isdigit(): heart_numbers.append(int(matches[1])); print(f"[Bot 2] Dòng {i+1} số tim: {int(matches[1])}")
                                    else: heart_numbers.append(0); print(f"[Bot 2] Dòng {i+1} không tìm thấy số tim, mặc định 0")
                                if sum(heart_numbers) == 0: print("[Bot 2] Không có số tim nào, bỏ qua.\n")
                                else:
                                    max_num = max(heart_numbers)
                                    if max_num < heart_threshold_2: print(f"[Bot 2] Số tim lớn nhất {max_num} < {heart_threshold_2}, không grab!\n")
                                    else:
                                        max_index = heart_numbers.index(max_num); emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]; delay = {"1️⃣": 0.8, "2️⃣": 1.8, "3️⃣": 2.5}[emoji]
                                        print(f"[Bot 2] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")
                                        def grab_2():
                                            try: bot.addReaction(main_channel_id, last_drop_msg_id, emoji); print("[Bot 2] Đã thả emoji grab!"); bot.sendMessage(ktb_channel_id, "kt b"); print("[Bot 2] Đã nhắn 'kt b'!")
                                            except Exception as e: print(f"[Bot 2] Lỗi khi grab hoặc nhắn kt b: {e}")
                                        threading.Timer(delay, grab_2).start()
                                break
                    threading.Thread(target=read_karibbit_2).start()
    if is_main_3:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled_3, heart_threshold_3, last_drop_msg_id
            if resp.event.message:
                msg = resp.parsed.auto(); author = msg.get("author", {}).get("id"); content = msg.get("content", ""); channel = msg.get("channel_id"); mentions = msg.get("mentions", [])
                if author == karuta_id and channel == main_channel_id and "is dropping" not in content and not mentions and auto_grab_enabled_3:
                    print("\n[Bot 3] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n"); last_drop_msg_id = msg["id"]
                    def read_karibbit_3():
                        time.sleep(0.5); messages = bot.getMessages(main_channel_id, num=5).json()
                        for msg_inner in messages:
                            if msg_inner.get("author", {}).get("id") == karibbit_id and "embeds" in msg_inner and len(msg_inner["embeds"]) > 0:
                                desc = msg_inner["embeds"][0].get("description", ""); print(f"\n[Bot 3] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 3] ===== Kết thúc tin nhắn =====\n")
                                lines = desc.split('\n'); heart_numbers = []
                                for i, line in enumerate(lines[:3]):
                                    matches = re.findall(r'`([^`]*)`', line)
                                    if len(matches) >= 2 and matches[1].isdigit(): heart_numbers.append(int(matches[1])); print(f"[Bot 3] Dòng {i+1} số tim: {int(matches[1])}")
                                    else: heart_numbers.append(0); print(f"[Bot 3] Dòng {i+1} không tìm thấy số tim, mặc định 0")
                                if sum(heart_numbers) == 0: print("[Bot 3] Không có số tim nào, bỏ qua.\n")
                                else:
                                    max_num = max(heart_numbers)
                                    if max_num < heart_threshold_3: print(f"[Bot 3] Số tim lớn nhất {max_num} < {heart_threshold_3}, không grab!\n")
                                    else:
                                        max_index = heart_numbers.index(max_num); emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]; delay = {"1️⃣": 1.1, "2️⃣": 2.1, "3️⃣": 2.8}[emoji]
                                        print(f"[Bot 3] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")
                                        def grab_3():
                                            try: bot.addReaction(main_channel_id, last_drop_msg_id, emoji); print("[Bot 3] Đã thả emoji grab!"); bot.sendMessage(ktb_channel_id, "kt b"); print("[Bot 3] Đã nhắn 'kt b'!")
                                            except Exception as e: print(f"[Bot 3] Lỗi khi grab hoặc nhắn kt b: {e}")
                                        threading.Timer(delay, grab_3).start()
                                break
                    threading.Thread(target=read_karibbit_3).start()
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

def run_work_bot(token, acc_index):
    bot = discum.Client(token=token, log={"console": False, "file": False})
    headers = {"Authorization": token, "Content-Type": "application/json"}; step = {"value": 0}
    def send_karuta_command(): print(f"[Work Acc {acc_index}] Gửi lệnh 'kc o:ef'..."); bot.sendMessage(work_channel_id, "kc o:ef")
    def send_kn_command(): print(f"[Work Acc {acc_index}] Gửi lệnh 'kn'..."); bot.sendMessage(work_channel_id, "kn")
    def send_kw_command(): print(f"[Work Acc {acc_index}] Gửi lệnh 'kw'..."); bot.sendMessage(work_channel_id, "kw"); step["value"] = 2
    def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            payload = {"type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": "a", "data": {"component_type": 2, "custom_id": custom_id}}
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload)
            if r.status_code == 204: print(f"[Work Acc {acc_index}] Click tick thành công!")
            else: print(f"[Work Acc {acc_index}] Click thất bại! Mã lỗi: {r.status_code}, Nội dung: {r.text}")
        except Exception as e: print(f"[Work Acc {acc_index}] Lỗi click tick: {str(e)}")
    @bot.gateway.command
    def on_message(resp):
        if resp.event.message:
            m = resp.parsed.auto()
            if str(m.get('channel_id')) != work_channel_id: return
            author_id = str(m.get('author', {}).get('id', '')); guild_id = m.get('guild_id')
            if step["value"] == 0 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                desc = m['embeds'][0].get('description', ''); card_codes = re.findall(r'\bv[a-zA-Z0-9]{6}\b', desc)
                if card_codes and len(card_codes) >= 10:
                    first_5, last_5 = card_codes[:5], card_codes[-5:]
                    print(f"[Work Acc {acc_index}] Mã đầu: {', '.join(first_5)}"); print(f"[Work Acc {acc_index}] Mã cuối: {', '.join(last_5)}")
                    for i, code in enumerate(last_5): suffix = chr(97 + i); time.sleep(2 if i == 0 else 1.5); bot.sendMessage(work_channel_id, f"kjw {code} {suffix}")
                    for i, code in enumerate(first_5): suffix = chr(97 + i); time.sleep(1.5); bot.sendMessage(work_channel_id, f"kjw {code} {suffix}")
                    time.sleep(1); send_kn_command(); step["value"] = 1
            elif step["value"] == 1 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                desc = m['embeds'][0].get('description', ''); lines = desc.split('\n')
                if len(lines) >= 2:
                    match = re.search(r'\d+\.\s*`([^`]+)`', lines[1])
                    if match:
                        resource = match.group(1); print(f"[Work Acc {acc_index}] Tài nguyên chọn: {resource}"); time.sleep(2); bot.sendMessage(work_channel_id, f"kjn `{resource}` a b c d e"); time.sleep(1); send_kw_command()
            elif step["value"] == 2 and author_id == karuta_id and 'components' in m:
                message_id = m['id']; application_id = m.get('application_id', karuta_id); last_custom_id = None
                for comp in m['components']:
                    if comp['type'] == 1:
                        for btn in comp['components']:
                            if btn['type'] == 2: last_custom_id = btn['custom_id']; print(f"[Work Acc {acc_index}] Phát hiện button, custom_id: {last_custom_id}")
                if last_custom_id: click_tick(work_channel_id, message_id, last_custom_id, application_id, guild_id); step["value"] = 3; bot.gateway.close()
    print(f"[Work Acc {acc_index}] Bắt đầu hoạt động..."); threading.Thread(target=bot.gateway.run, daemon=True).start(); time.sleep(3); send_karuta_command()
    timeout = time.time() + 90
    while step["value"] != 3 and time.time() < timeout: time.sleep(1)
    bot.gateway.close(); print(f"[Work Acc {acc_index}] Đã hoàn thành, chuẩn bị tới acc tiếp theo.")

def auto_work_loop():
    global auto_work_enabled
    while True:
        if auto_work_enabled:
            with bots_lock: current_tokens = tokens.copy()
            for i, token in enumerate(current_tokens):
                if token.strip(): print(f"[Auto Work] Đang chạy acc {i+1}..."); run_work_bot(token.strip(), i+1); print(f"[Auto Work] Acc {i+1} xong, chờ {work_delay_between_acc} giây..."); time.sleep(work_delay_between_acc)
            print(f"[Auto Work] Hoàn thành tất cả acc, chờ {work_delay_after_all} giây để lặp lại..."); time.sleep(work_delay_after_all)
        else: time.sleep(10)

def auto_reboot_loop():
    global auto_reboot_stop_event
    print("[Auto Reboot] Luồng tự động reboot đã bắt đầu.")
    while not auto_reboot_stop_event.is_set():
        print(f"[Auto Reboot] Bắt đầu chu kỳ reboot. Chờ {auto_reboot_delay} giây cho chu kỳ tiếp theo...")
        interrupted = auto_reboot_stop_event.wait(timeout=auto_reboot_delay)
        if interrupted: break
        print("[Auto Reboot] Hết thời gian chờ, tiến hành reboot 3 tài khoản chính.")
        if main_bot: reboot_bot('main_1'); time.sleep(5)
        if main_bot_2: reboot_bot('main_2'); time.sleep(5)
        if main_bot_3: reboot_bot('main_3')
    print("[Auto Reboot] Luồng tự động reboot đã dừng.")

def spam_loop():
    global spam_enabled, spam_message, spam_delay
    while True:
        if spam_enabled and spam_message:
            all_bots_to_spam, all_bot_names = [], []
            with bots_lock:
                if main_bot: all_bots_to_spam.append(main_bot); all_bot_names.append("Acc Chính 1")
                if main_bot_2: all_bots_to_spam.append(main_bot_2); all_bot_names.append("Acc Chính 2")
                if main_bot_3: all_bots_to_spam.append(main_bot_3); all_bot_names.append("Acc Chính 3")
                all_bots_to_spam.extend(bots); all_bot_names.extend(acc_names[:len(bots)])
            for idx, bot in enumerate(all_bots_to_spam):
                try:
                    bot_name = all_bot_names[idx]; bot.sendMessage(spam_channel_id, spam_message); print(f"[{bot_name}] đã gửi: {spam_message}"); time.sleep(2)
                except Exception as e:
                    print(f"Lỗi gửi spam từ {all_bot_names[idx]}: {e}")
        time.sleep(spam_delay)

def keep_alive():
    while True:
        try: time.sleep(random.randint(60, 120))
        except: pass

app = Flask(__name__)
HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>D.E.E.P. C.O.N.T.R.O.L</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        /* === GIAO DIỆN DEEPWEB / HORROR === */
        @keyframes text-flicker {{ 0% {{ opacity: 0.8; }} 2% {{ opacity: 1; }} 8% {{ opacity: 0.5; }} 9% {{ opacity: 1; }} 12% {{ opacity: 0.9; }} 20% {{ opacity: 1; }} 25% {{ opacity: 0.4; }} 30% {{ opacity: 1; }} 70% {{ opacity: 1; }} 72% {{ opacity: 0.6; }} 77% {{ opacity: 1; }} 100% {{ opacity: 1; }} }}
        @keyframes scanline {{ 0% {{ transform: translateY(0); }} 100% {{ transform: translateY(100%); }} }}
        * {{ box-sizing: border-box; }}
        body {{
            background-color: #000000;
            font-family: 'Courier New', Courier, monospace;
            color: #00ff00;
            text-shadow: 0 0 5px #00ff00, 0 0 10px rgba(0, 255, 0, 0.5);
            margin: 0; padding: 20px 0;
            overflow-x: hidden;
        }}
        body::before {{
            content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: repeating-linear-gradient(0deg, rgba(0,0,0,0.5), rgba(0,0,0,0.5) 1px, transparent 1px, transparent 2px);
            pointer-events: none; z-index: 1000;
        }}
        .container-fluid {{ padding: 0 25px; }}
        .header-section {{ border-bottom: 2px solid #ff0000; padding: 1.5rem; margin-bottom: 2rem; text-align: center; }}
        .header-section h1 {{ font-size: 2.5rem; font-weight: 700; color: #ff0000; text-shadow: 0 0 10px #ff0000, 0 0 20px #ff0000; animation: text-flicker 4s linear infinite; }}
        .header-section p {{ font-size: 1.1rem; color: #888; letter-spacing: 2px; }}
        .control-card {{ background: #0a0a0a; border: 1px solid #ff0000; box-shadow: 0 0 15px rgba(255, 0, 0, 0.4), inset 0 0 10px rgba(255, 0, 0, 0.2); margin-bottom: 2rem; border-radius: 0; }}
        .control-card .card-header {{ background: #1a0000; border-bottom: 1px solid #ff0000; padding: 1rem; }}
        .control-card .card-header h5 {{ color: #ff0000; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; animation: text-flicker 5s linear infinite reverse; }}
        .control-card .card-body {{ padding: 1.5rem; }}
        .form-control, .form-select {{ background: #000; border: 1px solid #00ff00; border-radius: 0; color: #00ff00; }}
        .form-control:focus, .form-select:focus {{ background: #111; border-color: #ff0000; box-shadow: 0 0 8px #ff0000; color: #ff0000; }}
        .form-control::placeholder {{ color: #444; }}
        .form-select option {{ background: #000; color: #00ff00; }}
        .form-label {{ color: #00ff00; }}
        .input-group-text {{ background: #1a0000; border: 1px solid #ff0000; color: #ff0000; border-radius: 0; }}
        .btn {{ border-radius: 0; text-transform: uppercase; font-weight: bold; transition: all 0.2s; }}
        .btn-primary {{ background: transparent; border: 1px solid #00ff00; color: #00ff00; }}
        .btn-primary:hover {{ background: #00ff00; color: #000; box-shadow: 0 0 15px #00ff00; }}
        .btn-warning {{ background: transparent; border: 1px solid #ffff00; color: #ffff00; }}
        .btn-warning:hover {{ background: #ffff00; color: #000; box-shadow: 0 0 15px #ffff00; }}
        .btn-success {{ background: transparent; border: 1px solid #00ff00; color: #00ff00; }}
        .btn-success:hover {{ background: #00ff00; color: #000; box-shadow: 0 0 15px #00ff00; }}
        .btn-danger {{ background: transparent; border: 1px solid #ff0000; color: #ff0000; }}
        .btn-danger:hover {{ background: #ff0000; color: #fff; box-shadow: 0 0 15px #ff0000; }}
        .status-badge {{ padding: 8px 16px; font-weight: bold; letter-spacing: 1px; }}
        .status-active {{ border: 1px solid #00ff00; color: #00ff00; background: rgba(0, 255, 0, 0.1); text-shadow: 0 0 5px #00ff00; }}
        .status-inactive {{ border: 1px solid #ff0000; color: #ff0000; background: rgba(255, 0, 0, 0.1); }}
        .alert-success {{ background: rgba(0, 255, 0, 0.1); border: 1px solid #00ff00; color: #00ff00; border-radius: 0; }}
        small {{ color: #888 !important; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row"><div class="col-12"><div class="header-section">
            <h1 class="text-center mb-0"><i class="fas fa-skull-crossbones me-3"></i> D.E.E.P. C.O.N.T.R.O.L</h1>
            <p class="text-center text-muted">> EST. 2025 // SYSTEM ONLINE</p>
        </div></div></div>
        {alert_section}
        <div class="row g-4">
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-magic me-2"></i> > AUTO_GRAB::ACC_1</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {auto_grab_status}"><i class="fas fa-broadcast-tower me-1"></i> {auto_grab_text}</span></div>
                    <form method="POST" class="mb-4"><div class="btn-group w-100" role="group"><button name="toggle" value="on" type="submit" class="btn btn-success">INITIATE</button><button name="toggle" value="off" type="submit" class="btn btn-danger">TERMINATE</button></div></form>
                    <div class="heart-threshold"><h6 class="mb-3">> SET_HEART_THRESHOLD:</h6><form method="POST"><div class="input-group"><span class="input-group-text"><i class="fas fa-heart-pulse text-danger"></i></span><input type="number" class="form-control" name="heart_threshold" value="{heart_threshold}" min="0"><button type="submit" class="btn btn-primary">UPDATE</button></div></form></div>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-magic me-2"></i> > AUTO_GRAB::ACC_2</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {auto_grab_status_2}"><i class="fas fa-broadcast-tower me-1"></i> {auto_grab_text_2}</span></div>
                    <form method="POST" class="mb-4"><div class="btn-group w-100" role="group"><button name="toggle_2" value="on" type="submit" class="btn btn-success">INITIATE</button><button name="toggle_2" value="off" type="submit" class="btn btn-danger">TERMINATE</button></div></form>
                    <div class="heart-threshold"><h6 class="mb-3">> SET_HEART_THRESHOLD:</h6><form method="POST"><div class="input-group"><span class="input-group-text"><i class="fas fa-heart-pulse text-danger"></i></span><input type="number" class="form-control" name="heart_threshold_2" value="{heart_threshold_2}" min="0"><button type="submit" class="btn btn-primary">UPDATE</button></div></form></div>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-magic me-2"></i> > AUTO_GRAB::ACC_3</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {auto_grab_status_3}"><i class="fas fa-broadcast-tower me-1"></i> {auto_grab_text_3}</span></div>
                    <form method="POST" class="mb-4"><div class="btn-group w-100" role="group"><button name="toggle_3" value="on" type="submit" class="btn btn-success">INITIATE</button><button name="toggle_3" value="off" type="submit" class="btn btn-danger">TERMINATE</button></div></form>
                    <div class="heart-threshold"><h6 class="mb-3">> SET_HEART_THRESHOLD:</h6><form method="POST"><div class="input-group"><span class="input-group-text"><i class="fas fa-heart-pulse text-danger"></i></span><input type="number" class="form-control" name="heart_threshold_3" value="{heart_threshold_3}" min="0"><button type="submit" class="btn btn-primary">UPDATE</button></div></form></div>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-cogs me-2"></i> > AUTO_WORK::SUBS</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {auto_work_status}"><i class="fas fa-broadcast-tower me-1"></i> {auto_work_text}</span></div>
                    <form method="POST" class="mb-4"><div class="btn-group w-100" role="group"><button name="auto_work_toggle" value="on" type="submit" class="btn btn-success">INITIATE</button><button name="auto_work_toggle" value="off" type="submit" class="btn btn-danger">TERMINATE</button></div></form>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-history me-2"></i> > AUTO_REBOOT::MAINS</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {auto_reboot_status}"><i class="fas fa-broadcast-tower me-1"></i> {auto_reboot_text}</span></div>
                    <form method="POST">
                        <div class="input-group mb-3">
                            <span class="input-group-text"><i class="fas fa-hourglass-half"></i></span>
                            <input type="number" class="form-control" name="auto_reboot_delay" value="{auto_reboot_delay}" min="60">
                            <button type="submit" class="btn btn-primary">UPDATE_DELAY</button>
                        </div>
                        <div class="btn-group w-100" role="group"><button name="auto_reboot_toggle" value="on" type="submit" class="btn btn-success">INITIATE</button><button name="auto_reboot_toggle" value="off" type="submit" class="btn btn-danger">TERMINATE</button></div>
                    </form>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-sync-alt me-2"></i> > MANUAL_REBOOT</h5></div>
                <div class="card-body">
                    <form method="POST">
                        <div class="input-group">
                            <select name="reboot_target" class="form-select">{reboot_options}</select>
                            <button type="submit" class="btn btn-warning">EXECUTE_REBOOT</button>
                        </div>
                    </form>
                </div>
            </div></div>
            <div class="col-12"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-repeat me-2"></i> > SPAM_CONTROL</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {spam_status}"><i class="fas fa-broadcast-tower me-1"></i> {spam_text}</span></div>
                    <form method="POST"><div class="row g-3">
                        <div class="col-md-6"><label class="form-label">> PAYLOAD:</label><input type="text" name="spammsg" class="form-control" value="{spam_message}"></div>
                        <div class="col-md-3"><label class="form-label">> DELAY (s):</label><input type="number" name="spam_delay" class="form-control" value="{spam_delay}" min="1"></div>
                        <div class="col-md-3"><label class="form-label">> COMMAND:</label><div class="btn-group w-100" role="group"><button name="spamtoggle" value="on" type="submit" class="btn btn-success">INITIATE</button><button name="spamtoggle" value="off" type="submit" class="btn btn-danger">TERMINATE</button></div></div>
                    </div></form>
                </div>
            </div></div>
        </div>
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global auto_grab_enabled, auto_grab_enabled_2, auto_grab_enabled_3
    global heart_threshold, heart_threshold_2, heart_threshold_3
    global auto_work_enabled, spam_enabled, spam_message, spam_delay
    global auto_reboot_enabled, auto_reboot_delay, auto_reboot_thread, auto_reboot_stop_event
    msg_status = ""

    if request.method == "POST":
        if "auto_reboot_toggle" in request.form or "auto_reboot_delay" in request.form:
            if "auto_reboot_toggle" in request.form:
                auto_reboot_toggle = request.form.get("auto_reboot_toggle")
                if auto_reboot_toggle == "on":
                    if not auto_reboot_enabled:
                        auto_reboot_enabled = True
                        auto_reboot_stop_event = threading.Event()
                        auto_reboot_thread = threading.Thread(target=auto_reboot_loop, daemon=True)
                        auto_reboot_thread.start()
                        msg_status = "Đã BẬT chế độ tự động reboot acc chính."
                    else: msg_status = "Chế độ tự động reboot đã được bật từ trước."
                elif auto_reboot_toggle == "off":
                    if auto_reboot_enabled and auto_reboot_stop_event:
                        auto_reboot_enabled = False
                        auto_reboot_stop_event.set()
                        auto_reboot_thread = None
                        msg_status = "Đã TẮT chế độ tự động reboot."
                    else: msg_status = "Chế độ tự động reboot chưa được bật."
            if "auto_reboot_delay" in request.form:
                try:
                    delay_val = int(request.form.get("auto_reboot_delay"))
                    if delay_val >= 60:
                        auto_reboot_delay = delay_val
                        msg_status = f"Đã cập nhật delay tự động reboot thành {auto_reboot_delay} giây."
                    else: msg_status = "Lỗi: Delay phải lớn hơn hoặc bằng 60 giây."
                except (ValueError, TypeError): pass
        else:
            if 'toggle' in request.form: auto_grab_enabled = request.form['toggle'] == "on"; msg_status = f"Tự grab Acc 1 {'đã bật' if auto_grab_enabled else 'đã tắt'}"
            if 'toggle_2' in request.form: auto_grab_enabled_2 = request.form['toggle_2'] == "on"; msg_status = f"Tự grab Acc 2 {'đã bật' if auto_grab_enabled_2 else 'đã tắt'}"
            if 'toggle_3' in request.form: auto_grab_enabled_3 = request.form['toggle_3'] == "on"; msg_status = f"Tự grab Acc 3 {'đã bật' if auto_grab_enabled_3 else 'đã tắt'}"
            if 'heart_threshold' in request.form:
                try: heart_threshold = int(request.form['heart_threshold']); msg_status = f"Đã cập nhật mức tim Acc 1: {heart_threshold}"
                except: msg_status = "Mức tim Acc 1 không hợp lệ!"
            if 'heart_threshold_2' in request.form:
                try: heart_threshold_2 = int(request.form['heart_threshold_2']); msg_status = f"Đã cập nhật mức tim Acc 2: {heart_threshold_2}"
                except: msg_status = "Mức tim Acc 2 không hợp lệ!"
            if 'heart_threshold_3' in request.form:
                try: heart_threshold_3 = int(request.form['heart_threshold_3']); msg_status = f"Đã cập nhật mức tim Acc 3: {heart_threshold_3}"
                except: msg_status = "Mức tim Acc 3 không hợp lệ!"
            if 'spamtoggle' in request.form:
                spam_enabled = request.form['spamtoggle'] == "on"
                spam_message = request.form.get("spammsg", "").strip()
                if 'spam_delay' in request.form:
                    try: spam_delay = int(request.form['spam_delay'])
                    except: pass
                msg_status = f"Spam {'đã bật' if spam_enabled else 'đã tắt'}"
            if 'auto_work_toggle' in request.form: auto_work_enabled = request.form['auto_work_toggle'] == "on"; msg_status = f"Auto Work {'đã bật' if auto_work_enabled else 'đã tắt'}"
            if 'reboot_target' in request.form: reboot_bot(request.form['reboot_target']); msg_status = f"Đã gửi yêu cầu reboot cho {request.form['reboot_target']}!"
    
    if msg_status:
        alert_section = f'<div class="row"><div class="col-12"><div class="alert alert-success">{msg_status}</div></div></div>'
    else:
        alert_section = ""

    auto_grab_status, auto_grab_text = ("ONLINE", "ONLINE") if auto_grab_enabled else ("OFFLINE", "OFFLINE")
    auto_grab_status_2, auto_grab_text_2 = ("ONLINE", "ONLINE") if auto_grab_enabled_2 else ("OFFLINE", "OFFLINE")
    auto_grab_status_3, auto_grab_text_3 = ("ONLINE", "ONLINE") if auto_grab_enabled_3 else ("OFFLINE", "OFFLINE")
    auto_work_status, auto_work_text = ("ACTIVE", "ACTIVE") if auto_work_enabled else ("INACTIVE", "INACTIVE")
    auto_reboot_status, auto_reboot_text = ("ACTIVE", "ACTIVE") if auto_reboot_enabled else ("INACTIVE", "INACTIVE")
    spam_status, spam_text = ("ACTIVE", "ACTIVE") if spam_enabled else ("INACTIVE", "INACTIVE")

    reboot_options = ""
    if main_bot: reboot_options += '<option value="main_1">ACC_MAIN_1</option>'
    if main_bot_2: reboot_options += '<option value="main_2">ACC_MAIN_2</option>'
    if main_bot_3: reboot_options += '<option value="main_3">ACC_MAIN_3</option>'
    for i, name in enumerate(acc_names):
        if i < len(bots): reboot_options += f'<option value="sub_{i}">ACC_SUB_{i+1} ({name})</option>'
    acc_options = "".join(f'<option value="{i}">{name}</option>' for i, name in enumerate(acc_names) if i < len(bots))

    return render_template_string(HTML.format(
        alert_section=alert_section, auto_grab_status=auto_grab_status, auto_grab_text=auto_grab_text,
        auto_grab_status_2=auto_grab_status_2, auto_grab_text_2=auto_grab_text_2, auto_grab_status_3=auto_grab_status_3,
        auto_grab_text_3=auto_grab_text_3, auto_work_status=auto_work_status, auto_work_text=auto_work_text,
        heart_threshold=heart_threshold, heart_threshold_2=heart_threshold_2, heart_threshold_3=heart_threshold_3,
        reboot_options=reboot_options, auto_reboot_status=auto_reboot_status, auto_reboot_text=auto_reboot_text,
        auto_reboot_delay=auto_reboot_delay, acc_options=acc_options, spam_status=spam_status, spam_text=spam_text,
        spam_message=spam_message, spam_delay=spam_delay
    ))

if __name__ == "__main__":
    print("Đang khởi tạo các bot...")
    with bots_lock:
        if main_token: main_bot = create_bot(main_token, is_main=True)
        if main_token_2: main_bot_2 = create_bot(main_token_2, is_main_2=True)
        if main_token_3: main_bot_3 = create_bot(main_token_3, is_main_3=True)
        for token in tokens:
            if token.strip(): bots.append(create_bot(token.strip()))
    print("Tất cả các bot đã được khởi tạo.")
    print("Đang khởi tạo các luồng nền...")
    threading.Thread(target=spam_loop, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=auto_work_loop, daemon=True).start()
    print("Các luồng nền đã sẵn sàng.")
    port = int(os.environ.get("PORT", 8080))
    print(f"Khởi động Web Server tại cổng {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
