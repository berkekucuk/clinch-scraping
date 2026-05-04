FROM public.ecr.aws/lambda/python:3.12

ENV TLDEXTRACT_CACHE=/tmp/.tldextract_cache

COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip install --no-cache-dir -r requirements.txt

COPY . ${LAMBDA_TASK_ROOT}

CMD [ "lambda_function.handler" ]
