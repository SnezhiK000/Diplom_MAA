from django.contrib import messages
import os
import re
from django.template.loader import render_to_string
import matplotlib
import matplotlib.pyplot as plt
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import (
    Role, Position, Department, Building, Office, Manufacturer,
    EquipmentModel, EquipmentType, EquipmentStatus, Warranty, Photos,
    Equipment, RequestCategory, RepairStage, Priority, SparePart,
    Employee, RequestFix, RequestSparePart, RequestService, ThirdPartyService, File
)
# --------------------------------------------------------------
# ВХОД В СИСТЕМУ
def login_view(request):
    if request.method == 'POST':
        login_input = request.POST.get("username")
        password = request.POST.get("password")
        try: #Поиск пользователя по логину, исключая удаленных
            user = Employee.objects.get(login=login_input, delete_date__isnull=True)
            if user.password == password:
                request.session['user_id'] = user.id
                request.session['user_login'] = user.login
                role_name = user.role.role_name if user.role else 'Сотрудник'
                request.session['user_role'] = role_name
                request.session['user_name'] = f'{user.last_name} {user.first_name} {user.middle_name}'
                request.session['user_position'] = user.position.name if user.position else None
                request.session['form_open'] = False
                user.last_login = timezone.now()
                user.save()
                #Выбор соответствующей роли
                if role_name == 'Администратор':
                    return redirect('show_admin')
                elif role_name == 'Техник':
                    return redirect('show_technician')
                elif role_name == 'Руководитель':
                    return redirect('manager_dashboard')
                else:
                    return redirect('show_customer')
            else:
                messages.error(request, 'Неверный пароль')
        # Обработка ошибок
        except Employee.DoesNotExist:
            messages.error(request, 'Пользователь с таким логином не найден')
        except Exception as e:
            messages.error(request, f'Ошибка при входе: {str(e)}')
    return render(request, 'login.html')

# --------------------------------------------------------------
# ВЫХОД
def logout_view(request):
    try:
        request.session.flush()
        # Обработка ошибок в случае успеха и ошибки
        messages.info(request, "Вы вышли из системы!")
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
    return redirect('login_view')

# --------------------------------------------------------------
# ГЛАВНАЯ СТРАНИЦА | Перенаправление пользователей по ролям
def index(request):
    if 'user_id' in request.session:
        role = request.session.get('user_role')
        if role == 'Администратор':
            return redirect('show_admin')
        elif role == 'Техник':
            return redirect('show_technician')
        elif role == 'Руководитель':
            return redirect('manager_dashboard')
        else:
            return redirect('show_customer')
    return redirect('login_view')

# --------------------------------------------------------------
# ПАНЕЛЬ АДМИНИСТРАТОРА
def show_admin(request):
    #Проверка роли вошедшего сотрудника
    if 'user_id' not in request.session or request.session.get('user_role') != 'Администратор':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        #Получение всех сотрудников
        employees = Employee.objects.filter(delete_date__isnull=True).select_related('role', 'position', 'department', 'office', 'office__building').order_by('last_name')
        #Поиск по логину или ФИО
        search_query = request.GET.get('search', '')
        if search_query:
            employees = employees.filter(
                Q(login__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(middle_name__icontains=search_query)
            )
        #Фильтр по ролям
        role_filter = request.GET.get('role', '')
        if role_filter:
            employees = employees.filter(role_id=role_filter)
        #Получение всех ролей для фильтра
        roles = Role.objects.filter(delete_date__isnull=True)
        #Статистика для Администратора через подсчет по количеству
        total_employees = employees.count()
        total_requests = RequestFix.objects.filter(delete_date__isnull=True).count()
        total_equipment = Equipment.objects.filter(delete_date__isnull=True).count()
        #Передача в html шаблоны
        context = {
            'employees': employees,
            'roles': roles,
            'search_query': search_query,
            'role_filter': role_filter,
            'user_name': request.session.get('user_name', ''),
            'user_role': request.session.get('user_role', ''),
            'total_employees': total_employees,
            'total_requests': total_requests,
            'total_equipment': total_equipment,
        }
        return render(request, 'show_admin.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_admin')

# --------------------------------------------------------------
# СОЗДАНИЕ СОТРУДНИКА (АДМИНИСТРАТОР)
def create_employee_admin(request):
    #Проверка роли вошедшего сотрудника
    if 'user_id' not in request.session or request.session.get('user_role') != 'Администратор':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Получение данных из формы
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        login = request.POST.get('login', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        position_id = request.POST.get('position')
        department_id = request.POST.get('department')
        office_id = request.POST.get('office')
        role_id = request.POST.get('role')
        #Валидация обязательных полей
        if not first_name or not last_name or not login or not password:
            messages.error(request, 'Заполните все обязательные поля')
            return redirect('create_employee_admin')
        #Проверка совпадения паролей
        if password != password_confirm:
            messages.error(request, 'Пароли не совпадают')
            return redirect('create_employee_admin')
        #Проверка логина на повтор
        if Employee.objects.filter(login=login, delete_date__isnull=True).exists():
            messages.error(request, 'Пользователь с таким логином уже существует')
            return redirect('create_employee_admin')
        #Создание нового пользователя учитывая настройки из models (может ли быть пустым)
        try:
            new_user = Employee(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name if middle_name else '',
                login=login,
                phone_number=phone_number if phone_number else '',
                password=password,
                role_id=role_id if role_id else None,
                position_id=position_id if position_id else None,
                department_id=department_id if department_id else None,
                office_id=office_id if office_id else None
            )
            #Сохранение в БД
            new_user.save()
            messages.success(request, f'Сотрудник {last_name} {first_name} создан!')
            return redirect('show_admin')
        #Обработка ошибок
        except Exception as e:
            messages.error(request, f'Ошибка при создании: {str(e)}')
            return redirect('create_employee_admin')
    # Передача в html шаблоны
    context = {
        'positions': Position.objects.filter(delete_date__isnull=True),
        'departments': Department.objects.filter(delete_date__isnull=True),
        'offices': Office.objects.filter(delete_date__isnull=True).select_related('building'),
        'roles': Role.objects.filter(delete_date__isnull=True),
        'user_name': request.session.get('user_name', ''),
    }
    return render(request, 'create_employee_admin.html', context)

# --------------------------------------------------------------
# РЕДАКТИРОВАНИЕ СОТРУДНИКА (АДМИНИСТРАТОР)
def edit_employee_admin(request, employee_id):
    #Проверка роли вошедшего сотрудника
    if 'user_id' not in request.session or request.session.get('user_role') != 'Администратор':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try: #Получение сотрудника среди не удаленных
        employee = get_object_or_404(Employee, id=employee_id, delete_date__isnull=True)
        #Обновление полей сотрудника данными из формы
        if request.method == 'POST':
            employee.first_name = request.POST.get('first_name', '').strip()
            employee.last_name = request.POST.get('last_name', '').strip()
            employee.middle_name = request.POST.get('middle_name', '').strip()
            employee.login = request.POST.get('login', '').strip()
            employee.phone_number = request.POST.get('phone_number', '').strip()
            employee.position_id = request.POST.get('position')
            employee.department_id = request.POST.get('department')
            employee.office_id = request.POST.get('office')
            employee.role_id = request.POST.get('role')
            #Обновление пароля только в случае если поле заполнено
            new_password = request.POST.get('password', '')
            if new_password:
                employee.password = new_password
            #Сохранение в БД
            employee.save()
            messages.success(request, f'Сотрудник {employee.last_name} обновлён!')
            return redirect('show_admin')
        #Передача в html шаблоны
        context = {
            'employee': employee,
            'positions': Position.objects.filter(delete_date__isnull=True),
            'departments': Department.objects.filter(delete_date__isnull=True),
            'offices': Office.objects.filter(delete_date__isnull=True).select_related('building'),
            'roles': Role.objects.filter(delete_date__isnull=True),
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'edit_employee_admin.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_admin')

# --------------------------------------------------------------
# МЯГКОЕ УДАЛЕНИЕ СОТРУДНИКА (АДМИНИСТРАТОР)
def delete_employee_admin(request, employee_id):
    #Проверка роли вошедшего сотрудника
    if 'user_id' not in request.session or request.session.get('user_role') != 'Администратор':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Обработка запроса
    if request.method == 'POST':
        try:#Получение сотрудника
            employee = Employee.objects.get(id=employee_id, delete_date__isnull=True)
            #Администратор не может удалить себя
            if employee.id == request.session['user_id']:
                messages.error(request, 'Нельзя удалить свою учётную запись')
                return redirect('show_admin')
            #Установка текущей даты, как даты удаления
            employee.delete_date = timezone.now()
            #Сохранение изменений
            employee.save()
            messages.success(request, f'Сотрудник {employee.last_name} удалён!')
        #Обработка ошибок
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_admin')

# --------------------------------------------------------------
# УДАЛЕННЫЕ СОТРУДНИКИ (АДМИНИСТРАТОР)
def show_deleted_employees(request):
    #Проверка роли вошедшего сотрудника
    if 'user_id' not in request.session or request.session.get('user_role') != 'Администратор':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:#Получение удаленных сотрудников (если дата удаления пуста)
        employees = Employee.objects.filter(delete_date__isnull=False).select_related('role', 'position', 'department', 'office').order_by('-delete_date')
        #Передача в html шаблоны
        context = {
            'employees': employees,
            'user_name': request.session.get('user_name', ''),
            'page_title': 'Удалённые сотрудники',
        }
        return render(request, 'show_deleted_employees.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_admin')

# --------------------------------------------------------------
# ВОССТАНОВЛЕНИЕ СОТРУДНИКА (АДМИНИСТРАТОР)
def restore_employee(request, employee_id):
    #Проверка роли вошедшего сотрудника
    if 'user_id' not in request.session or request.session.get('user_role') != 'Администратор':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Обработка запроса
    if request.method == 'POST':
        try:#Получение удаленного сотрудника (если есть дата удаления)
            emp = Employee.objects.get(id=employee_id, delete_date__isnull=False)
            #Очистка даты удаления
            emp.delete_date = None
            #Сохранение изменений
            emp.save()
            #Обработка ошибок
            messages.success(request, f'Сотрудник {emp.last_name} {emp.first_name} восстановлен!')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    return redirect('show_deleted_employees')

# --------------------------------------------------------------
# БЕЗВОЗВРАТНОЕ УДАЛЕНИЕ СОТРУДНИКА (АДМИНИСТРАТОР)
def delete_employee_permanent(request, employee_id):
    #Проверка роли вошедшего сотрудника
    if 'user_id' not in request.session or request.session.get('user_role') != 'Администратор':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Обработка запроса
    if request.method == 'POST':
        try:#Получение удаленного сотрудников
            emp = Employee.objects.get(id=employee_id, delete_date__isnull=False)
            #Администратор не может удалить себя
            if emp.id == request.session['user_id']:
                messages.error(request, 'Нельзя удалить свою учётную запись')
                return redirect('show_deleted_employees')
            #Полное удаление записи
            emp.delete()
            #Обработка ошибок
            messages.success(request, f'Сотрудник {emp.last_name} {emp.first_name} удалён навсегда!')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    return redirect('show_deleted_employees')

# --------------------------------------------------------------
# ЗАЯВКИ СОТРУДНИКА (listview) | (ДОСТУПЕН ВСЕМ РОЛЯМ)
class CustomerRequestListView(ListView):
    #Выбор модели, шаблона и имени для переменной в шаблоне со списком
    model = RequestFix
    template_name = 'show_customer.html'
    context_object_name = 'requests'
    #Функция проверки роли вошедшего сотрудника
    def dispatch(self, request, *args, **kwargs):
        #Проверка доступа к странице
        if 'user_id' not in request.session:
            messages.error(request, 'Необходимо авторизоваться')
            return redirect('login_view')
        #Проверка доступа роли к странице
        if request.session.get('user_role') not in ['Сотрудник', 'Администратор','Руководитель','Техник']:
            #Обработка ошибок
            messages.error(request, 'Нет доступа')
            return redirect('login_view')
        return super().dispatch(request, *args, **kwargs)
    #Формирование списка заявок
    def get_queryset(self):
        #Получение активного сотрудника
        one_employee = Employee.objects.get(id=self.request.session['user_id'], delete_date__isnull=True)
        #Получение заявок активного сотрудника, исключая удаленные
        queryset = RequestFix.objects.filter(
            requester=one_employee,
            delete_date__isnull=True
        ).select_related(
            'equipment', 'equipment__model', 'equipment__type',
            'equipment__status', 'equipment__assigned_office',
            'assigned_technician', 'category', 'repair_stage', 'priority'
        )
        #Поиск по проблеме, номеру акта и инвентарному номеру
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(problem_description__icontains=search_query) |
                Q(act_number__icontains=search_query) |
                Q(equipment__inventory_number__icontains=search_query)
            )
        #Фильтрация заявок по статусу
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(equipment__status_id=status_filter)
        #Сортировка заявок по дате регистрации и номеру акта (убывание-возрастание)
        sort_by = self.request.GET.get('sort', '-registration_date')
        if sort_by in ['registration_date', '-registration_date', 'act_number', '-act_number']:
            queryset = queryset.order_by(sort_by)
        return queryset
    #Получение данных для шаблона
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #Добавление данных в контекст
        context['statuses'] = EquipmentStatus.objects.filter(delete_date__isnull=True)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['sort_by'] = self.request.GET.get('sort', '-registration_date')
        context['user_name'] = self.request.session.get('user_name', '')
        context['user_role'] = self.request.session.get('user_role', '')
        return context

# --------------------------------------------------------------
# СОЗДАНИЕ ЗАЯВКИ (СОТРУДНИК) | (ДОСТУПЕН ВСЕМ РОЛЯМ)
def create_request_customer(request):
    #Проверка доступа к странице
    if 'user_id' not in request.session:
        messages.error(request, 'Необходимо авторизоваться')
        return redirect('login_view')
    #Проверка роли вошедшего сотрудника
    if request.session.get('user_role') not in ['Сотрудник', 'Администратор','Руководитель','Техник']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:#Получение активного сотрудника
        one_employee = Employee.objects.get(id=request.session['user_id'], delete_date__isnull=True)
        #Получение списка оборудования, соответствующее кабинету активного сотрудника
        equipment_list = Equipment.objects.filter(assigned_office=one_employee.office,delete_date__isnull=True).select_related('model', 'type', 'status')
        #Сброс флага формы
        if request.method == 'GET':
            request.session['form_open'] = False
        #Обработка запроса на создание заявки
        if request.method == 'POST':
            #Флаг предупреждающий создания дубликата страницы при ее обновлении
            if request.session.get('form_open', False):
                messages.error(request, 'Форма уже открыта. Обновите страницу.')
                return redirect('create_request_customer')
            try: #Установка флага, как отправленной формы
                request.session['form_open'] = True
                #Получение данных из формы: номер, описание, категория и приоритет
                equipment_inv_num = request.POST.get('equipment')
                description = request.POST.get('problem_description', '').strip()
                category_id = request.POST.get('category')
                priority_id = request.POST.get('priority')
                #Валидация обязательных полей
                if not description or not equipment_inv_num:
                    messages.error(request, 'Заполните обязательные поля')
                    request.session['form_open'] = False
                    return redirect('create_request_customer')
                #Получение связанных объектов
                equipment = Equipment.objects.get(inventory_number=equipment_inv_num, delete_date__isnull=True)
                category = RequestCategory.objects.get(id=category_id) if category_id else None
                priority = Priority.objects.get(id=priority_id) if priority_id else None
                #Номер акта генерируется нахождением последней заявки и прибавлением номера
                last_req = RequestFix.objects.filter(delete_date__isnull=True).order_by('-act_number').first()
                new_act_number = (last_req.act_number + 1) if last_req else 1
                #Создание заявки
                req = RequestFix(
                    act_number=new_act_number,
                    problem_description=description,
                    registration_date=timezone.now(),
                    requester=one_employee,
                    equipment=equipment,
                    category=category,
                    priority=priority,
                    repair_stage=RepairStage.objects.first()
                )
                #Сохранение заявки
                req.save()
                #Сброс флага формы
                request.session['form_open'] = False
                messages.success(request, 'Заявка создана!')
                return redirect('show_customer')
            #Обработка ошибки, если она возникла - сброс флага формы
            except Exception as e:
                request.session['form_open'] = False
                messages.error(request, f'Ошибка создания: {str(e)}')
                return redirect('create_request_customer')
        #Передача HTML в шаблон
        context = {
            'employee': one_employee,
            'equipment_list': equipment_list,
            'categories': RequestCategory.objects.filter(delete_date__isnull=True),
            'priorities': Priority.objects.filter(delete_date__isnull=True),
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'create_request_customer.html', context)
    #Обработка ошибки, если она возникла - сброс флага формы
    except Exception as e:
        request.session['form_open'] = False
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_customer')

# --------------------------------------------------------------
# ЗАЯВКИ ТЕХНИКА (ListView) | (ТЕХНИК И АДМИНИСТРАТОР)
class TechnicianRequestListView(ListView):
    #Выбор модели, шаблона и имени для переменной в шаблоне со списком
    model = RequestFix
    template_name = 'show_technician.html'
    context_object_name = 'requests'
    #Функция проверки роли вошедшего сотрудника
    def dispatch(self, request, *args, **kwargs):
        #Проверка доступа к странице
        if 'user_id' not in request.session:
            messages.error(request, 'Необходимо авторизоваться')
            return redirect('login_view')
        #Проверка доступа роли к странице
        if request.session.get('user_role') not in ['Техник', 'Администратор']:
            #Обработка ошибок
            messages.error(request, 'Нет доступа')
            return redirect('login_view')
        return super().dispatch(request, *args, **kwargs)
    #Создание списка заявок с фильтром и поиском
    def get_queryset(self):
        #Получение всех заявок и их данных, без удаленных заявок
        queryset = RequestFix.objects.filter(delete_date__isnull=True).select_related(
            'requester', 'assigned_technician', 'equipment',
            'equipment__model', 'equipment__type', 'equipment__status',
            'category', 'repair_stage', 'priority'
        )
        #Поиск по описанию, номера акта, ФИО заказчика, инвентарному номеру
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(problem_description__icontains=search_query) |
                Q(act_number__icontains=search_query) |
                Q(requester__last_name__icontains=search_query) |
                Q(requester__first_name__icontains=search_query) |
                Q(equipment__inventory_number__icontains=search_query)
            )
        #Фильтр по статусу оборудования
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(equipment__status_id=status_filter)
        #Фильтр по приоритету заявки
        priority_filter = self.request.GET.get('priority', '')
        if priority_filter:
            queryset = queryset.filter(priority_id=priority_filter)
        # Сортировка по дате регистрации (возрастание-убывание), номер акта, фамилии заказчика, статусу оборудования
        sort_by = self.request.GET.get('sort', '-registration_date')
        valid_sorts = ['registration_date', '-registration_date', 'act_number',
                       'requester__last_name', 'equipment__status__name']
        #Действие сортировки если в списке допустимого
        if sort_by in valid_sorts or sort_by.replace('-', '') in valid_sorts:
            queryset = queryset.order_by(sort_by)
        return queryset
    #Получение связанных данных для шаблона
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = EquipmentStatus.objects.filter(delete_date__isnull=True)
        context['priorities'] = Priority.objects.filter(delete_date__isnull=True)  # ← НОВОЕ
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['priority_filter'] = self.request.GET.get('priority', '')  # ← НОВОЕ
        context['sort_by'] = self.request.GET.get('sort', '-registration_date')
        context['user_name'] = self.request.session.get('user_name', '')
        #Счет новых заявок без техника или бех даты выполнения заявки
        context['new_requests_count'] = RequestFix.objects.filter(
            Q(delete_date__isnull=True) &
            (Q(assigned_technician__isnull=True) | Q(completion_date__isnull=True))
        ).count()
        return context

# --------------------------------------------------------------
# НОВЫЕ ЗАЯВКИ (ТЕХНИК И АДМИНИСТРАТОР)
def show_new_requests(request):
    # Проверка доступа к странице
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    # Проверка доступа роли к странице
    if request.session.get('user_role') not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try: #Получение новых заявок без техника или без даты выполнения
        all_new_requests = RequestFix.objects.filter(
            Q(assigned_technician__isnull=True) | Q(completion_date__isnull=True)).select_related(
            'requester', 'assigned_technician', 'equipment', 'equipment__status'
        )
        #Полностью новые заявки без техника и без даты выполнения
        completely_new = all_new_requests.filter(
            assigned_technician__isnull=True,
            completion_date__isnull=True
        )
        #Заявки только с датой выполнения
        needs_technician = all_new_requests.filter(assigned_technician__isnull=True, completion_date__isnull=False)
        #Заявки только с техником
        in_progress = all_new_requests.filter(assigned_technician__isnull=False, completion_date__isnull=True)
        #Счет количества каждой категории заявки
        completely_new_count = completely_new.count()
        needs_technician_count = needs_technician.count()
        in_progress_count = in_progress.count()
        total_new_count = all_new_requests.count()
        #Сортировка по дате создания (возрастание-убывание), номер акта, категории заявки
        sort_by = request.GET.get('sort', '-registration_date')
        if sort_by in ['registration_date', '-registration_date', 'act_number']:
            all_new_requests = all_new_requests.order_by(sort_by)
            completely_new = completely_new.order_by(sort_by)
            needs_technician = needs_technician.order_by(sort_by)
            in_progress = in_progress.order_by(sort_by)
        #Подготовка данных для HTML шаблона
        context = {
            'requests': all_new_requests,
            'completely_new': completely_new,
            'needs_technician': needs_technician,
            'in_progress': in_progress,
            'completely_new_count': completely_new_count,
            'needs_technician_count': needs_technician_count,
            'in_progress_count': in_progress_count,
            'total_new_count': total_new_count,
            'sort_by': sort_by,
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'show_new_requests.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')

# --------------------------------------------------------------
# МОИ ЗАЯВКИ (ТЕХНИК И АДМИНИСТРАТОР)
def my_requests(request):
    # Проверка доступа к странице
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    # Проверка доступа роли к странице
    if request.session.get('user_role') not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try: #Получение активного техника
        current_technician_id = request.session['user_id']
        #Получение заявок закрепленных за этим техником
        requests = RequestFix.objects.filter( delete_date__isnull=True, assigned_technician_id=current_technician_id ).select_related(
            'requester', 'assigned_technician', 'equipment',
            'equipment__model', 'equipment__type', 'equipment__status',
            'category', 'repair_stage', 'priority'
        ).order_by('-registration_date')
        #Фильтрация по приоритету заявки
        priority_filter = request.GET.get('priority', '')
        if priority_filter:
            requests = requests.filter(priority_id=priority_filter)
        #Счет незавершенных заявок техника
        new_requests_count = RequestFix.objects.filter(
            delete_date__isnull=True,
            assigned_technician_id=current_technician_id,
            completion_date__isnull=True
        ).count()
        #Подготовка данных для HTML шаблона
        context = {
            'requests': requests,
            'new_requests_count': new_requests_count,
            'user_name': request.session.get('user_name', ''),
            'page_title': 'Мои заявки',
            'priorities': Priority.objects.filter(delete_date__isnull=True),
            'priority_filter': priority_filter,
        }
        return render(request, 'show_technican_requests.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')

# --------------------------------------------------------------
# СОЗДАНИЕ ЗАЯВКИ ТЕХНИКОМ (ТЕХНИК И АДМИНИСТРАТОР)
def create_request_technician(request):
    #Проверка доступа к странице
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Проверка доступа роли к странице
    if request.session.get('user_role') not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:#Получение данных для формы
        technicians = Employee.objects.filter(delete_date__isnull=True, role__role_name='Техник')
        customers = Employee.objects.filter(delete_date__isnull=True)
        equipment_list = Equipment.objects.filter(delete_date__isnull=True)
        statuses = EquipmentStatus.objects.filter(delete_date__isnull=True)
        categories = RequestCategory.objects.filter(delete_date__isnull=True)
        priorities = Priority.objects.filter(delete_date__isnull=True)
        stages = RepairStage.objects.filter(delete_date__isnull=True)
        #Обработка запроса на создание
        if request.method == 'POST':
            try:#Получение данных с формы
                customer_id = request.POST.get('requester')
                equipment_inv_num = request.POST.get('equipment')
                technician_id = request.POST.get('assigned_technician')
                description = request.POST.get('problem_description', '').strip()
                category_id = request.POST.get('category')
                priority_id = request.POST.get('priority')
                stage_id = request.POST.get('repair_stage')
                status_id = request.POST.get('status')
                date_done_str = request.POST.get('completion_date', '')
                #Проверка обязательных полей
                if not description or not equipment_inv_num or not customer_id:
                    messages.error(request, 'Заполните обязательные поля')
                    return redirect('create_request_technician')
                #Получение связанных данных
                customer = Employee.objects.get(id=customer_id, delete_date__isnull=True)
                equipment = Equipment.objects.get(inventory_number=equipment_inv_num, delete_date__isnull=True)
                assigned_tech = Employee.objects.get(id=technician_id) if technician_id else None
                category = RequestCategory.objects.get(id=category_id) if category_id else None
                priority = Priority.objects.get(id=priority_id) if priority_id else None
                stage = RepairStage.objects.get(id=stage_id) if stage_id else None
                #Обработка даты выполнения
                date_done = None
                if date_done_str:
                    date_done = timezone.make_aware(datetime.strptime(date_done_str, '%Y-%m-%d'))
                #Создание номера акта поиском последнего и прибавлением к нему 1
                last_act = RequestFix.objects.all().order_by('-act_number').first()
                new_act_number = (last_act.act_number + 1) if last_act else 1
                #Создание заявки
                req = RequestFix(
                    act_number=new_act_number,
                    problem_description=description,
                    registration_date=timezone.now(),
                    completion_date=date_done,
                    requester=customer,
                    assigned_technician=assigned_tech,
                    equipment=equipment,
                    category=category,
                    repair_stage=stage,
                    priority=priority
                )
                #Сохранение заявки
                req.save()
                #Если статус выбран - обновляется
                if status_id:
                    equipment.status = EquipmentStatus.objects.get(id=status_id)
                    equipment.save()
                messages.success(request, 'Заявка создана!')
                return redirect('show_technician')
            #Обработка ошибок
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
        #Подготовка данных для HTML шаблона
        context = {
            'technicians': technicians,
            'customers': customers,
            'equipment_list': equipment_list,
            'statuses': statuses,
            'categories': categories,
            'priorities': priorities,
            'stages': stages,
            'now': timezone.now(),
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'create_request_technician.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')

# --------------------------------------------------------------
# РЕДАКТИРОВАНИЕ ЗАЯВКИ (ТЕХНИК И АДМИНИСТРАТОР)
def edit_request(request, request_id):
    #Проверка авторизации пользователя
    if 'user_id' not in request.session:
        messages.error(request, 'Необходимо авторизоваться')
        return redirect('login_view')
    #Получение роли
    user_role = request.session.get('user_role', '')
    #Проверка соответствия роли
    if user_role not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try: #Получение заявки по номеру акта
        req = get_object_or_404(RequestFix, act_number=request_id)
        #Получение справочников для формы
        technicians = Employee.objects.filter(delete_date__isnull=True, role__role_name='Техник')
        statuses = EquipmentStatus.objects.filter(delete_date__isnull=True)
        equipment_list = Equipment.objects.filter(delete_date__isnull=True)
        categories = RequestCategory.objects.filter(delete_date__isnull=True)
        priorities = Priority.objects.filter(delete_date__isnull=True)
        stages = RepairStage.objects.filter(delete_date__isnull=True)
        spare_parts_list = SparePart.objects.filter(delete_date__isnull=True)
        services_list = ThirdPartyService.objects.filter(delete_date__isnull=True)
        #Обработка запроса
        if request.method == 'POST':
            try:
                #Получение данных из формы
                technician_id = request.POST.get('assigned_technician')
                description = request.POST.get('problem_description', '').strip()
                equipment_inv_num = request.POST.get('equipment')
                category_id = request.POST.get('category')
                priority_id = request.POST.get('priority')
                stage_id = request.POST.get('repair_stage')
                status_id = request.POST.get('status')
                date_done_str = request.POST.get('completion_date', '')
                # Проверка обязательных полей
                if not description:
                    messages.error(request, 'Описание проблемы обязательно')
                    return redirect('edit_request', request_id=request_id)
                #Обновление основных полей заявки
                req.problem_description = description
                req.equipment = Equipment.objects.get(inventory_number=equipment_inv_num)
                req.assigned_technician = Employee.objects.get(id=technician_id) if technician_id else None
                #Обновление связанных полей
                if category_id:
                    req.category = RequestCategory.objects.get(id=category_id)
                if priority_id:
                    req.priority = Priority.objects.get(id=priority_id)
                if stage_id:
                    req.repair_stage = RepairStage.objects.get(id=stage_id)
                #Дата выполнения
                if date_done_str:
                    req.completion_date = timezone.make_aware(datetime.strptime(date_done_str, '%Y-%m-%d'))
                else:
                    req.completion_date = None
                #Сохранение
                req.save()
                #Обновление статуса оборудования
                if status_id:
                    req.equipment.status = EquipmentStatus.objects.get(id=status_id)
                    req.equipment.save()
                #Сохранение запчастей, включая цену и количество
                spare_part_ids = request.POST.getlist('spare_part_id[]')
                spare_part_prices = request.POST.getlist('spare_part_price[]')
                spare_part_quantities = request.POST.getlist('spare_part_quantity[]')
                if spare_part_ids:
                    #Удаление старых запчастей
                    req.used_spare_parts.all().delete()
                    #Добавление новых запчастей
                    for i, part_id in enumerate(spare_part_ids):
                        if part_id and spare_part_quantities[i]:
                            try:
                                part = SparePart.objects.get(id=part_id)
                                price = spare_part_prices[i] if spare_part_prices[i] else part.cost
                                quantity = int(spare_part_quantities[i])
                                #Создание запчастей
                                RequestSparePart.objects.create(
                                    request=req,
                                    spare_part=part,
                                    quantity=quantity,
                                    cost_at_repair=price
                                )
                            #Обработка ошибок
                            except Exception as e:
                                messages.warning(request, f'Ошибка сохранения запчасти: {str(e)}')
                #Сохранение услуг включая цену и количество
                service_ids = request.POST.getlist('service_id[]')
                service_prices = request.POST.getlist('service_price[]')
                service_quantities = request.POST.getlist('service_quantity[]')
                service_files = request.FILES.getlist('service_file[]')
                if service_ids:
                    #Удаление старой услуги
                    req.used_services.all().delete()
                    #Добавление новых услуг
                    for i, service_id in enumerate(service_ids):
                        if service_id and service_quantities[i]:
                            try:
                                service = ThirdPartyService.objects.get(id=service_id)
                                price = service_prices[i] if service_prices[i] else service.cost
                                quantity = int(service_quantities[i])
                                #Обработка файла чека
                                receipt_file = None
                                if i < len(service_files) and service_files[i]:
                                    file_obj = File.objects.create(file=service_files[i])
                                    receipt_file = file_obj
                                #Создание услуги
                                RequestService.objects.create(
                                    request=req,
                                    service=service,
                                    quantity=quantity,
                                    cost_at_repair=price,
                                    receipt_file=receipt_file
                                )
                            #Обработка ошибок
                            except Exception as e:
                                messages.warning(request, f'Ошибка сохранения услуги: {str(e)}')
                messages.success(request, f'Заявка №{req.act_number} обновлена!')
                return redirect('show_technician')
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении: {str(e)}')
                return redirect('edit_request', request_id=request_id)
        #Подготовка данных для HTML шаблона
        context = {
            'request_obj': req,
            'technicians': technicians,
            'statuses': statuses,
            'equipment_list': equipment_list,
            'categories': categories,
            'priorities': priorities,
            'stages': stages,
            'spare_parts_list': spare_parts_list,
            'services_list': services_list,
            'user_name': request.session.get('user_name', ''),
            'user_role': user_role,
        }
        return render(request, 'edit_request.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')

# --------------------------------------------------------------
# МЯГКОЕ УДАЛЕНИЕ ЗАЯВКИ (СОТРУДНИК, ТЕХНИК, АДМИНИСТРАТОР)
def delete_request_customer(request, request_id):
    #Проверка авторизации пользователя
    if 'user_id' not in request.session:
        messages.error(request, 'Необходимо авторизоваться')
        return redirect('login_view')
    #Проверка роли активного сотрудника
    if request.session.get('user_role') not in ['Сотрудник', 'Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Обработка запроса
    if request.method == 'POST':
        try: #Получение заявки
            req = RequestFix.objects.get(act_number=request_id)
            #Проверка на возможность удаления пользователем
            if req.requester.id != request.session['user_id']:
                messages.error(request, 'Это не ваша заявка')
                return redirect('show_customer')
            #Проверка выполнена ли заявка
            if not req.completion_date:
                messages.error(request, 'Можно удалить только выполненную заявку')
                return redirect('show_customer')
            #Мягкое удаление помещением даты удаления
            req.delete_date = timezone.now()
            #Сохранение
            req.save()
            messages.success(request, 'Заявка удалена (архивирована)')
        #Обработка обшибок
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_customer')

# --------------------------------------------------------------
# МЯГКО УДАЛЁННЫЕ ЗАЯВКИ (ТЕХНИК И АДМИНИСТРАТОР)
def show_deleted_requests(request):
    #Проверка авторизации пользователя
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Проверка на наличие нужной роли
    if request.session.get('user_role') not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try: #Получение удаленных заявок
        requests = RequestFix.objects.filter(delete_date__isnull=False).select_related(
            'requester', 'assigned_technician', 'equipment',
            'equipment__model', 'equipment__type', 'equipment__status').order_by('-delete_date')
        #Подготовка данных в HTML шаблон
        context = {
            'requests': requests,
            'user_name': request.session.get('user_name', ''),
            'page_title': 'Мягко удалённые заявки',
        }
        return render(request, 'show_deleted_requests.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')

# --------------------------------------------------------------
# ВОССТАНОВЛЕНИЕ ЗАЯВКИ (ТЕХНИК И АДМИНИСТРАТОР)
def restore_request(request, request_id):
    # Проверка авторизации пользователя
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    # Проверка на наличие нужной роли
    if request.session.get('user_role') not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Обработка запроса
    if request.method == 'POST':
        try: #Получение заявки
            req = RequestFix.objects.get(act_number=request_id)
            #Восстановление через очистку даты удаления
            req.delete_date = None
            #Сохранение
            req.save()
            messages.success(request, f'Заявка №{req.act_number} восстановлена!')
        #Обработка ошибок
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    return redirect('show_deleted_requests')

# --------------------------------------------------------------
# БЕЗВОЗВРАТНОЕ УДАЛЕНИЕ (ТЕХНИК И АДМИНИСТРАТОР)
def delete_request_technician(request, request_id):
    # Проверка авторизации пользователя
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    # Проверка на наличие нужной роли
    if request.session.get('user_role') not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    # Обработка запроса
    if request.method == 'POST':
        try: #Получение заявки
            req = RequestFix.objects.get(act_number=request_id)
            #Безвозвратное удаление
            req.delete()
            messages.success(request, 'Заявка полностью удалена')
        #Обработка ошибок
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')

# --------------------------------------------------------------
# ОБОРУДОВАНИЕ (ListView) | (ТЕХНИК, РУКОВОДИТЕЛЬ, АДМИНИСТРАТОР)
class EquipmentListView(ListView):
    #Выбор модели, шаблона и имени для переменной в шаблоне со списком
    model = Equipment
    template_name = 'show_equipment.html'
    context_object_name = 'equipment_list'
    #Проверка доступа
    def dispatch(self, request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.error(request, 'Нет доступа')
            return redirect('login_view')
        user_role = request.session.get('user_role', '')
        if user_role not in ['Техник', 'Руководитель', 'Администратор']:
            messages.error(request, 'Нет доступа')
            return redirect('login_view')
        return super().dispatch(request, *args, **kwargs)
    #Список оборудования с фильтрами
    def get_queryset(self):
        queryset = Equipment.objects.filter(delete_date__isnull=True).select_related(
            'model', 'model__manufacturer', 'type', 'status',
            'assigned_office', 'assigned_office__building', 'warranty', 'photo'
        )
        #Поиск по инвентарному номеру или модели
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(inventory_number__icontains=search_query) |
                Q(model__name__icontains=search_query)
            )
        #Фильтрация по типу
        type_filter = self.request.GET.get('type', '')
        if type_filter:
            queryset = queryset.filter(type_id=type_filter)
        #Фильтрация по статусу
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status_id=status_filter)
        #Сортировка по инвентарному номеру(убывание-возрастание), модели и статусу
        sort_by = self.request.GET.get('sort', 'inventory_number')
        if sort_by in ['inventory_number', '-inventory_number', 'model__name', 'status__name']:
            queryset = queryset.order_by(sort_by)
        return queryset
    #Дополнительные данные для шаблона
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types'] = EquipmentType.objects.filter(delete_date__isnull=True)
        context['statuses'] = EquipmentStatus.objects.filter(delete_date__isnull=True)
        context['search_query'] = self.request.GET.get('search', '')
        context['type_filter'] = self.request.GET.get('type', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['sort_by'] = self.request.GET.get('sort', 'inventory_number')
        context['user_name'] = self.request.session.get('user_name', '')
        context['user_role'] = self.request.session.get('user_role', '')
        context['MEDIA_URL'] = '/media/'
        #Установка текущей даты для сравнении гарантии
        context['today'] = timezone.now().date()
        return context

# --------------------------------------------------------------
# ИСТОРИЯ РЕМОНТОВ ОБОРУДОВАНИЯ (ТЕХНИК, РУКОВОДИТЕЛЬ, АДМИНИСТРАТОР)
def show_equipment_history(request, inventory_number):
    #Проверка авторизации пользователя
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Проверка доступа по роли
    if request.session.get('user_role') not in ['Техник', 'Руководитель', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try: #Получение оборудования
        equipment = get_object_or_404(Equipment.objects.select_related('model', 'type', 'status'),
            inventory_number=inventory_number,
            delete_date__isnull=True
        )
        #Получение всех заявок для текущего оборудования
        repair_history = RequestFix.objects.filter(equipment=equipment,delete_date__isnull=True
        ).select_related('requester', 'assigned_technician').prefetch_related(
            'used_spare_parts', 'used_services').order_by('-registration_date')
        #Подсчет количества
        breakdown_count = repair_history.count()
        #Расчет затрат
        total_cost = 0
        for req in repair_history:
            spare_parts_cost = sum(
                float(item.total_cost or 0) for item in req.used_spare_parts.filter(delete_date__isnull=True))
            services_cost = sum(
                float(item.total_cost or 0) for item in req.used_services.filter(delete_date__isnull=True))
            req.total_cost = spare_parts_cost + services_cost
            total_cost += req.total_cost
        avg_cost = total_cost / breakdown_count if breakdown_count > 0 else 0
        #Подготовка данных для HTML шаблона
        context = {
            'equipment': equipment,
            'repair_history': repair_history,
            'breakdown_count': breakdown_count,
            'total_cost': round(total_cost, 2),
            'avg_cost': round(avg_cost, 2),
            'user_name': request.session.get('user_name', ''),
            'user_role': request.session.get('user_role', ''),
            'can_see_costs': (request.session.get('user_role') in ['Руководитель', 'Администратор']),
        }
        return render(request, 'show_equipment_history.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_equipment')

# --------------------------------------------------------------
# СОЗДАНИЕ НОВОГО ТИПА ОБОРУДОВАНИЯ (РУКОВОДИТЕЛЬ, АДМИНИСТРАТОР)
#Использование JS для мгновенного ответа
@require_POST
def create_equipment_type(request):
    #Проверка авторизации
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    #Проверка роли активного пользователя
    if request.session.get('user_role') not in ['Руководитель', 'Администратор']:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    try: #Получение значения для названия
        name = request.POST.get('name', '').strip()
        #Проверка на обязательное заполнение названия
        if not name:
            return JsonResponse({'error': 'Название обязательно'}, status=400)
        #Проверка на содержание дубликата
        existing = EquipmentType.objects.filter(name__iexact=name, delete_date__isnull=True).first()
        if existing:
            return JsonResponse({'id': existing.id, 'name': existing.name, 'created': False})
        #Создание нового типа
        new_type = EquipmentType(name=name)
        new_type.save()
        return JsonResponse({'id': new_type.id, 'name': new_type.name, 'created': True})
    #Обработка ошибок
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# --------------------------------------------------------------
# СОЗДАНИЕ НОВОЙ МОДЕЛИ ОБОРУДОВАНИЯ (РУКОВОДИТЕЛЬ, АДМИНИСТРАТОР)
#Использование JS для мгновенного ответа
@require_POST
def create_equipment_model(request):
    # Проверка авторизации
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    # Проверка роли активного пользователя
    if request.session.get('user_role') not in ['Руководитель', 'Администратор']:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    try: #Получение названия и производителя
        name = request.POST.get('name', '').strip()
        manufacturer_id = request.POST.get('manufacturer')
        #Проверка на обязательное наличие названия
        if not name:
            return JsonResponse({'error': 'Название обязательно'}, status=400)
        #Проверка на дубликат
        existing = EquipmentModel.objects.filter(name__iexact=name, delete_date__isnull=True).first()
        if existing:
            return JsonResponse({'id': existing.id, 'name': existing.name, 'created': False})
        #Создание новой модели
        new_model = EquipmentModel(name=name)
        if manufacturer_id:
            new_model.manufacturer_id = manufacturer_id
        new_model.save()
        return JsonResponse({'id': new_model.id, 'name': new_model.name, 'created': True})
    #Обработка ошибки
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# --------------------------------------------------------------
# СОЗДАНИЕ НОВОГО ПРОИЗВОДИТЕЛЯ (РУКОВОДИТЕЛЬ, АДМИНИСТРАТОР)
#Использование JS для мгновенного ответа
@require_POST
def create_manufacturer(request):
    #Проверка авторизации
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    #Проверка роли активного пользователя
    if request.session.get('user_role') not in ['Руководитель', 'Администратор']:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    try: #Получение названия
        name = request.POST.get('name', '').strip()
        #Проверка на обязательное наличие наименования
        if not name:
            return JsonResponse({'error': 'Название обязательно'}, status=400)
        #Проверка на наличие дубликата
        existing = Manufacturer.objects.filter(name__iexact=name, delete_date__isnull=True).first()
        if existing:
            return JsonResponse({'id': existing.id, 'name': existing.name, 'created': False})
        #Создание нового производителя
        new_manufacturer = Manufacturer(name=name)
        new_manufacturer.save()
        return JsonResponse({
            'id': new_manufacturer.id,
            'name': new_manufacturer.name,
            'created': True
        })
    #Обработка ошибок
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# --------------------------------------------------------------
# СОЗДАНИЕ НОВОГО КАБИНЕТА (РУКОВОДИТЕЛЬ, АДМИНИСТРАТОР)
#Использование JS для мгновенного ответа
@require_POST
def create_office(request):
    #Проверка авторизации
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    #Проверка роли активного пользователя
    if request.session.get('user_role') not in ['Руководитель', 'Администратор']:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    try: #Получение номера и комплектации
        number = request.POST.get('number', '').strip()
        building_id = request.POST.get('building')
        if not number:
            number = None
        #Проверка на дубликат
        if number:
            existing = Office.objects.filter(number=number, delete_date__isnull=True).first()
            if existing:
                return JsonResponse({'id': existing.id, 'number': existing.number, 'created': False})
        #Создание нового кабинета
        new_office = Office(number=number)
        if building_id:
            new_office.building_id = building_id
        new_office.save()
        return JsonResponse({'id': new_office.id, 'number': new_office.number or 'Не распределён', 'created': True})
    #Обработка ошибок
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# --------------------------------------------------------------
# СОЗДАНИЕ НОВОЙ ГАРАНТИИ (ТЕХНИК, РУКОВОДИТЕЛЬ, АДМИНИСТРАТОР)
#Использование JS для мгновенного ответа
@require_POST
def create_warranty(request):
    #Проверка авторизации
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    #Проверка на текущую роль
    if request.session.get('user_role') not in ['Техник', 'Руководитель', 'Администратор']:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    try: #Получение начала и конца даты
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        #Проверка на наличие хотя-бы одной даты
        if not start_date and not end_date:
            return JsonResponse({'id': None, 'created': False})
        #Создание новой гарантии
        new_warranty = Warranty()
        if start_date:
            new_warranty.start_date = start_date
        if end_date:
            new_warranty.end_date = end_date
        new_warranty.save()
        return JsonResponse({
            'id': new_warranty.id,
            'end_date': str(new_warranty.end_date) if new_warranty.end_date else 'Без срока',
            'created': True
        })
    #Обработка ошибок
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# --------------------------------------------------------------
# ДОБАВЛЕНИЕ ОБОРУДОВАНИЯ (ТЕХНИК, АДМИНИСТРАТОР)
def create_equipment(request):
    #Проверка авторизации
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Проверка роли
    if request.session.get('user_role') not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try: #Нахождение максимального значения инвентарного номера, автоматический расчет +1
        max_equipment = Equipment.objects.all().order_by('-inventory_number').first()
        next_inventory_number = (max_equipment.inventory_number + 1) if max_equipment else 10001
        #Обработка запроса
        if request.method == 'POST':
            #Выбор действия
            action = request.POST.get('action', '')
            #Создание гарантии
            if action == 'create_warranty':
                new_start_date = request.POST.get('new_warranty_start')
                new_end_date = request.POST.get('new_warranty_end')
                if new_start_date or new_end_date:
                    new_warranty = Warranty()
                    if new_start_date:
                        new_warranty.start_date = new_start_date
                    if new_end_date:
                        new_warranty.end_date = new_end_date
                    new_warranty.save()
                    messages.success(request, 'Гарантия создана!')
                return redirect('create_equipment?show_new_warranty=1')
            #Создание нового типа (Администратор)
            elif action == 'create_type':
                if request.session.get('user_role') not in ['Администратор']:
                    messages.error(request, 'Нет прав')
                    return redirect('create_equipment')
                new_type_name = request.POST.get('new_type_name', '').strip()
                if new_type_name:
                    new_type = EquipmentType(name=new_type_name)
                    new_type.save()
                    messages.success(request, f'Тип "{new_type_name}" создан!')
                return redirect('create_equipment?show_new_type=1')
            #Создание новой модели (Администратор)
            elif action == 'create_model':
                if request.session.get('user_role') not in ['Администратор']:
                    messages.error(request, 'Нет прав')
                    return redirect('create_equipment')
                new_model_name = request.POST.get('new_model_name', '').strip()
                new_manufacturer_id = request.POST.get('new_model_manufacturer')
                if new_model_name:
                    new_model = EquipmentModel(name=new_model_name)
                    if new_manufacturer_id:
                        new_model.manufacturer_id = new_manufacturer_id
                    new_model.save()
                    messages.success(request, f'Модель "{new_model_name}" создана!')
                return redirect('create_equipment?show_new_model=1')
            #Создание нового кабинета (Администратор)
            elif action == 'create_office':
                if request.session.get('user_role') not in ['Администратор']:
                    messages.error(request, 'Нет прав')
                    return redirect('create_equipment')
                new_office_number = request.POST.get('new_office_number', '').strip()
                new_building_id = request.POST.get('new_office_building')
                if new_building_id:
                    new_office = Office(number=new_office_number if new_office_number else None)
                    new_office.building_id = new_building_id
                    new_office.save()
                    messages.success(request, 'Кабинет создан!')
                return redirect('create_equipment?show_new_office=1')
            #Создание нового оборудования
            elif action == 'create_equipment':
                inventory_number = request.POST.get('inventory_number')
                model_id = request.POST.get('model')
                type_id = request.POST.get('type')
                status_id = request.POST.get('status')
                configuration = request.POST.get('configuration', '')
                purchase_date = request.POST.get('purchase_date') or None
                assigned_office_id = request.POST.get('assigned_office') or None
                warranty_id = request.POST.get('warranty') or None
                #Проверка на существующий инвентарный номер
                if Equipment.objects.filter(inventory_number=inventory_number, delete_date__isnull=True).exists():
                    messages.error(request, f'Оборудование с инвентарным номером {inventory_number} уже существует!')
                    return redirect('create_equipment')
                #Обработка загрузки фото
                photo_file = request.FILES.get('photo')
                photo = None
                #Проверка загружено ли фото
                if photo_file:
                    #Получение расширение файла через разделение
                    ext = os.path.splitext(photo_file.name)[1]
                    #Генерация идентификатора в виде текущего времени
                    unique_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    #Создание имени
                    filename = f"equipment_{inventory_number}_{unique_id}{ext}"
                    #Относительный путь сохранения
                    file_path = os.path.join('equipment', filename)
                    #Абсолютный путь сохранения
                    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
                    #Создание директории для сохранения если ее еще нет
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    #Открытие файла для записи в бинарном виде
                    with open(full_path, 'wb+') as destination:
                        for chunk in photo_file.chunks():
                            destination.write(chunk)
                    #Создание записи в базе данных
                    photo = Photos.objects.create(name=filename)
                #Создание оборудования
                equipment = Equipment(
                    inventory_number=inventory_number,
                    model_id=model_id,
                    type_id=type_id,
                    status_id=status_id,
                    configuration=configuration or '',
                    purchase_date=purchase_date,
                    assigned_office_id=assigned_office_id,
                    warranty_id=warranty_id,
                    photo=photo
                )
                equipment.save()
                messages.success(request, f'Оборудование #{inventory_number} создано!')
                return redirect('show_equipment')
            else:
                messages.error(request, 'Неизвестное действие')
                return redirect('create_equipment')
        #Подготовка данных к HTML шаблону
        context = {
            'models': EquipmentModel.objects.filter(delete_date__isnull=True),
            'types': EquipmentType.objects.filter(delete_date__isnull=True),
            'statuses': EquipmentStatus.objects.filter(delete_date__isnull=True),
            'offices': Office.objects.filter(delete_date__isnull=True),
            'buildings': Building.objects.filter(delete_date__isnull=True),
            'warranties': Warranty.objects.filter(delete_date__isnull=True),
            'manufacturers': Manufacturer.objects.filter(delete_date__isnull=True),
            'next_inventory_number': next_inventory_number,
            'user_name': request.session.get('user_name', ''),
            'user_role': request.session.get('user_role', ''),
            'show_new_type': request.GET.get('show_new_type') == '1',
            'show_new_model': request.GET.get('show_new_model') == '1',
            'show_new_office': request.GET.get('show_new_office') == '1',
            'show_new_warranty': request.GET.get('show_new_warranty') == '1',
        }
        return render(request, 'create_equipment.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_equipment')

# --------------------------------------------------------------
# РЕДАКТИРОВАНИЕ ОБОРУДОВАНИЯ (ТЕХНИК, АДМИНИСТРАТОР)
def edit_equipment(request, inventory_number):
    #Проверка авторизации
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Проверка роли
    if request.session.get('user_role') not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try: #Получение оборудования
        equipment = get_object_or_404(Equipment, inventory_number=inventory_number, delete_date__isnull=True)
        #Обработка запроса
        if request.method == 'POST':
            try: #Получение данных
                equipment.model_id = request.POST.get('model')
                equipment.type_id = request.POST.get('type')
                equipment.status_id = request.POST.get('status')
                equipment.configuration = request.POST.get('configuration', '')
                equipment.assigned_office_id = request.POST.get('assigned_office')
                #Обработка загрузки фото аналогично созданию фото
                photo_file = request.FILES.get('photo')
                if photo_file:
                    ext = os.path.splitext(photo_file.name)[1]
                    unique_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"equipment_{equipment.inventory_number}_{unique_id}{ext}"
                    file_path = os.path.join('equipment', filename)
                    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, 'wb+') as destination:
                        for chunk in photo_file.chunks():
                            destination.write(chunk)
                    photo = Photos.objects.create(name=filename)
                    if equipment.photo and equipment.photo.id != photo.id:
                        equipment.photo.delete_date = timezone.now()
                        equipment.photo.save()
                    equipment.photo = photo
                equipment.save()
                messages.success(request, 'Оборудование обновлено!')
                return redirect('show_equipment')
            #Обработка ошибок
            except Exception as e:
                messages.error(request, f'Ошибка при обновлении: {str(e)}')
        #Подготовка данных к HTML шаблону
        context = {
            'equipment': equipment,
            'models': EquipmentModel.objects.filter(delete_date__isnull=True),
            'types': EquipmentType.objects.filter(delete_date__isnull=True),
            'statuses': EquipmentStatus.objects.filter(delete_date__isnull=True),
            'offices': Office.objects.filter(delete_date__isnull=True),
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'edit_equipment.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_equipment')

# --------------------------------------------------------------
# МЯГКОЕ УДАЛЕНИЕ ОБОРУДОВАНИЯ (ТЕХНИК, АДМИНИСТРАТОР)
def delete_equipment(request, inventory_number):
    #Проверка авторизации
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Проверка роли
    user_role = request.session.get('user_role', '')
    if user_role not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Обработка запроса
    if request.method == 'POST':
        try: #Получение оборудования
            equipment = Equipment.objects.get(inventory_number=inventory_number, delete_date__isnull=True)
            #Удаление администратором навсегда
            if user_role == 'Администратор':
                #Проверка на наличие нужного параметра для удаления
                permanent = request.POST.get('permanent', 'false')
                if permanent == 'true':
                    #Безвозвратное удаление
                    equipment.delete()
                    messages.success(request, f'Оборудование #{inventory_number} удалено навсегда!')
                    return redirect('show_deleted_equipment')
            #Мягкое удаление через постановку текущей даты как даты удаления
            equipment.delete_date = timezone.now()
            equipment.save()
            messages.success(request, f'Оборудование #{inventory_number} удалено (архивировано)!')
        #Обработка ошибок
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_equipment')
    return redirect('show_equipment')

# --------------------------------------------------------------
# УДАЛЁННОЕ ОБОРУДОВАНИЕ (ТЕХНИК, АДМИНИСТРАТОР)
def show_deleted_equipment(request):
    #Проверка авторизации
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Проверка роли
    user_role = request.session.get('user_role', '')
    if user_role not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:#Получение удаленного оборудования
        equipment_list = Equipment.objects.filter(delete_date__isnull=False).select_related(
            'model', 'model__manufacturer', 'type', 'status',
            'assigned_office', 'assigned_office__building', 'warranty', 'photo'
        ).order_by('-delete_date')
        #Подготовка данных к HTML формы
        context = {
            'equipment_list': equipment_list,
            'user_name': request.session.get('user_name', ''),
            'user_role': user_role,
            'page_title': 'Удалённое оборудование',
        }
        return render(request, 'show_deleted_equipment.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_equipment')

# --------------------------------------------------------------
# ВОССТАНОВЛЕНИЕ ОБОРУДОВАНИЯ (ТЕХНИК, АДМИНИСТРАТОР)
def restore_equipment(request, inventory_number):
    #Проверка авторизации
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Получение роли пользователя
    user_role = request.session.get('user_role', '')
    #Проверка роли
    if user_role not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Обработка запроса
    if request.method == 'POST':
        try: #Получение оборудования
            equipment = Equipment.objects.get(inventory_number=inventory_number, delete_date__isnull=False)
            #Очистка даты удаления
            equipment.delete_date = None
            equipment.save()
            messages.success(request, f'Оборудование #{inventory_number} восстановлено!')
        #Обработка ошибок
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    return redirect('show_deleted_equipment')

# --------------------------------------------------------------
# ПОЛНОЕ УДАЛЕНИЕ ОБОРУДОВАНИЯ (АДМИНИСТРАТОР)
def delete_equipment_permanent(request, inventory_number):
    # Проверка авторизации
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    # Получение роли пользователя
    user_role = request.session.get('user_role', '')
    # Проверка роли
    if user_role not in [ 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Обработка запроса
    if request.method == 'POST':
        try:#Получение удаленного оборудования
            equipment = Equipment.objects.get(inventory_number=inventory_number, delete_date__isnull=False)
            #Безвозвратное удаление
            equipment.delete()
            messages.success(request, f'Оборудование #{inventory_number} удалено навсегда!')
        #Обработка ошибок
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    return redirect('show_deleted_equipment')

# --------------------------------------------------------------
# ЗАТРАТЫ НА ОБОРУДОВАНИЕ (ТЕХНИК, РУКОВОДИТЕЛЬ, АДМИНИСТРАТОР)
def equipment_costs(request):
    #Проверка авторизации
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Проверка роли
    if request.session.get('user_role') not in ['Техник', 'Руководитель', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try: #Получение оборудования
        equipment_id = request.GET.get('equipment_id')
        equipment = None
        #При наличии номера - фильтруется
        if equipment_id:
            equipment = get_object_or_404(Equipment, inventory_number=int(equipment_id), delete_date__isnull=True)
            requests = RequestFix.objects.filter(equipment=equipment, delete_date__isnull=True).prefetch_related(
                'used_spare_parts', 'used_services'
            )
        else:
            requests = RequestFix.objects.filter(delete_date__isnull=True).prefetch_related(
                'used_spare_parts', 'used_services'
            )
        #Фильтрация по датам
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        if date_from:
            requests = requests.filter(registration_date__gte=date_from)
        if date_to:
            requests = requests.filter(registration_date__lte=date_to)
        #Расчет затрат
        total_cost = 0
        for req in requests:
            spare_parts_cost = sum(item.total_cost for item in req.used_spare_parts.filter(delete_date__isnull=True))
            services_cost = sum(item.total_cost for item in req.used_services.filter(delete_date__isnull=True))
            req.total_cost = spare_parts_cost + services_cost
            req.spare_parts_cost = spare_parts_cost
            req.services_cost = services_cost
            total_cost += req.total_cost
        avg_cost = total_cost / requests.count() if requests.count() > 0 else 0
        #Подготовка данных к HTML форме
        context = {
            'equipment': equipment,
            'requests': requests,
            'total_cost': total_cost,
            'avg_cost': round(avg_cost, 2),
            'date_from': date_from,
            'date_to': date_to,
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'equipment_costs.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_equipment')

# -------------------------------------------------------------
# СТРАНИЦА РУКОВОДИТЕЛЯ (РУКОВОДИТЕЛЬ, АДМИНИСТРАТОР)
def manager_dashboard(request):
    #Проверка авторизации
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Проверка роли
    if request.session.get('user_role') not in ['Руководитель', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try: #Общая статистика
        total_requests = RequestFix.objects.filter(delete_date__isnull=True).count()
        completed_requests = RequestFix.objects.filter(
            delete_date__isnull=True,
            completion_date__isnull=False
        ).count()
        pending_requests = total_requests - completed_requests
        #Генерация графика при помощи библиотеки MATPLOTLIB
        matplotlib.use('Agg')
        # Создание папки для графиков
        charts_folder = os.path.join(settings.MEDIA_ROOT, 'charts')
        os.makedirs(charts_folder, exist_ok=True)
        # Данные для графика
        labels = ['Всего заявок', 'Выполнено', 'В работе']
        values = [total_requests, completed_requests, pending_requests]
        colors = ['#EB5A61', '#ab47bc', '#ff6f00']
        # Создание графика
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(labels, values, color=colors, edgecolor='black', linewidth=1.5)
        # Добавление значений на столбцы
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=12, fontweight='bold')
        ax.set_title('Статистика заявок', fontsize=14, fontweight='bold', pad=20)
        ax.set_ylabel('Количество', fontsize=12)
        ax.set_ylim(0, max(values) * 1.2 if max(values) > 0 else 10)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        #Сохранение графика
        chart_filename = f'manager_stats_{timezone.now().strftime("%Y%m%d_%H%M%S")}.png'
        chart_path = os.path.join(charts_folder, chart_filename)
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        #Частые поломки
        equipment_stats = RequestFix.objects.filter(
            delete_date__isnull=True
        ).values(
            'equipment__inventory_number',
            'equipment__model__name',
            'equipment__type__name'
        ).annotate(
            breakdown_count=Count('act_number')
        ).order_by('-breakdown_count')[:5]
        #По месяцам
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_stats = RequestFix.objects.filter(
            delete_date__isnull=True,
            registration_date__gte=six_months_ago
        ).extra(
            select={'month': "TO_CHAR(registration_date, 'YYYY-MM')"}
        ).values('month').annotate(
            count=Count('act_number')
        ).order_by('month')
        #Затраты
        all_requests = RequestFix.objects.filter(delete_date__isnull=True).prefetch_related(
            'used_spare_parts', 'used_services', 'equipment__type'
        )
        total_cost = 0
        monthly_costs = {}
        type_costs = {}
        for req in all_requests:
            spare_parts_cost = sum(
                float(item.total_cost or 0) for item in req.used_spare_parts.filter(delete_date__isnull=True))
            services_cost = sum(
                float(item.total_cost or 0) for item in req.used_services.filter(delete_date__isnull=True))
            req_cost = spare_parts_cost + services_cost
            total_cost += req_cost
            month = req.registration_date.strftime('%Y-%m')
            monthly_costs[month] = monthly_costs.get(month, 0) + req_cost
            equip_type = req.equipment.type.name if req.equipment.type else 'Без типа'
            type_costs[equip_type] = type_costs.get(equip_type, 0) + req_cost
        monthly_labels = list(monthly_costs.keys())[-6:]
        monthly_data = [round(monthly_costs[m], 2) for m in monthly_labels]
        type_costs_list = [(type_name, round(cost, 2)) for type_name, cost in type_costs.items()]
        context = {
            'total_requests': total_requests,
            'completed_requests': completed_requests,
            'pending_requests': pending_requests,
            'equipment_stats': list(equipment_stats),
            'monthly_stats': list(monthly_stats),
            'total_cost': round(total_cost, 2),
            'monthly_labels': monthly_labels,
            'monthly_data': monthly_data,
            'type_costs_list': type_costs_list,
            'user_name': request.session.get('user_name', ''),
            'chart_filename': chart_filename,
        }
        return render(request, 'manager_dashboard.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('login_view')

# --------------------------------------------------------------
# ЗАТРАТЫ ПО ОБОРУДОВАНИЮ (РУКОВОДИТЕЛЬ, АДМИНИСТРАТОР)
def manager_equipment_costs(request):
    #Проверка авторизации
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    #Проверка рооли
    if request.session.get('user_role') not in ['Руководитель', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try: #Получение оборудования
        equipment_id = request.GET.get('equipment_id')
        equipment = None
        if equipment_id: #Если указан нномер - фильтрация по нему
            equipment = get_object_or_404(Equipment, inventory_number=int(equipment_id), delete_date__isnull=True)
            requests = RequestFix.objects.filter(equipment=equipment, delete_date__isnull=True).prefetch_related(
                'used_spare_parts', 'used_services'
            )
        else:
            requests = RequestFix.objects.filter(delete_date__isnull=True).prefetch_related(
                'used_spare_parts', 'used_services'
            )
        #Фильтр по датам
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        if date_from:
            requests = requests.filter(registration_date__gte=date_from)
        if date_to:
            requests = requests.filter(registration_date__lte=date_to)
        #Расчет затрат
        total_cost = 0
        for req in requests:
            spare_parts_cost = sum(
                item.total_cost or 0 for item in req.used_spare_parts.filter(delete_date__isnull=True))
            services_cost = sum(item.total_cost or 0 for item in req.used_services.filter(delete_date__isnull=True))
            req.total_cost = spare_parts_cost + services_cost
            total_cost += req.total_cost
        avg_cost = total_cost / requests.count() if requests.count() > 0 else 0
        #Подготовка данных к HTML форме
        context = {
            'equipment': equipment,
            'requests': requests,
            'total_cost': total_cost,
            'avg_cost': round(avg_cost, 2),
            'date_from': date_from,
            'date_to': date_to,
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'manager_equipment_costs.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('manager_dashboard')

# --------------------------------------------------------------
# РЕГИСТРАЦИЯ НОВОГО ПОЛЬЗОВАТЕЛЯ
def registration_view(request):
    #Обработка запроса
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        login = request.POST.get('login', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        position_id = request.POST.get('position')
        department_id = request.POST.get('department')
        office_id = request.POST.get('office')
        #Обработка обязательных полей
        if not first_name or not last_name or not login or not password:
            messages.error(request, 'Заполните все обязательные поля (Имя, Фамилия, Логин, Пароль)')
            return redirect('registration_view')
        #Проверка совпадения паролей
        if password != password_confirm:
            messages.error(request, 'Пароли не совпадают')
            return redirect('registration_view')
        #Проверка на дубликат логина
        if Employee.objects.filter(login=login, delete_date__isnull=True).exists():
            messages.error(request, 'Пользователь с таким логином уже существует')
            return redirect('registration_view')
        try: #Получение или создание роли Сотрудник автоматически
            employee_role, created = Role.objects.get_or_create(
                role_name='Сотрудник',
                defaults={'role_name': 'Сотрудник'}
            )
            #Создание нового пользователя
            new_user = Employee(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name if middle_name else '',
                login=login,
                phone_number=phone_number if phone_number else '',
                password=password,
                role=employee_role,
                position_id=position_id if position_id else None,
                department_id=department_id if department_id else None,
                office_id=office_id if office_id else None
            )
            #Сохранение
            new_user.save()
            messages.success(request, f'Регистрация успешна! Добро пожаловать, {first_name} {last_name}!')
            #Автоматический вход в систему по введенным данным
            request.session['user_id'] = new_user.id
            request.session['user_login'] = new_user.login
            request.session['user_role'] = 'Сотрудник'
            request.session['user_name'] = f'{last_name} {first_name} {middle_name}'.strip()
            request.session['form_open'] = False
            return redirect('show_customer')
        #Обработка ошибок
        except Exception as e:
            messages.error(request, f'Ошибка при регистрации: {str(e)}')
            return redirect('registration_view')
    #Подготовка данных к HTML форме
    context = {
        'positions': Position.objects.filter(delete_date__isnull=True),
        'departments': Department.objects.filter(delete_date__isnull=True),
        'offices': Office.objects.filter(
            delete_date__isnull=True
        ).select_related('building').order_by('building__name', 'number'),
    }
    return render(request, 'registration.html', context)

# --------------------------------------------------------------
# МОЙ ПРОФИЛЬ (ДОСТУПЕН ВСЕМ РОЛЯМ)
def show_my_profile(request):
    #Проверка авторизации
    if 'user_id' not in request.session:
        messages.error(request, 'Необходимо авторизоваться')
        return redirect('login_view')
    try: #Получение данных активного пользователя
        user_id = request.session['user_id']
        user_role = request.session.get('user_role', '')
        employee = get_object_or_404(Employee, id=user_id, delete_date__isnull=True)
        #Обработка запроса
        if request.method == 'POST':
            #Редактирование всех полей Администратором
            if user_role == 'Администратор':
                employee.first_name = request.POST.get('first_name', '').strip()
                employee.last_name = request.POST.get('last_name', '').strip()
                employee.middle_name = request.POST.get('middle_name', '').strip()
                employee.login = request.POST.get('login', '').strip()
                employee.phone_number = request.POST.get('phone_number', '').strip()
                employee.position_id = request.POST.get('position')
                employee.department_id = request.POST.get('department')
                employee.office_id = request.POST.get('office')
                # Проверка дубликата логина
                if Employee.objects.filter(login=employee.login).exclude(id=employee.id).exists():
                    messages.error(request, 'Такой логин уже занят!')
                    return redirect('show_my_profile')
            #Редактирование полей для остальных ролей
            else:
                employee.first_name = request.POST.get('first_name', '').strip()
                employee.last_name = request.POST.get('last_name', '').strip()
                employee.middle_name = request.POST.get('middle_name', '').strip()
                employee.login = request.POST.get('login', '').strip()
                employee.phone_number = request.POST.get('phone_number', '').strip()
                # Проверка дубликата логина
                if Employee.objects.filter(login=employee.login).exclude(id=employee.id).exists():
                    messages.error(request, 'Такой логин уже занят!')
                    return redirect('show_my_profile')
            # Обновление пароля если он заполнен
            new_password = request.POST.get('password', '')
            if new_password:
                employee.password = new_password
            #Сохранение
            employee.save()
            messages.success(request, 'Профиль обновлён!')
            #Обновление имени в сессии
            request.session['user_name'] = f'{employee.last_name} {employee.first_name} {employee.middle_name}'.strip()
            return redirect('show_my_profile')
        #Подготовка данных к HTML форме
        context = {
            'employee': employee,
            'user_role': user_role,
            'positions': Position.objects.filter(delete_date__isnull=True),
            'departments': Department.objects.filter(delete_date__isnull=True),
            'offices': Office.objects.filter(delete_date__isnull=True).select_related('building'),
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'show_my_profile.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('login_view')

# --------------------------------------------------------------
# ПЕЧАТЬ НОВОЙ ЗАЯВКИ (ТЕХНИК, АДМИНИСТРАТОР)
def print_new_request(request, request_id):
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    user_role = request.session.get('user_role', '')
    if user_role not in ['Техник', 'Администратор',]:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        req = get_object_or_404(RequestFix, act_number=request_id)
        #Проверяем есть ли уже созданный файл печати по дате и номеру
        forms_folder = os.path.join(settings.MEDIA_ROOT, 'request_forms')
        os.makedirs(forms_folder, exist_ok=True)
        #Создание названия
        registration_date_str = req.registration_date.strftime('%Y%m%d')
        duplicate_key = f"new_{req.act_number}_{registration_date_str}"
        #Поиск с таким же названием для избежания дублирования
        existing_file = None
        if os.path.exists(forms_folder):
            for filename in os.listdir(forms_folder):
                if filename.startswith('Акт_о_подаче_заявки_') and filename.endswith('.html'):
                    if duplicate_key in filename:
                        existing_file = filename
                        break
        #Если файл уже существует, то его открывает
        if existing_file:
            #Номер акта берется из имени
            match = re.search(r'_(\d+)\.html$', existing_file)
            act_number = int(match.group(1)) if match else 1
            context = {
                'request': req,
                'organization_name': 'ГБУЗ РХ «Абаканская межрайонная клиническая больница»',
                'print_date': timezone.now().strftime('%d.%m.%Y %H:%M'),
                'act_number': act_number,
                'existing_file': True,
            }
            return render(request, 'print_new_request.html', context)
        #Поиск максимального номера акта
        max_act_number = 0
        if os.path.exists(forms_folder):
            for filename in os.listdir(forms_folder):
                if filename.startswith('Акт_о_подаче_заявки_') and filename.endswith('.html'):
                    match = re.search(r'_(\d+)\.html$', filename)
                    if match:
                        num = int(match.group(1))
                        if num > max_act_number:
                            max_act_number = num
        new_act_number = max_act_number + 1
        # Сохранение в HTML файл
        context = {
            'request': req,
            'organization_name': 'ГБУЗ РХ «Абаканская межрайонная клиническая больница»',
            'print_date': timezone.now().strftime('%d.%m.%Y'),
            'act_number': new_act_number,
            'existing_file': False,
        }
        from django.template.loader import render_to_string
        html_string = render_to_string('print_new_request.html', context)
        filename = f"Акт_о_подаче_заявки_{new_act_number}_{req.act_number}_{registration_date_str}.html"
        file_path = os.path.join(forms_folder, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_string)
        return render(request, 'print_new_request.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')

# --------------------------------------------------------------
# ПЕЧАТЬ ВЫПОЛНЕННОЙ ЗАЯВКИ (ТЕХНИК, АДМИНИСТРАТОР))
def print_completed_request(request, request_id):
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    user_role = request.session.get('user_role', '')
    if user_role not in ['Техник', 'Администратор']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        req = get_object_or_404(RequestFix, act_number=request_id)
        #Проверка что-бы заявка уже была завершена
        if req.repair_stage.name != 'Завершена':
            messages.error(request, 'Печать доступна только для заявок с этапом ремонта "Завершена"')
            return redirect('show_technician')
        #Проверка существует ли уже файл
        forms_folder = os.path.join(settings.MEDIA_ROOT, 'request_forms')
        os.makedirs(forms_folder, exist_ok=True)
        #Новое значение
        completion_date_str = req.completion_date.strftime('%Y%m%d') if req.completion_date else 'no_date'
        duplicate_key = f"completed_{req.act_number}_{completion_date_str}"
        # Поиск существующего
        existing_file = None
        if os.path.exists(forms_folder):
            for filename in os.listdir(forms_folder):
                if filename.startswith('Акт_об_выполнении_Заявки_') and filename.endswith('.html'):
                    if duplicate_key in filename:
                        existing_file = filename
                        break
        #Если уже есть файл, то открывается он
        if existing_file:
            match = re.search(r'_(\d+)\.html$', existing_file)
            act_number = int(match.group(1)) if match else 1
            context = {
                'request': req,
                'organization_name': 'ГБУЗ РХ «Абаканская межрайонная клиническая больница»',
                'print_date': timezone.now().strftime('%d.%m.%Y %H:%M'),
                'act_number': act_number,
                'existing_file': True,
            }
            return render(request, 'print_completed_request.html', context)
        # Поиск максимального номера акта
        max_act_number = 0
        if os.path.exists(forms_folder):
            for filename in os.listdir(forms_folder):
                if filename.startswith('Акт_об_выполнении_Заявки_') and filename.endswith('.html'):
                    match = re.search(r'_(\d+)\.html$', filename)
                    if match:
                        num = int(match.group(1))
                        if num > max_act_number:
                            max_act_number = num
        new_act_number = max_act_number + 1
        #Сохранение в HTML
        context = {
            'request': req,
            'organization_name': 'ГБУЗ РХ «Абаканская межрайонная клиническая больница»',
            'act_number': new_act_number,
            'existing_file': False,
        }
        from django.template.loader import render_to_string
        html_string = render_to_string('print_completed_request.html', context)
        filename = f"Акт_об_выполнении_Заявки_{new_act_number}_{req.act_number}_{completion_date_str}.html"
        file_path = os.path.join(forms_folder, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_string)
        return render(request, 'print_completed_request.html', context)
    #Обработка ошибок
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')

# --------------------------------------------------------------
# СОХРАНЕНИЕ ПЕЧАТНОЙ ФОРМЫ В ПАПКУ
def save_request_form_to_folder(request, request_id):
    #Проверка авторизации и роли
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Необходимо авторизоваться'}, status=403)
    if request.session.get('user_role') not in ['Техник', 'Администратор']:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    try: # Получение заявки
        req = get_object_or_404(RequestFix.objects.select_related(
            'requester', 'assigned_technician', 'equipment'
        ).prefetch_related('used_spare_parts', 'used_services'), act_number=request_id, delete_date__isnull=True)
        forms_folder = os.path.join(settings.MEDIA_ROOT, 'request_forms')
        os.makedirs(forms_folder, exist_ok=True)
        # Проверка на дубликат
        completion_date_str = req.completion_date.strftime('%Y%m%d') if req.completion_date else 'no_date'
        duplicate_key = f"completed_{req.act_number}_{completion_date_str}"
        existing_file = None
        if os.path.exists(forms_folder):
            for filename in os.listdir(forms_folder):
                if filename.startswith('Акт_об_выполнении_Заявки_') and filename.endswith('.pdf'):
                    if duplicate_key in filename:
                        existing_file = filename
                        break
        #Если файл уже существует
        if existing_file:
            return JsonResponse({
                'success': True,
                'file_path': f'/media/request_forms/{existing_file}',
                'existing': True
            })
        #Поиск максимального номера
        max_act_number = 0
        if os.path.exists(forms_folder):
            for filename in os.listdir(forms_folder):
                if filename.startswith('Акт_об_выполнении_Заявки_') and filename.endswith('.pdf'):
                    match = re.search(r'_(\d+)\.html$', filename)
                    if match:
                        num = int(match.group(1))
                        if num > max_act_number:
                            max_act_number = num
        new_act_number = max_act_number + 1
        #Создание в HTML
        html_string = render_to_string('print_completed_request.html', {
            'request': req,
            'organization_name': 'ГБУЗ РХ «Абаканская межрайонная клиническая больница»',
            'print_date': timezone.now().strftime('%d.%m.%Y %H:%M'),
            'act_number': new_act_number,
        })
        # Сохранение файла
        filename = f"Акт_об_выполнении_Заявки_{new_act_number}_{req.act_number}_{completion_date_str}.pdf"
        file_path = os.path.join(forms_folder, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_string)
        return JsonResponse({
            'success': True,
            'file_path': f'/media/request_forms/{filename}',
            'existing': False,
            'act_number': new_act_number
        })
    #Обработка ошибок
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)