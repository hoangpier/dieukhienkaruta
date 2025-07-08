# multi_bot_control_fixed.py
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
acc_names = ["accphu1","accphu2","accphu3","accphu4","accphu5","accphu6","accphu7","accphu8","accphu9","accphu10","accphu11","accphu12"]
spam_enabled, spam_message, spam_delay, spam_channel_id = False, "", 10, "1389525697084526592"
auto_work_enabled, work_channel_id, work_delay_between_acc, work_delay_after_all = False, "1390851619016671246", 10, 44100

auto_reboot_enabled = False
auto_reboot_delay = 3600
auto_reboot_thread = None
auto_reboot_stop_event = None

bots_lock = threading.Lock()

def reboot_bot(target_id):
    """Khởi động lại một bot dựa trên ID định danh của nó."""
    global main_bot, main_bot_2, main_bot_3, bots

    with bots_lock:
        print(f"[Reboot] Nhận được yêu cầu reboot cho target: {target_id}")
        
        if target_id == 'main_1' and main_token:
            print("[Reboot] Đang xử lý Acc Chính 1...")
            try:
                if main_bot: main_bot.gateway.close()
            except Exception as e:
                print(f"[Reboot] Lỗi khi đóng Acc Chính 1: {e}")
            main_bot = create_bot(main_token, is_main=True)
            print("[Reboot] Acc Chính 1 đã được khởi động lại.")

        elif target_id == 'main_2' and main_token_2:
            print("[Reboot] Đang xử lý Acc Chính 2...")
            try:
                if main_bot_2: main_bot_2.gateway.close()
            except Exception as e:
                print(f"[Reboot] Lỗi khi đóng Acc Chính 2: {e}")
            main_bot_2 = create_bot(main_token_2, is_main_2=True)
            print("[Reboot] Acc Chính 2 đã được khởi động lại.")
        
        elif target_id == 'main_3' and main_token_3:
            print("[Reboot] Đang xử lý Acc Chính 3...")
            try:
                if main_bot_3: main_bot_3.gateway.close()
            except Exception as e:
                print(f"[Reboot] Lỗi khi đóng Acc Chính 3: {e}")
            main_bot_3 = create_bot(main_token_3, is_main_3=True)
            print("[Reboot] Acc Chính 3 đã được khởi động lại.")

        elif target_id.startswith('sub_'):
            try:
                index = int(target_id.split('_')[1])
                if 0 <= index < len(tokens):
                    print(f"[Reboot] Đang xử lý Acc Phụ {index+1}...")
                    try:
                        # Ensure the bot exists at the index before trying to close it
                        if index < len(bots) and bots[index]:
                            bots[index].gateway.close()
                    except Exception as e:
                        print(f"[Reboot] Lỗi khi đóng Acc Phụ {index+1}: {e}")
                    
                    token_to_reboot = tokens[index]
                    new_bot = create_bot(token_to_reboot.strip())
                    if index < len(bots):
                        bots[index] = new_bot
                    else: # This case should ideally not happen if logic is correct
                        bots.append(new_bot)
                    print(f"[Reboot] Acc Phụ {index+1} đã được khởi động lại.")
                else:
                    print(f"[Reboot] Index không hợp lệ: {index}")
            except (ValueError, IndexError) as e:
                print(f"[Reboot] Lỗi xử lý target Acc Phụ: {e}")
        else:
            print(f"[Reboot] Target không xác định: {target_id}")

def create_bot(token, is_main=False, is_main_2=False, is_main_3=False):
    bot = discum.Client(token=token, log=False)

    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                user_info = bot.gateway.session.user
                user_id = user_info['id']
                username = user_info['username']
                bot_type = "(Acc chính 1)" if is_main else "(Acc chính 2)" if is_main_2 else "(Acc chính 3)" if is_main_3 else "(Acc phụ)"
                print(f"Đã đăng nhập: {username} ({user_id}) {bot_type}")
            except Exception as e:
                print(f"Lỗi lấy thông tin user: {e}")

    # --- ĐỊNH NGHĨA CÁC HÀM XỬ LÝ MESSAGE CHO TỪNG BOT ---
    # (Giữ nguyên các hàm on_message cho is_main, is_main_2, is_main_3)
    if is_main:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled, heart_threshold, last_drop_msg_id
            if resp.event.message:
                msg = resp.parsed.auto()
                author = msg.get("author", {}).get("id")
                content = msg.get("content", "")
                channel = msg.get("channel_id")
                mentions = msg.get("mentions", [])
                if author == karuta_id and channel == main_channel_id:
                    if "is dropping" not in content and not mentions and auto_grab_enabled:
                        print("\n[Bot 1] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n")
                        last_drop_msg_id = msg["id"]
                        def read_karibbit():
                            time.sleep(0.5)
                            messages = bot.getMessages(main_channel_id, num=5).json()
                            for msg_inner in messages:
                                author_id = msg_inner.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg_inner and len(msg_inner["embeds"]) > 0:
                                    desc = msg_inner["embeds"][0].get("description", "")
                                    print(f"\n[Bot 1] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 1] ===== Kết thúc tin nhắn =====\n")
                                    lines = desc.split('\n')
                                    heart_numbers = []
                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            heart_numbers.append(int(matches[1]))
                                            print(f"[Bot 1] Dòng {i+1} số tim: {int(matches[1])}")
                                        else:
                                            heart_numbers.append(0)
                                            print(f"[Bot 1] Dòng {i+1} không tìm thấy số tim, mặc định 0")
                                    if sum(heart_numbers) == 0:
                                        print("[Bot 1] Không có số tim nào, bỏ qua.\n")
                                    else:
                                        max_num = max(heart_numbers)
                                        if max_num < heart_threshold:
                                            print(f"[Bot 1] Số tim lớn nhất {max_num} < {heart_threshold}, không grab!\n")
                                        else:
                                            max_index = heart_numbers.index(max_num)
                                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                            delay = {"1️⃣": 0.5, "2️⃣": 1.5, "3️⃣": 2.2}[emoji]
                                            print(f"[Bot 1] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")
                                            def grab():
                                                try:
                                                    bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                    print("[Bot 1] Đã thả emoji grab!")
                                                    bot.sendMessage(ktb_channel_id, "kt b")
                                                    print("[Bot 1] Đã nhắn 'kt b'!")
                                                except Exception as e:
                                                    print(f"[Bot 1] Lỗi khi grab hoặc nhắn kt b: {e}")
                                            threading.Timer(delay, grab).start()
                                    break
                        threading.Thread(target=read_karibbit).start()
    
    if is_main_2:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled_2, heart_threshold_2, last_drop_msg_id
            if resp.event.message:
                msg = resp.parsed.auto()
                author = msg.get("author", {}).get("id")
                content = msg.get("content", "")
                channel = msg.get("channel_id")
                mentions = msg.get("mentions", [])
                if author == karuta_id and channel == main_channel_id:
                    if "is dropping" not in content and not mentions and auto_grab_enabled_2:
                        print("\n[Bot 2] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n")
                        last_drop_msg_id = msg["id"]
                        def read_karibbit_2():
                            time.sleep(0.5)
                            messages = bot.getMessages(main_channel_id, num=5).json()
                            for msg_inner in messages:
                                author_id = msg_inner.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg_inner and len(msg_inner["embeds"]) > 0:
                                    desc = msg_inner["embeds"][0].get("description", "")
                                    print(f"\n[Bot 2] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 2] ===== Kết thúc tin nhắn =====\n")
                                    lines = desc.split('\n')
                                    heart_numbers = []
                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            heart_numbers.append(int(matches[1]))
                                            print(f"[Bot 2] Dòng {i+1} số tim: {int(matches[1])}")
                                        else:
                                            heart_numbers.append(0)
                                            print(f"[Bot 2] Dòng {i+1} không tìm thấy số tim, mặc định 0")
                                    if sum(heart_numbers) == 0:
                                        print("[Bot 2] Không có số tim nào, bỏ qua.\n")
                                    else:
                                        max_num = max(heart_numbers)
                                        if max_num < heart_threshold_2:
                                            print(f"[Bot 2] Số tim lớn nhất {max_num} < {heart_threshold_2}, không grab!\n")
                                        else:
                                            max_index = heart_numbers.index(max_num)
                                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                            delay = {"1️⃣": 0.8, "2️⃣": 1.8, "3️⃣": 2.5}[emoji]
                                            print(f"[Bot 2] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")
                                            def grab_2():
                                                try:
                                                    bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                    print("[Bot 2] Đã thả emoji grab!")
                                                    bot.sendMessage(ktb_channel_id, "kt b")
                                                    print("[Bot 2] Đã nhắn 'kt b'!")
                                                except Exception as e:
                                                    print(f"[Bot 2] Lỗi khi grab hoặc nhắn kt b: {e}")
                                            threading.Timer(delay, grab_2).start()
                                    break
                        threading.Thread(target=read_karibbit_2).start()
                        
    if is_main_3:
        @bot.gateway.command
        def on_message(resp):
            global auto_grab_enabled_3, heart_threshold_3, last_drop_msg_id
            if resp.event.message:
                msg = resp.parsed.auto()
                author = msg.get("author", {}).get("id")
                content = msg.get("content", "")
                channel = msg.get("channel_id")
                mentions = msg.get("mentions", [])
                if author == karuta_id and channel == main_channel_id:
                    if "is dropping" not in content and not mentions and auto_grab_enabled_3:
                        print("\n[Bot 3] Phát hiện tự drop! Đọc tin nhắn Karibbit...\n")
                        last_drop_msg_id = msg["id"]
                        def read_karibbit_3():
                            time.sleep(0.5)
                            messages = bot.getMessages(main_channel_id, num=5).json()
                            for msg_inner in messages:
                                author_id = msg_inner.get("author", {}).get("id")
                                if author_id == karibbit_id and "embeds" in msg_inner and len(msg_inner["embeds"]) > 0:
                                    desc = msg_inner["embeds"][0].get("description", "")
                                    print(f"\n[Bot 3] ===== Tin nhắn Karibbit đọc được =====\n{desc}\n[Bot 3] ===== Kết thúc tin nhắn =====\n")
                                    lines = desc.split('\n')
                                    heart_numbers = []
                                    for i, line in enumerate(lines[:3]):
                                        matches = re.findall(r'`([^`]*)`', line)
                                        if len(matches) >= 2 and matches[1].isdigit():
                                            heart_numbers.append(int(matches[1]))
                                            print(f"[Bot 3] Dòng {i+1} số tim: {int(matches[1])}")
                                        else:
                                            heart_numbers.append(0)
                                            print(f"[Bot 3] Dòng {i+1} không tìm thấy số tim, mặc định 0")
                                    if sum(heart_numbers) == 0:
                                        print("[Bot 3] Không có số tim nào, bỏ qua.\n")
                                    else:
                                        max_num = max(heart_numbers)
                                        if max_num < heart_threshold_3:
                                            print(f"[Bot 3] Số tim lớn nhất {max_num} < {heart_threshold_3}, không grab!\n")
                                        else:
                                            max_index = heart_numbers.index(max_num)
                                            emoji = ["1️⃣", "2️⃣", "3️⃣"][max_index]
                                            delay = {"1️⃣": 1.1, "2️⃣": 2.1, "3️⃣": 2.8}[emoji]
                                            print(f"[Bot 3] Chọn dòng {max_index+1} với số tim {max_num} → Emoji {emoji} sau {delay}s\n")
                                            def grab_3():
                                                try:
                                                    bot.addReaction(main_channel_id, last_drop_msg_id, emoji)
                                                    print("[Bot 3] Đã thả emoji grab!")
                                                    bot.sendMessage(ktb_channel_id, "kt b")
                                                    print("[Bot 3] Đã nhắn 'kt b'!")
                                                except Exception as e:
                                                    print(f"[Bot 3] Lỗi khi grab hoặc nhắn kt b: {e}")
                                            threading.Timer(delay, grab_3).start()
                                    break
                        threading.Thread(target=read_karibbit_3).start()
    
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

# --- CÁC HÀM XỬ LÝ VÒNG LẶP NỀN (ĐÃ CẢI TIẾN) ---

def run_work_bot(token, acc_index):
    # (Hàm này giữ nguyên, vì nó là một tiến trình ngắn hạn và đã có timeout)
    bot = discum.Client(token=token, log={"console": False, "file": False})
    headers = {"Authorization": token, "Content-Type": "application/json"}
    step = {"value": 0}
    def send_karuta_command():
        print(f"[Work Acc {acc_index}] Gửi lệnh 'kc o:ef'...")
        bot.sendMessage(work_channel_id, "kc o:ef")
    def send_kn_command():
        print(f"[Work Acc {acc_index}] Gửi lệnh 'kn'...")
        bot.sendMessage(work_channel_id, "kn")
    def send_kw_command():
        print(f"[Work Acc {acc_index}] Gửi lệnh 'kw'...")
        bot.sendMessage(work_channel_id, "kw")
        step["value"] = 2
    def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            payload = {"type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": "a", "data": {"component_type": 2, "custom_id": custom_id}}
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=payload)
            if r.status_code == 204: print(f"[Work Acc {acc_index}] Click tick thành công!")
            else: print(f"[Work Acc {acc_index}] Click thất bại! Mã lỗi: {r.status_code}, Nội dung: {r.text}")
        except Exception as e:
            print(f"[Work Acc {acc_index}] Lỗi click tick: {str(e)}")
    @bot.gateway.command
    def on_message(resp):
        if resp.event.message:
            m = resp.parsed.auto()
            if str(m.get('channel_id')) != work_channel_id:
                return
            author_id = str(m.get('author', {}).get('id', ''))
            guild_id = m.get('guild_id')
            if step["value"] == 0 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                desc = m['embeds'][0].get('description', '')
                card_codes = re.findall(r'\bv[a-zA-Z0-9]{6}\b', desc)
                if card_codes and len(card_codes) >= 10:
                    first_5, last_5 = card_codes[:5], card_codes[-5:]
                    print(f"[Work Acc {acc_index}] Mã đầu: {', '.join(first_5)}")
                    print(f"[Work Acc {acc_index}] Mã cuối: {', '.join(last_5)}")
                    for i, code in enumerate(last_5):
                        suffix = chr(97 + i)
                        time.sleep(2 if i == 0 else 1.5)
                        bot.sendMessage(work_channel_id, f"kjw {code} {suffix}")
                    for i, code in enumerate(first_5):
                        suffix = chr(97 + i)
                        time.sleep(1.5)
                        bot.sendMessage(work_channel_id, f"kjw {code} {suffix}")
                    time.sleep(1)
                    send_kn_command()
                    step["value"] = 1
            elif step["value"] == 1 and author_id == karuta_id and 'embeds' in m and len(m['embeds']) > 0:
                desc = m['embeds'][0].get('description', '')
                lines = desc.split('\n')
                if len(lines) >= 2:
                    match = re.search(r'\d+\.\s*`([^`]+)`', lines[1])
                    if match:
                        resource = match.group(1)
                        print(f"[Work Acc {acc_index}] Tài nguyên chọn: {resource}")
                        time.sleep(2)
                        bot.sendMessage(work_channel_id, f"kjn `{resource}` a b c d e")
                        time.sleep(1)
                        send_kw_command()
            elif step["value"] == 2 and author_id == karuta_id and 'components' in m:
                message_id = m['id']
                application_id = m.get('application_id', karuta_id)
                last_custom_id = None
                for comp in m['components']:
                    if comp['type'] == 1:
                        for btn in comp['components']:
                            if btn['type'] == 2:
                                last_custom_id = btn['custom_id']
                                print(f"[Work Acc {acc_index}] Phát hiện button, custom_id: {last_custom_id}")
                if last_custom_id:
                    click_tick(work_channel_id, message_id, last_custom_id, application_id, guild_id)
                    step["value"] = 3
                    bot.gateway.close()
    print(f"[Work Acc {acc_index}] Bắt đầu hoạt động...")
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    time.sleep(3)
    send_karuta_command()
    timeout = time.time() + 90
    while step["value"] != 3 and time.time() < timeout:
        time.sleep(1)
    if step["value"] != 3:
        print(f"[Work Acc {acc_index}] Timeout, không hoàn thành công việc.")
    bot.gateway.close()
    print(f"[Work Acc {acc_index}] Đã hoàn thành, chuẩn bị tới acc tiếp theo.")

def auto_work_loop():
    global auto_work_enabled
    while True:
        try:
            if auto_work_enabled:
                with bots_lock:
                    current_tokens = tokens.copy()
                
                if not current_tokens:
                    print("[Auto Work] Không có token nào cho acc phụ. Tạm dừng 10 phút.")
                    time.sleep(600)
                    continue

                for i, token in enumerate(current_tokens):
                    if not auto_work_enabled: # Check again in case it was disabled during the loop
                        print("[Auto Work] Chức năng đã bị tắt. Dừng chu kỳ hiện tại.")
                        break
                    if token.strip():
                        print(f"\n[Auto Work] >>> Đang chạy acc {i+1}/{len(current_tokens)}... <<<")
                        run_work_bot(token.strip(), i+1)
                        print(f"[Auto Work] Acc {i+1} xong, chờ {work_delay_between_acc} giây...")
                        time.sleep(work_delay_between_acc)
                
                if auto_work_enabled:
                    print(f"\n[Auto Work] === Hoàn thành tất cả acc, chờ {work_delay_after_all / 60} phút để lặp lại... ===\n")
                    time.sleep(work_delay_after_all)
            else:
                time.sleep(10) # Sleep when disabled
        except Exception as e:
            print(f"[LỖI NGHIÊM TRỌNG] trong auto_work_loop: {e}")
            print("[Auto Work] Sẽ thử lại sau 60 giây...")
            time.sleep(60)

def auto_reboot_loop():
    global auto_reboot_stop_event
    print("[Auto Reboot] Luồng tự động reboot đã bắt đầu.")
    while not auto_reboot_stop_event.is_set():
        try:
            print(f"[Auto Reboot] Bắt đầu chu kỳ reboot. Chờ {auto_reboot_delay / 3600:.2f} giờ cho chu kỳ tiếp theo...")
            interrupted = auto_reboot_stop_event.wait(timeout=auto_reboot_delay)
            if interrupted:
                break
            
            print("[Auto Reboot] Hết thời gian chờ, tiến hành reboot toàn bộ các tài khoản.")
            
            # Reboot Acc Chính
            if main_bot: reboot_bot('main_1'); time.sleep(5)
            if main_bot_2: reboot_bot('main_2'); time.sleep(5)
            if main_bot_3: reboot_bot('main_3'); time.sleep(5)

            # Reboot Acc Phụ
            num_sub_bots = 0
            with bots_lock:
                num_sub_bots = len(bots)
            
            if num_sub_bots > 0:
                print("[Auto Reboot] Tiến hành reboot các tài khoản phụ...")
                for i in range(num_sub_bots):
                    if auto_reboot_stop_event.is_set(): break
                    print(f"[Auto Reboot] Đang reboot Acc Phụ {i+1}...")
                    reboot_bot(f'sub_{i}')
                    time.sleep(5)
            
            print("[Auto Reboot] Chu kỳ reboot hoàn tất.")

        except Exception as e:
            print(f"[LỖI NGHIÊM TRỌNG] trong auto_reboot_loop: {e}")
            print("[Auto Reboot] Sẽ thử lại sau 5 phút...")
            time.sleep(300)

    print("[Auto Reboot] Luồng tự động reboot đã dừng.")
    
def spam_loop():
    global spam_enabled, spam_message, spam_delay
    while True:
        try:
            if spam_enabled and spam_message:
                all_bots_to_spam = []
                all_bot_names = []
                with bots_lock:
                    if main_bot: all_bots_to_spam.append(main_bot); all_bot_names.append("Acc Chính 1")
                    if main_bot_2: all_bots_to_spam.append(main_bot_2); all_bot_names.append("Acc Chính 2")
                    if main_bot_3: all_bots_to_spam.append(main_bot_3); all_bot_names.append("Acc Chính 3")
                    all_bots_to_spam.extend(bots)
                    all_bot_names.extend(acc_names[:len(bots)])

                for idx, bot in enumerate(all_bots_to_spam):
                    if not spam_enabled: break # Stop if disabled mid-spam
                    try:
                        bot_name = all_bot_names[idx]
                        bot.sendMessage(spam_channel_id, spam_message)
                        print(f"[{bot_name}] đã gửi: {spam_message}")
                        time.sleep(2) # Delay between each account
                    except Exception as e:
                        print(f"Lỗi gửi spam từ {all_bot_names[idx]}: {e}")
            time.sleep(spam_delay)
        except Exception as e:
            print(f"[LỖI NGHIÊM TRỌNG] trong spam_loop: {e}")
            print("[Spam] Sẽ thử lại sau 60 giây...")
            time.sleep(60)

def health_check_loop():
    """Periodically checks if bots are connected and reboots them if not."""
    time.sleep(60) # Initial delay
    while True:
        try:
            print("[Health Check] Bắt đầu kiểm tra trạng thái các bot...")
            with bots_lock:
                # Check main bots
                if main_bot and not main_bot.gateway.READY:
                    print("[Health Check] ‼️ Acc Chính 1 mất kết nối. Đang reboot...")
                    reboot_bot('main_1')
                    time.sleep(10)
                
                if main_bot_2 and not main_bot_2.gateway.READY:
                    print("[Health Check] ‼️ Acc Chính 2 mất kết nối. Đang reboot...")
                    reboot_bot('main_2')
                    time.sleep(10)

                if main_bot_3 and not main_bot_3.gateway.READY:
                    print("[Health Check] ‼️ Acc Chính 3 mất kết nối. Đang reboot...")
                    reboot_bot('main_3')
                    time.sleep(10)

                # Check sub bots
                for i, bot in enumerate(bots):
                    if bot and not bot.gateway.READY:
                        print(f"[Health Check] ‼️ Acc Phụ {i+1} mất kết nối. Đang reboot...")
                        reboot_bot(f'sub_{i}')
                        time.sleep(10)
            
            print("[Health Check] Kiểm tra hoàn tất. Chu kỳ tiếp theo sau 5 phút.")
        except Exception as e:
            print(f"[LỖI NGHIÊM TRỌNG] trong health_check_loop: {e}")
        
        time.sleep(300) # Check every 5 minutes

# --- FLASK WEB SERVER ---
app = Flask(__name__)
HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Karuta Deep</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; }} body {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); min-height: 100vh; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #ffffff; margin: 0; padding: 20px 0; }}
        .header-section {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin-bottom: 2rem; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); }}
        .header-section h1 {{ font-size: 2.5rem; font-weight: 700; background: linear-gradient(45deg, #00d4ff, #ff9500); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 0.5rem; text-shadow: 0 0 20px rgba(0, 212, 255, 0.3); }}
        .header-section p {{ font-size: 1.1rem; color: #b0b0b0; margin-bottom: 0; }} .control-card {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); transition: all 0.3s ease; overflow: hidden; margin-bottom: 2rem; }}
        .control-card:hover {{ transform: translateY(-5px); box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4); border-color: rgba(0, 212, 255, 0.3); }} .control-card .card-header {{ background: linear-gradient(45deg, rgba(0, 212, 255, 0.2), rgba(255, 149, 0, 0.2)); border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding: 1.5rem; border-radius: 20px 20px 0 0; }}
        .control-card .card-header h5 {{ color: #ffffff; font-weight: 600; margin: 0; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3); }} .control-card .card-body {{ padding: 1.5rem; }}
        .form-control {{ background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; color: #ffffff; padding: 12px 16px; font-size: 1rem; transition: all 0.3s ease; }}
        .form-control:focus {{ background: rgba(255, 255, 255, 0.15); border-color: #00d4ff; box-shadow: 0 0 0 0.2rem rgba(0, 212, 255, 0.25); color: #ffffff; }}
        .form-control::placeholder {{ color: #b0b0b0; }} .form-select {{ background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; color: #ffffff; padding: 12px 16px; font-size: 1rem; transition: all 0.3s ease; }}
        .form-select:focus {{ background: rgba(255, 255, 255, 0.15); border-color: #00d4ff; box-shadow: 0 0 0 0.2rem rgba(0, 212, 255, 0.25); color: #ffffff; }}
        .form-select option {{ background: #1a1a2e; color: #ffffff; }} .form-label {{ color: #ffffff; font-weight: 500; margin-bottom: 0.5rem; }}
        .input-group-text {{ background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #ffffff; border-radius: 12px 0 0 12px; }}
        .btn {{ border-radius: 12px; padding: 12px 24px; font-weight: 500; font-size: 1rem; transition: all 0.3s ease; text-transform: uppercase; letter-spacing: 0.5px; border: none; position: relative; overflow: hidden; }}
        .btn::before {{ content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent); transition: left 0.5s ease; }}
        .btn:hover::before {{ left: 100%; }} .btn-primary {{ background: linear-gradient(45deg, #00d4ff, #0099cc); color: #ffffff; box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4); }}
        .btn-primary:hover {{ background: linear-gradient(45deg, #0099cc, #00d4ff); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 212, 255, 0.6); }} .btn-warning {{ background: linear-gradient(45deg, #ffc107, #ff9800); color: #1a1a2e; box-shadow: 0 4px 15px rgba(255, 193, 7, 0.4); }}
        .btn-warning:hover {{ background: linear-gradient(45deg, #ff9800, #ffc107); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(255, 193, 7, 0.6); }} .btn-success {{ background: linear-gradient(45deg, #28a745, #20c997); color: #ffffff; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4); }}
        .btn-success:hover {{ background: linear-gradient(45deg, #20c997, #28a745); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(40, 167, 69, 0.6); }} .btn-danger {{ background: linear-gradient(45deg, #dc3545, #e83e8c); color: #ffffff; box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4); }}
        .btn-danger:hover {{ background: linear-gradient(45deg, #e83e8c, #dc3545); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(220, 53, 69, 0.6); }} .status-indicator {{ display: flex; align-items: center; margin-bottom: 1rem; }}
        .status-badge {{ display: inline-flex; align-items: center; padding: 8px 16px; border-radius: 20px; font-size: 0.9rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; transition: all 0.3s ease; }}
        .status-active {{ background: linear-gradient(45deg, #28a745, #20c997); color: #ffffff; box-shadow: 0 0 20px rgba(40, 167, 69, 0.3); }}
        .status-inactive {{ background: linear-gradient(45deg, #dc3545, #e83e8c); color: #ffffff; box-shadow: 0 0 20px rgba(220, 53, 69, 0.3); }}
        .alert {{ background: rgba(40, 167, 69, 0.2); border: 1px solid rgba(40, 167, 69, 0.3); border-radius: 12px; color: #ffffff; backdrop-filter: blur(10px); margin-bottom: 1rem; }}
        .alert-success {{ background: rgba(40, 167, 69, 0.2); border-color: rgba(40, 167, 69, 0.3); }}
        @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(30px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .control-card {{ animation: fadeInUp 0.6s ease-out; }} .quick-commands {{ margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid rgba(255, 255, 255, 0.1); }}
        .quick-commands h6 {{ color: #ffffff; font-weight: 600; margin-bottom: 1rem; }} .heart-threshold {{ margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid rgba(255, 255, 255, 0.1); }}
        .heart-threshold h6 {{ color: #ffffff; font-weight: 600; margin-bottom: 1rem; }}
        @media (max-width: 768px) {{ .header-section {{ padding: 1.5rem; margin-bottom: 1.5rem; }} .header-section h1 {{ font-size: 2rem; }} .control-card .card-header, .control-card .card-body {{ padding: 1rem; }} .btn {{ padding: 10px 20px; font-size: 0.9rem; }} }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row"><div class="col-12"><div class="header-section">
            <h1 class="text-center mb-0"><i class="fas fa-robot me-3"></i> Karuta Deep</h1>
            <p class="text-center text-muted">Quản lý bot Discord với giao diện hiện đại</p>
        </div></div></div>
        {alert_section}
        <div class="row g-4">
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-paper-plane me-2"></i>Điều khiển bot nhắn tin</h5></div>
                <div class="card-body">
                    <form method="POST" class="mb-4"><div class="input-group">
                        <input type="text" class="form-control" name="message" placeholder="Nhập nội dung tin nhắn...">
                        <button class="btn btn-primary" type="submit"><i class="fas fa-send me-1"></i>Gửi thủ công</button>
                    </div></form>
                    <div class="quick-commands"><h6 class="mb-3">Menu nhanh</h6><form method="POST"><div class="input-group">
                        <select name="quickmsg" class="form-select">
                            <option value="kc o:w">kc o:w</option><option value="kc o:ef">kc o:ef</option><option value="kc o:p">kc o:p</option>
                            <option value="kc e:1">kc e:1</option><option value="kc e:2">kc e:2</option><option value="kc e:3">kc e:3</option>
                            <option value="kc e:4">kc e:4</option><option value="kc e:5">kc e:5</option><option value="kc e:6">kc e:6</option><option value="kc e:7">kc e:7</option>
                        </select>
                        <button type="submit" class="btn btn-success"><i class="fas fa-bolt me-1"></i>Gửi</button>
                    </div></form></div>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-briefcase me-2"></i>Auto Work</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {auto_work_status}"><i class="fas fa-circle me-1"></i> {auto_work_text}</span></div>
                    <form method="POST" class="mb-4"><div class="btn-group w-100" role="group"><button name="auto_work_toggle" value="on" type="submit" class="btn btn-success"><i class="fas fa-play me-1"></i>Bật</button><button name="auto_work_toggle" value="off" type="submit" class="btn btn-danger"><i class="fas fa-stop me-1"></i>Tắt</button></div></form>
                    <div class="mt-2"><small class="text-muted"><i class="fas fa-info-circle me-1"></i> Tự động làm việc cho tất cả account phụ</small></div>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-magic me-2"></i>Auto Grab - Acc Chính 1</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {auto_grab_status}"><i class="fas fa-circle me-1"></i> {auto_grab_text}</span></div>
                    <form method="POST" class="mb-4"><div class="btn-group w-100" role="group"><button name="toggle" value="on" type="submit" class="btn btn-success"><i class="fas fa-play me-1"></i>Bật</button><button name="toggle" value="off" type="submit" class="btn btn-danger"><i class="fas fa-stop me-1"></i>Tắt</button></div></form>
                    <div class="heart-threshold"><h6 class="mb-3">Mức tim tiêu chuẩn</h6><form method="POST"><div class="input-group"><span class="input-group-text"><i class="fas fa-heart text-danger"></i></span><input type="number" class="form-control" name="heart_threshold" value="{heart_threshold}" min="0" placeholder="Mức tim"><button type="submit" class="btn btn-primary"><i class="fas fa-save me-1"></i>Lưu</button></div></form></div>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-magic me-2"></i>Auto Grab - Acc Chính 2</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {auto_grab_status_2}"><i class="fas fa-circle me-1"></i> {auto_grab_text_2}</span></div>
                    <form method="POST" class="mb-4"><div class="btn-group w-100" role="group"><button name="toggle_2" value="on" type="submit" class="btn btn-success"><i class="fas fa-play me-1"></i>Bật</button><button name="toggle_2" value="off" type="submit" class="btn btn-danger"><i class="fas fa-stop me-1"></i>Tắt</button></div></form>
                    <div class="heart-threshold"><h6 class="mb-3">Mức tim tiêu chuẩn</h6><form method="POST"><div class="input-group"><span class="input-group-text"><i class="fas fa-heart text-danger"></i></span><input type="number" class="form-control" name="heart_threshold_2" value="{heart_threshold_2}" min="0" placeholder="Mức tim"><button type="submit" class="btn btn-primary"><i class="fas fa-save me-1"></i>Lưu</button></div></form></div>
                    <div class="mt-2"><small class="text-muted"><i class="fas fa-info-circle me-1"></i> Delay grab chậm hơn 0.3s so với Acc 1</small></div>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-magic me-2"></i>Auto Grab - Acc Chính 3</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {auto_grab_status_3}"><i class="fas fa-circle me-1"></i> {auto_grab_text_3}</span></div>
                    <form method="POST" class="mb-4"><div class="btn-group w-100" role="group"><button name="toggle_3" value="on" type="submit" class="btn btn-success"><i class="fas fa-play me-1"></i>Bật</button><button name="toggle_3" value="off" type="submit" class="btn btn-danger"><i class="fas fa-stop me-1"></i>Tắt</button></div></form>
                    <div class="heart-threshold"><h6 class="mb-3">Mức tim tiêu chuẩn</h6><form method="POST"><div class="input-group"><span class="input-group-text"><i class="fas fa-heart text-danger"></i></span><input type="number" class="form-control" name="heart_threshold_3" value="{heart_threshold_3}" min="0" placeholder="Mức tim"><button type="submit" class="btn btn-primary"><i class="fas fa-save me-1"></i>Lưu</button></div></form></div>
                    <div class="mt-2"><small class="text-muted"><i class="fas fa-info-circle me-1"></i> Delay grab chậm hơn 0.3s so với Acc 2</small></div>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-history me-2"></i> Tự động Reboot Acc Chính</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {auto_reboot_status}"><i class="fas fa-circle me-1"></i> {auto_reboot_text}</span></div>
                    <form method="POST">
                        <div class="input-group mb-3">
                            <span class="input-group-text"><i class="fas fa-hourglass-half"></i></span>
                            <input type="number" class="form-control" name="auto_reboot_delay" value="{auto_reboot_delay}" min="60" placeholder="giây">
                            <button type="submit" class="btn btn-primary">Cập nhật Delay</button>
                        </div>
                        <div class="btn-group w-100" role="group"><button name="auto_reboot_toggle" value="on" type="submit" class="btn btn-success"><i class="fas fa-play me-1"></i>Bật</button><button name="auto_reboot_toggle" value="off" type="submit" class="btn btn-danger"><i class="fas fa-stop me-1"></i>Tắt</button></div>
                    </form>
                    <div class="mt-2"><small class="text-muted"><i class="fas fa-info-circle me-1"></i> Tự động khởi động lại 3 acc chính theo chu kỳ.</small></div>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-sync-alt me-2"></i> Reboot Thủ Công</h5></div>
                <div class="card-body">
                    <form method="POST">
                        <div class="input-group">
                            <select name="reboot_target" class="form-select">{reboot_options}</select>
                            <button type="submit" class="btn btn-warning"><i class="fas fa-power-off me-1"></i>Reboot Bot</button>
                        </div>
                    </form>
                    <div class="mt-2"><small class="text-muted"><i class="fas fa-info-circle me-1"></i> Dùng khi một bot bị "đơ" hoặc không hoạt động đúng.</small></div>
                </div>
            </div></div>
            <div class="col-lg-6"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-code me-2"></i>Gửi danh sách mã theo acc chọn</h5></div>
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6"><label class="form-label">Chọn acc:</label><select name="acc_index" class="form-select">{acc_options}</select></div>
                            <div class="col-md-6"><label class="form-label">Thời gian cách nhau (giây):</label><input type="number" step="0.1" name="delay" class="form-control" value="11" placeholder="11"></div>
                            <div class="col-12"><label class="form-label">Nội dung mẫu:</label><input type="text" name="prefix" class="form-control" placeholder="vd: kt n"></div>
                            <div class="col-12"><label class="form-label">Danh sách mã:</label><textarea name="codes" class="form-control" rows="4" placeholder="Danh sách mã, cách nhau dấu phẩy"></textarea></div>
                            <div class="col-12"><button type="submit" name="send_codes" value="1" class="btn btn-primary btn-lg"><i class="fas fa-paper-plane me-2"></i>Gửi danh sách mã</button></div>
                        </div>
                    </form>
                </div>
            </div></div>
            <div class="col-12"><div class="control-card">
                <div class="card-header"><h5 class="mb-0"><i class="fas fa-repeat me-2"></i>Spam Control</h5></div>
                <div class="card-body">
                    <div class="status-indicator mb-3"><span class="status-badge {spam_status}"><i class="fas fa-circle me-1"></i> {spam_text}</span></div>
                    <form method="POST"><div class="row g-3">
                        <div class="col-md-6"><label class="form-label">Nội dung spam:</label><input type="text" name="spammsg" class="form-control" placeholder="Nội dung spam" value="{spam_message}"></div>
                        <div class="col-md-3"><label class="form-label">Thời gian lặp (giây):</label><input type="number" name="spam_delay" class="form-control" value="{spam_delay}" min="1" placeholder="10"></div>
                        <div class="col-md-3"><label class="form-label">Điều khiển:</label><div class="btn-group w-100" role="group"><button name="spamtoggle" value="on" type="submit" class="btn btn-success"><i class="fas fa-play me-1"></i>Bật</button><button name="spamtoggle" value="off" type="submit" class="btn btn-danger"><i class="fas fa-stop me-1"></i>Tắt</button></div></div>
                    </div></form>
                </div>
            </div></div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
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
        # Tách riêng logic xử lý form để tránh nhầm lẫn
        form_data = request.form.to_dict()

        if "message" in form_data and form_data["message"]:
            with bots_lock:
                # Gửi tin nhắn từ acc phụ
                for idx, bot in enumerate(bots):
                    try:
                        threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, form_data['message'])).start()
                    except Exception as e:
                        print(f"Lỗi gửi tin nhắn từ acc phụ {idx+1}: {e}")
            msg_status = "Đã gửi tin nhắn thủ công từ các acc phụ!"
        
        elif "quickmsg" in form_data:
            with bots_lock:
                for idx, bot in enumerate(bots):
                    try:
                        threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, form_data['quickmsg'])).start()
                    except Exception as e:
                        print(f"Lỗi gửi lệnh nhanh từ acc phụ {idx+1}: {e}")
            msg_status = f"Đã gửi lệnh nhanh '{form_data['quickmsg']}' từ các acc phụ!"
        
        elif "toggle" in form_data:
            auto_grab_enabled = form_data['toggle'] == "on"
            msg_status = f"Auto Grab Acc 1 đã được {'BẬT' if auto_grab_enabled else 'TẮT'}."
        
        elif "toggle_2" in form_data:
            auto_grab_enabled_2 = form_data['toggle_2'] == "on"
            msg_status = f"Auto Grab Acc 2 đã được {'BẬT' if auto_grab_enabled_2 else 'TẮT'}."

        elif "toggle_3" in form_data:
            auto_grab_enabled_3 = form_data['toggle_3'] == "on"
            msg_status = f"Auto Grab Acc 3 đã được {'BẬT' if auto_grab_enabled_3 else 'TẮT'}."

        elif "heart_threshold" in form_data:
            try:
                heart_threshold = int(form_data['heart_threshold'])
                msg_status = f"Đã cập nhật mức tim Acc 1 thành: {heart_threshold}"
            except ValueError:
                msg_status = "Lỗi: Mức tim Acc 1 không hợp lệ!"

        elif "heart_threshold_2" in form_data:
            try:
                heart_threshold_2 = int(form_data['heart_threshold_2'])
                msg_status = f"Đã cập nhật mức tim Acc 2 thành: {heart_threshold_2}"
            except ValueError:
                msg_status = "Lỗi: Mức tim Acc 2 không hợp lệ!"
        
        elif "heart_threshold_3" in form_data:
            try:
                heart_threshold_3 = int(form_data['heart_threshold_3'])
                msg_status = f"Đã cập nhật mức tim Acc 3 thành: {heart_threshold_3}"
            except ValueError:
                msg_status = "Lỗi: Mức tim Acc 3 không hợp lệ!"
        
        elif "auto_work_toggle" in form_data:
            auto_work_enabled = form_data['auto_work_toggle'] == "on"
            msg_status = f"Auto Work đã được {'BẬT' if auto_work_enabled else 'TẮT'}."

        elif "reboot_target" in form_data:
            target = form_data['reboot_target']
            reboot_bot(target)
            msg_status = f"Đã gửi yêu cầu reboot cho {target}!"

        elif "auto_reboot_toggle" in form_data or "auto_reboot_delay" in form_data:
            if "auto_reboot_delay" in form_data and form_data.get("auto_reboot_delay"):
                try:
                    delay_val = int(form_data["auto_reboot_delay"])
                    if delay_val >= 60:
                        auto_reboot_delay = delay_val
                        msg_status = f"Đã cập nhật delay tự động reboot thành {auto_reboot_delay} giây."
                    else:
                        msg_status = "Lỗi: Delay phải lớn hơn hoặc bằng 60 giây."
                except (ValueError, TypeError):
                    msg_status = "Lỗi: Giá trị delay không hợp lệ."
            
            if "auto_reboot_toggle" in form_data:
                toggle_val = form_data["auto_reboot_toggle"]
                if toggle_val == "on":
                    if not auto_reboot_enabled:
                        auto_reboot_enabled = True
                        auto_reboot_stop_event = threading.Event()
                        auto_reboot_thread = threading.Thread(target=auto_reboot_loop, daemon=True)
                        auto_reboot_thread.start()
                        msg_status = "Đã BẬT chế độ tự động reboot."
                    else:
                        msg_status = "Chế độ tự động reboot đã được bật từ trước."
                elif toggle_val == "off":
                    if auto_reboot_enabled and auto_reboot_stop_event:
                        auto_reboot_enabled = False
                        auto_reboot_stop_event.set()
                        auto_reboot_thread = None
                        msg_status = "Đã TẮT chế độ tự động reboot."
                    else:
                        msg_status = "Chế độ tự động reboot chưa được bật."

        elif "spamtoggle" in form_data:
            spam_enabled = form_data['spamtoggle'] == "on"
            spam_message = form_data.get("spammsg", spam_message).strip()
            if spam_enabled and not spam_message:
                msg_status = "Lỗi: Không thể bật spam với nội dung rỗng."
                spam_enabled = False
            else:
                try:
                    spam_delay_val = int(form_data.get('spam_delay', spam_delay))
                    if spam_delay_val > 0:
                        spam_delay = spam_delay_val
                    else:
                        spam_delay = 10 # default
                except (ValueError, TypeError):
                    pass # Keep old value
                msg_status = f"Spam đã được {'BẬT' if spam_enabled else 'TẮT'}."
        
        elif 'send_codes' in form_data:
            acc_index, delay, prefix, codes = form_data.get("acc_index"), form_data.get("delay"), form_data.get("prefix"), form_data.get("codes")
            if acc_index is not None and delay and codes:
                try:
                    acc_idx = int(acc_index)
                    delay_val = float(delay)
                    codes_list = [c.strip() for c in codes.split(",") if c.strip()]
                    
                    with bots_lock:
                        if 0 <= acc_idx < len(bots):
                            target_bot = bots[acc_idx]
                            for i, code in enumerate(codes_list):
                                final_msg = f"{prefix} {code}" if prefix else code
                                threading.Timer(delay_val * i, target_bot.sendMessage, args=(other_channel_id, final_msg)).start()
                            msg_status = f"Đã bắt đầu gửi {len(codes_list)} mã cho Acc Phụ {acc_idx + 1}!"
                        else:
                            msg_status = "Lỗi: Index của Acc Phụ không hợp lệ."
                except Exception as e:
                    msg_status = f"Lỗi xử lý gửi mã: {e}"
                    print(f"Lỗi xử lý codes: {e}")

    # --- FORMAT HTML RESPONSE ---
    alert_section = f'<div class="row"><div class="col-12"><div class="alert alert-success">{msg_status}</div></div></div>' if msg_status else ""

    reboot_options = ""
    if main_bot: reboot_options += '<option value="main_1">Acc Chính 1</option>'
    if main_bot_2: reboot_options += '<option value="main_2">Acc Chính 2</option>'
    if main_bot_3: reboot_options += '<option value="main_3">Acc Chính 3</option>'
    for i in range(len(bots)):
        name = acc_names[i] if i < len(acc_names) else f"Phụ {i+1}"
        reboot_options += f'<option value="sub_{i}">Acc {name}</option>'
    
    acc_options = "".join(f'<option value="{i}">{acc_names[i] if i < len(acc_names) else f"Phụ {i+1}"}</option>' for i in range(len(bots)))

    return render_template_string(HTML.format(
        alert_section=alert_section,
        auto_grab_status="status-active" if auto_grab_enabled else "status-inactive",
        auto_grab_text="Đang bật" if auto_grab_enabled else "Đang tắt",
        auto_grab_status_2="status-active" if auto_grab_enabled_2 else "status-inactive",
        auto_grab_text_2="Đang bật" if auto_grab_enabled_2 else "Đang tắt",
        auto_grab_status_3="status-active" if auto_grab_enabled_3 else "status-inactive",
        auto_grab_text_3="Đang bật" if auto_grab_enabled_3 else "Đang tắt",
        auto_work_status="status-active" if auto_work_enabled else "status-inactive",
        auto_work_text="Đang bật" if auto_work_enabled else "Đang tắt",
        auto_reboot_status="status-active" if auto_reboot_enabled else "status-inactive",
        auto_reboot_text="Đang bật" if auto_reboot_enabled else "Đang tắt",
        spam_status="status-active" if spam_enabled else "status-inactive",
        spam_text="Đang bật" if spam_enabled else "Đang tắt",
        heart_threshold=heart_threshold,
        heart_threshold_2=heart_threshold_2,
        heart_threshold_3=heart_threshold_3,
        auto_reboot_delay=auto_reboot_delay,
        spam_message=spam_message,
        spam_delay=spam_delay,
        reboot_options=reboot_options,
        acc_options=acc_options
    ))

if __name__ == "__main__":
    print("="*40)
    print(">> KHỞI TẠO HỆ THỐNG BOT KARUTA DEEP <<")
    print("="*40)
    
    with bots_lock:
        print("\n[Init] Đang khởi tạo các bot...")
        if main_token: main_bot = create_bot(main_token, is_main=True)
        if main_token_2: main_bot_2 = create_bot(main_token_2, is_main_2=True)
        if main_token_3: main_bot_3 = create_bot(main_token_3, is_main_3=True)
        
        # Create sub-bots and store them in the list
        temp_bots = []
        for token in tokens:
            if token.strip():
                temp_bots.append(create_bot(token.strip()))
        bots.extend(temp_bots)

    time.sleep(5) # Wait for bots to connect
    print("\n[Init] Tất cả các bot đã được khởi tạo.")

    print("\n[Init] Đang khởi tạo các luồng nền...")
    threading.Thread(target=spam_loop, daemon=True).start()
    threading.Thread(target=auto_work_loop, daemon=True).start()
    threading.Thread(target=health_check_loop, daemon=True).start() # Thêm luồng health check
    print("[Init] Các luồng nền đã sẵn sàng.")

    port = int(os.environ.get("PORT", 8080))
    print(f"\n[Init] Khởi động Web Server tại: http://0.0.0.0:{port}")
    print("\n>> HỆ THỐNG SẴN SÀNG <<\n")
    
    # Use waitress for production instead of Flask's debug server
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)
