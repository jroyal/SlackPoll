FROM python:2.7-slim

MAINTAINER James Royal <jhr.atx@gmail.com>

ADD . /code
WORKDIR /code
RUN pip install -r requirements.txt
CMD ["python", "-u", "slack-poll.py"]

