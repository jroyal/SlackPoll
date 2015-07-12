FROM ubuntu:14.04

MAINTAINER James Royal <jhr.atx@gmail.com>

RUN apt-get update && apt-get -y install python-pip python-dev
RUN pip install flask==0.10.1 \
                PyYAML==3.11 \
                requests==2.5.3 \
                cloudant==0.5.9 \
                pymongo
CMD ["python", "-u", "/opt/slack-poll/slack-poll.py"]

