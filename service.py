import os
import subprocess
import time

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
        # Если command_args переданы как строка, разбиваем на список
        if isinstance(command_args, str):
            command_args = command_args.split()

        try:
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
                raise Exception(f"Ошибка при создании службы: {error_output}")

        except Exception as e:
            error_msg = f"Ошибка при установке службы: {str(e)}"
            print(error_msg)
            self.set_status(error_msg)
            return False
    
    def remove_service(self):
        """
        Удаляет службу DPI
        
        Returns:
            bool: True при успешном удалении, False при ошибке
        """
        try:
            # Проверяем существует ли служба
            if not self.check_service_exists():
                self.set_status("Служба DPI не установлена")
                return True

            # Даже если остановка не удалась, пытаемся удалить
            time.sleep(0.1)  # Даем время на остановку
            
            existing_services = [self.service_name, "ZapretService", "Zapret by Censorliber"]
            for svc in existing_services:
                check_cmd = f'sc query "{svc}"'
                result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    self.set_status(f"Служба \"{svc}\" уже существует. Удаление...")
                    stop_cmd = f'sc stop "{svc}"'
                    subprocess.run(stop_cmd, shell=True, capture_output=True)
                    time.sleep(0.1)
                    delete_cmd = f'sc delete "{svc}"'
                    delete_result = subprocess.run(delete_cmd, shell=True, capture_output=True, text=True)
                    if delete_result.returncode != 0:
                        self.set_status(f"Не удалось удалить службу \"{svc}\"")
                    time.sleep(0.1)

            if delete_result.returncode == 0:
                self.set_status("Служба DPI успешно удалена")
                return True
            else:
                error_output = delete_result.stderr.strip() if delete_result.stderr else delete_result.stdout.strip()
                raise Exception(f"Ошибка при удалении службы: {error_output}")
                
        except Exception as e:
            error_msg = f"Ошибка при удалении службы: {str(e)}"
            print(error_msg)
            self.set_status(error_msg)
            return False
