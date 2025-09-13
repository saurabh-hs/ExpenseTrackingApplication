import json
from django.http import JsonResponse
from django.shortcuts import render, redirect
from userpreferences.models import UserPreferences
from .models import Source, UserIncome
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q


# Create your views here.

def search_income(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText', "").strip()

        try:
            # Try converting search string to float for amount matching
            amount_value = float(search_str)
        except (ValueError, TypeError):
            amount_value = None

        incomes = UserIncome.objects.filter(owner=request.user).filter(
            Q(date__istartswith=search_str) |
            Q(description__icontains=search_str) |
            Q(source__icontains=search_str) |
            (Q(amount=amount_value) if amount_value is not None else Q())
        ).distinct()

        data = incomes.values()
        return JsonResponse(list(data), safe=False)


@login_required(login_url='/authentication/login')
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
def index(request):
    sources = Source.objects.all()
    income = UserIncome.objects.filter(owner=request.user)
    paginator = Paginator(income, 5)  # Show 5 income records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    currency = UserPreferences.objects.get(user=request.user).currency
    context = {
        'income': income,
        'page_obj': page_obj,
        'currency': currency
    }
    return render(request, 'income/index.html', context)

def add_income(request):
    sources = Source.objects.all()
    context = {
        'sources': sources,
        'values': request.POST
    }
    if request.method == 'GET':
        return render(request, 'income/add-income.html', context)

    if request.method == 'POST':
        amount = request.POST['amount']
        description = request.POST['description']
        source = request.POST['source']
        income_date = request.POST['income_date']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'income/add-income.html', context)

        if not description:
            messages.error(request, 'Description is required')
            return render(request, 'expenses/add-expense.html', context)
        
        if not source:
            messages.error(request, 'Source is required')
            return render(request, 'income/add-income.html', context)

        if not income_date:
            messages.error(request, 'Date is required')
            return render(request, 'income/add-income.html', context)
        
        UserIncome.objects.create(amount=amount, description=description, source=source, owner=request.user, date=income_date)
        messages.success(request, 'Record saved successfully')
        return redirect('income')
    
def income_edit(request, id):
    sources = Source.objects.all()
    income = UserIncome.objects.get(pk=id)
    context = {
        'income': income,
        'values' : income,
        'sources' : sources
    }
    if request.method == 'GET':
        return render(request, 'income/edit-income.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']
        description = request.POST['description']
        source = request.POST['source']
        income_date = request.POST['income_date']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'income/edit-income.html', context)

        if not description:
            messages.error(request, 'Description is required')
            return render(request, 'income/edit-income.html', context)

        income.owner = request.user
        income.amount = amount
        income.description = description
        income.source = source
        income.date = income_date
        income.save()
        messages.success(request, 'Income updated successfully')
        return redirect('income')

def delete_income(request, id):
    income = UserIncome.objects.get(pk=id)
    income.delete()
    messages.success(request, 'Income deleted successfully')
    return redirect('income')