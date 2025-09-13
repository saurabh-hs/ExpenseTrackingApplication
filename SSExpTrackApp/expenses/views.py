from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from openpyxl import Workbook
from .models import Expense, Category
from django.contrib import messages
from django.core.paginator import Paginator
import json
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from userpreferences.models import UserPreferences
import datetime
import csv
from django.template.loader import render_to_string
# from weasyprint import HTML
import tempfile
from django.db.models import Sum

def search_expenses(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText', "").strip()

        try:
            # Try converting search string to float for amount matching
            amount_value = float(search_str)
        except (ValueError, TypeError):
            amount_value = None

        expenses = Expense.objects.filter(owner=request.user).filter(
            Q(date__istartswith=search_str) |
            Q(description__icontains=search_str) |
            Q(category__icontains=search_str) |
            (Q(amount=amount_value) if amount_value is not None else Q())
        ).distinct()

        data = expenses.values()
        return JsonResponse(list(data), safe=False)

@login_required(login_url='/authentication/login')
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
def index(request):
    categories = Category.objects.all()
    expenses = Expense.objects.filter(owner=request.user)
    paginator = Paginator(expenses, 5)  # Show 5 expenses per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    user_preferences, created = UserPreferences.objects.get_or_create(
        user=request.user,
        defaults={"currency": "INR"}  
    )
    context = {
        'expenses': expenses,
        'page_obj': page_obj,
        'currency': user_preferences.currency
    }
    return render(request, 'expenses/index.html', context)

def add_expense(request):
    categories = Category.objects.all()
    context = {
        'categories': categories,
        'values': request.POST
    }
    if request.method == 'GET':
        return render(request, 'expenses/add-expense.html', context)

    if request.method == 'POST':
        amount = request.POST['amount']
        description = request.POST['description']
        category = request.POST['category']
        expense_date = request.POST['expense_date']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/add-expense.html', context)

        if not description:
            messages.error(request, 'Description is required')
            return render(request, 'expenses/add-expense.html', context)
        
        if not category:
            messages.error(request, 'Category is required')
            return render(request, 'expenses/add-expense.html', context)
        
        if not expense_date:
            messages.error(request, 'Date is required')
            return render(request, 'expenses/add-expense.html', context)
        
        Expense.objects.create(amount=amount, description=description, category=category, owner=request.user, date=expense_date)
        messages.success(request, 'Expense added successfully')
        return redirect('expenses')
    
def expense_edit(request, id):
    categories = Category.objects.all()
    expense = Expense.objects.get(pk=id)
    context = {
        'expense': expense,
        'values' : expense,
        'categories' : categories
    }
    if request.method == 'GET':
        return render(request, 'expenses/edit-expense.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']
        description = request.POST['description']
        category = request.POST['category']
        expense_date = request.POST['expense_date']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/edit-expense.html', context)

        if not description:
            messages.error(request, 'Description is required')
            return render(request, 'expenses/edit-expense.html', context)
        
        expense.owner = request.user
        expense.amount = amount
        expense.description = description
        expense.category = category
        expense.date = expense_date
        expense.save()
        messages.success(request, 'Expense updated successfully')
        return redirect('expenses')
    
def delete_expense(request, id):
    expense = Expense.objects.get(pk=id)
    expense.delete()
    messages.success(request, 'Expense deleted successfully')
    return redirect('expenses')

def expense_category_summary(request):
    todays_date = datetime.date.today()
    six_months_ago = todays_date - datetime.timedelta(days=30*6)
    expenses = Expense.objects.filter(date__gte=six_months_ago, date__lte=todays_date, owner=request.user)
    finalrep = {}

    def get_category(expense):
        return expense.category
    category_list = list(set(map(get_category, expenses)))

    def get_expense_category_amount(category):
        amount = 0
        filtered_by_category = expenses.filter(category=category)

        for item in filtered_by_category:
            amount += item.amount
        return amount

    for x in expenses:
        for y in category_list:
            finalrep[y] = get_expense_category_amount(y)
    
    return JsonResponse({'expense_category_data': finalrep}, safe=False)

def stats_view(request):
    return render(request, 'expenses/stats.html')

def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=Expenses '+datetime.datetime.now().strftime("%d-%m-%Y")+'.csv'
   
    writer = csv.writer(response)
    writer.writerow(['Amount', 'Description', 'Category', 'Date'])

    expenses = Expense.objects.filter(owner=request.user)
    for expense in expenses:
        writer.writerow([expense.amount, expense.description, expense.category, expense.date])
    return response

def export_excel(request):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Expenses '+datetime.datetime.now().strftime("%d-%m-%Y")+'.xlsx'

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Expenses'

    # Write the header
    worksheet.append(['Amount', 'Description', 'Category', 'Date'])

    expenses = Expense.objects.filter(owner=request.user)
    for expense in expenses:
        worksheet.append([expense.amount, expense.description, expense.category, expense.date])

    workbook.save(response)
    return response

# def export_pdf(request):
#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = 'inline; attachment; filename=Expenses '+datetime.datetime.now().strftime("%d-%m-%Y")+'.pdf'

#     expenses = Expense.objects.filter(owner=request.user)
#     total = expenses.aggregate(Sum('amount'))

#     html_string = render_to_string('expenses/pdf-output.html', {'expenses': expenses, 'total': total['amount__sum']})
#     html = HTML(string=html_string)

#     result = html.write_pdf()
#     with tempfile.NamedTemporaryFile(delete=True) as output:
#         output.write(result)
#         output.flush()
#         output = open(output.name, 'rb')
#         response.write(output.read())

#     return response