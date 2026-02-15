# models.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QMessageBox, QHeaderView, QCheckBox, QComboBox,
    QWidget, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


# Список провайдеров, у которых URL задаётся автоматически
AUTO_URL_PROVIDERS = {
    "gigachat": "GigaChat",
    "yandex": "Yandex GPT",
}

# Пример: можно вынести в network.py
def get_provider_url(provider: str) -> str:
    """Возвращает URL по провайдеру — используется при сохранении"""
    urls = {
        "gigachat": "https://gigachat.sbercloud.ru/v1/chat/completions",
        "yandex": "https://d5dsop9op9ghv14u968d.hsvi2zuh.apigw.yandexcloud.net"
        
    }
    return urls.get(provider, "")

class ModelsManager:
    """Редактор моделей с поддержкой БД"""

    def __init__(self, db, parent=None):
        self.db = db
        self.parent = parent
        self.models = []

    def open_editor(self):
        """Открывает редактор моделей"""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Редактировать модели")
        dialog.resize(950, 500)  # Увеличили ширину
        layout = QVBoxLayout()

        # Таблица: +1 колонка для API Key
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Имя", "API URL", "Модель", "Провайдер", "API Key", "Активна", "Действия"
        ])

        # Режим выделения: всю строку
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)  # Только одна строка

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Имя
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # URL — растягиваем
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Модель
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Провайдер
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # API Key
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)             # Активна
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Действия
        self.table.setColumnWidth(6, 60)

        layout.addWidget(self.table)

        # Кнопки под таблицей
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        add_btn = QPushButton("➕ Добавить")
        del_btn = QPushButton("🗑 Удалить")
        save_btn = QPushButton("✅ Сохранить")

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)
        self.dialog = dialog

        # Загружаем модели из БД
        self.load_from_db()
        self.refresh_table()

        # Подключаем сигналы
        add_btn.clicked.connect(self.add_model)
        del_btn.clicked.connect(self.delete_model)
        save_btn.clicked.connect(self.save_to_db)

        dialog.exec()

    def load_from_db(self):
        """Загружает модели из БД"""
        try:
            print("[ModelsManager] Загружаю модели из БД...")
            models = self.db.get_all_models()
            print(f"[ModelsManager] Получено моделей: {len(models)}")
            self.models = models if models is not None else []
        except Exception as e:
            QMessageBox.critical(self.parent, "Ошибка", f"Не удалось загрузить модели из базы данных:\n{e}")
            self.models = []

    def refresh_table(self):
        """Обновляет таблицу с кнопками редактирования и копирования"""
        self.table.setRowCount(0)
        for row, model in enumerate(self.models):
            self.table.insertRow(row)

            # ID
            self.table.setItem(row, 0, QTableWidgetItem(str(model["id"])))

            # Имя
            self.table.setItem(row, 1, QTableWidgetItem(model["name"]))

            # API URL
            api_url_item = QTableWidgetItem()
            provider = model["provider"]
            if provider in AUTO_URL_PROVIDERS:
                api_url_item.setText(f"🔒 {AUTO_URL_PROVIDERS[provider]}")
                api_url_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                api_url_item.setToolTip("URL задаётся автоматически")
                api_url_item.setForeground(Qt.GlobalColor.darkBlue)
                api_url_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            else:
                api_url_item.setText(model["api_url"] or "")
            self.table.setItem(row, 2, api_url_item)

            # Модель
            self.table.setItem(row, 3, QTableWidgetItem(model["model_name"]))

            # Провайдер
            provider_item = QTableWidgetItem(provider)
            provider_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 4, provider_item)

            # API Key Variable
            key_item = QTableWidgetItem(model["api_key_var"] or "")
            self.table.setItem(row, 5, key_item)

            # Активна — чекбокс
            active = QCheckBox()
            active.setChecked(model["is_active"] == 1)

            # Сохраняем изменение в model
            def on_active_toggled(state, m=model):
                m["is_active"] = 1 if state == Qt.CheckState.Checked else 0

            active.stateChanged.connect(on_active_toggled)
            self.table.setCellWidget(row, 6, active)

            # Действия — кнопки
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 0, 2, 0)
            btn_layout.setSpacing(4)

            edit_btn = QPushButton("✎")
            edit_btn.setFixedSize(30, 24)
            edit_btn.setToolTip("Редактировать")

            copy_btn = QPushButton("📋")
            copy_btn.setFixedSize(30, 24)
            copy_btn.setToolTip("Копировать")

            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(copy_btn)
            btn_layout.addStretch()

            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 7, btn_widget)

            # Подключаем кнопки
            edit_btn.clicked.connect(lambda checked, r=row: self.edit_model(r))
            copy_btn.clicked.connect(lambda checked, r=row: self.copy_model(r))

    def add_model(self):
        """Добавляет новую модель"""
        new_model = {
            "id": 0,
            "name": "Новая модель",
            "api_url": "",
            "api_key_var": "CUSTOM_API_KEY",
            "is_active": 1,
            "provider": "custom",
            "model_name": "custom"
        }
        self.models.append(new_model)
        self.refresh_table()

    def copy_model(self, row: int):
        """Копирует модель"""
        original = self.models[row].copy()
        original["id"] = 0
        original["name"] = f"{original['name']} (копия)"
        self.models.append(original)
        self.refresh_table()

    def edit_model(self, row: int):
        """Редактирует модель: ввод имени, модели, API URL, провайдера, API Key"""
        model = self.models[row]
        dialog = QDialog(self.dialog)
        dialog.setWindowTitle("Редактировать модель")
        dialog.resize(550, 450)
        layout = QVBoxLayout()

        # Форма
        form = QFormLayout()

        # Имя
        name_input = QLineEdit(model["name"])
        form.addRow("Имя:", name_input)

        # Модель (model_name)
        model_name_input = QLineEdit(model["model_name"])
        form.addRow("Модель (model_name):", model_name_input)

        # API URL
        api_url_input = QLineEdit(model["api_url"])
        api_url_input.setPlaceholderText("https://api.example.com/v1/chat/completions")
        form.addRow("API URL:", api_url_input)

        # API Key Variable
        api_key_input = QLineEdit(model["api_key_var"])
        api_key_input.setPlaceholderText("GIGACHAT, POLZA_API_KEY и т.д.")
        form.addRow("API Key Variable:", api_key_input)

        # Провайдер
        provider_input = QLineEdit(model["provider"])
        provider_input.setPlaceholderText("Polza, gigachat, yandex и т.д.")
        form.addRow("Провайдер:", provider_input)

        layout.addLayout(form)

        # Кнопки
        btns = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        cancel_btn = QPushButton("Отмена")
        btns.addStretch()
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

        dialog.setLayout(layout)

        # Обработка сохранения
        def save():
            name = name_input.text().strip()
            model_name = model_name_input.text().strip()
            api_url = api_url_input.text().strip()
            provider = provider_input.text().strip().lower()  # нормализуем
            api_key_var = api_key_input.text().strip()

            if not name:
                QMessageBox.warning(dialog, "Ошибка", "Имя модели обязательно")
                return
            if not api_key_var:
                QMessageBox.warning(dialog, "Ошибка", "API Key Variable обязателен")
                return

            # Обновляем модель
            model.update({
                "id": model["id"],  # ✅ Так правильно
                "name": name,
                "api_url": api_url,
                "api_key_var": api_key_var,
                "is_active": model["is_active"],
                "provider": provider,
                "model_name": model_name
            })

            # Обновляем в списке
            self.models[row] = model
            self.refresh_table()
            dialog.accept()

        save_btn.clicked.connect(save)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec()


    def delete_model(self):
        """Удаляет выбранную модель из списка и из БД"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self.dialog, "Ошибка", "Выберите строку для удаления")
            return

        model = self.models[row]
        model_name = model["name"]

        reply = QMessageBox.question(
            self.dialog,
            "Подтвердите удаление",
            f"Вы действительно хотите удалить модель:\n\"{model_name}\"?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Удаляем из списка
            del self.models[row]
            self.refresh_table()

            # Удаляем из БД, если модель существовала (id > 0)
            if model["id"] > 0:
                try:
                    # Используем метод из db.py — он сам вызывает commit
                    self.db.delete_model(model["id"])
                    print(f"[ModelsManager] Модель {model['name']} (ID: {model['id']}) удалена из БД")
                except Exception as e:
                    QMessageBox.critical(self.dialog, "Ошибка", f"Не удалось удалить модель из базы:\n{e}")
                    return

            # Обновляем UI в основном окне
            if hasattr(self.parent, "load_models"):
                self.parent.load_models()

    def save_to_db(self):
        """Сохраняет модели из внутреннего списка self.models, а не из таблицы"""
        try:
            models_to_save = []
            for idx, model in enumerate(self.models):
                name = model["name"].strip()
                provider = (model.get("provider") or "custom").strip().lower()
                model_name = model["model_name"].strip()
                api_key_var = model["api_key_var"].strip()

                # Определяем API URL
                if provider in AUTO_URL_PROVIDERS:
                    api_url = get_provider_url(provider)
                else:
                    api_url = model["api_url"].strip()

                # Проверки
                if not name:
                    QMessageBox.warning(self.parent, "Ошибка", "Имя модели не может быть пустым")
                    return
                if not api_url:
                    QMessageBox.warning(self.parent, "Ошибка", f"API URL обязателен для модели '{name}'")
                    return
                if not api_key_var:
                    QMessageBox.warning(self.parent, "Ошибка", f"API Key Variable обязателен для модели '{name}'")
                    return
                print(f"ID: {model['id']}, Active: {model['is_active']}, Type: {type(model['is_active'])}")

                # Добавляем в список для сохранения
                models_to_save.append({
                    "id": model["id"],
                    "name": name,
                    "api_url": api_url,
                    "api_key_var": api_key_var,
                    "is_active": 1 if model["is_active"] else 0,
                    "provider": provider,
                    "model_name": model_name
                })

            # Сохраняем в БД
            self.db.save_models(models_to_save)
            QMessageBox.information(self.parent, "Успех", "Модели сохранены!")
            self.dialog.accept()

            # Обновляем основное окно
            if hasattr(self.parent, "load_models"):
                self.parent.load_models()

        except Exception as e:
            QMessageBox.critical(self.parent, "Ошибка", f"Не удалось сохранить:\n{e}")
            print(f"[ModelsManager] Ошибка сохранения: {e}")
