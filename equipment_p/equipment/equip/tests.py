from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import (
    Role, Position, Department, Building, Office, Manufacturer,
    EquipmentModel, EquipmentType, EquipmentStatus, Warranty, Photos,
    Equipment, RequestCategory, RepairStage, Priority, SparePart,
    ThirdPartyService, File, Employee, RequestFix, RequestSparePart, RequestService
)
# ТЕСТ ВХОДА В СИСТЕМУ
class TestLogin(TestCase):
    def setUp(self):
        self.role = Role.objects.create(id=1, role_name='Техник')
        self.position = Position.objects.create(id=1, name='Инженер')
        self.department = Department.objects.create(id=1, name='ИТ-отдел')
        self.building = Building.objects.create(id=1, name='Главный корпус')
        self.office = Office.objects.create(id=1, number='101', building_id=1)

        self.technician = Employee.objects.create(
            id=1,
            login='tech1@hospital.ru',
            password='password123',
            last_name='Иванов',
            first_name='Иван',
            middle_name='Иванович',
            phone_number='+79001234567',
            position_id=1,
            department_id=1,
            role_id=1,
            office_id=1
        )
        self.client = Client()
#Техник
    def test_login_success(self):
        response = self.client.post(reverse('login_view'), {
            'username': 'tech1@hospital.ru',
            'password': 'password123'
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session['user_id'], 1)
        self.assertEqual(self.client.session['user_role'], 'Техник')
        self.assertRedirects(response, reverse('show_technician'))

#Неверный пароль
    def test_login_wrong_password(self):
        response = self.client.post(reverse('login_view'), {
            'username': 'tech1@hospital.ru',
            'password': 'wrongpassword'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Неверный пароль')
#Несуществующий логин
    def test_login_user_not_found(self):
        response = self.client.post(reverse('login_view'), {
            'username': 'nonexistent@hospital.ru',
            'password': 'password123'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertEqual(str(messages[0]), 'Пользователь с таким логином не найден')


# ТЕСТ НАВИГАЦИИ
class TestNavigation(TestCase):
    def setUp(self):
        self.role = Role.objects.create(id=1, role_name='Техник')
        self.position = Position.objects.create(id=1, name='Инженер')
        self.department = Department.objects.create(id=1, name='ИТ-отдел')
        self.building = Building.objects.create(id=1, name='Главный корпус')
        self.office = Office.objects.create(id=1, number='101', building_id=1)

        self.technician = Employee.objects.create(
            id=1,
            login='tech1@hospital.ru',
            password='password123',
            last_name='Иванов',
            first_name='Иван',
            middle_name='Иванович',
            phone_number='+79001234567',
            position_id=1,
            department_id=1,
            role_id=1,
            office_id=1
        )
        self.client = Client()
        self.client.post(reverse('login_view'), {
            'username': 'tech1@hospital.ru',
            'password': 'password123'
        })
#Оборудование
    def test_navigation_to_equipment(self):
        response = self.client.get(reverse('show_equipment'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Оборудование')
#Статистика
    def test_navigation_to_statistics(self):
        response = self.client.get(reverse('statistics_view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Статистика')
#Авторизация
    def test_navigation_without_login(self):
        """Проверка навигации без авторизации"""
        client = Client()
        response = client.get(reverse('show_technician'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login_view'))


# ТЕСТ УДАЛЕНИЯ ЗАЯВКИ
class TestDeleteRequest(TestCase):
    def setUp(self):
        self.role_tech = Role.objects.create(id=1, role_name='Техник')
        self.role_emp = Role.objects.create(id=2, role_name='Сотрудник')
        self.position = Position.objects.create(id=1, name='Инженер')
        self.department = Department.objects.create(id=1, name='ИТ-отдел')
        self.building = Building.objects.create(id=1, name='Главный корпус')
        self.office = Office.objects.create(id=1, number='101', building_id=1)
        self.manufacturer = Manufacturer.objects.create(id=1, name='HP')
        self.equipment_model = EquipmentModel.objects.create(id=1, name='HP ProDesk', manufacturer_id=1)
        self.equipment_type = EquipmentType.objects.create(id=1, name='Компьютер')
        self.equipment_status = EquipmentStatus.objects.create(id=1, name='Исправно')

        self.equipment = Equipment.objects.create(
            inventory_number=10001,
            assigned_office_id=1,
            model_id=1,
            type_id=1,
            status_id=1,
            configuration='Стандартная',
            purchase_date='2023-01-01'
        )

        self.employee = Employee.objects.create(
            id=1,
            login='emp1@hospital.ru',
            password='password123',
            last_name='Петров',
            first_name='Петр',
            middle_name='Петрович',
            phone_number='+79007654321',
            position_id=1,
            department_id=1,
            role_id=2,
            office_id=1
        )

        self.technician = Employee.objects.create(
            id=2,
            login='tech1@hospital.ru',
            password='password123',
            last_name='Иванов',
            first_name='Иван',
            middle_name='Иванович',
            phone_number='+79001234567',
            position_id=1,
            department_id=1,
            role_id=1,
            office_id=1
        )

        self.stage = RepairStage.objects.create(id=1, name='Новая')
        self.category = RequestCategory.objects.create(id=1, name='Аппаратная неисправность')
        self.priority = Priority.objects.create(id=1, name='Низкий')

        self.request = RequestFix.objects.create(
            act_number=2024001,
            requester_id=1,
            assigned_technician_id=2,
            equipment_id=10001,
            category_id=1,
            repair_stage_id=1,
            priority_id=1,
            problem_description='Тестовая проблема',
            completion_date=timezone.now()
        )

        self.client = Client()
        self.client.post(reverse('login_view'), {
            'username': 'emp1@hospital.ru',
            'password': 'password123'
        })
#Мягкое удаление
    def test_delete_request_success(self):
        self.assertEqual(RequestFix.objects.filter(delete_date__isnull=True).count(), 1)
        response = self.client.post(reverse('delete_request_customer', args=[2024001]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RequestFix.objects.filter(delete_date__isnull=True).count(), 0)
        self.assertEqual(RequestFix.objects.filter(delete_date__isnull=False).count(), 1)

#Удаление невыполненной заявки
    def test_delete_request_not_completed(self):
        request_not_completed = RequestFix.objects.create(
            act_number=2024002,
            requester_id=1,
            assigned_technician_id=2,
            equipment_id=10001,
            category_id=1,
            repair_stage_id=1,
            priority_id=1,
            problem_description='Тестовая проблема 2',
            completion_date=None
        )

        response = self.client.post(reverse('delete_request_customer', args=[2024002]), follow=True)

        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertEqual(str(messages[0]), 'Можно удалить только выполненную заявку')
#Удаление техником
    def test_delete_request_technician(self):
        client = Client()
        client.post(reverse('login_view'), {
            'username': 'tech1@hospital.ru',
            'password': 'password123'
        })

        self.assertEqual(RequestFix.objects.count(), 1)

        response = client.post(reverse('delete_request_technician', args=[2024001]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(RequestFix.objects.count(), 0)


# ТЕСТ СОРТИРОВКИ
class TestSorting(TestCase):
    def setUp(self):
        self.role = Role.objects.create(id=1, role_name='Техник')
        self.position = Position.objects.create(id=1, name='Инженер')
        self.department = Department.objects.create(id=1, name='ИТ-отдел')
        self.building = Building.objects.create(id=1, name='Главный корпус')
        self.office = Office.objects.create(id=1, number='101', building_id=1)

        self.technician = Employee.objects.create(
            id=1,
            login='tech1@hospital.ru',
            password='password123',
            last_name='Иванов',
            first_name='Иван',
            middle_name='Иванович',
            phone_number='+79001234567',
            position_id=1,
            department_id=1,
            role_id=1,
            office_id=1
        )

        self.manufacturer = Manufacturer.objects.create(id=1, name='HP')
        self.equipment_model = EquipmentModel.objects.create(id=1, name='HP ProDesk', manufacturer_id=1)
        self.equipment_type = EquipmentType.objects.create(id=1, name='Компьютер')
        self.equipment_status = EquipmentStatus.objects.create(id=1, name='Исправно')

        self.equipment = Equipment.objects.create(
            inventory_number=10001,
            assigned_office_id=1,
            model_id=1,
            type_id=1,
            status_id=1,
            configuration='Стандартная',
            purchase_date='2023-01-01'
        )

        self.stage = RepairStage.objects.create(id=1, name='Новая')
        self.category = RequestCategory.objects.create(id=1, name='Аппаратная неисправность')
        self.priority = Priority.objects.create(id=1, name='Низкий')

        self.request1 = RequestFix.objects.create(
            act_number=2024001,
            requester_id=1,
            equipment_id=10001,
            category_id=1,
            repair_stage_id=1,
            priority_id=1,
            problem_description='Заявка 1',
            registration_date='2024-01-01 10:00:00'
        )
        self.request2 = RequestFix.objects.create(
            act_number=2024002,
            requester_id=1,
            equipment_id=10001,
            category_id=1,
            repair_stage_id=1,
            priority_id=1,
            problem_description='Заявка 2',
            registration_date='2024-01-02 10:00:00'
        )
        self.request3 = RequestFix.objects.create(
            act_number=2024003,
            requester_id=1,
            equipment_id=10001,
            category_id=1,
            repair_stage_id=1,
            priority_id=1,
            problem_description='Заявка 3',
            registration_date='2024-01-03 10:00:00'
        )

        self.client = Client()
        self.client.post(reverse('login_view'), {
            'username': 'tech1@hospital.ru',
            'password': 'password123'
        })
#Убывание даты
    def test_sort_by_date_desc(self):
        response = self.client.get(reverse('show_technician'), {'sort': '-registration_date'})
        self.assertEqual(response.status_code, 200)

        requests = response.context['requests']
        self.assertEqual(requests[0].act_number, 2024003)
        self.assertEqual(requests[1].act_number, 2024002)
        self.assertEqual(requests[2].act_number, 2024001)
#Возрастение даты
    def test_sort_by_date_asc(self):
        response = self.client.get(reverse('show_technician'), {'sort': 'registration_date'})
        self.assertEqual(response.status_code, 200)

        requests = response.context['requests']
        self.assertEqual(requests[0].act_number, 2024001)
        self.assertEqual(requests[1].act_number, 2024002)
        self.assertEqual(requests[2].act_number, 2024003)
#Сортировка по номеру заказа
    def test_sort_by_act_number(self):
        response = self.client.get(reverse('show_technician'), {'sort': 'act_number'})
        self.assertEqual(response.status_code, 200)

        requests = response.context['requests']
        self.assertEqual(requests[0].act_number, 2024001)
        self.assertEqual(requests[1].act_number, 2024002)
        self.assertEqual(requests[2].act_number, 2024003)

# ТЕСТ ФИЛЬТРАЦИИ
class TestFiltering(TestCase):
    def setUp(self):
        self.role_tech = Role.objects.create(id=1, role_name='Техник')
        self.role_emp = Role.objects.create(id=2, role_name='Сотрудник')
        self.position = Position.objects.create(id=1, name='Инженер')
        self.department = Department.objects.create(id=1, name='ИТ-отдел')
        self.building = Building.objects.create(id=1, name='Главный корпус')
        self.office = Office.objects.create(id=1, number='101', building_id=1)

        self.technician = Employee.objects.create(
            id=1,
            login='tech1@hospital.ru',
            password='password123',
            last_name='Иванов',
            first_name='Иван',
            middle_name='Иванович',
            phone_number='+79001234567',
            position_id=1,
            department_id=1,
            role_id=1,
            office_id=1
        )
        self.manufacturer = Manufacturer.objects.create(id=1, name='HP')
        self.equipment_model = EquipmentModel.objects.create(id=1, name='HP ProDesk', manufacturer_id=1)
        self.equipment_type = EquipmentType.objects.create(id=1, name='Компьютер')
        self.status_ok = EquipmentStatus.objects.create(id=1, name='Исправно')
        self.status_repair = EquipmentStatus.objects.create(id=2, name='В ремонте')

        self.equipment1 = Equipment.objects.create(
            inventory_number=10001,
            assigned_office_id=1,
            model_id=1,
            type_id=1,
            status_id=1,
            configuration='Стандартная',
            purchase_date='2023-01-01'
        )
        self.equipment2 = Equipment.objects.create(
            inventory_number=10002,
            assigned_office_id=1,
            model_id=1,
            type_id=1,
            status_id=2,
            configuration='Стандартная',
            purchase_date='2023-01-01'
        )

        self.stage = RepairStage.objects.create(id=1, name='Новая')
        self.category = RequestCategory.objects.create(id=1, name='Аппаратная неисправность')
        self.priority = Priority.objects.create(id=1, name='Низкий')

        self.request1 = RequestFix.objects.create(
            act_number=2024001,
            requester_id=1,
            equipment_id=10001,
            category_id=1,
            repair_stage_id=1,
            priority_id=1,
            problem_description='Проблема с исправным оборудованием'
        )
        self.request2 = RequestFix.objects.create(
            act_number=2024002,
            requester_id=1,
            equipment_id=10002,
            category_id=1,
            repair_stage_id=1,
            priority_id=1,
            problem_description='Проблема с оборудованием в ремонте'
        )

        self.client = Client()
        self.client.post(reverse('login_view'), {
            'username': 'tech1@hospital.ru',
            'password': 'password123'
        })
#Статус
    def test_filter_by_status(self):
        response = self.client.get(reverse('show_technician'), {'status': '2'})
        self.assertEqual(response.status_code, 200)
        requests = response.context['requests']
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].equipment.status.id, 2)
        self.assertContains(response, 'Проблема с оборудованием в ремонте')
        
#Ремонт
    def test_filter_by_search(self):
        response = self.client.get(reverse('show_technician'), {'search': 'ремонте'})
        self.assertEqual(response.status_code, 200)
        requests = response.context['requests']
        self.assertEqual(len(requests), 1)
        self.assertContains(response, 'Проблема с оборудованием в ремонте')

# Без включенного значения
    def test_filter_no_results(self):
        response = self.client.get(reverse('show_technician'), {'search': 'несуществующий текст'})
        self.assertEqual(response.status_code, 200)
        requests = response.context['requests']
        self.assertEqual(len(requests), 0)