from app import app
from flask import Response, request
from reporting import streams_google_line_chart_dataservice as linechart
from reporting import streams_google_stackedbar_chart_dataservice as stackedbar

@app.route('/dash-q/dataservice/streams_line_chart')
def stream_chart():
    stream = request.args.get('stream')
    startdate = request.args.get('startdate')
    platform = request.args.get('platform')
    print "Platform {}".format(platform)
    return Response(response=linechart.get_data(stream, platform if platform != "" else None, startdate), mimetype="application/json")


@app.route('/dash-q/dataservice/streams_bar_chart')
def streams_bar_chart():
    return Response(response=stackedbar.get_data(), mimetype="application/json")
