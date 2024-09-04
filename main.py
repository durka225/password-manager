import sys
import sqlite3
from PyQt6.QtGui import QAction
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtWidgets import QMenu, QApplication, QMessageBox, QFileDialog
from cryptography.fernet import Fernet
import re
import os
import random
import string

# Путь к файлу с ключом
KEY_FILE = 'key.key'

# Функция для загрузки или генерации ключа шифрования
def load_or_generate_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as key_file:
            return key_file.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as key_file:
            key_file.write(key)
        return key


# Загрузка или генерация ключа
key = load_or_generate_key()
cipher_suite = Fernet(key)

# Подключение к базе данных SQLite
conn = sqlite3.connect('passwords.db')
cursor = conn.cursor()

# Создание таблиц для паролей и мастер-пароля, если их еще нет
cursor.execute('''CREATE TABLE IF NOT EXISTS passwords
                  (id INTEGER PRIMARY KEY, site TEXT, username TEXT, password TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS master_password
                  (id INTEGER PRIMARY KEY, password TEXT)''')
conn.commit()

class RoundedButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 25px;
                border: none;
                padding: 10px 20px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.setFixedHeight(50)
        self.setFixedWidth(200)

class ClickablePasswordLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal(str)

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self.text())

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        context_menu = QMenu(self)
        copy_action = QAction("Копировать пароль", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self.text()))
        context_menu.addAction(copy_action)
        context_menu.exec(event.globalPos())

class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal(str)

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self.text())

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        context_menu = QMenu(self)
        copy_action = QAction("Копировать", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self.text()))
        context_menu.addAction(copy_action)
        context_menu.exec(event.globalPos())

class PasswordManagerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Менеджер паролей")
        self.setFixedSize(700, 600)

        self.setStyleSheet("""
            QWidget {
                background-color: #1c1e26;
                color: #e0e6ed;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLabel {
                font-size: 16px;
                color: #e0e6ed;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #2e2e3e;
                border: 2px solid #2e2e3e;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                color: #e0e6ed;
            }
            QLineEdit:focus {
                border-color: #4e8ef7;
            }
        """)

        self.initUI()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        form_layout = QtWidgets.QFormLayout()
        form_layout.setVerticalSpacing(10)
        form_layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.site_entry = QtWidgets.QLineEdit()
        self.username_entry = QtWidgets.QLineEdit()
        self.password_entry = QtWidgets.QLineEdit()
        self.password_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        password_layout = QtWidgets.QHBoxLayout()

        self.password_entry = QtWidgets.QLineEdit()
        self.password_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.password_entry)

        self.toggle_visibility_button = QtWidgets.QPushButton("👁️")
        self.toggle_visibility_button.setCheckable(True)
        self.toggle_visibility_button.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.toggle_visibility_button)

        form_layout.addRow("Сайт:", self.site_entry)
        form_layout.addRow("Логин:", self.username_entry)
        form_layout.addRow("Пароль:", password_layout)
        
        layout.addLayout(form_layout)

        self.toggle_settings_button = QtWidgets.QPushButton("Показать настройки")
        self.toggle_settings_button.setCheckable(True)
        self.toggle_settings_button.setChecked(False)
        self.toggle_settings_button.toggled.connect(self.toggle_settings_visibility)

        self.settings_frame = QtWidgets.QFrame()
        self.settings_frame.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        settings_layout = QtWidgets.QVBoxLayout(self.settings_frame)

        self.length_label = QtWidgets.QLabel("Длина пароля:")
        self.length_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.length_slider.setRange(6, 32)
        self.length_slider.setValue(12)
        self.length_slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        self.length_slider.setTickInterval(2)
        self.length_display = QtWidgets.QLabel("12")
        self.length_slider.valueChanged.connect(lambda: self.length_display.setText(str(self.length_slider.value())))

        length_layout = QtWidgets.QHBoxLayout()
        length_layout.addWidget(self.length_slider)
        length_layout.addWidget(self.length_display)

        settings_layout.addWidget(self.length_label)
        settings_layout.addLayout(length_layout)

        self.lowercase_checkbox = QtWidgets.QCheckBox("Строчные буквы")
        self.lowercase_checkbox.setChecked(True)

        self.uppercase_checkbox = QtWidgets.QCheckBox("Прописные буквы")
        self.uppercase_checkbox.setChecked(True)

        self.digits_checkbox = QtWidgets.QCheckBox("Цифры")
        self.digits_checkbox.setChecked(True)

        self.specials_checkbox = QtWidgets.QCheckBox("Специальные символы")
        self.specials_checkbox.setChecked(True)

        settings_layout.addWidget(self.lowercase_checkbox)
        settings_layout.addWidget(self.uppercase_checkbox)
        settings_layout.addWidget(self.digits_checkbox)
        settings_layout.addWidget(self.specials_checkbox)

        layout.addWidget(self.toggle_settings_button)
        layout.addWidget(self.settings_frame)

        generate_button_layout = QtWidgets.QHBoxLayout()
        self.generate_button = RoundedButton("Сгенерировать пароль", self)
        self.generate_button.clicked.connect(self.generate_password)
        self.generate_button.setFixedWidth(210)

        generate_button_layout.addStretch()
        generate_button_layout.addWidget(self.generate_button)
        generate_button_layout.addStretch()

        layout.addLayout(generate_button_layout) 

        self.add_button = RoundedButton("Добавить пароль", self)
        self.show_button = RoundedButton("Показать пароли", self)
        self.import_button = RoundedButton("Импорт паролей", self)

        self.add_button.clicked.connect(self.add_password)
        self.show_button.clicked.connect(self.request_master_password)
        self.import_button.clicked.connect(self.import_passwords)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(5)
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.show_button)
        button_layout.addWidget(self.import_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.settings_frame.hide()

        cursor.execute("SELECT password FROM master_password")
        result = cursor.fetchone()

        if result is None:
            self.setup_master_password()
        else:
            self.master_password_encrypted = result[0]


    def toggle_settings_visibility(self):
        if self.toggle_settings_button.isChecked():
            self.settings_frame.show()
            self.toggle_settings_button.setText("Скрыть настройки")
        else:
            self.settings_frame.hide()
            self.toggle_settings_button.setText("Показать настройки")

    def toggle_password_visibility(self):
        if self.toggle_visibility_button.isChecked():
            self.password_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
            self.toggle_visibility_button.setText("🙈")
        else:
            self.password_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
            self.toggle_visibility_button.setText("👁️")

    def generate_password(self):
        length = self.length_slider.value()

        characters = ''
        if self.lowercase_checkbox.isChecked():
            characters += string.ascii_lowercase
        if self.uppercase_checkbox.isChecked():
            characters += string.ascii_uppercase
        if self.digits_checkbox.isChecked():
            characters += string.digits
        if self.specials_checkbox.isChecked():
            characters += string.punctuation

        if characters:
            generated_password = ''.join(random.choice(characters) for i in range(length))
            self.password_entry.setText(generated_password)
        else:
            self.password_entry.setText("Ошибка: выберите хотя бы один тип символов.")
    def setup_master_password(self):
        while True:
            master_password, ok = QtWidgets.QInputDialog.getText(self, "Мастер-пароль", "Установите мастер-пароль:", QtWidgets.QLineEdit.EchoMode.Password)
            confirm_password, ok = QtWidgets.QInputDialog.getText(self, "Мастер-пароль", "Подтвердите мастер-пароль:", QtWidgets.QLineEdit.EchoMode.Password)

            if master_password and master_password == confirm_password:
                encrypted_password = cipher_suite.encrypt(master_password.encode())
                cursor.execute("INSERT INTO master_password (password) VALUES (?)", (encrypted_password,))
                conn.commit()
                self.master_password_encrypted = encrypted_password
                QtWidgets.QMessageBox.information(self, "Успех", "Мастер-пароль успешно установлен!")
                break
            else:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Пароли не совпадают. Попробуйте снова.")

    def request_master_password(self):
        master_password, ok = QtWidgets.QInputDialog.getText(
            self,
            "Мастер-пароль",
            "Введите мастер-пароль:",
            QtWidgets.QLineEdit.EchoMode.Password
        )
        if ok and master_password:
            try:
                decrypted_master_password = cipher_suite.decrypt(self.master_password_encrypted).decode()
                if master_password == decrypted_master_password:
                    self.show_passwords()
                else:
                    QtWidgets.QMessageBox.warning(self, "Ошибка", "Неверный мастер-пароль.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {str(e)}")

    def add_password(self):
        site = self.site_entry.text()
        username = self.username_entry.text()
        password = self.password_entry.text()

        if site and username and password:
            encrypted_password = cipher_suite.encrypt(password.encode())
            cursor.execute("INSERT INTO passwords (site, username, password) VALUES (?, ?, ?)",
                           (site, username, encrypted_password))
            conn.commit()
            QtWidgets.QMessageBox.information(self, "Успех", "Пароль успешно добавлен!")
            self.site_entry.clear()
            self.username_entry.clear()
            self.password_entry.clear()
        else:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Заполните все поля.")

    def show_passwords(self):
        cursor.execute("SELECT id, site, username, password FROM passwords")
        data = cursor.fetchall()

        self.passwords_window = QtWidgets.QWidget()
        self.passwords_window.setWindowTitle("Сохраненные пароли")
        self.passwords_window.setFixedSize(1100, 800)

        self.passwords_window.setStyleSheet("""
            QWidget {
                background-color: #1c1e26;
                color: #e0e6ed;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLabel {
                font-size: 16px;
                color: #e0e6ed;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #2e2e3e;
                border: 2px solid #2e2e3e;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                color: #e0e6ed;
            }
            QLineEdit:focus {
                border-color: #4e8ef7;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(20, 20, 20, 20)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(15)

        site_header = QtWidgets.QLabel("Сайт")
        site_header.setStyleSheet("font-size: 16px; color: #e0e6ed;")
        site_header.setFixedWidth(250)
        header_layout.addWidget(site_header)

        username_header = QtWidgets.QLabel("Логин")
        username_header.setStyleSheet("font-size: 16px; color: #e0e6ed;")
        username_header.setFixedWidth(250)
        header_layout.addWidget(username_header)

        password_header = QtWidgets.QLabel("Пароль")
        password_header.setStyleSheet("font-size: 16px; color: #e0e6ed;")
        password_header.setFixedWidth(250)
        header_layout.addWidget(password_header)

        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        scroll_area_content = QtWidgets.QWidget()
        scroll_area_layout = QtWidgets.QVBoxLayout()
        scroll_area_layout.setSpacing(10)
        scroll_area_layout.setContentsMargins(0, 0, 0, 0)

        for record_id, site, username, encrypted_password in data:
            decrypted_password = cipher_suite.decrypt(encrypted_password).decode()

            hbox = QtWidgets.QHBoxLayout()
            hbox.setSpacing(10)

            site_entry = QtWidgets.QLabel(site)
            site_entry.setStyleSheet("font-size: 16px; color: #e0e6ed; padding: 10px; background-color: #2c3e50; border-radius: 5px;")
            site_entry.setFixedWidth(250)
            hbox.addWidget(site_entry)

            username_entry = ClickableLabel(username)
            username_entry.setStyleSheet("font-size: 16px; color: #e0e6ed; padding: 10px; background-color: #2c3e50; border-radius: 5px;")
            username_entry.setFixedWidth(250)
            username_entry.clicked.connect(lambda text=username: self.copy_text_to_clipboard(text))
            hbox.addWidget(username_entry)

            password_entry = QtWidgets.QLineEdit(decrypted_password)
            password_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
            password_entry.setStyleSheet("font-size: 16px; color: #e0e6ed; padding: 10px; background-color: #2c3e50; border-radius: 5px;")
            password_entry.setReadOnly(True)
            password_entry.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            password_entry.setFixedWidth(250)

            password_entry.mouseReleaseEvent = lambda event, text=decrypted_password: self.copy_text_to_clipboard(text) if event.button() == QtCore.Qt.MouseButton.LeftButton else None

            toggle_button = QtWidgets.QPushButton("👁️")
            toggle_button.setFixedWidth(40)
            toggle_button.setCheckable(True)
            toggle_button.setStyleSheet("background-color: #2c3e50; color: #ecf0f1; border: none; font-size: 16px;")
            toggle_button.clicked.connect(lambda _, password_entry=password_entry, toggle_button=toggle_button: self.toggle_password_visibility_save_menu(password_entry, toggle_button))

            password_entry_layout = QtWidgets.QHBoxLayout()
            password_entry_layout.addWidget(password_entry)
            password_entry_layout.addWidget(toggle_button)
            hbox.addLayout(password_entry_layout)

            edit_button = QtWidgets.QPushButton("Изменить")
            edit_button.setStyleSheet("background-color: #e67e22; color: white; padding: 10px; font-size: 16px; border-radius: 5px;")
            edit_button.setFixedWidth(100)
            edit_button.clicked.connect(lambda _, rid=record_id: self.show_edit_dialog(rid))
            hbox.addWidget(edit_button)

            delete_button = QtWidgets.QPushButton("Удалить")
            delete_button.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px; font-size: 16px; border-radius: 5px;")
            delete_button.setFixedWidth(100)
            delete_button.clicked.connect(lambda _, rid=record_id: self.delete_record(rid))
            hbox.addWidget(delete_button)

            hbox.addStretch()
            scroll_area_layout.addLayout(hbox)

        scroll_area_content.setLayout(scroll_area_layout)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_area_content)

        main_layout.addWidget(scroll_area)
        self.passwords_window.setLayout(main_layout)
        self.passwords_window.show()

    def show_password_context_menu(self, pos, password_entry):
        context_menu = QMenu(self.passwords_window)
        copy_action = QAction("Копировать пароль", self.passwords_window)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(password_entry.text()))
        context_menu.addAction(copy_action)
        context_menu.exec(self.passwords_window.mapToGlobal(pos))

    def toggle_password_visibility_save_menu(self, password_entry, toggle_button):
        if toggle_button.isChecked():
            password_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
            toggle_button.setText("🙈")
        else:
            password_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
            toggle_button.setText("👁️")

    def copy_text_to_clipboard(self, text):
        QApplication.clipboard().setText(text)
        
        dialog = QtWidgets.QDialog(self.passwords_window)
        dialog.setWindowTitle("Копирование")
        dialog.setStyleSheet("""
            QDialog {
                background-color: #34495e; 
                color: white;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                padding: 20px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                margin-bottom: 15px;
                background: none;
            }
            QPushButton {
                background-color: #3498db; 
                color: white; 
                border: 2px solid #2980b9; 
                border-radius: 5px; 
                font-size: 14px; 
                padding: 5px 10px; 
                min-width: 80px; 
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


        message_label = QtWidgets.QLabel("Скопирован в буфер обмена!")
        message_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        ok_button = QtWidgets.QPushButton("ОК")
        ok_button.clicked.connect(dialog.accept)
        ok_button.setFixedWidth(100)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        button_layout.addWidget(ok_button)

        main_layout.addWidget(message_label)
        main_layout.addLayout(button_layout)
        dialog.setLayout(main_layout)

        dialog.exec()

    def show_edit_dialog(self, record_id):
        cursor.execute("SELECT site, username, password FROM passwords WHERE id = ?", (record_id,))
        site, username, encrypted_password = cursor.fetchone()
        decrypted_password = cipher_suite.decrypt(encrypted_password).decode()

        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Изменить запись")
        dialog.setFixedSize(400, 200)
        
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: #ecf0f1;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #34495e;
                color: #ecf0f1;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        layout = QtWidgets.QFormLayout()
        site_entry = QtWidgets.QLineEdit(site)
        username_entry = QtWidgets.QLineEdit(username)
        password_entry = QtWidgets.QLineEdit(decrypted_password)
        password_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        layout.addRow("Сайт:", site_entry)
        layout.addRow("Логин:", username_entry)
        layout.addRow("Пароль:", password_entry)

        save_button = QtWidgets.QPushButton("Сохранить")
        save_button.clicked.connect(lambda: self.save_edited_record(record_id, site_entry.text(), username_entry.text(), password_entry.text(), dialog))

        layout.addWidget(save_button)
        dialog.setLayout(layout)
        
        dialog.exec()

    def save_edited_record(self, record_id, site, username, password, dialog):
        if site and username and password:
            encrypted_password = cipher_suite.encrypt(password.encode())
            cursor.execute("UPDATE passwords SET site = ?, username = ?, password = ? WHERE id = ?",
                        (site, username, encrypted_password, record_id))
            conn.commit()
            QtWidgets.QMessageBox.information(None, "Успех", "Запись успешно обновлена!")
            dialog.accept()

            self.show_passwords()
        else:
            QtWidgets.QMessageBox.warning(None, "Ошибка", "Заполните все поля.")

    def delete_record(self, record_id):

        dialog = QtWidgets.QMessageBox()
        dialog.setWindowTitle("Удаление записи")
        dialog.setText("Вы уверены, что хотите удалить эту запись?")
        dialog.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)

        reply = dialog.exec()

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            cursor.execute("DELETE FROM passwords WHERE id = ?", (record_id,))
            conn.commit()
            QtWidgets.QMessageBox.information(None, "Успех", "Запись успешно удалена!")
            
        self.show_passwords()


    def import_passwords(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Текстовые файлы (*.txt)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            password_blocks = content.strip().split("\n\n")

            for block in password_blocks:
                site_match = re.search(r"(.+):", block)
                username_match = re.search(r"Почта:\s*(.+)", block)
                password_match = re.search(r"Пароль:\s*(.+)", block)

                if site_match and username_match and password_match:
                    site = site_match.group(1).strip()
                    username = username_match.group(1).strip()
                    password = password_match.group(1).strip()

                    encrypted_password = cipher_suite.encrypt(password.encode())

                    cursor.execute("INSERT INTO passwords (site, username, password) VALUES (?, ?, ?)",
                                   (site, username, encrypted_password))
                    conn.commit()

            QtWidgets.QMessageBox.information(self, "Успех", "Пароли успешно импортированы!")
        else:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Файл не выбран.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PasswordManagerApp()
    window.show()
    sys.exit(app.exec())