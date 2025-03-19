import ctypes, sys, os
import winreg
import subprocess
import webbrowser, time, shutil

from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QTimer, pyqtProperty
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QComboBox, QLabel, QSpacerItem,QSizePolicy,QHBoxLayout,QMessageBox
from qt_material import apply_stylesheet
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import QFrame

from downloader import download_files, DOWNLOAD_URLS
from config import DPI_COMMANDS, APP_VERSION, BIN_FOLDER, LISTS_FOLDER
from hosts import HostsManager
from service import ServiceManager
from start import DPIStarter
from urls import *

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

WINWS_EXE = os.path.join(BIN_FOLDER, "winws.exe")
ICON_PATH = os.path.join(BIN_FOLDER, "zapret.ico")  # Путь к иконке в папке bin

BUTTON_STYLE = """
QPushButton {{
    border: none;
    background-color: rgb({0});
    color: #fff;
    border-radius: 4px;
    padding: 8px;
}}
QPushButton:hover {{
    background-color: rgb({0});
}}
"""
COMMON_STYLE = "color:rgb(0, 119, 255); font-weight: bold;"
BUTTON_HEIGHT = 10
STYLE_SHEET = """
    @keyframes ripple {
        0% {
            transform: scale(0, 0);
            opacity: 0.5;
        }
        100% {
            transform: scale(40, 40);
            opacity: 0;
        }
    }
"""

THEMES = {
    "Темная синяя": {"file": "dark_blue.xml", "status_color": "#ffffff"},
    "Темная бирюзовая": {"file": "dark_cyan.xml", "status_color": "#ffffff"},
    "Темная янтарная": {"file": "dark_amber.xml", "status_color": "#ffffff"},
    "Темная розовая": {"file": "dark_pink.xml", "status_color": "#ffffff"},
    "Светлая синяя": {"file": "light_blue.xml", "status_color": "#000000"},
    "Светлая бирюзовая": {"file": "light_cyan.xml", "status_color": "#000000"},
    "РКН Тян": {"file": "dark_blue.xml", "status_color": "#ffffff"},  # Временно используем dark_blue как основу
}

class RippleButton(QPushButton):
    def __init__(self, text, parent=None, color=""):
        super().__init__(text, parent)
        self._ripple_pos = QPoint()
        self._ripple_radius = 0
        self._ripple_opacity = 0
        self._bgcolor = color

        # Настройка анимаций
        self._ripple_animation = QPropertyAnimation(self, b"rippleRadius", self)
        self._ripple_animation.setDuration(300)
        self._ripple_animation.setStartValue(0)
        self._ripple_animation.setEndValue(100)
        self._ripple_animation.setEasingCurve(QEasingCurve.OutQuad)

        self._fade_animation = QPropertyAnimation(self, b"rippleOpacity", self)
        self._fade_animation.setDuration(300)
        self._fade_animation.setStartValue(0.5)
        self._fade_animation.setEndValue(0)

    @pyqtProperty(float)
    def rippleRadius(self):
        return self._ripple_radius

    @rippleRadius.setter
    def rippleRadius(self, value):
        self._ripple_radius = value
        self.update()

    @pyqtProperty(float)
    def rippleOpacity(self):
        return self._ripple_opacity

    @rippleOpacity.setter
    def rippleOpacity(self, value):
        self._ripple_opacity = value
        self.update()

    def mousePressEvent(self, event):
        self._ripple_pos = event.pos()
        self._ripple_opacity = 0.5
        self._ripple_animation.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._fade_animation.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._ripple_radius > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setOpacity(self._ripple_opacity)
            
            painter.setBrush(QColor(255, 255, 255, 60))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self._ripple_pos, self._ripple_radius, self._ripple_radius)

def get_windows_theme():
    """Определяет текущую тему Windows (светлая/темная)"""
    try:
        registry = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(registry, "AppsUseLightTheme")
        winreg.CloseKey(registry)
        return "light" if value == 1 else "dark"
    except:
        return "dark"  # По умолчанию темная тема
    
def get_version(self):
    """Возвращает текущую версию программы"""
    return APP_VERSION

class LupiDPIApp(QWidget):
    def check_for_updates(self):
        """Проверяет наличие обновлений и запускает процесс обновления через BAT-файл"""
        try:
            # Проверяем наличие модуля requests
            try:
                import requests
                from packaging import version
            except ImportError:
                self.set_status("Установка зависимостей для проверки обновлений...")
                subprocess.run([sys.executable, "-m", "pip", "install", "requests packaging"], 
                            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                import requests
                from packaging import version
                
            # URL для проверки обновлений
            version_url = VERSION_URL
            
            self.set_status("Проверка наличия обновлений...")
            response = requests.get(version_url, timeout=5)
            if response.status_code == 200:
                info = response.json()
                latest_version = info.get("version")
                release_notes = info.get("release_notes", "Нет информации об изменениях")
                
                # URL для скачивания BAT-файла обновления
                bat_url = info.get("updater_bat_url", UPDATER_BAT_URL)
                
                # Сравниваем версии
                if version.parse(latest_version) > version.parse(APP_VERSION):
                    # Нашли обновление
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Information)
                    msg.setWindowTitle("Доступно обновление")
                    msg.setText(f"Доступна новая версия: {latest_version}\nТекущая версия: {APP_VERSION}")
                    
                    # Добавляем информацию о выпуске
                    msg.setInformativeText(f"Список изменений:\n{release_notes}\n\nХотите обновиться сейчас?")
                    
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    if msg.exec_() == QMessageBox.Yes:
                        # Запускаем процесс обновления
                        self.set_status("Запуск обновления...")
                        
                        # Получаем путь к текущему исполняемому файлу
                        exe_path = os.path.abspath(sys.executable)
                        
                        # Если это не скомпилированное приложение, updater не сможет заменить .py файл
                        if not getattr(sys, 'frozen', False):
                            QMessageBox.warning(self, "Обновление невозможно", 
                                            "Автоматическое обновление возможно только для скомпилированных (.exe) версий программы.")
                            return
                        
                        # Скачиваем BAT-файл обновления
                        try:
                            # Создаем временный файл для скрипта обновления
                            updater_bat = os.path.join(os.path.dirname(exe_path), "update_zapret.bat")
                            
                            # Скачиваем BAT-файл
                            self.set_status("Скачивание скрипта обновления...")
                            bat_response = requests.get(bat_url)
                            bat_content = bat_response.text

                            # Заменяем переменные в BAT-файле
                            bat_content = bat_content.replace("{EXE_PATH}", exe_path)
                            bat_content = bat_content.replace("{EXE_DIR}", os.path.dirname(exe_path))
                            bat_content = bat_content.replace("{EXE_NAME}", os.path.basename(exe_path))
                            bat_content = bat_content.replace("{CURRENT_VERSION}", APP_VERSION)
                            bat_content = bat_content.replace("{NEW_VERSION}", latest_version)

                            # Сохраняем BAT-файл
                            with open(updater_bat, 'w', encoding='utf-8') as f:
                                f.write(bat_content)
                            
                            # Запускаем BAT-файл
                            self.set_status("Запуск скрипта обновления...")
                            # Изменим способ запуска BAT-файла, чтобы показать консоль
                            subprocess.Popen(f'cmd /c start cmd /k "{updater_bat}"', shell=True)
                            
                            # Завершаем текущий процесс после небольшой задержки
                            self.set_status("Запущен процесс обновления. Приложение будет перезапущено.")
                            QTimer.singleShot(2000, lambda: sys.exit(0))
                            
                        except Exception as e:
                            self.set_status(f"Ошибка при подготовке обновления: {str(e)}")
                            # Если произошла ошибка при скачивании BAT-файла, создаем его локально
                            try:
                                # Создаем BAT-файл вручную
                                updater_bat = os.path.join(os.path.dirname(exe_path), "update_zapret.bat")
                                with open(updater_bat, 'w', encoding='utf-8') as f:
                                    f.write(f"""@echo off
                                    chcp 65001 > nul
                                    echo UPDATE ZAPRET!
                                    title Old v{APP_VERSION} to new v{latest_version}

                                    echo Wait...
                                    timeout /t 3 /nobreak > nul
                                    del /f /q "{exe_path}" >nul 2>&1
                                    echo  Download new version...
                                    powershell -Command "(New-Object System.Net.WebClient).DownloadFile('{EXE_UPDATE_URL}', '%TEMP%\\zapret_new.exe')"

                                    if %ERRORLEVEL% NEQ 0 (
                                        echo Error download update!
                                        pause
                                        exit /b 1
                                    )

                                    echo Replace old to new version
                                    copy /Y "%TEMP%\\zapret_new.exe" "{exe_path}"

                                    if %ERRORLEVEL% NEQ 0 (
                                        echo "Не удалось заменить файл. Проверьте права доступа."
                                        pause
                                        exit /b 1
                                    )

                                    set CURRENT_DIR=%CD%
                                    cd /d "{os.path.dirname(exe_path)}"
                                    cd /d %CURRENT_DIR%
                                    echo Del temp file...
                                    del "%TEMP%\\zapret_new.exe" >nul 2>&1
                                    echo Update done success!
                                    echo Please run Zapret (main.exe) again!
                                    del "%~f0" >nul 2>&1
                                    """)
                                                                
                                # Запускаем BAT-файл
                                subprocess.Popen(f'cmd /c start cmd /k "{updater_bat}"', shell=True)
                                
                                # Завершаем текущий процесс после небольшой задержки
                                self.set_status("Запущен процесс обновления. Приложение будет перезапущено.")
                                QTimer.singleShot(2000, lambda: sys.exit(0))
                            except Exception as inner_e:
                                self.set_status(f"Критическая ошибка обновления: {str(inner_e)}")
                    else:
                        self.set_status("У вас установлена последняя версия.")
                else:
                    self.set_status("У вас установлена последняя версия.")
            else:
                self.set_status(f"Не удалось проверить обновления. Код: {response.status_code}")
        except Exception as e:
            self.set_status(f"Ошибка при проверке обновлений: {str(e)}")
    
    def download_files_wrapper(self):
        """Обертка для скачивания файлов, использующая внешнюю функцию"""
        return self.dpi_starter.download_files(DOWNLOAD_URLS)

    def __init__(self):
        """Initializes the application window."""
        super().__init__()
        self.setWindowTitle(f'Zapret v{APP_VERSION}')  # Добавляем версию в заголовок

        # Устанавливаем иконку приложения
        icon_path = os.path.abspath(ICON_PATH)  # Используем абсолютный путь
        print(f"Путь к иконке: {icon_path}, существует: {os.path.exists(icon_path)}")  # Отладка
            
        if os.path.exists(icon_path):
            from PyQt5.QtGui import QIcon
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            QApplication.instance().setWindowIcon(app_icon)
            
            # Для панели задач в Windows
            try:
                from PyQt5.QtWinExtras import QtWin
                myappid = f'zapret.gui.app.{APP_VERSION}'  # Уникальный ID для Windows
                QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
            except ImportError:
                pass  # QtWinExtras может быть недоступен
        else:
            print(f"ОШИБКА: Файл иконки {icon_path} не найден")
        # Определяем системную тему
        windows_theme = get_windows_theme()
        default_theme = "Светлая синяя" if windows_theme == "light" else "Темная синяя"

        self.init_ui()
        self.hosts_manager = HostsManager(status_callback=self.set_status)

        self.service_manager = ServiceManager(
            winws_exe=WINWS_EXE,
            bin_folder=BIN_FOLDER,
            lists_folder=LISTS_FOLDER,
            status_callback=self.set_status
        )

        self.dpi_starter = DPIStarter(
            winws_exe=WINWS_EXE,
            bin_folder=BIN_FOLDER,
            lists_folder=LISTS_FOLDER,
            status_callback=self.set_status
        )

        # Проверяем наличие службы и обновляем видимость кнопок автозапуска
        service_running = self.service_manager.check_service_exists()
        self.update_autostart_ui(service_running)
        
        # После обновления видимости кнопок автозапуска обновляем состояние запуска
        self.update_ui(running=True)

        # Настраиваем тему
        self.theme_combo.setCurrentText(default_theme)
        theme_info = THEMES[default_theme]
        apply_stylesheet(QApplication.instance(), theme=theme_info["file"])
        self.status_label.setStyleSheet(f"color: {theme_info['status_color']};")
        
        # Устанавливаем цвет ссылки автора
        status_color = theme_info['status_color']
        self.author_label.setStyleSheet(f"""
            color: {status_color}; 
            opacity: 0.6; 
            font-size: 9pt;
        """)
        self.author_label.setText(f'Автор: <a href="{AUTHOR_URL}" style="color:{status_color}">t.me/bypassblock</a>')
        
        
        # Проверяем наличие необходимых файлов
        self.set_status("Проверка файлов...")
        if not os.path.exists(WINWS_EXE):
            self.download_files_wrapper()

        # Обновляем состояние кнопок автозапуска
        service_running = self.service_manager.check_service_exists()
        self.update_ui(service_running)
        
        # Запускаем первую стратегию
        first_strategy = list(DPI_COMMANDS.keys())[0]
        self.start_mode_combo.setCurrentText(first_strategy)
        self.start_dpi()

        QTimer.singleShot(3000, self.check_for_updates)  # Проверяем через 3 секунды после запуска
    
    def init_ui(self):
        """Creates the user interface elements."""
        self.setStyleSheet(STYLE_SHEET)
        layout = QVBoxLayout()

        header_layout = QVBoxLayout()

        title_label = QLabel('Zapret GUI')
        title_label.setStyleSheet(f"{COMMON_STYLE} font: 16pt Arial;")
        header_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        layout.addLayout(header_layout)

        # Добавляем разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Статусная строка
        status_layout = QVBoxLayout()
        
        # Статус запуска программы
        process_status_layout = QHBoxLayout()
        process_status_label = QLabel("Статус программы:")
        process_status_label.setStyleSheet("font-weight: bold;")
        process_status_layout.addWidget(process_status_label)
        
        self.process_status_value = QLabel("проверка...")
        process_status_layout.addWidget(self.process_status_value)
        process_status_layout.addStretch(1)  # Добавляем растяжку для центрирования
        
        status_layout.addLayout(process_status_layout)

        layout.addLayout(status_layout)
        
        # Остальные элементы интерфейса
        self.start_mode_combo = QComboBox(self)
        self.start_mode_combo.setStyleSheet(f"{COMMON_STYLE} text-align: center;")
        self.start_mode_combo.addItems(DPI_COMMANDS.keys())
        self.start_mode_combo.currentTextChanged.connect(self.start_dpi)  # Добавляем обработчик
        layout.addWidget(self.start_mode_combo)

        # --- Создаем сетку для размещения кнопок в два столбца ---
        from PyQt5.QtWidgets import QGridLayout
        button_grid = QGridLayout()

        # Создаем кнопку Запустить
        self.start_btn = RippleButton('Запустить Zapret', self, "54, 153, 70")
        self.start_btn.setStyleSheet(BUTTON_STYLE.format("54, 153, 70"))
        self.start_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.start_btn.clicked.connect(self.start_dpi)

        # Создаем кнопку Остановить
        self.stop_btn = RippleButton('Остановить Zapret', self, "255, 93, 174")
        self.stop_btn.setStyleSheet(BUTTON_STYLE.format("255, 93, 174"))
        self.stop_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.stop_btn.clicked.connect(self.stop_dpi)

        # Создаем кнопки автозапуска
        self.autostart_enable_btn = RippleButton('Вкл. автозапуск', self, "54, 153, 70")
        self.autostart_enable_btn.setStyleSheet(BUTTON_STYLE.format("54, 153, 70"))
        self.autostart_enable_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.autostart_enable_btn.clicked.connect(self.install_service)

        self.autostart_disable_btn = RippleButton('Выкл. автозапуск', self, "255, 93, 174") 
        self.autostart_disable_btn.setStyleSheet(BUTTON_STYLE.format("255, 93, 174"))
        self.autostart_disable_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.autostart_disable_btn.clicked.connect(self.remove_service)

        # Добавляем все кнопки напрямую в сетку вместо использования контейнеров
        button_grid = QGridLayout()

        # Устанавливаем равномерное распределение пространства между колонками
        button_grid.setColumnStretch(0, 1)  # Левая колонка растягивается с коэффициентом 1
        button_grid.setColumnStretch(1, 1)  # Правая колонка растягивается с коэффициентом 1

        # Добавляем кнопки напрямую в grid layout
        button_grid.addWidget(self.start_btn, 0, 0)
        button_grid.addWidget(self.autostart_enable_btn, 0, 1)
        button_grid.addWidget(self.stop_btn, 0, 0)
        button_grid.addWidget(self.autostart_disable_btn, 0, 1)

        # По умолчанию устанавливаем правильную видимость кнопок
        self.start_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.autostart_enable_btn.setVisible(True)
        self.autostart_disable_btn.setVisible(False)
        
        # Определяем кнопки
        button_configs = [            
            ('Открыть папку Zapret', self.open_folder, "0, 119, 255", 2, 0),
            ('Тест соединения', self.open_connection_test, "0, 119, 255", 2, 1),
            ('Обновить список сайтов', self.update_other_list, "0, 119, 255", 3, 0),
            ('Добавить свои сайты', self.open_general, "0, 119, 255", 3, 1),
            ('Разблокировать ChatGPT, Spotify, Notion и др.', self.some_method_that_calls_add_proxy_domains, "218, 165, 32", 4, 0, 2),  # col_span=2
            ('Что это такое?', self.open_info, "38, 38, 38", 5, 0, 2),
            ('Проверить обновления', self.check_for_updates, "38, 38, 38", 6, 0, 2)  # col_span=2
        ]

        # Создаем и размещаем кнопки в сетке
        for button_info in button_configs:
            text, callback, color, row, col = button_info[:5]
            
            # Определяем col_span (либо из кортежа, либо по умолчанию)
            col_span = button_info[5] if len(button_info) > 5 else (2 if (row == 4 or row == 5 or row == 6) else 1)
            
            btn = RippleButton(text, self, color)
            btn.setStyleSheet(BUTTON_STYLE.format(color))
            btn.setMinimumHeight(BUTTON_HEIGHT)
            btn.clicked.connect(callback)
            
            button_grid.addWidget(btn, row, col, 1, col_span)
            
            # Сохраняем ссылку на кнопку запуска
            if text == 'Запустить Zapret':
                self.start_btn = btn
        
        # Добавляем сетку с кнопками в основной лейаут
        layout.addLayout(button_grid)

        theme_layout = QVBoxLayout()
        theme_label = QLabel('Тема оформления:')
        theme_label.setStyleSheet(COMMON_STYLE)
        theme_layout.addWidget(theme_label, alignment=Qt.AlignCenter)
    
        self.theme_combo = QComboBox(self)
        self.theme_combo.setStyleSheet(f"{COMMON_STYLE} text-align: center;")
        self.theme_combo.addItems(THEMES.keys())
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        # Предупреждение
        #self.warning_label = QLabel('Не закрывайте открывшийся терминал!')  # Доступ нужен
        #self.warning_label.setStyleSheet("color:rgb(255, 93, 174);")
        #layout.addWidget(self.warning_label, alignment=Qt.AlignCenter)

        # Статусная строка
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color:rgb(0, 0, 0);")
        
        layout.addWidget(self.status_label)
        
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)

        # Добавляем ссылку на авторство
        self.author_label = QLabel('Автор: <a href="https://t.me/bypassblock">t.me/bypassblock</a>')
        self.author_label.setOpenExternalLinks(True)  # Разрешаем открытие внешних ссылок
        self.author_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.author_label)
        
        self.setLayout(layout)

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_process_status)
        self.status_timer.start(2000)  # Проверка каждые 1 секунды

    def change_theme(self, theme_name):
        """Changes the application's theme."""
        if theme_name == "РКН Тян":
            # Показываем специальное сообщение для темы РКН Тян
            QMessageBox.information(self, "РКН Тян", 
                                "Тема РКН Тян появится скоро...\n\nОставайтесь на связи!")
            
            # Возвращаем combobox к предыдущей теме (если была выбрана)
            current_index = self.theme_combo.findText(theme_name)
            if current_index > 0:
                self.theme_combo.setCurrentIndex(0)  # Устанавливаем первую тему по умолчанию
            return
            
        if theme_name in THEMES:
            try:
                theme_info = THEMES[theme_name]
                # Применяем тему
                apply_stylesheet(QApplication.instance(), theme=theme_info["file"])
                # Обновляем цвет текста статуса
                self.status_label.setStyleSheet(f"color: {theme_info['status_color']};")
                
                # Обновляем цвет ссылки автора - используем тот же цвет для всего текста
                status_color = theme_info['status_color']
                self.author_label.setStyleSheet(f"""
                    color: {status_color}; 
                    opacity: 0.6; 
                    font-size: 9pt;
                """)
                # Используем HTML для установки цвета ссылки
                self.author_label.setText(f'Автор: <a href="https://t.me/bypassblock" style="color:{status_color}">t.me/bypassblock</a>')
                
                self.set_status(f"Тема изменена на: {theme_name}")
            except Exception as e:
                self.set_status(f"Ошибка при смене темы: {str(e)}")

    def open_info(self):
        """Opens the info website."""
        try:
            webbrowser.open(INFO_URL)
            self.set_status("Открываю руководство...")
        except Exception as e:
            error_msg = f"Ошибка при открытии руководства: {str(e)}"
            print(error_msg)
            self.set_status(error_msg)

    def open_folder(self):
        """Opens the DPI folder."""
        try:
            subprocess.Popen('explorer.exe .', shell=True)
        except Exception as e:
            self.set_status(f"Ошибка при открытии папки: {str(e)}")

    def stop_dpi(self):
        """Останавливает процесс DPI."""
        if self.dpi_starter.stop_dpi():
            self.update_ui(running=False)
        else:
            # Показываем сообщение об ошибке, если метод вернул False
            QMessageBox.warning(self, "Невозможно остановить", 
                            "Невозможно остановить Zapret, пока установлена служба.\n\n"
                            "Пожалуйста, сначала отключите автозапуск (нажмите на кнопку 'Отключить автозапуск').")
        self.check_process_status()  # Обновляем статус в интерфейсе

    def start_dpi(self):
        """Запускает DPI с текущей конфигурацией, если служба ZapretCensorliber не установлена"""
        # Используем существующий метод проверки службы из ServiceManager
        service_found = self.service_manager.check_service_exists()
        
        if service_found:
            # При необходимости здесь можно показать предупреждение
            return
            
        # Если службы нет, запускаем DPI
        selected_mode = self.start_mode_combo.currentText()
        success = self.dpi_starter.start_dpi(selected_mode, DPI_COMMANDS, DOWNLOAD_URLS)
        if success:
            self.update_ui(running=True)
            # Проверяем, не завершился ли процесс сразу после запуска
            QTimer.singleShot(1500, self.check_if_process_started_correctly)
        else:
            self.check_process_status()  # Обновляем статус в интерфейсе

    def check_if_process_started_correctly(self):
        """Проверяет, что процесс успешно запустился и продолжает работать"""
        if not self.dpi_starter.check_process_running():
            # Если процесс не запущен через 1.5 секунды после старта, показываем ошибку
            QMessageBox.critical(self, "Ошибка запуска", 
                                "Процесс winws.exe запустился, но затем неожиданно завершился.\n\n"
                                "Это может быть вызвано:\n"
                                "1. Недостаточными правами администратора\n"
                                "2. Блокировкой антивирусом\n"
                                "3. Конфликтом с другим программным обеспечением\n\n"
                                "Запустите программу от имени администратора или создайте исключение в антивирусе.")
            self.update_ui(running=False)
            
        # В любом случае обновляем статус
        self.check_process_status()
        
    def open_general(self):
        """Opens the list-general.txt file."""
        try:
            general_path = os.path.join(LISTS_FOLDER, 'other.txt')
            # Проверяем существование файла и создаем его при необходимости
            if not os.path.exists(general_path):
                os.makedirs(os.path.dirname(general_path), exist_ok=True)
                with open(general_path, 'w', encoding='utf-8') as f:
                    f.write("# Добавьте сюда свои домены, по одному на строку\n")
            
            subprocess.Popen(f'notepad.exe "{general_path}"', shell=True)
        except Exception as e:
            self.set_status(f"Ошибка при открытии файла: {str(e)}")

    def install_service(self):
        """Устанавливает службу DPI с текущей конфигурацией"""
        selected_config = self.start_mode_combo.currentText()
        if selected_config not in DPI_COMMANDS:
            self.set_status(f"Недопустимая конфигурация: {selected_config}")
            return
            
        # Получаем аргументы командной строки для выбранной конфигурации
        command_args = DPI_COMMANDS.get(selected_config, [])
        
        # Устанавливаем службу через ServiceManager и обновляем UI, если успешно
        if self.service_manager.install_service(command_args, config_name=selected_config):
            self.update_autostart_ui(True)
            self.check_process_status()

    def remove_service(self):
        """Удаляет службу DPI"""
        if self.service_manager.remove_service():
            self.update_autostart_ui(False)
            self.check_process_status()

    def update_ui(self, running):
        """Updates the UI based on the running state."""
        # Обновляем только кнопки запуска/остановки
        self.start_btn.setVisible(not running)
        self.stop_btn.setVisible(running)

    def update_autostart_ui(self, service_running):
        """Обновляет состояние кнопок включения/отключения автозапуска"""
        self.autostart_enable_btn.setVisible(not service_running)
        self.autostart_disable_btn.setVisible(service_running)

    def set_status(self, text):
        """Sets the status text."""
        self.status_label.setText(text)

    ################################# ПРОВЕРЯТЬ ЗАПУЩЕН ЛИ ПРОЦЕСС #################################
    def check_process_status(self):
        """Проверяет статус процесса и обновляет UI"""
        # Запоминаем текущее состояние
        previous_running = self.process_status_value.text() == "ВКЛЮЧЕН"
        previous_service = self.autostart_disable_btn.isVisible()
        
        # Проверяем статус службы
        service_running = self.service_manager.check_service_exists()
        
        # Проверяем статус процесса
        process_running = self.dpi_starter.check_process_running()
        
        # Обновляем UI только если состояние изменилось
        if previous_service != service_running:
            self.update_autostart_ui(service_running)
        
        if previous_running != process_running:
            if process_running:
                self.process_status_value.setText("ВКЛЮЧЕН")
                self.process_status_value.setStyleSheet("color: green; font-weight: bold;")
                self.update_ui(running=True)
            else:
                self.process_status_value.setText("ВЫКЛЮЧЕН")
                self.process_status_value.setStyleSheet("color: red; font-weight: bold;")
                self.update_ui(running=False)

    ################################# hosts #################################
    def some_method_that_calls_add_proxy_domains(self):
        self.hosts_manager.add_proxy_domains()

    ################################# test #################################
    def open_connection_test(self):
        """Открывает окно тестирования соединения."""
        try:
            # Проверяем наличие требуемого модуля requests
            try:
                import requests
            except ImportError:
                self.set_status("Установка необходимых зависимостей...")
                subprocess.run([sys.executable, "-m", "pip", "install", "requests"], 
                            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.set_status("Зависимости установлены")
            
            # Импортируем модуль тестирования
            from connection_test import ConnectionTestDialog
            dialog = ConnectionTestDialog(self)
            dialog.exec_()
            
        except Exception as e:
            error_msg = f"Ошибка при запуске тестирования: {str(e)}"
            print(error_msg)
            self.set_status(error_msg)
            
    ################################# other update #################################
    def update_other_list(self):
        """Обновляет файл списка other.txt с удаленного сервера"""
        try:
            self.set_status("Обновление списка доменов...")
            
            # Проверка наличия модуля requests
            try:
                import requests
            except ImportError:
                self.set_status("Установка зависимостей...")
                subprocess.run([sys.executable, "-m", "pip", "install", "requests"], 
                            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                import requests
            
            # Путь к локальному файлу
            other_path = os.path.join(LISTS_FOLDER, 'other.txt')
            
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(other_path), exist_ok=True)
            
            # Скачиваем файл с сервера
            self.set_status("Загрузка списка доменов...")
            response = requests.get(OTHER_LIST_URL, timeout=10)
            
            if response.status_code == 200:
                # Обрабатываем полученное содержимое
                domains = []
                for line in response.text.splitlines():
                    line = line.strip()  # Удаляем пробелы в начале и конце строки
                    if line:  # Пропускаем пустые строки
                        domains.append(line)
                
                # Собираем все домены в один текст, каждый на новой строке БЕЗ пустых строк
                downloaded_content = "\n".join(domains)
                
                # Читаем текущий файл, если он существует
                current_content = ""
                if os.path.exists(other_path):
                    with open(other_path, 'r', encoding='utf-8') as f:
                        # Также обрабатываем существующее содержимое
                        current_domains = []
                        for line in f:
                            line = line.strip()
                            if line:
                                current_domains.append(line)
                        current_content = "\n".join(current_domains)
                
                # Если файла нет или содержимое отличается
                if not os.path.exists(other_path) or current_content != downloaded_content:
                    # Делаем резервную копию текущего файла
                    if os.path.exists(other_path):
                        backup_path = other_path + '.bak'
                        shutil.copy2(other_path, backup_path)
                    
                    # Сохраняем новый файл (без пустых строк)
                    with open(other_path, 'w', encoding='utf-8') as f:
                        f.write(downloaded_content)
                        
                    self.set_status("Список успешно обновлен")
                    QMessageBox.information(self, "Успешно", "Список доменов успешно обновлен")
                else:
                    self.set_status("Список уже актуален")
                    QMessageBox.information(self, "Информация", "Список доменов уже актуален")
            else:
                self.set_status(f"Ошибка при загрузке списка доменов: {response.status_code}")
                QMessageBox.warning(self, "Ошибка", f"Не удалось получить список доменов с сервера. Код ответа: {response.status_code}")
                
        except Exception as e:
            error_msg = f"Ошибка при обновлении списка доменов: {str(e)}"
            print(error_msg)
            self.set_status(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def moveEvent(self, event):
        """Вызывается при перемещении окна"""
        # Временно останавливаем таймер
        was_active = self.status_timer.isActive()
        if was_active:
            self.status_timer.stop()
        
        # Выполняем стандартную обработку события
        super().moveEvent(event)
        
        # Перезапускаем таймер после небольшой задержки
        if was_active:
            QTimer.singleShot(200, lambda: self.status_timer.start())

def check_if_in_archive():
    """
    Проверяет, находится ли EXE-файл в временной директории,
    что обычно характерно для распаковки из архива.
    """
    try:
        exe_path = os.path.abspath(sys.executable)
        print(f"DEBUG: Executable path: {exe_path}")

        # Получаем пути к системным временным директориям
        temp_env = os.environ.get("TEMP", "")
        tmp_env = os.environ.get("TMP", "")
        temp_dirs = [temp_env, tmp_env]
        
        for temp_dir in temp_dirs:
            if temp_dir and exe_path.lower().startswith(os.path.abspath(temp_dir).lower()):
                print("DEBUG: EXE запущен из временной директории:", temp_dir)
                return True
        return False
    except Exception as e:
        print(f"DEBUG: Ошибка при проверке расположения EXE: {str(e)}")
        return False

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--version":
            print(APP_VERSION)
            sys.exit(0)
        elif sys.argv[1] == "--update" and len(sys.argv) > 3:
            # Режим обновления: updater.py запускает main.py --update old_exe new_exe
            old_exe = sys.argv[2]
            new_exe = sys.argv[3]
            
            # Ждем, пока старый exe-файл будет доступен для замены
            for i in range(10):  # 10 попыток с интервалом 0.5 сек
                try:
                    if not os.path.exists(old_exe) or os.access(old_exe, os.W_OK):
                        break
                    time.sleep(0.5)
                except:
                    time.sleep(0.5)
            
            # Копируем новый файл поверх старого
            try:
                shutil.copy2(new_exe, old_exe)
                # Запускаем обновленное приложение
                subprocess.Popen([old_exe])
            except Exception as e:
                print(f"Ошибка при обновлении: {str(e)}")
            finally:
                # Удаляем временный файл
                try:
                    os.remove(new_exe)
                except:
                    pass
                sys.exit(0)
    
    # Стандартный запуск
    app = QApplication(sys.argv)
    
    if check_if_in_archive():
        error_message = (
            "Приложение не может быть запущено из временной директории!\n\n"
            "Пожалуйста, распакуйте архив полностью в отдельную папку и запустите программу."
        )
        QMessageBox.critical(None, "Ошибка запуска", error_message)
        sys.exit(1)
    
    # Далее создаем и запускаем основное окно
    try:
        if is_admin():
            window = LupiDPIApp()
            window.show()
            sys.exit(app.exec_())
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0)
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Произошла ошибка: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
