import os
import logging

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

logger = logging.getLogger(__name__)

def init_tracer():
    """
    Initializes and configures the OpenTelemetry tracer based on environment variables.
    """
    resource = Resource(attributes={
        "service.name": "cards-cartel-bot"
    })

    provider = TracerProvider(resource=resource)

    exporter_type = os.getenv("OTEL_EXPORTER_TYPE", "CONSOLE").upper()

    if exporter_type == "JAEGER":
        # Use environment variable for endpoint, default to localhost for local testing
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        otlp_exporter = OTLPSpanExporter(
            endpoint=endpoint,
            insecure=True
        )
        processor = BatchSpanProcessor(otlp_exporter)
        logger.info(f"Tracer configured to export to Jaeger at {endpoint}.")
    else:
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        logger.info("Tracer configured to export to CONSOLE. Set OTEL_EXPORTER_TYPE=JAEGER to use Jaeger.")

    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()
    logger.info("HTTPX client instrumented for automatic tracing.")

def get_tracer(name: str):
    return trace.get_tracer(name)