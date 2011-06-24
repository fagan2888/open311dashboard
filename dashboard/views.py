from open311dashboard.settings import CITY
from open311dashboard.dashboard.models import Request

from django.http import HttpResponse, HttpRequest
from django.template import Context
from django.shortcuts import render
from django.db.models import Count
from django.core import serializers

from open311dashboard.dashboard.utils import str_to_day, day_to_str, \
    date_range

import json
import datetime
import qsstats

def index(request):
    return render(request,'index.html')

def city(request):
    request_list = Request.objects.all()[:10]
    c = Context({
        'request_list': request_list,
        'city': CITY['NAME'],
        })
    return render(request, 'city.html', c)

# API Views
def ticket_days(request, ticket_status="opened", start=None, end=None,
        num_days=None):
    '''Returns JSON with the number of opened/closed tickets in a specified
    date range'''
    if ticket_status == "opened":
        request = Request.objects.all()
        stats = qsstats.QuerySetStats(request, 'requested_datetime')
    elif ticket_status == "closed":
        request = Request.objects.filter(status="Closed")
        stats = qsstats.QuerySetStats(request, 'updated_datetime')

    # If no start or end variables are passed, do the past 30 days. If one is
    # passed, check if num_days and do the past num_days. If num_days isn't
    # passed, just do one day. Else, do the range.
    if start == None and end == None:
        end = datetime.date.today()
        start = end - datetime.timedelta(days=30)
    elif end != None and num_days != None:
        end = str_to_day(end)
        start = end - datetime.timedelta(days=int(num_days))
    elif end != None:
        end = str_to_day(end)
        start = end
    else:
        start = str_to_day(start)
        end = str_to_day(end)

    raw_data = stats.time_series(start, end, engine='postgres')
    data = []

    for row in raw_data:
        temp_data = {'date': day_to_str(row[0]), 'count': row[1]}
        data.append(temp_data)

    json_data = json.dumps(data)

    return HttpResponse(json_data, content_type='application/json')

# Get service_name stats for a range of dates
def ticket_day(request, begin=day_to_str(datetime.date.today()), end=None):
    if end == None:
        key = begin
    else:
        key = "% - %" % [begin, end]

    # Request and group by service_name.
    requests = Request.objects \
            .filter(requested_datetime__range=date_range(begin, end)) \
            .values('service_name').annotate(count=Count('service_name'))

    data = {key: [item for item in requests]}
    json_data = json.dumps(data)

    return HttpResponse(json_data, content_type='application/json')

# List requests in a given date range
def list_requests(request, begin=day_to_str(datetime.date.today()), end=None):
    requests = Request.objects \
        .filter(requested_datetime__range=date_range(begin,end))

    # TODO: FIX dthandler so it is more robust.
    dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else None
    data = [item for item in requests.values()]
    json_data = json.dumps(data, default=dthandler)
    return HttpResponse(json_data, content_type='application/json')
