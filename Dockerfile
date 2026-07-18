FROM python:3.12-alpine

WORKDIR /tg

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY ./tg_bot.py .
COPY ./requirements.txt .
COPY ./run.sh .

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

RUN chmod +x ./run.sh

CMD ["./run.sh"]