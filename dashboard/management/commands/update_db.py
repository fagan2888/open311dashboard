from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from open311dashboard.dashboard.models import City, Request
from dateutil import parser

from optparse import make_option
import urllib2
import urllib
import datetime as dt
import xml.dom.minidom as dom

ONE_DAY = dt.timedelta(days=1)

def get_time_range(on_day=None):
    if on_day is None:
        on_day = dt.datetime.utcnow() - ONE_DAY

    # End at the begining of on_day; start at the beginning of the previous
    # day.
    end = on_day.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - ONE_DAY

    return (start, end)

def parse_date(date_string):
    new_date = parser.parse(date_string)
    return new_date.strftime("%Y-%m-%d %I:%M")

def validate_dt_value(datetime):
    """
    Verify that the given datetime will not cause problems for the Open311 API.
    For the San Francisco Open311 API, start and end dates are ISO8601 strings,
    but they are expected to be a specific subset.
    """
    if datetime.microsecond != 0:
        raise ValueError('Microseconds on datetime must be 0: %s' % datetime)

    if datetime.tzinfo is not None:
        raise ValueError('Tzinfo on datetime must be None: %s' % datetime)

def get_requests_from_SF(start,end,page,city):
    """
    Retrieve the requests from the San Francisco 311 API within the time range
    specified by the dates start and end.

    Returns a stream containing the content from the API call.
    """

    validate_dt_value(start)
    validate_dt_value(end)

    #url = r'https://open311.sfgov.org/dev/Open311/v2/requests.xml' #dev
    url = city.url
    query_data = {
        'start_date' : start.isoformat() + 'Z',
        'end_date' : end.isoformat() + 'Z',
        'jurisdiction_id' : city.jurisdiction_id,
    }

    if page > 0:
        query_data['page'] = page

    query_str = urllib.urlencode(query_data)
    print url + '?' + query_str

    requests_stream = urllib2.urlopen(url + '?' + query_str)
    return requests_stream

def parse_requests_doc(stream):
    """
    Converts the given file-like object, which presumably contains a service
    requests document, into a list of request dictionaries.
    """

    import xml.dom

    xml_string = stream.read()

    columns = [] #holding columns for a day's worth of incident data
    values = [] #holding values for a day's worth of incident data

    try:
        requests_root = dom.parseString(xml_string).documentElement
    except ExpatError:
        print(xml_string)
        raise

    if len(requests_root.childNodes) < 1:
        return False

    for request_node in requests_root.childNodes:
        indiv_columns_list = []
        indiv_values_list = []

        if request_node.nodeType != xml.dom.Node.ELEMENT_NODE:
            continue

        if request_node.tagName != 'request':
            raise Exception('Unexpected node: %s' % requests_root.toprettyxml())

        for request_attr in request_node.childNodes:
            if request_attr.childNodes:
                if request_attr.tagName.find('datetime') > -1:
                    request_attr.childNodes[0].data = parse_date(request_attr.childNodes[0].data)

                if request_attr.tagName in Request._meta.get_all_field_names():
                    indiv_columns_list.append(request_attr.tagName)
                    indiv_values_list.append(request_attr.childNodes[0].data)

        columns.append(indiv_columns_list)
        values.append(indiv_values_list)
    return (columns,values)

def insert_data(requests, city):
    '''
    Takes the requests tuple, turns it into a dictionary, and saves it to the
    Requests model in django.
    '''

    columns,values = requests

    for i in range(len(values)):

        # Put the key-value pairs into a dictionary and then an arguments list.
        request_dict = dict(zip(columns[i], values[i]))

        # Check if the record already exists.
        try:
            exists = Request.objects.get(service_request_id = request_dict['service_request_id'],
                                        service_code = request_dict['service_code'])
            request_dict['id'] = exists.id
        except:
            pass

        r = Request(**request_dict)

        # Hardcoded for now.
        r.city_id = city.id

        try:
            r.save()
            print "Successfully saved %s" % r.service_request_id
        except ValidationError, e:
            raise CommandError('Request "%s" does not validate correctly\n %s' %
                    (r.service_request_id, e))

def process_requests(start, end, page, city):
    requests_stream = get_requests_from_SF(start, end, page, city)
    requests = parse_requests_doc(requests_stream)

    if requests != False:
        insert_data(requests, city)

        if page != 0:
            page = page+1
            process_requests(start, end, page, city)
    return requests

def handle_open_requests(city):
    url = city.url
    open_requests = Request.objects.all().filter(status__iexact="open")
    length = len(open_requests)
    print "Checking %d tickets for changed status" % length

    for index in xrange(0, length, 10):
        data = []
        for i in xrange(0, 10):
            data.append(open_requests[index + i].service_request_id)

        query_data = {
                'jurisdiction_id': city.jurisdiction_id,
                'service_request_id': ','.join(data)
                }

        query_str = urllib.urlencode(query_data)
        print url + '?' + query_str

        requests_stream = urllib2.urlopen(url + '?' + query_str)
        try:
            print "Parsing open docs"
            requests = parse_requests_doc(requests_stream)
            print "Saving..."
            insert_data(requests)
        except:
            print "Could not process updates."

# At runtime...
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
            make_option('--checkopen', dest='open',
                default=False, help="Boolean to check open tickets"),
            make_option('--default', dest='default',
                default=True, help="Boolean to execute default functionality"),
            )

    help = """Update and seed the database from data retrieved from the API.
    Makes calls one day at a time"""

    def handle(self, *args, **options):
        cities = City.objects.all()

        for city in cities:
            if options['default'] is True:
                if len(args) >= 1:
                    start, end = get_time_range(dt.datetime.strptime(args[0], '%Y-%m-%d'))
                else:
                    start, end = get_time_range()

                if len(args) >= 2:
                    num_days = int(args[1])
                    print(args[1])
                else:
                    num_days = 1

                if city.paginated:
                    page = 1
                else:
                    page = False

                for _ in xrange(num_days):
                    requests = process_requests(start, end, page, city)

                    start -= ONE_DAY
                    end -= ONE_DAY

                    print start

            if options['open'] is True:
                handle_open_requests()


