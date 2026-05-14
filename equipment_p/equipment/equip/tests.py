from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import (
    Role, Position, Department, Building, Office, Manufacturer,
    EquipmentModel, EquipmentType, EquipmentStatus, Warranty, Photos,
    Equipment, RequestCategory, RepairStage, Priority, SparePart,
    ThirdPartyService, File, Employee, RequestFix, RequestSparePart, RequestService
)

class SystemTests(TestCase):
    #Создаем все справочники с данными и заполняем
    def setUp(self):
        self.client = Client()
        self.role_tech = Role.objects.create(id=1, role_name='Техник')
        self.role_emp = Role.objects.create(id=2, role_name='Сотрудник')
        self.position = Position.objects.create(id=1, name='Инженер')
        self.department = Department.objects.create(id=1, name='ИТ-отдел')
        self.building = Building.objects.create(id=1, name='Главный корпус')
        self.office = Office.objects.create(id=1, number='101', building_id=1)
        self.manufacturer = Manufacturer.objects.create(id=1, name='HP')
        self.equipment_model = EquipmentModel.objects.create(id=1, name='HP ProDesk', manufacturer_id=1)
        self.equipment_type = EquipmentType.objects.create(id=1, name='Компьютер')
        self.status_ok = EquipmentStatus.objects.create(id=1, name='Исправно')
        self.status_repair = EquipmentStatus.objects.create(id=2, name='В ремонте')
        self.category = RequestCategory.objects.create(id=1, name='Аппаратная неисправность')
        self.stage_new = RepairStage.objects.create(id=1, name='Новая')
        self.stage_done = RepairStage.objects.create(id=2, name='Завершена')
        self.priority_low = Priority.objects.create(id=1, name='Низкий')
        self.priority_high = Priority.objects.create(id=2, name='Высокий')
        #Создание оборудования
        self.equipment = Equipment.objects.create(
            inventory_number=10001,
            assigned_office_id=1,
            model_id=1,
            type_id=1,
            status_id=2,
            configuration='Стандартная',
            purchase_date='2023-01-01'
        )
        #Создание пользователей
        self.technician = Employee.objects.create(
            id=1,
            login='tech@hospital.ru',
            password='password123',
            last_name='Иванов',
            first_name='Иван',
            middle_name='Иванович',
            phone_number='89001234567',
            position_id=1,
            department_id=1,
            role_id=1,
            office_id=1
        )
        self.employee = Employee.objects.create(
            id=2,
            login='emp@hospital.ru',
            password='password123',
            last_name='Петров',
            first_name='Петр',
            middle_name='Петрович',
            phone_number='89007654321',
            position_id=1,
            department_id=1,
            role_id=2,
            office_id=1
        )

    #Тестирование входа в аккаунт как техник
    def test_login_technician(self):
        response = self.client.post(reverse('login_view'), {
            'username': 'tech@hospital.ru',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('show_technician'))
        session = self.client.session
        self.assertEqual(session['user_id'], 1)
        self.assertEqual(session['user_role'], 'Техник')

    #Тестирование навигации техника
    def test_navigation_technician_flow(self):
        self.client.post(reverse('login_view'), {
            'username': 'tech@hospital.ru',
            'password': 'password123'
        })
        #Переход на новые заявки
        response_new = self.client.get(reverse('show_new_requests'))
        self.assertEqual(response_new.status_code, 200)
        self.assertContains(response_new, 'Новые заявки')
        #Переход на оборудование
        response_equip = self.client.get(reverse('show_equipment'))
        self.assertEqual(response_equip.status_code, 200)
        self.assertContains(response_equip, 'Оборудование')
    #Тестирование удаления заявки
    def test_delete_request(self):
        #Создание заявки
        req = RequestFix.objects.create(
            act_number=2024001,
            requester_id=2,
            assigned_technician_id=1,
            equipment_id=10001,
            category_id=1,
            repair_stage_id=2,
            priority_id=1,
            problem_description='Тест удаления',
            completion_date=timezone.now(),
            delete_date=None
        )
        #Удаление полностью со стороны техника
        self.client.post(reverse('login_view'), {
            'username': 'tech@hospital.ru',
            'password': 'password123'
        })
        count_before = RequestFix.objects.count()
        response = self.client.post(reverse('delete_request_technician', args=[2024001]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RequestFix.objects.count(), count_before - 1)
        self.assertFalse(RequestFix.objects.filter(act_number=2024001).exists())

        #Удаление сотрудником (архивирование) заявки
        #Создание заявки
        req2 = RequestFix.objects.create(
            act_number=2024002,
            requester_id=2,
            assigned_technician_id=1,
            equipment_id=10001,
            category_id=1,
            repair_stage_id=2,
            priority_id=1,
            problem_description='Тест удаления',
            completion_date=timezone.now(),
            delete_date=None
        )
        self.client.logout()
        self.client.post(reverse('login_view'), {
            'username': 'emp@hospital.ru',
            'password': 'password123'
        })
        response_soft = self.client.post(reverse('delete_request_customer', args=[2024002]))
        self.assertEqual(response_soft.status_code, 302)
        #Заявка не удалена совсем, но теперь есть дата удаления
        deleted_req = RequestFix.objects.get(act_number=2024002)
        self.assertIsNotNone(deleted_req.delete_date)

    #Тестирование сортировки на странице техника
    def test_sorting_on_technician_page(self):
        self.client.post(reverse('login_view'), {
            'username': 'tech@hospital.ru',
            'password': 'password123'
        })
        #Создание заявки с разными датами
        RequestFix.objects.create(
            act_number=2024010, requester_id=2, assigned_technician_id=1,
            equipment_id=10001, category_id=1, repair_stage_id=1, priority_id=1,
            problem_description='Заявка 1', registration_date='2024-01-01 10:00:00'
        )
        RequestFix.objects.create(
            act_number=2024020, requester_id=2, assigned_technician_id=1,
            equipment_id=10001, category_id=1, repair_stage_id=1, priority_id=1,
            problem_description='Заявка 2', registration_date='2024-01-03 10:00:00'
        )
        #Тестирование по убыванию
        response_desc = self.client.get(reverse('show_technician'), {'sort': '-registration_date'})
        requests_desc = response_desc.context['requests']
        self.assertEqual(requests_desc[0].act_number, 2024020)
        self.assertEqual(requests_desc[1].act_number, 2024010)
        #Тестирование по возрастанию
        response_asc = self.client.get(reverse('show_technician'), {'sort': 'registration_date'})
        requests_asc = response_asc.context['requests']
        self.assertEqual(requests_asc[0].act_number, 2024010)
        self.assertEqual(requests_asc[1].act_number, 2024020)

    #Тестирование поиска и фильтрации статуса у техника
    def test_search_and_status_filter(self):
        self.client.post(reverse('login_view'), {
            'username': 'tech@hospital.ru',
            'password': 'password123'
        })
        #Создание разного оборудования
        equip_ok = Equipment.objects.create(
            inventory_number=10002, assigned_office_id=1, model_id=1, type_id=1,
            status_id=1, configuration='OK'
        )
        equip_bad = Equipment.objects.create(
            inventory_number=10003, assigned_office_id=1, model_id=1, type_id=1,
            status_id=2, configuration='Bad'
        )
        #Поиск по "принтер"
        RequestFix.objects.create(
            act_number=2024030, requester_id=2, assigned_technician_id=1,
            equipment_id=10001, category_id=1, repair_stage_id=1, priority_id=1,
            problem_description='Сломался принтер'
        )
        #Другой текст
        RequestFix.objects.create(
            act_number=2024040, requester_id=2, assigned_technician_id=1,
            equipment_id=10002, category_id=1, repair_stage_id=1, priority_id=1,
            problem_description='Сломался сканер'
        )
        #Заявка со статусом оборудования "В ремонте"
        RequestFix.objects.create(
            act_number=2024050, requester_id=2, assigned_technician_id=1,
            equipment_id=10003, category_id=1, repair_stage_id=1, priority_id=1,
            problem_description='Полная поломка'
        )
        #Тестирование поиска
        response_search = self.client.get(reverse('show_technician'), {'search': 'принтер'})
        self.assertEqual(len(response_search.context['requests']), 1)
        self.assertIn('принтер', response_search.context['requests'][0].problem_description.lower())
        #Тест фильтра по статусу
        response_status = self.client.get(reverse('show_technician'), {'status': '2'})
        self.assertEqual(len(response_status.context['requests']), 2)

    def test_edit_request_and_services(self):
        # Авторизация под техником
        self.client.post(reverse('login_view'), {
            'username': 'tech@hospital.ru',
            'password': 'password123'
        })
        # Создание заявки
        req = RequestFix.objects.create(
            act_number=2024999,
            requester_id=self.employee.id,
            assigned_technician_id=self.technician.id,
            equipment_id=self.equipment.inventory_number,
            category_id=self.category.id,
            repair_stage_id=self.stage_new.id,
            priority_id=self.priority_low.id,
            problem_description='Тест некорректных данных в запчастях или услугах'
        )
        # Создание справочных записей для привязки
        spare = SparePart.objects.create(id=500, name='ТестЗапчасть', quantity=10, cost=100.00)
        service = ThirdPartyService.objects.create(id=500, name='ТестУслуга', cost=200.00)
        # Формируются POST-данные с буквами вместо цифр в количестве и цене
        invalid_data = {
            'problem_description': 'Проверка валидации ввода',
            'assigned_technician': str(self.technician.id),
            'equipment': str(self.equipment.inventory_number),
            'category': str(self.category.id),
            'priority': str(self.priority_low.id),
            'repair_stage': str(self.stage_new.id),
            'status': str(self.status_ok.id),
            'completion_date': '',
            # Некорректные запчасти (буквы в количестве и цене)
            'spare_part_id[]': [str(spare.id)],
            'spare_part_quantity[]': ['abc'],
            'spare_part_price[]': ['xyz'],
            # Некорректные услуги (буквы в количестве и цене)
            'service_id[]': [str(service.id)],
            'service_quantity[]': ['def'],
            'service_price[]': ['uvw'],
        }
        # Отправка запроса на редактирование
        response = self.client.post(reverse('edit_request', args=[req.act_number]), data=invalid_data)
        # Проверка, что view отработал штатно и сделал редирект без ошибок
        self.assertEqual(response.status_code, 302)
        # Проверка, что НЕКОРРЕКТНЫЕ данные НЕ попали в БД.
        self.assertEqual(
            RequestSparePart.objects.filter(request=req).count(), 0,
            "Некорректная запчасть не должна была сохраниться в БД"
        )
        self.assertEqual(
            RequestService.objects.filter(request=req).count(), 0,
            "Некорректная услуга не должна была сохраниться в БД"
        )
        # Проверка, что сама заявка осталась в системе и не была удалена
        req.refresh_from_db()
        self.assertIsNone(req.delete_date, "Заявка не должна была быть удалена")