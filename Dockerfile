FROM python:3.12.14-slim-bookworm
WORKDIR /app
RUN useradd --uid 10001 --create-home faro
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock
COPY --chown=faro:faro . /app
RUN pip install --no-deps --no-build-isolation . && mkdir -p data reports && chown -R faro:faro data reports
USER faro
ENV FARO_HOME=/app DBT_SEND_ANONYMOUS_USAGE_STATS=false
ENTRYPOINT ["faro"]
CMD ["demo"]

