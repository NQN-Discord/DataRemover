FROM python:3.7
RUN apt-get update \
 && apt-get -y install cron

COPY requirements.txt requirements.txt

RUN pip install -U pip wheel setuptools \
 && pip install -r requirements.txt

COPY crontab /etc/cron.d/data_remover

RUN chmod 0644 /etc/cron.d/data_remover

# Apply cron job
RUN crontab /etc/cron.d/data_remover

ADD . .

CMD ["cron", "-f"]