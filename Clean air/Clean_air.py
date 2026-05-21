import tkinter as tk
import customtkinter as ctk
import threading

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AirQualityEngine:
    def __init__(self, log_callback=None):
        self.BASE_CO2 = 400
        self.ROOM_FACTORS = {
            "Маленькая (10-15 м²)": 1.8,
            "Средняя (20-30 м²)": 1.0,
            "Большая (40+ м²)": 0.6
        }
        self.log = log_callback

    def _log(self, msg):
        if self.log:
            self.log(msg)
        else:
            print(msg)

    def estimate_indoor(self, people, minutes, devices, room_size, window_state):
        try:
            if window_state == "Открыто":
                return int(400)

            room_multiplier = self.ROOM_FACTORS.get(room_size, 1.0)
            window_multiplier = 0.2 if window_state == "Микро" else 1.0
            co2_increase = (people * minutes * 0.35) * room_multiplier * window_multiplier
            device_impact = (devices * minutes * 0.05) * window_multiplier
            return int(460 + co2_increase + device_impact)
        except (ValueError, TypeError):
            return 450


    def generate_advice_for_ventilation(self, window_state, room_size):
        advice_parts = []

        if window_state == "Открыто":
            advice_parts.append("Окно открыто — идёт активный воздухообмен")
        elif window_state == "Микро":
            advice_parts.append("Микропроветривание — ограниченный воздухообмен")
        else:
            advice_parts.append("Окно закрыто — требуется проветривание")

        if "Маленькая" in room_size:
            advice_parts.append("В маленьком помещении CO₂ накапливается быстрее")
        elif "Большая" in room_size:
            advice_parts.append("В большом помещении воздухообмен происходит медленнее")

        return " | ".join(advice_parts)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Чистый Воздух")
        self.geometry("550x800")

        def ui_log(msg):
            print(msg)

        self.engine = AirQualityEngine(log_callback=ui_log)
        self._setup_ui()

    def _setup_ui(self):
        ctk.CTkLabel(self, text="АНАЛИЗ ВОЗДУХА: ПРОВЕТРИВАНИЕ", font=("Roboto", 24, "bold")).pack(pady=20)

        ctk.CTkLabel(self, text="Текущий режим окна:", font=("Roboto", 12, "bold")).pack(pady=(15, 5))
        self.window_var = ctk.StringVar(value="Закрыто")
        self.window_picker = ctk.CTkSegmentedButton(
            self,
            values=["Закрыто", "Микро", "Открыто"],
            variable=self.window_var,
            command=self.update_ui_state
        )
        self.window_picker.pack(padx=20, fill="x")

        ctk.CTkLabel(self, text="Тип помещения:", font=("Roboto", 12, "bold")).pack(pady=(15, 5))
        self.room_var = ctk.StringVar(value="Средняя (20-30 м²)")
        self.room_picker = ctk.CTkSegmentedButton(
            self,
            values=list(self.engine.ROOM_FACTORS.keys()),
            variable=self.room_var
        )
        self.room_picker.pack(padx=20, fill="x")

        self.create_slider_group("Людей в помещении:", 0, 30, 2, "чел.", "people")
        self.create_slider_group("Окна закрыты уже:", 0, 1200, 60, "мин.", "time")
        self.create_slider_group("Техника в работе:", 0, 20, 3, "шт.", "devices")

        self.btn_calc = ctk.CTkButton(
            self,
            text="ПРОВЕРИТЬ СОСТОЯНИЕ",
            font=("Roboto", 16, "bold"),
            height=50,
            command=self.start_process_thread
        )
        self.btn_calc.pack(pady=30, padx=50, fill="x")

        self.res_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=15)
        self.res_frame.pack(fill="x", padx=30, pady=10)

        self.indoor_label = ctk.CTkLabel(
            self.res_frame,
            text="-- PPM",
            font=("Roboto", 32, "bold")
        )
        self.indoor_label.pack(pady=(15, 5))

        self.status_textbox = ctk.CTkTextbox(
            self.res_frame,
            height=90,
            wrap="word",
            state="disabled",
            font=("Roboto", 14),
            fg_color="#333333",
            text_color="white",
            border_width=2,
            border_color="#444444"
        )
        self.status_textbox.pack(fill="x", padx=10, pady=(0, 15))

        self.status_textbox.configure(state="normal")
        self.status_textbox.delete("1.0", "end")
        self.status_textbox.insert("1.0", "Настройте параметры и нажмите ПРОВЕРИТЬ СОСТОЯНИЕ")
        self.status_textbox.configure(state="disabled")


    def create_slider_group(self, label_text, from_val, to_val, start_val, unit, attr_name):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=40, pady=(15, 0))
        lbl = ctk.CTkLabel(frame, text=label_text)
        lbl.pack(side="left")
        val_lbl = ctk.CTkLabel(frame, text=f"{start_val} {unit}", text_color="#3B8ED0", font=("Roboto", 12, "bold"))
        val_lbl.pack(side="right")

        slider = ctk.CTkSlider(
            self,
            from_=from_val,
            to=to_val,
            command=lambda v, l=val_lbl, u=unit: l.configure(text=f"{int(v)} {u}")
        )
        slider.set(start_val)
        slider.pack(fill="x", padx=40, pady=(0, 10))

        setattr(self, f"{attr_name}_slider", slider)
        setattr(self, f"{attr_name}_label", val_lbl)
        setattr(self, f"{attr_name}_title", lbl)

    def update_ui_state(self, choice):
        if choice == "Открыто":
            self.time_slider.configure(state="disabled", button_color="#555")
            self.time_label.configure(text_color="#555")
            self.time_title.configure(text="Время не учитывается (окно открыто)")
        else:
            self.time_slider.configure(state="normal", button_color="#3B8ED0")
            self.time_label.configure(text_color="#3B8ED0")
            self.time_title.configure(text="Окна закрыты уже:")

    def start_process_thread(self):
        self.btn_calc.configure(state="disabled", text="РАСЧЁТ...")

        params = {
            "people": int(self.people_slider.get()),
            "time": int(self.time_slider.get()),
            "devices": int(self.devices_slider.get()),
            "room_size": self.room_var.get(),
            "window_state": self.window_var.get()
        }

        threading.Thread(target=self.async_process, args=(params,), daemon=True).start()

    def async_process(self, params):
        score = self.engine.estimate_indoor(
            params["people"], params["time"], params["devices"],
            params["room_size"], params["window_state"]
        )
        advice = self.engine.generate_advice_for_ventilation(
            params["window_state"], params["room_size"]
        )
        self.after(0, self.update_ui_results, score, advice, params)

    def update_ui_results(self, score, advice, params):
        color = "#2EB872" if score < 800 else "#FFB347" if score < 1200 else "#FF4B4B"
        status = "Идеально" if score < 800 else "Нужно проветрить" if score < 1200 else "Опасно для здоровья"

        self.indoor_label.configure(text=f"{score} PPM", text_color=color)

        advice_parts = []

        window_state = params["window_state"]
        time_closed = params["time"]
        people = params["people"]

        if score < 800:
            if window_state == "Открыто":
                advice_parts.append("Проветривание достаточно. Можно закрыть окно через 5–10 мин.")
            elif window_state == "Микро":
                advice_parts.append("Микропроветривание достаточно для поддержания качества воздуха")
            else:
                if time_closed < 60:
                    advice_parts.append("Качество воздуха хорошее. Проветривайте каждые 1–2 часа")
                else:
                    advice_parts.append("Рекомендуется открыть окно на 10–15 мин для профилактики")

        elif score < 1200:
            if window_state == "Закрыто":
                advice_parts.append(f"Срочно откройте окно! CO₂ повышен из‑за {time_closed} мин без проветривания")
                advice_parts.append(f"При {people} чел. в помещении проветривайте каждые 40–60 мин по 15–20 мин")
            elif window_state == "Микро":
                advice_parts.append("Усильте проветривание — откройте окно полностью на 15–20 мин")
            else:
                advice_parts.append("Продолжайте проветривать ещё 10–15 мин, затем можно прикрыть")
        else:
            advice_parts.append("КРИТИЧЕСКИЙ УРОВЕНЬ CO₂! Немедленно откройте все окна!")
            if people > 0:
                advice_parts.append(f"С {people} чел. в помещении требуется интенсивное проветривание 20–30 мин")
            advice_parts.append("После проветривания установите режим микропроветривания")
            advice_parts.append("Рассмотрите установку приточной вентиляции")

        if window_state == "Закрыто" and time_closed >= 120:
            advice_parts.append("Окно закрыто более 2 часов — обязательное проветривание 15+ мин!")
        elif window_state == "Закрыто" and time_closed >= 60:
            advice_parts.append("Рекомендуется проветрить помещение 10–15 мин")

        final_advice = " | ".join(advice_parts)

        self.status_textbox.configure(state="normal")
        self.status_textbox.delete("1.0", "end")
        self.status_textbox.insert("1.0", f"{status} | Совет: {final_advice}")
        self.status_textbox.configure(state="disabled")

        self.btn_calc.configure(state="normal", text="ПРОВЕРИТЬ СОСТОЯНИЕ")

if __name__ == "__main__":
    app = App()
    app.mainloop()
