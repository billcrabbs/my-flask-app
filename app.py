# app.py
from flask import Flask, request, Response
import os
import time
from prometheus_client import generate_latest, Counter, Histogram, Gauge
import json
import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

logging.basicConfig(level=logging.INFO)
logging.getLogger("opentelemetry").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

resource = Resource.create({
    "service.name": "my-flask-app",
    "service.version": "1.1",
    "env": "production"
})

provider = TracerProvider(resource=resource)
print("🔍 OTEL_EXPORTER_OTLP_ENDPOINT:", os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
span_exporter = OTLPSpanExporter()


provider.add_span_processor(BatchSpanProcessor(span_exporter))
trace.set_tracer_provider(provider)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP Request Latency', ['method', 'endpoint'])
IN_PROGRESS_REQUESTS = Gauge('http_requests_in_progress', 'In-progress HTTP Requests', ['method', 'endpoint'])

@app.route('/')
def hello():
    start_time = time.time()
    method = request.method
    endpoint = '/'

    IN_PROGRESS_REQUESTS.labels(method=method, endpoint=endpoint).inc()

    try:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("hello-endpoint-processing") as span:
            span.set_attribute("http.method", method)
            span.set_attribute("http.path", endpoint)


            message = "Hello from Flask on GKE! (Version 1.1 with Tracing)"

            log_entry = {
                "severity": "INFO",
                "message": message,
                "service_name": "my-flask-app",
                "http_method": method,
                "http_path": endpoint,
                "request_id": request.headers.get('X-Request-ID', 'N/A')
            }
            logger.info(json.dumps(log_entry))

            return message
    finally:
        IN_PROGRESS_REQUESTS.labels(method=method, endpoint=endpoint).dec()
        REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(time.time() - start_time)

@app.route('/metrics')
def metrics():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test-span-for-metrics"):
        print("📦 Created test span for /metrics")
    return Response(generate_latest(), mimetype='text/plain')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

