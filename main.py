import tkinter as tk
from tkinter import messagebox, filedialog
import os
import threading
import pygame
from mutagen.mp3 import MP3
from mutagen.wave import WAVE

# Импорты твоих модулей
from models import Track, Playlist, format_time
from engine import PlaybackManager
from storage import DataStorage


class MusicPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Winamp")
        try:
            # Если файл лежит в той же папке, что и main.py
            self.icon_img = tk.PhotoImage(file='logo.png') 
            self.root.iconphoto(False, self.icon_img)
        except Exception as e:
            print(f"Иконка не найдена: {e}")

        self.storage = DataStorage()
        self.engine = PlaybackManager()
        self.playlists = []
        
        # 1. СНАЧАЛА все переменные состояния
        self.is_dragging = False 
        self.start_time_offset = 0 # ТЕПЕРЬ ОНА ТУТ
        
        # 2. ЗАТЕМ загрузка данных
        self.init_data()
        
        # 3. И ТОЛЬКО ПОТОМ создание GUI и запуск цикла обновления
        self.build_gui()


    def remove_track_action(self):
        selection = self.queue_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if messagebox.askyesno("Удаление", "Удалить трек из очереди?"):
            # 1. Удаляем из движка (из памяти)
            self.engine.remove_track(index) 
            
            # 2. Обновляем наши объекты плейлистов, чтобы storage их увидел
            # Предположим, у тебя один основной плейлист в self.playlists[0]
            if self.playlists:
                self.playlists[0].tracks = self.engine.current_queue.copy()
            
            # 3. Сохраняем ЧЕРЕЗ STORAGE (правильная структура JSON)
            settings = {"last_playlist": "", "volume": int(self.engine.volume_var.get() * 100 if hasattr(self.engine, 'volume_var') else 70)}
            self.storage.save_data(self.playlists, settings)
            
            # 4. Обновляем UI
            self.update_queue_ui()
        

    def seek_track_action(self, value):
        """Метод для перемотки, когда пользователь двигает ползунок"""
        track = self.engine.get_current_track()
        if track:
            pygame.mixer.music.play(start=float(value))

    def add_track_action(self):
        file_path = filedialog.askopenfilename(
            title="Выберите аудиофайл",
            filetypes=(("Audio Files", "*.mp3 *.wav"), ("All Files", "*.*"))
        )
        
        if file_path:
            # Получаем имя файла без полного пути для красоты
            filename = os.path.basename(file_path)
            actual_duration = 0
            
            try:
                # Определяем длительность в зависимости от расширения
                if file_path.lower().endswith('.mp3'):
                    audio = MP3(file_path)
                    actual_duration = int(audio.info.length)
                elif file_path.lower().endswith('.wav'):
                    audio = WAVE(file_path)
                    actual_duration = int(audio.info.length)
            except Exception as e:
                print(f"Ошибка чтения метаданных: {e}")
                actual_duration = 0 # Оставляем 0, если файл поврежден

            # ПЕРЕДАЕМ actual_duration ВМЕСТО 0
            new_track = Track(
                title=filename, 
                artist="Неизвестен", 
                duration=actual_duration, 
                file_path=file_path
            )
            
            if self.playlists:
                self.playlists[0].add_track(new_track)
                self.engine.load_queue(self.playlists[0].tracks)
                self.update_queue_ui()

    def init_data(self):
        # Автозагрузка последнего плейлиста из JSON при старте [cite: 13]
        data = self.storage.load_data()
        
        for pl_data in data.get("playlists", []):
            pl = Playlist(pl_data["name"])
            for t in pl_data["tracks"]:
                pl.add_track(Track(t["title"], t["artist"], t["duration"], t["path"]))
            self.playlists.append(pl)
            
        if not self.playlists:
            # Создаем тестовые данные, если БД пуста
            pl = Playlist("Избранное")
            pl.add_track(Track("Song Name", "Artist", 210, "C:/music/song.mp3"))
            self.playlists.append(pl)
            
        # Загружаем первый плейлист в движок
        self.engine.load_queue(self.playlists[0].tracks)

    def build_gui(self):
        # 1. Цвета и параметры
        BG_COLOR = "#212121"    # Темно-серый
        FG_COLOR = "#FFFFFF"    # Белый текст
        ACCENT_COLOR = "#1DB954" # Зеленый (Spotify)
        BTN_COLOR = "#333333"   # Цвет кнопок

        self.root.configure(bg=BG_COLOR)

        # 2. СНАЧАЛА СОЗДАЕМ ВСЕ ПЕРЕМЕННЫЕ (чтобы не было NameError)
        self.info_var = tk.StringVar(value="Остановлено")
        self.progress_var = tk.DoubleVar(value=0)
        self.volume_var = tk.DoubleVar(value=0.05)
        self.shuffle_var = tk.BooleanVar(value=False)
        self.repeat_var = tk.StringVar(value="None")

        # Параметры для кнопок (чтобы не дублировать код)
        btn_params = {
            "bg": BTN_COLOR, 
            "fg": FG_COLOR, 
            "activebackground": ACCENT_COLOR, 
            "relief": "flat", 
            "font": ("Segoe UI", 10),
            "width": 10
        }

        # 3. ВИДЖЕТЫ: Информационная панель (Название трека)
        tk.Label(
            self.root, 
            textvariable=self.info_var, 
            bg=BG_COLOR, 
            fg=ACCENT_COLOR, 
            font=("Segoe UI", 14, "bold")
        ).pack(pady=15)

        # 4. ВИДЖЕТЫ: Окно очереди (Listbox)
        self.queue_listbox = tk.Listbox(
            self.root, 
            width=50, 
            height=10,
            bg="#181818", 
            fg=FG_COLOR, 
            borderwidth=0, 
            highlightthickness=1,
            highlightcolor=ACCENT_COLOR,
            selectbackground=ACCENT_COLOR,
            font=("Segoe UI", 10)
        )
        self.queue_listbox.pack(pady=5, padx=10)
        self.update_queue_ui()

        # 5. ВИДЖЕТЫ: Блок управления (кнопки ⏮ ▶ ⏸ ⏭)
        control_frame = tk.Frame(self.root, bg=BG_COLOR)
        control_frame.pack(pady=5)

        tk.Button(control_frame, text="⏮ Prev", command=self.prev_action, **btn_params).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="▶ Play", command=self.play_action, **btn_params).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="⏸ Pause", command=self.pause_action, **btn_params).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="⏭ Next", command=self.next_action, **btn_params).pack(side=tk.LEFT, padx=5)

        # 6. ВИДЖЕТЫ: Кнопки работы с файлами
        file_ops_frame = tk.Frame(self.root, bg=BG_COLOR)
        file_ops_frame.pack(pady=5)
        
        tk.Button(file_ops_frame, text="Добавить", command=self.add_track_action, **btn_params).pack(side=tk.LEFT, padx=5)
        # Кнопка удаления с красным текстом
        del_params = btn_params.copy()
        del_params["fg"] = "#FF4444"
        tk.Button(file_ops_frame, text="Удалить", command=self.remove_track_action, **del_params).pack(side=tk.LEFT, padx=5)

        # 7. ВИДЖЕТЫ: Блок режимов (Shuffle/Repeat)
        mode_frame = tk.Frame(self.root, bg=BG_COLOR)
        mode_frame.pack(pady=5)

        tk.Checkbutton(
            mode_frame, text="🔀 Shuffle", variable=self.shuffle_var, 
            command=self.toggle_shuffle, bg=BG_COLOR, fg=FG_COLOR, 
            selectcolor=BTN_COLOR, activebackground=BG_COLOR
        ).pack(side=tk.LEFT, padx=5)

        for text, mode in [("None", "None"), ("All", "Playlist"), ("One", "Track")]:
            tk.Radiobutton(
                mode_frame, text=text, variable=self.repeat_var, value=mode,
                bg=BG_COLOR, fg=FG_COLOR, selectcolor=ACCENT_COLOR, activebackground=BG_COLOR
            ).pack(side=tk.LEFT, padx=2)

        # 8. ВИДЖЕТЫ: Ползунок прогресса
        slider_frame = tk.Frame(self.root, bg=BG_COLOR)
        slider_frame.pack(pady=10, fill=tk.X, padx=20)

        self.time_label = tk.Label(slider_frame, text="00:00 / 00:00", bg=BG_COLOR, fg=FG_COLOR, font=("Consolas", 10))
        self.time_label.pack()

        self.progress_scale = tk.Scale(
            slider_frame, 
            variable=self.progress_var, 
            from_=0, to=100, 
            orient=tk.HORIZONTAL,
            
            # --- ПРАВИЛЬНЫЕ ПАРАМЕТРИ WINAMP ---
            bg=BG_COLOR,              # Фон вокруг
            troughcolor="#111111",    # Глубокая черная дорожка
            activebackground=ACCENT_COLOR, # Цвет при нажатии
            
            width=10,                 # ТОЛЩИНА ДОРОЖКИ (вместо thickness)
            sliderlength=25,          # ДЛИНА БЕГУНКА (кирпичика)
            
            relief="flat",            # Плоские края
            borderwidth=0,            # Без рамок
            highlightthickness=0,     # Без фокуса
            showvalue=False           # Не показывать цифры над ползунком
        )
        self.progress_scale.bind("<ButtonPress-1>", self.on_slider_press)
        self.progress_scale.bind("<B1-Motion>", self.on_slider_motion)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_slider_release)
        self.progress_scale.pack(fill=tk.X)

        # 9. ВИДЖЕТЫ: Громкость
        volume_frame = tk.Frame(self.root, bg=BG_COLOR)
        volume_frame.pack(pady=5)

        tk.Label(volume_frame, text="🔊", bg=BG_COLOR, fg=FG_COLOR).pack(side=tk.LEFT)
        self.volume_scale = tk.Scale(
            volume_frame, from_=0, to=1, resolution=0.05,
            orient=tk.HORIZONTAL, variable=self.volume_var,
            showvalue=False, command=self.change_volume,
            bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0,
            troughcolor=BTN_COLOR, activebackground=ACCENT_COLOR, sliderrelief="flat"
        )
        self.volume_scale.pack(side=tk.LEFT, padx=5)

        # 10. ЗАПУСК ДВИЖКА
        pygame.mixer.music.set_volume(self.volume_var.get())
        self.update_slider()

    def change_volume(self, val):
        """Метод вызывается автоматически при движении слайдера громкости"""
        volume = float(val)
        pygame.mixer.music.set_volume(volume)
        # Если хочешь, можно выводить уровень в консоль для теста:
        # print(f"Громкость: {int(volume * 100)}%")

    def update_slider(self):
        track = self.engine.get_current_track()
        
        # Если трека нет, просто перезапускаем цикл, чтобы не «умер»
        if not track or track.duration <= 0:
            self.root.after(500, self.update_slider)
            return

        # 1. Принудительно синхронизируем макс. значение ползунка с длиной трека
        if float(self.progress_scale['to']) != float(track.duration):
            self.progress_scale.config(to=track.duration)

        # 2. Получаем позицию от pygame
        current_ms = pygame.mixer.music.get_pos()
        
        if current_ms != -1 and not self.is_dragging:
            # Считаем текущую секунду (смещение + прогресс)
            current_sec = self.start_time_offset + (current_ms / 1000)
            
            # 3. Обновляем ползунок и таймер
            self.progress_var.set(current_sec)
            self.time_label.config(text=f"{format_time(current_sec)} / {format_time(track.duration)}")

            # 4. Проверка автовоспроизведения (чуть раньше конца трека)
            if track.duration - current_sec < 1.0:
                self.next_action()
                return # Выходим, так как next_action сам вызовет update_slider через play_track

        # 5. Перезапуск цикла ВСЕГДА
        self.root.after(500, self.update_slider)


    def update_queue_ui(self):
        self.queue_listbox.delete(0, tk.END)
        for track in self.engine.current_queue:
            # Вытаскиваем данные. Если поля нет — пишем "???"
            artist = getattr(track, 'artist', 'Unknown')
            title = getattr(track, 'title', 'Unknown')
            
            # Если и артист, и название есть — клеим через тире
            # Если нет (например, это просто путь), оставляем имя файла
            if artist != 'Unknown' or title != 'Unknown':
                display_text = f"{artist} — {title}"
            else:
                # Если метаданных нет, берем просто имя файла
                import os
                path = getattr(track, 'path', str(track))
                display_text = os.path.basename(path)

            self.queue_listbox.insert(tk.END, display_text)

    def update_info_ui(self, status="Играет"):
        # Переключение (в виде текстовых уведомлений/статусов) 
        track = self.engine.get_current_track()
        if track:
            self.info_var.set(f"{status}: {track.artist} - {track.title}")
        else:
            self.info_var.set("Остановлено. Конец очереди.")

    def play_action(self):
        track = self.engine.get_current_track()
        if track:
            # Если песня уже играла и была на паузе — просто продолжаем
            if self.engine.is_paused:
                self.engine.pause_track() # Снимет с паузы
            else:
                # Если это запуск с нуля или после Стопа
                self.reset_playback_ui()
                self.engine.play_track()
            self.update_info_ui("Играет")

    def pause_action(self):
        if self.engine.get_current_track():
            self.engine.pause_track() # Поставит на паузу или снимет с неё
            status = "Пауза" if self.engine.is_paused else "Играет"
            self.update_info_ui(status)

    def next_action(self, fade_ms=0):
        if fade_ms > 0:
            pygame.mixer.music.fadeout(fade_ms)
            # Передаем fade_ms=0 в следующем вызове, чтобы выполнить саму логику смены
            self.root.after(fade_ms, lambda: self.next_action(fade_ms=0))
            return

        # 1. Сначала сбрасываем визуальный ползунок в 0, 
        # чтобы update_slider перестал видеть "конец трека"
        self.progress_var.set(0)
        self.start_time_offset = 0

        repeat_mode = self.repeat_var.get()

        if repeat_mode == "Track":
            # Повтор текущего: индекс не меняем
            track = self.engine.get_current_track()
        else:
            # Обычный переход или повтор плейлиста
            pygame.mixer.music.stop()
            track = self.engine.next_track()

        if track:
            # Обновляем масштаб (на случай если трек всё же сменился)
            self.progress_scale.config(to=track.duration)
            self.engine.play_track()
            self.update_info_ui("Играет")
        else:
            self.info_var.set("Конец плейлиста")
            

    def prev_action(self):
        self.reset_playback_ui() # Сначала чистим
        track = self.engine.prev_track()
        if track:
            self.engine.play_track()
            self.progress_scale.config(to=track.duration)
            self.update_info_ui("Играет")

    def toggle_shuffle(self):
        # 1. Спрашиваем у движка: перемешать или вернуть как было?
        if self.shuffle_var.get():
            self.engine.shuffle_queue()
        else:
            # Возвращаем дефолтный порядок из первого плейлиста
            if self.playlists:
                self.engine.load_queue(self.playlists[0].tracks)
        
        # 2. СБРОС: Чтобы старое время не приклеилось к новому треку
        self.start_time_offset = 0
        pygame.mixer.music.stop() # Останови старый поток, чтобы не было каши
        
        # 3. ОБНОВЛЕНИЕ: Синхронизируем GUI со списком движка
        self.update_queue_ui()
        self.update_info_ui("Список перемешан")

    def toggle_repeat(self):
        self.engine.set_repeat(self.repeat_var.get())
    
    def on_slider_press(self, event):
        self.is_dragging = True

    def on_slider_motion(self, event):
        track = self.engine.get_current_track()
        if track:
            current_val = self.progress_scale.get()
            current_str = format_time(current_val)
            total_str = format_time(track.duration)
            self.time_label.config(text=f"{current_str} / {total_str}")

    def on_slider_release(self, event):
        new_pos = self.progress_scale.get()
        self.start_time_offset = new_pos # Запоминаем, куда перемотали
        pygame.mixer.music.play(start=float(new_pos))
        self.is_dragging = False

    def reset_playback_ui(self):
        """Полный сброс всех переменных времени перед новым треком"""
        self.start_time_offset = 0
        self.progress_var.set(0)
        # Сбрасываем текст, чтобы старое время не висело ни секунды
        self.time_label.config(text="00:00 / 00:00")

    def smooth_next(self, fade_ms=1500):
        """Плавно гасит звук и переключает на следующий трек"""
        # 1. Запускаем затухание звука в pygame
        pygame.mixer.music.fadeout(fade_ms)
        
        # 2. Ждем окончания затухания, прежде чем физически сменить трек
        # Используем after, чтобы не вешать интерфейс
        self.root.after(fade_ms, self.next_action)

    def update_slider(self):
        track = self.engine.get_current_track()
        
        # Если трек есть, ПЕРВЫМ ДЕЛОМ проверяем масштаб
        if track and track.duration > 0:
            if float(self.progress_scale['to']) != float(track.duration):
                self.progress_scale.config(to=track.duration)

            # Если музыка реально звучит
            if pygame.mixer.music.get_busy() and not self.is_dragging:
                current_ms = pygame.mixer.music.get_pos()
                
                if current_ms != -1:
                    current_sec = self.start_time_offset + (current_ms / 1000)
                    current_sec = min(current_sec, track.duration)
                    
                    # Обновляем цифры и ползунок
                    self.progress_var.set(current_sec)
                    self.time_label.config(text=f"{format_time(current_sec)} / {format_time(track.duration)}")

                    # ПЛАВНОЕ АВТОПЕРЕКЛЮЧЕНИЕ
                    # Если осталось 2 секунды — начинаем гасить звук
                    if track.duration - current_sec < 2.0:
                        self.next_action(fade_ms=1500)
                        self.root.after(2000, self.update_slider)
                        return

        # Цикл не должен прерываться
        self.root.after(500, self.update_slider)
if __name__ == "__main__":
    root = tk.Tk()
    app = MusicPlayerApp(root)
    
    # Сохранение при закрытии приложения
    def on_closing():
        app.storage.save_data(app.playlists, {"last_playlist": "Избранное", "volume": 70})
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()