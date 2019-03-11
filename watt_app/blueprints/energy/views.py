from flask import (
    Blueprint,
    redirect,
    request,
    url_for,
    render_template
    )


from watt_app.extensions import db
from watt_app.blueprints.energy import models
import datetime
import json
import arrow
import xively

energy = Blueprint('energy', __name__,
                   template_folder='templates')

KWH_COST = .297
TIME_OFFSET = datetime.timedelta(hours=4)

XI_API_KEY = xively.XivelyAPIClient(
    "7Zx8Qepgh2lXlgVSxYMGVOjo1zpwj9b9yonnoQrsyIFOML02")

XI_FEED = XI_API_KEY.feeds.get(2134785632)


def xiv(watts, time):
    """Helper method that allows sensor() to send wattage data to xively.com"""
    XI_FEED.datastreams = [
        xively.Datastream(id="wattvision", current_value=watts, at=time)]
    XI_FEED.update()


def query_from(start, end):
    begin = start + TIME_OFFSET
    print("begin at {}".format(_jinja2_filter_datetime(begin)))
    finish = end + TIME_OFFSET
    print("Queried period is {} to {}".format(_jinja2_filter_datetime(begin),
                                              _jinja2_filter_datetime(finish)))
    return models.Events.query.filter(models.Events.timestamp <
                                      finish, models.Events.timestamp >
                                      begin).all()


def interval_usage(start, end):
    """provides total energy usage for an interval with given start
    and end date"""
    results = query_from(start, end)
    energy_used = results[-1].watthours - results[0].watthours
    print("{}-{}={}".format(results[-1].watthours, results[0].watthours,
                            results[-1].watthours - results[0].watthours))
    return energy_used, energy_used * KWH_COST / 1000


@energy.route('/monthly/', methods=['GET'])
def monthly_usage():
    """provides total energy usage starting from the 5th of current month
    until the current day. This will be called by a getJSON javascript funtion
    from index.html and will run as a celery background process. This was
    briefly tabulated using celery task queues."""
    fifth_of_month = datetime.datetime(datetime.datetime.now().year,
                                       datetime.datetime.now().month, 5)
    today = datetime.datetime.today()

    try:
        # An out of range exception will occur with this code when it runs
            # at the beginning of a new month
            total = interval_usage(fifth_of_month, today)
            kwh = total[0]/1000
            usage = round(total[1], 2)
    except Exception as e:
            print(e)
            # "This except clauses sets the month as the previous month."
            fifth_of_month = \
                datetime.datetime(datetime.datetime.now().year,
                                  datetime.datetime.now().month-1, 5)
            total = interval_usage(fifth_of_month, today)
            kwh = total[0]/1000
            usage = round(total[1], 2)

    kwh = total[0]/1000
    usage = round(total[1], 2)
    return json.dumps({'kilowatts': kwh, 'total_cost': usage})


@energy.route('/yesterday/', methods=['GET'])
def yesterday():
    """provides energy costs for previous day"""
    yesterday = \
        datetime.datetime.fromordinal(datetime.date.today().toordinal() - 1)
    today = datetime.datetime.fromordinal(datetime.date.today().toordinal())
    usage = round(interval_usage(yesterday, today)[1], 2)
    return json.dumps({'yesterday': usage})


def daily_usage(start, end):
    """provides a daily breakdown of energy usage given start and end
    dates. Start and end must be datetime objects"""
    delta = end - start
    results = []
    for i in range(delta.days):
        results.append(interval_usage(start + datetime.timedelta(days=i),
                                      start + datetime.timedelta(days=i + 1)))
    return results


@energy.route('/init_db')
def init_db():
    """
    Initializes database.
    """
    # db.drop_all()
    # db.create_all()
    return None


@energy.route('/this_month', methods=['GET'])
def this_month():
    """
    Applies daily_usage() to every day this month starting with the fifth of
    the month.
    """
    fifth_of_month = datetime.datetime(datetime.datetime.now().year,
                                       datetime.datetime.now().month, 5)
    today = datetime.datetime.today()
    usage_list = daily_usage(fifth_of_month, today)
    usage = [day for day in usage_list]
    return render_template('base.html', usage=usage)


def hourly_usage(begin):
    """provides an hourly breakdown of energy usage for current given
    day. Supplied day must be a datetime object."""
    start = datetime.datetime(begin.year, begin.month, begin.day)
    end = datetime.datetime(begin.year, begin.month, begin.day, 23)
    delta = end - start
    results = []
    for i in range(int(delta.seconds / 3600) + 1):
        try:
            results.append(interval_usage(start + datetime.timedelta(hours=i),
                                          start +
                                          datetime.timedelta(hours=i + 1)))
        except Exception as e:
            # the variable end is set to hour 23 of given day.
            # if current day is queried this will throw an exception.
            print(e)
    return results


def hourly_breakdown(begin):
    """Prints a formatted version of hourly_usage()"""
    total = 0
    for hour in enumerate(hourly_usage(begin)):
        total += hour[1][1]
        print(hour, total)


@energy.route('/today/', methods=['GET'])
def today():
    """displays hourly_usage with today's date """
    hours = hourly_usage(datetime.datetime.today())
    return render_template('today.html', hours=hours)


@energy.route('/usage/', methods=['GET'])
def usage():
    today = datetime.datetime.now().date()
    start = datetime.datetime(today.year, today.month, today.day) + TIME_OFFSET
    events = models.Events.query.filter(models.Events.timestamp >
                                        start).all()
    events.reverse()
    print('+++++++++++++++++++++++++++++++++++')
    print(today, start)
    print(events)
    # print(models.Events.query.filter(models.Events.timestamp == start).all())
    # print(dir(models.Events.query.filter()))
    print('+++++++++++++++++++++++++++++++++++')
    energy_used = events[0].watthours - events[-1].watthour
    return json.dumps({'cost': round(energy_used * KWH_COST / 1000, 2),
                      'energy_used': energy_used})


@energy.route('/sensor/', methods=['POST'])
def sensor():
    watts = float(request.form.getlist('w')[0])
    watthours = float(request.form.getlist('wh')[0])
    raw_time = datetime.datetime.strptime(request.form.getlist('t')[0],
                                          "%Y-%m-%dT%H:%M:%S")
    # payload = json.dumps({"sensor_id": SENSOR_ID, "api_id": API_ID,
    # "api_key": API_KEY, "watts": watts, 'watthours': watthours})
    # url = 'https://www.wattvision.com/api/v0.2/elec'
    print(watts)
    try:
        current = models.Events(timestamp=raw_time, watts=watts,
                                watthours=watthours)
        db.session.add(current)
        db.session.commit()

    except Exception as e:
        print(e)
        db.session.rollback()

    try:
        xiv(watts, arrow.get(raw_time).to('US/Eastern').datetime)
    except Exception as e:
        print(e)
    return 'OK'


@energy.route('/', methods=['GET', 'POST'])
def index():
    # db.configure_mappers()
    # db.drop_all()
    # db.create_all()

    print("************************************************")
    # print(dir(db))
    print(db)
    print("************************************************")
    today = datetime.datetime.now().date()
    start = datetime.datetime(today.year, today.month, today.day) + TIME_OFFSET
    events = models.Events.query.filter(models.Events.timestamp > start).all()
    events.reverse()
    print (models.Events.query.all())
    # print(models.Events.query(models.Events).first())
    current = json.loads(usage())
    # return render_template('app.html', events=events,
    #    cost=current['cost'],
    #    energy=current['energy_used'],
    # monthly = round(deferred.wait()[1],2)
    #    )
    return render_template('layouts/app.html')


@energy.app_template_filter('datetime')
def _jinja2_filter_datetime(date):
    return arrow.get(date).to('local').strftime('%I:%M:%S %p %m/%d ')
