import os
import subprocess
import time, winreg
from config import DPI_COMMANDS

# Константы для работы с реестром
REGISTRY_KEY = r"SOFTWARE\Zapret"
CONFIG_VALUE = "ZapretServiceConfig"

def save_config_to_registry(config_name):
    """Сохраняет имя конфигурации в реестр Windows"""
    try:
        # Пытаемся открыть существующий ключ
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_WRITE)
        except FileNotFoundError:
            # Если ключ не существует, создаем его
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        
        # Записываем значение
        winreg.SetValueEx(key, CONFIG_VALUE, 0, winreg.REG_SZ, config_name)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении конфигурации в реестр: {str(e)}")
        return False

def get_config_from_registry():
    """Получает имя конфигурации из реестра Windows"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, CONFIG_VALUE)
        winreg.CloseKey(key)
        return value
    except FileNotFoundError:
        # Ключ или значение не найдены
        return None
    except Exception as e:
        print(f"Ошибка при получении конфигурации из реестра: {str(e)}")
        return None

class ServiceManager:
    def __init__(self, winws_exe, bin_folder, lists_folder, status_callback=None, service_name="ZapretCensorliber"):
        """
        Инициализирует менеджер служб.
        
        Args:
            winws_exe (str): Путь к исполняемому файлу winws.exe
            bin_folder (str): Путь к папке с бинарными файлами
            lists_folder (str): Путь к папке со списками
            status_callback (callable): Функция обратного вызова для отображения статуса
            service_name (str): Имя службы
        """
        self.winws_exe = winws_exe
        self.bin_folder = bin_folder
        self.lists_folder = lists_folder
        self.status_callback = status_callback
        self.service_name = service_name
    
    def set_status(self, text):
        """Отображает статусное сообщение"""
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)
    
    def check_service_exists(self):
        """Проверяет существует ли служба"""
        check_cmd = f'sc query "{self.service_name}"'
        check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        return check_result.returncode == 0

    def install_service(self, command_args, config_name=""):
        """
        Устанавливает службу Windows для автоматического запуска DPI.
        
        Args:
            command_args (list): Аргументы командной строки для winws.exe
            config_name (str, optional): Имя конфигурации для отображения в сообщениях
            
        Returns:
            bool: True если служба успешно установлена, False в случае ошибки
        """
        try:
            # Если command_args переданы как строка, разбиваем на список
            if isinstance(command_args, str):
                command_args = command_args.split()

            # Проверяем путь на наличие пробелов
            current_path = os.path.dirname(os.path.abspath(self.winws_exe))
            if " " in current_path:
                error_msg = (
                    "Ошибка: Невозможно установить службу, так как путь к программе содержит пробелы:\n"
                    f"{current_path}\n\n"
                    "Пожалуйста, переместите программу в папку без пробелов в пути "
                    "(например, в корень диска C:\\Zapret) и повторите попытку."
                )
                self.set_status("Ошибка: Путь содержит пробелы")
                
                # Используем QMessageBox для вывода сообщения
                from PyQt5.QtWidgets import QMessageBox
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("Ошибка пути")
                msg_box.setText(error_msg)
                msg_box.exec_()
                
                return False
                
            # Проверяем существует ли служба
            if self.check_service_exists():
                self.set_status("Служба уже существует. Удаление...")
                stop_cmd = f'sc stop "{self.service_name}"'
                subprocess.run(stop_cmd, shell=True, capture_output=True)
                time.sleep(0.1)
                delete_cmd = f'sc delete "{self.service_name}"'
                delete_result = subprocess.run(delete_cmd, shell=True, capture_output=True, text=True)
                if delete_result.returncode != 0:
                    self.set_status("Не удалось удалить существующую службу")
                time.sleep(0.1)

            exe_path = os.path.abspath(self.winws_exe)
            processed_args = []
            for arg in command_args:
                if ".txt" in arg or ".bin" in arg:
                    if "=" in arg:
                        prefix, filename = arg.split("=", 1)
                        if ".txt" in filename:
                            full_path = os.path.join(os.path.abspath(self.lists_folder), os.path.basename(filename))
                            processed_args.append(f"{prefix}={full_path}")
                        elif ".bin" in filename:
                            full_path = os.path.join(os.path.abspath(self.bin_folder), os.path.basename(filename))
                            processed_args.append(f"{prefix}={full_path}")
                        else:
                            processed_args.append(arg)
                    else:
                        processed_args.append(arg)
                else:
                    processed_args.append(arg)

            args_str = " ".join(processed_args)
            service_command = f'"{exe_path}" {args_str}'

            # Создаем службу без описания
            create_cmd = (
                f'sc create "{self.service_name}" type= own binPath= "{service_command}" '
                f'start= auto DisplayName= "{self.service_name}"'
            )
            print(f"DEBUG: Service command: {create_cmd}")
            create_result = subprocess.run(create_cmd, shell=True, capture_output=True, text=True)
            if create_result.returncode == 0:
                # Устанавливаем описание службы отдельной командой
                desc_cmd = f'sc description "{self.service_name}" "Служба для работы Zapret DPI https://t.me/bypassblock"'
                subprocess.run(desc_cmd, shell=True, capture_output=True, text=True)
                
                # Сохраняем конфигурацию в реестр
                save_config_to_registry(config_name if config_name else "Пользовательская")
                subprocess.run("taskkill /IM winws.exe /F", shell=True, check=False)
                time.sleep(0.1)
                # Запускаем службу
                start_cmd = f'sc start "{self.service_name}"'
                start_result = subprocess.run(start_cmd, shell=True, capture_output=True, text=True)
                if start_result.returncode == 0:
                    self.set_status(f"Служба установлена и запущена (конфиг: {config_name})")
                    return True
                else:
                    self.set_status("Служба создана, но не удалось запустить её")
                    return False
            else:
                error_output = create_result.stderr.strip() if create_result.stderr else create_result.stdout.strip()
                self.set_status(f"Ошибка при создании службы: {error_output}")
                return False
        except Exception as e:
            self.set_status(f"Ошибка при установке службы: {str(e)}")
            return False
        
    def remove_service(self):
        """
        Удаляет службу ZapretCensorliber.
        
        Returns:
            bool: True если служба успешно удалена, False в случае ошибки
        """
        try:
            # Проверяем существует ли служба
            if not self.check_service_exists():
                self.set_status("Служба не найдена")
                return True  # Считаем успешным выполнение, если службы нет
                
            # Останавливаем службу
            stop_cmd = f'sc stop "{self.service_name}"'
            subprocess.run(stop_cmd, shell=True, capture_output=True)
            time.sleep(0.1)  # Даем время на остановку
            
            # Удаляем службу
            delete_cmd = f'sc delete "{self.service_name}"'
            delete_result = subprocess.run(delete_cmd, shell=True, capture_output=True, text=True)
            
            if delete_result.returncode == 0:
                # Удаляем информацию о конфигурации из реестра
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_ALL_ACCESS)
                    winreg.DeleteValue(key, CONFIG_VALUE)
                    winreg.CloseKey(key)
                except FileNotFoundError:
                    pass  # Если ключа или значения нет, игнорируем
                except Exception as e:
                    print(f"Ошибка при удалении конфигурации из реестра: {str(e)}")
                
                self.set_status("Служба успешно удалена")
                return True
            else:
                error_output = delete_result.stderr.strip() if delete_result.stderr else delete_result.stdout.strip()
                self.set_status(f"Не удалось удалить службу: {error_output}")
                return False
        except Exception as e:
            self.set_status(f"Ошибка при удалении службы: {str(e)}")
            return False
            
    def get_current_service_config(self):
        """
        Получает текущую конфигурацию запущенной службы ZapretCensorliber из реестра
        
        Returns:
            str: Имя стратегии или None, если службы нет или не удалось определить
        """
        try:
            # Проверяем существование службы
            if not self.check_service_exists():
                return None  # Служба не существует
            
            # Получаем конфигурацию из реестра
            config = get_config_from_registry()
            return config if config else "Пользовательская"
                
        except Exception as e:
            print(f"Ошибка при определении конфигурации службы: {str(e)}")
            return "Неизвестная"
