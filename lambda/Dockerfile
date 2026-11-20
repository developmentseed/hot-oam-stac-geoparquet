FROM public.ecr.aws/lambda/python:3.13
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY requirements.txt /tmp/requirements.txt
RUN uv pip install --no-cache --compile-bytecode --target "${LAMBDA_TASK_ROOT}" \
    -r /tmp/requirements.txt

COPY handler.py "${LAMBDA_TASK_ROOT}/handler.py"

CMD ["handler.handler"]
