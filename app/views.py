from app import app
from flask import Response, request
from reporting import streams_google_line_chart_dataservice


@app.route('/dash-q/dataservice/streams_chart')
def stream_chart():
    stream = request.args.get('stream')
    return Response(response=streams_google_line_chart_dataservice.get_data(stream), mimetype="application/json")
