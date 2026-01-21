FROM mcr.microsoft.com/playwright/python:v1.38.0-jammy

ENV LAMBDA_TASK_ROOT=/var/task \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp

WORKDIR ${LAMBDA_TASK_ROOT}

RUN pip install --no-cache-dir awslambdaric

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lambda_function.py ./

ENTRYPOINT ["/usr/bin/python3", "-m", "awslambdaric"]
CMD ["lambda_function.lambda_handler"]
