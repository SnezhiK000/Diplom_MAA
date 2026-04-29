from django.db import models
import os
# --------------------------------------------------------------
# РОЛЬ
class Role(models.Model):
    ROLE_CHOICES = [
        ('technician', 'Техник'),
        ('employee', 'Сотрудник'),
        ('manager', 'Руководитель'),
        ('admin', 'Администратор'),
    ]
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    role_name = models.CharField(max_length=250, choices=ROLE_CHOICES, unique=True, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

# --------------------------------------------------------------
# ДОЛЖНОСТЬ
class Position(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ОТДЕЛ
class Department(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование отдела")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# КОРПУСА
class Building(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование корпуса")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# КАБИНЕТ
class Office(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    number = models.CharField(max_length=50, verbose_name="Номер кабинета", null=True, blank=True)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, verbose_name="Корпус", null=True, blank=True)
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return f"Кабинет {self.number}" if self.number else "Не распределён"

    # Нахождение следующего номера
    def save(self, *args, **kwargs):
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM equip_office")
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        super().save(*args, **kwargs)

# --------------------------------------------------------------
# ПРОИЗВОДИТЕЛИ
class Manufacturer(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

    # Нахождение следующего номера
    def save(self, *args, **kwargs):
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM equip_manufacturer")
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        super().save(*args, **kwargs)

# --------------------------------------------------------------
# МОДЕЛИ ОБОРУДОВАНИЯ
class EquipmentModel(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование модели")
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, verbose_name="Производитель", null=True,
                                     blank=True)
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

    # Нахождение следующего номера
    def save(self, *args, **kwargs):
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM equip_equipmentmodel")
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        super().save(*args, **kwargs)


# --------------------------------------------------------------
# ТИП ОБОРУДОВАНИЯ
class EquipmentType(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование типа")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

    # Нахождение следующего номера
    def save(self, *args, **kwargs):
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM equip_equipmenttype")
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        super().save(*args, **kwargs)

# --------------------------------------------------------------
# СТАТУСЫ ОБОРУДОВАНИЯ
class EquipmentStatus(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование статуса")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

    # Нахождение следующего номера
    def save(self, *args, **kwargs):
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM equip_equipmentstatus")
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        super().save(*args, **kwargs)

# --------------------------------------------------------------
# ГАРАНТИИ
class Warranty(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    start_date = models.DateField(verbose_name="Дата начала", null=True, blank=True)
    end_date = models.DateField(verbose_name="Дата окончания", null=True, blank=True)
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return f"Гарантия до {self.end_date}" if self.end_date else "Без гарантии"

    # Нахождение следующего номера
    def save(self, *args, **kwargs):
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM equip_warranty")
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        super().save(*args, **kwargs)

# --------------------------------------------------------------
# ФОТОГРАФИИ
class Photos(models.Model):
    id = models.AutoField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Название фото")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def save(self, *args, **kwargs):
        #Нахождение следующего номера
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(MAX(id), 0) + 1 FROM equip_photos
                """)
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ОБОРУДОВАНИЕ
class Equipment(models.Model):
    inventory_number = models.IntegerField(primary_key=True, verbose_name="Инвентарный номер")
    assigned_office = models.ForeignKey(Office, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Закрепленный кабинет")
    model = models.ForeignKey(EquipmentModel, on_delete=models.CASCADE, verbose_name="Модель")
    type = models.ForeignKey(EquipmentType, on_delete=models.CASCADE, verbose_name="Тип оборудования")
    status = models.ForeignKey(EquipmentStatus, on_delete=models.CASCADE, verbose_name="Статус")
    configuration = models.CharField(max_length=255, verbose_name="Комплектация", null=True, blank=True)
    warranty = models.ForeignKey(Warranty, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Гарантия")
    purchase_date = models.DateField(verbose_name="Дата приобретения", null=True, blank=True)
    photo = models.ForeignKey(Photos, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Фото")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return f"{self.model.name} ({self.inventory_number})"

# --------------------------------------------------------------
# КАТЕГОРИИ ЗАЯВОК
class RequestCategory(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ЭТАПЫ РЕМОНТА
class RepairStage(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ПРИОРИТЕТЫ
class Priority(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ЗАПЧАСТИ
class SparePart(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    quantity = models.IntegerField(verbose_name="Количество на складе")
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Стоимость за 1 шт.")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# СТОРОННИЕ УСЛУГИ
class ThirdPartyService(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Стоимость")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ФАЙЛЫ
class File(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    file = models.FileField(upload_to='files/%Y/%m/%d/', verbose_name="Файл")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return os.path.basename(self.file.name)

    def filename(self):
        return os.path.basename(self.file.name)

    # Нахождение следующего номера
    def save(self, *args, **kwargs):
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM equip_file")
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        super().save(*args, **kwargs)

# --------------------------------------------------------------
# СОТРУДНИК
class Employee(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    login = models.CharField(max_length=250, unique=True, verbose_name="Почта (Логин)")
    phone_number = models.CharField(max_length=20, verbose_name="Номер телефона")
    last_name = models.CharField(max_length=250, verbose_name="Фамилия")
    first_name = models.CharField(max_length=250, verbose_name="Имя")
    middle_name = models.CharField(max_length=250, verbose_name="Отчество")
    position = models.ForeignKey(Position, on_delete=models.CASCADE, verbose_name="Должность")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name="Отдел")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name="Роль")
    password = models.CharField(max_length=250, verbose_name="Пароль")
    last_login = models.DateTimeField(null=True, blank=True, verbose_name="Время последнего захода")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")
    office = models.ForeignKey(Office, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Кабинет")

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    # Нахождение следующего номера
    def save(self, *args, **kwargs):
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM equip_employee")
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        super().save(*args, **kwargs)

        # Отображение номера уже в нужном формате
    def get_formatted_phone(self):
        if not self.phone_number:
            return ''
        #Удаление символов которые не являются цифрами
        digits = ''.join(filter(str.isdigit, self.phone_number))
        # Форматируется под вид: 8 (000) 00-00-00
        if len(digits) == 11 and digits.startswith('8'):
            return f"8 ({digits[1:4]}) {digits[4:6]}-{digits[6:8]}-{digits[8:10]}"
        elif len(digits) == 10:
            return f"8 ({digits[0:3]}) {digits[3:5]}-{digits[5:7]}-{digits[7:9]}"
        return self.phone_number

    def save(self, *args, **kwargs):
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM equip_employee")
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        #Очищние номера при сохранении
        if self.phone_number:
            digits = ''.join(filter(str.isdigit, self.phone_number))
            if digits.startswith('7') and len(digits) == 11:
                digits = '8' + digits[1:]
            if digits.startswith('9') and len(digits) == 10:
                digits = '8' + digits
            self.phone_number = digits[:11]
        super().save(*args, **kwargs)

# --------------------------------------------------------------
# ЗАЯВКИ-ЗАПЧАСТИ
class RequestSparePart(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    request = models.ForeignKey('RequestFix', on_delete=models.CASCADE, verbose_name="Заявка", related_name='used_spare_parts')
    spare_part = models.ForeignKey('SparePart', on_delete=models.CASCADE, verbose_name="Запчасть")
    quantity = models.IntegerField(default=1, verbose_name="Количество")
    cost_at_repair = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена на момент ремонта")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Общая стоимость", editable=False, null=True, blank=True)
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return f"{self.spare_part.name} x{self.quantity}"

    # Нахождение следующего номера
    def save(self, *args, **kwargs):
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM equip_requestsparepart")
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        if self.quantity and self.cost_at_repair:
            self.total_cost = self.quantity * self.cost_at_repair
        super().save(*args, **kwargs)

# --------------------------------------------------------------
# ЗАЯВКИ-УСЛУГИ
class RequestService(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    request = models.ForeignKey('RequestFix', on_delete=models.CASCADE, verbose_name="Заявка", related_name='used_services')
    service = models.ForeignKey('ThirdPartyService', on_delete=models.CASCADE, verbose_name="Услуга")
    quantity = models.IntegerField(default=1, verbose_name="Количество")
    cost_at_repair = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена на момент ремонта")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Общая стоимость", editable=False, null=True, blank=True)
    receipt_file = models.ForeignKey('File', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Чек (файл)")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return f"{self.service.name} x{self.quantity}"

    # Нахождение следующего номера
    def save(self, *args, **kwargs):
        if not self.id:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM equip_requestservice")
                result = cursor.fetchone()
                self.id = result[0] if result[0] else 1
        if self.quantity and self.cost_at_repair:
            self.total_cost = self.quantity * self.cost_at_repair
        super().save(*args, **kwargs)

# --------------------------------------------------------------
# ЗАЯВКА
class RequestFix(models.Model):
    act_number = models.IntegerField(primary_key=True, verbose_name="Номер акта")
    requester = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="requests_made", verbose_name="Заказчик")
    assigned_technician = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="requests_assigned", verbose_name="Назначенный исполнитель")
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, verbose_name="Оборудование")
    category = models.ForeignKey(RequestCategory, on_delete=models.CASCADE, verbose_name="Категория")
    repair_stage = models.ForeignKey(RepairStage, on_delete=models.CASCADE, verbose_name="Этап ремонта")
    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Приоритет")
    problem_description = models.CharField(max_length=500, verbose_name="Описание неисправности")
    registration_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")
    completion_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата выполнения")
    comment_technician = models.TextField(blank=True, null=True, verbose_name="Комментарий техника")

    spare_parts = models.ManyToManyField(
        SparePart,
        through='RequestSparePart',
        through_fields=('request', 'spare_part'),
        blank=True,
        verbose_name="Запчасти"
    )
    services = models.ManyToManyField(
        ThirdPartyService,
        through='RequestService',
        through_fields=('request', 'service'),
        blank=True,
        verbose_name="Услуги"
    )

    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")
    #Расчет суммы запчастей
    def get_total_spare_parts_cost(self):
        from django.db.models import Sum
        total = self.used_spare_parts.filter(delete_date__isnull=True).aggregate(
            total=Sum('total_cost')
        )['total']
        return total if total else 0
    #Расчет суммы услуг
    def get_total_services_cost(self):
        from django.db.models import Sum
        total = self.used_services.filter(delete_date__isnull=True).aggregate(
            total=Sum('total_cost')
        )['total']
        return total if total else 0
    #Расчет суммы запчастей и услуг
    def get_total_cost(self):
        return self.get_total_spare_parts_cost() + self.get_total_services_cost()

    def __str__(self):
        return f"Заявка №{self.act_number}"