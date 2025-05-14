import tkinter as tk
from tkinter import font as tkfont
import threading
import time
from plyer import notification
import pygame
import datetime

ALARM_TITLE = "알람"
ALARM_MESSAGE = "일어날 시간입니다!"
SOUND_PATH = "alarm_sound.mp3"

# 플랩시계 스타일 색상/폰트
BG_COLOR = "#181A1B"
CARD_BG = "#222325"
CARD_FG = "#FFF"
CARD_FG_ALERT = "#FFD600"
CARD_BORDER = "#444"
CARD_SHADOW = "#000"
DIVIDER = "#EEE"
BTN_BG = "#333"
BTN_FG = "#FFF"
STATUS_ON = "#FFD600"
STATUS_OFF = "#888"

class FlapCard(tk.Canvas):
    def __init__(self, master, digit="00", font_size=70, alert=False, **kwargs):
        super().__init__(master, width=120, height=160, bg=BG_COLOR, highlightthickness=0, **kwargs)
        self.font = self._get_font(font_size)
        self.digit = digit
        self.alert = alert
        self.last_digit = None
        self.animating = False
        self.draw_card(digit, alert)

    def _get_font(self, size):
        for fname in ["Orbitron", "Roboto Mono", "맑은 고딕", "Arial Black", "Arial"]:
            try:
                return tkfont.Font(family=fname, size=size, weight="bold")
            except:
                continue
        return ("Arial", size, "bold")

    def draw_card(self, digit, alert=False):
        self.delete("all")
        # 그림자
        self.create_rectangle(8, 8, 112, 152, fill=CARD_SHADOW, outline="", width=0)
        # 카드 배경
        self.create_rectangle(0, 0, 112, 152, fill=CARD_BG, outline=CARD_BORDER, width=3)
        fg = CARD_FG_ALERT if alert else CARD_FG
        # 숫자(중앙에 한 번만)
        self.create_text(56, 76, text=digit, font=self.font, fill=fg)

    def set_digit(self, digit, alert=False):
        if digit != self.digit:
            self.animate_slide_flip(digit, alert)
        else:
            self.draw_card(digit, alert)
        self.digit = digit
        self.alert = alert

    def animate_slide_flip(self, new_digit, alert):
        self.animating = True
        steps = 12
        delay = 15  # ms
        old_digit = self.digit
        def animate(step):
            self.delete("all")
            # 그림자
            self.create_rectangle(8, 8, 112, 152, fill=CARD_SHADOW, outline="", width=0)
            # 카드 배경
            self.create_rectangle(0, 0, 112, 152, fill=CARD_BG, outline=CARD_BORDER, width=3)
            fg = CARD_FG_ALERT if alert else CARD_FG
            # 슬라이드 위치 계산 (아래로)
            offset = int((step / steps) * 152)
            # 기존 숫자 아래로 슬라이드 아웃
            self.create_text(56, 76 + offset, text=old_digit, font=self.font, fill=fg)
            # 새 숫자 위에서 슬라이드 인
            self.create_text(56, 76 - (152 - offset), text=new_digit, font=self.font, fill=fg)
            if step < steps:
                self.after(delay, lambda: animate(step + 1))
            else:
                self.draw_card(new_digit, alert)
                self.animating = False
        animate(0)

class FlapClock(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=BG_COLOR, **kwargs)
        self.min_card = FlapCard(self, "00")
        self.colon = tk.Label(self, text=":", font=("Arial", 80, "bold"), fg=DIVIDER, bg=BG_COLOR)
        self.sec_card = FlapCard(self, "00")
        self.min_card.grid(row=0, column=0, padx=(30, 0), pady=10)
        self.colon.grid(row=0, column=1, padx=(0, 0))
        self.sec_card.grid(row=0, column=2, padx=(0, 30), pady=10)

    def set_time(self, mins, secs, alert=False):
        self.min_card.set_digit(f"{mins:02d}", alert)
        self.sec_card.set_digit(f"{secs:02d}", alert)

class AlarmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("플랩시계 알람")
        self.is_running = False
        self.alarm_thread = None
        self.remaining_time = 30 * 60
        self.update_timer_job = None
        self.is_alert = False
        self.root.configure(bg=BG_COLOR)
        self.root.geometry("500x370")
        self.root.minsize(400, 300)

        # 상태 표시
        self.status_label = tk.Label(root, text="알람 상태: OFF", font=("맑은 고딕", 18, "bold"), bg=BG_COLOR, fg=STATUS_OFF)
        self.status_label.pack(pady=(20, 5))

        # 플랩시계 타이머
        self.flap_clock = FlapClock(root)
        self.flap_clock.pack(pady=5)

        # 다음 알람 시각 표시
        self.next_alarm_label = tk.Label(root, text="", font=("맑은 고딕", 14), bg=BG_COLOR, fg="#BBB")
        self.next_alarm_label.pack(pady=(0, 10))

        # 버튼
        self.toggle_btn = tk.Button(root, text="알람 시작", font=("맑은 고딕", 16, "bold"), width=16, height=2,
                                    bg=BTN_BG, fg=BTN_FG, activebackground=CARD_FG_ALERT, activeforeground=BG_COLOR,
                                    bd=0, relief="flat", command=self.toggle_alarm, cursor="hand2")
        self.toggle_btn.pack(pady=15)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def toggle_alarm(self):
        if not self.is_running:
            self.is_running = True
            self.status_label.config(text="알람 상태: ON", fg=STATUS_ON)
            self.toggle_btn.config(text="알람 정지")
            self.is_alert = False
            self.update_timer()
            self.alarm_thread = threading.Thread(target=self.run_alarm, daemon=True)
            self.alarm_thread.start()
        else:
            self.is_running = False
            self.status_label.config(text="알람 상태: OFF", fg=STATUS_OFF)
            self.toggle_btn.config(text="알람 시작")
            self.flap_clock.set_time(0, 0)
            if self.update_timer_job:
                self.root.after_cancel(self.update_timer_job)

    def update_timer(self):
        if self.is_running:
            now = datetime.datetime.now()
            mins = now.minute
            secs = now.second
            # 다음 알람까지 남은 시간 계산
            if mins < 30:
                next_alarm_min = 30
            else:
                next_alarm_min = 60
            remain_min = next_alarm_min - mins - (1 if secs > 0 else 0)
            remain_sec = 60 - secs if secs > 0 else 0
            if remain_sec == 60:
                remain_sec = 0
            self.flap_clock.set_time(remain_min, remain_sec, alert=self.is_alert)
            # 다음 알람 시각 표시
            next_hour = now.hour
            next_min = next_alarm_min
            if next_min == 60:
                next_min = 0
                next_hour = (next_hour + 1) % 24
            self.next_alarm_label.config(text=f"다음 알람: {next_hour:02d}:{next_min:02d}")
            self.update_timer_job = self.root.after(1000, self.update_timer)

    def run_alarm(self):
        last_alarm_minute = None
        while self.is_running:
            now = datetime.datetime.now()
            # 정각 또는 30분(00, 30)에만 알람
            if (now.minute == 0 or now.minute == 30) and now.second == 0:
                if last_alarm_minute != now.minute:
                    self.root.after(0, lambda: self.flap_clock.set_time(0, 0, alert=True))
                    self.show_alarm_popup_once()
                    start_time = time.time()
                    while time.time() - start_time < 60:
                        if not self.is_running:
                            return
                        self.play_alarm_sound()
                    last_alarm_minute = now.minute
            time.sleep(1)

    def show_alarm_popup_once(self):
        try:
            notification.notify(
                title=ALARM_TITLE,
                message=ALARM_MESSAGE,
                timeout=10
            )
        except Exception as e:
            print(f"팝업 알림 오류: {e}")

    def play_alarm_sound(self):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(SOUND_PATH)
            pygame.mixer.music.play()
            for _ in range(100):
                if not pygame.mixer.music.get_busy():
                    break
                time.sleep(0.1)
            pygame.mixer.music.stop()
        except Exception as e:
            print(f"소리 재생 오류: {e}")

    def on_close(self):
        self.is_running = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AlarmApp(root)
    root.mainloop() 